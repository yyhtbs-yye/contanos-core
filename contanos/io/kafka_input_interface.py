from typing import Any, Dict, Tuple, Optional
import logging
import json
import time
import asyncio
import uuid

from abc import ABC
from asyncio import Queue

from aiokafka import AIOKafkaConsumer
from aiokafka.helpers import create_ssl_context


class KafkaInput(ABC):
    """
    Kafka message input implementation using asyncio.Queue and aiokafka.

    Config keys expected (mirrors your MQTT config where reasonable):
      - addr: "kafka://host:port"
      - topic: string or list[str]
      - group_id: kafka consumer group id (required for committed progress)
      - client_id: optional; auto-generated if not provided
      - auto_offset_reset: "latest" (default) | "earliest"
      - enable_auto_commit: bool (default True)
      - max_queue: int (default 100)
      - fetch_max_bytes / max_partition_fetch_bytes: optional performance tuning
      - security_protocol: "PLAINTEXT" | "SASL_PLAINTEXT" | "SSL" | "SASL_SSL"
      - sasl_mechanism: e.g. "PLAIN" | "SCRAM-SHA-256" | "SCRAM-SHA-512" | "OAUTHBEARER"
      - username / password: for SASL/PLAIN or SCRAM
      - ssl_cafile / ssl_certfile / ssl_keyfile: for SSL
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        # ---- helpers to sanitize config values ----
        def _as_int(v: Any, default: Optional[int] = None) -> Optional[int]:
            if v is None:
                return default
            if isinstance(v, (int,)) and not isinstance(v, bool):
                return v
            s = str(v).strip()
            if s == "" or s.lower() == "none":
                return default
            return int(s)
        def _as_bool(v: Any, default: bool) -> bool:
            if v is None:
                return default
            if isinstance(v, bool):
                return v
            return str(v).strip().lower() in {"1", "true", "yes", "on"}


        self.addr: str = config["addr"]
        proto, rest = self.addr.split("://", 1)
        if proto != "kafka":
            raise ValueError(f"addr must start with kafka://, got {proto}://")

        host, port = rest.split(":")
        self.bootstrap_servers = f"{host}:{int(port)}"

        self.topics = config["topic"]
        if isinstance(self.topics, str):
            self.topics = [self.topics]

        self.group_id: Optional[str] = config.get("group_id")
        if not self.group_id:
            # Kafka works without a group_id, but you won't commit offsets; better to require it.
            raise ValueError("group_id is required for KafkaInput")

        base_id = config.get("client_id", f"kafka_input_{int(time.time())}")
        unique_suffix = str(uuid.uuid4())[:8]
        self.client_id = f"{base_id}_{unique_suffix}"

        self.auto_offset_reset = config.get("auto_offset_reset", "latest")
        self.enable_auto_commit = _as_bool(config.get("enable_auto_commit"), True)

        # Asyncio constructs
        self.message_queue: Queue = Queue(maxsize=_as_int(config.get("max_queue"), 100))

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._consumer_task: Optional[asyncio.Task] = None

        # Security (all optional)
        self.security_protocol = config.get("security_protocol", 'PLAINTEXT')  # None -> defaults to PLAINTEXT in aiokafka
        self.sasl_mechanism = config.get("sasl_mechanism")
        self.username = config.get("username")
        self.password = config.get("password")
        self.ssl_cafile = config.get("ssl_cafile")
        self.ssl_certfile = config.get("ssl_certfile")
        self.ssl_keyfile = config.get("ssl_keyfile")

        # Perf tuning (optional)
        self.fetch_max_bytes = _as_int(config.get("fetch_max_bytes"))
        self.max_partition_fetch_bytes = _as_int(config.get("max_partition_fetch_bytes"))

        self.consumer: Optional[AIOKafkaConsumer] = None
        self.is_running = False

    async def initialize(self) -> bool:
        """Initialize Kafka connection and start background consume loop."""
        try:
            self._loop = asyncio.get_running_loop()

            ssl_context = None
            if (self.security_protocol or "").upper() in {"SSL", "SASL_SSL"}:
                ssl_context = create_ssl_context(
                    cafile=self.ssl_cafile,
                    certfile=self.ssl_certfile,
                    keyfile=self.ssl_keyfile,
                )

            # Build kwargs and only include optional ints if present
            consumer_kwargs = dict(
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                client_id=self.client_id,
                auto_offset_reset=self.auto_offset_reset,
                enable_auto_commit=self.enable_auto_commit,
                security_protocol=self.security_protocol,
                sasl_mechanism=self.sasl_mechanism,
                sasl_plain_username=self.username,
                sasl_plain_password=self.password,
                ssl_context=ssl_context,
                # Optionally: api_version="auto",
            )
            if self.fetch_max_bytes is not None:
                consumer_kwargs["fetch_max_bytes"] = self.fetch_max_bytes
            if self.max_partition_fetch_bytes is not None:
                consumer_kwargs["max_partition_fetch_bytes"] = self.max_partition_fetch_bytes

            self.consumer = AIOKafkaConsumer(*self.topics, **consumer_kwargs)

            await self.consumer.start()
            self.is_running = True
            logging.info(
                "Kafka consumer started",
                extra={
                    "servers": self.bootstrap_servers,
                    "topics": self.topics,
                    "group": self.group_id,
                    "client_id": self.client_id,
                    "fetch_max_bytes": self.fetch_max_bytes,
                    "max_partition_fetch_bytes": self.max_partition_fetch_bytes,
                },
            )
            # Background consumer task
            self._consumer_task = asyncio.create_task(self._consume_loop(), name=f"kafka_consume_{self.client_id}")
            return True

        except Exception as e:
            logging.error(f"Failed to initialize Kafka input: {e}", exc_info=True)
            self.is_running = False
            # Best effort stop if partially started
            try:
                if self.consumer:
                    await self.consumer.stop()
            except Exception:
                pass
            return False

    async def _consume_loop(self):
        assert self.consumer is not None
        try:
            async for record in self.consumer:
                try:
                    # record.value is bytes or None
                    if record.value is None:
                        continue

                    try:
                        payload_str = record.value.decode("utf-8")
                    except UnicodeDecodeError:
                        # Keep raw bytes if undecodable (mirrors your fallback)
                        payload = record.value
                        data = payload  # will be bytes
                    else:
                        # Skip x264 metadata (match your MQTT behavior)
                        if "x264" in payload_str:
                            continue
                        try:
                            data = json.loads(payload_str)
                        except json.JSONDecodeError:
                            data = payload_str

                    message = {
                        "payload": data,
                        "topic": record.topic,
                        "partition": record.partition,
                        "offset": record.offset,
                        "timestamp": record.timestamp / 1000.0 if record.timestamp is not None else time.time(),
                        "key": record.key.decode("utf-8", errors="ignore") if isinstance(record.key, (bytes, bytearray)) else record.key,
                        "headers": dict((k, (v.decode("utf-8", errors="ignore") if isinstance(v, (bytes, bytearray)) else v)) for k, v in (record.headers or [])),
                    }

                    # Frame id extraction (parity with MQTTInput)
                    if isinstance(message["payload"], dict):
                        frame_id = message["payload"].get("frame_id_str")
                    else:
                        frame_id = None
                    if frame_id is not None:
                        message["frame_id_str"] = frame_id

                    # Backpressure-aware put
                    await self.message_queue.put(message)

                except Exception as inner:
                    logging.error(f"Error processing Kafka record: {inner}", exc_info=True)

        except asyncio.CancelledError:
            # Normal shutdown path
            pass
        except Exception as e:
            logging.error(f"Kafka consume loop error: {e}", exc_info=True)
        finally:
            self.is_running = False

    async def read_data(self) -> Tuple[Any, Dict[str, Any]]:
        """Read a single message from the queue (with timeout)."""
        if not self.is_running:
            raise Exception("Kafka input not initialized or stopped")

        try:
            message = await asyncio.wait_for(self.message_queue.get(), timeout=5.0)
            data = message["payload"]
            metadata = {
                "frame_id_str": (data.get("frame_id_str") if isinstance(data, dict) else None),
                "topic": message.get("topic"),
                "partition": message.get("partition"),
                "offset": message.get("offset"),
                "timestamp": message.get("timestamp"),
                "key": message.get("key"),
                "headers": message.get("headers"),
                "payload_type": type(data).__name__,
            }
            self.message_queue.task_done()
            return data, metadata

        except asyncio.TimeoutError:
            raise Exception("No Kafka message received within timeout")
        except Exception as e:
            raise Exception(f"Failed to read Kafka message: {e}")

    async def cleanup(self):
        """Clean up Kafka resources."""
        # Stop consume loop first
        try:
            if self._consumer_task and not self._consumer_task.done():
                self._consumer_task.cancel()
                try:
                    await self._consumer_task
                except asyncio.CancelledError:
                    pass
        except Exception as e:
            logging.error(f"Error cancelling consumer task: {e}")

        # Stop consumer
        try:
            if self.consumer:
                await self.consumer.stop()
        except Exception as e:
            logging.error(f"Error during Kafka consumer stop: {e}")

        # Clear queue
        try:
            while not self.message_queue.empty():
                try:
                    self.message_queue.get_nowait()
                    self.message_queue.task_done()
                except asyncio.QueueEmpty:
                    break
        except Exception:
            pass

        self.is_running = False
        logging.info("Kafka input cleaned up")
