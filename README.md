# Contanos-Core

**Contanos-Core** is a lightweight Python framework that streamlines the containerization of machine learning (ML), deep learning (DL), and data visualization components using Docker. It provides a structured way to wrap various ML/DL tools into Docker containers with clear input/output interfaces, making it easier to deploy complex AI pipelines across cloud and edge environments. By using Contanos, developers can focus on their ML/DL logic while the framework handles container orchestration, standardized I/O handling, and inter-component communication.

## Project Description

Contanos-core is a minimal designed to simplify how ML and DL modules are packaged and run as microservices. The framework defines a common structure (using base classes and interfaces) for building containerized ML/DL components that can communicate seamlessly. Whether you are deploying a neural network on an edge device or orchestrating multiple AI services in the cloud, Contanos helps by:

- **Containerizing ML/DL Tools**: Each component (e.g., an object detector, a pose estimator, a data annotator, when using contanos) runs in its own Docker container with all dependencies included.
- **Standardizing Interfaces**: Every container uses clear input and output interfaces (such as MQTT messages or RTSP video streams) so that components can be easily connected in a pipeline.
- **Cloud-Edge Deployment**: The framework is lightweight and suitable for resource-constrained edge devices while remaining scalable for cloud deployments. It’s built to handle typical cloud-edge use cases, like an AI service on a server processing data from edge IoT devices.

In essence, Contanos-Core provides the boilerplate and structure needed to turn your ML/DL code into a portable containerized service with minimal effort.

## Features

- **Modular Design**: Contanos encourages a modular architecture where each functional component (e.g., a detector, tracker, or visualizer) is a self-contained module. This modularity makes it easy to develop, test, and deploy components independently or as part of a larger system.
- **Base Classes (`base_\*` Modules)**: The core of the framework is the **`base_\*` series of modules**:
  - **`base_service.py`** – A base class for service components (often called "main" services) that coordinate input and output flow and manage one or more workers.
  - **`base_worker.py`** – A base class for worker components that carry out the heavy ML/DL processing (e.g., running inference on a model). Workers handle reading input data, running the prediction, and writing outputs. The framework supports running multiple workers in parallel for scalability.
  - **`base_processor.py`** – A base class for processing units that can be used for intermediate processing or custom logic. (This can be extended if you want a component that processes data in-line without the full service/worker split.)
- **Standard Input/Output Interfaces**: Contanos comes with a set of pre-built I/O interface modules under `contanos/io`:
  - **MQTT messaging** – Interfaces for reading from and writing to MQTT topics (useful for sensor data, IoT messaging, or chaining modules via a message broker).
  - **RTSP video streams** – Interfaces to ingest video streams via RTSP (for camera input) and to output processed video or data to RTSP or other endpoints.
  - **Multi-source input** – A `MultiInputInterface` that can combine multiple input sources or streams and feed them into the processing pipeline.
  - These interfaces parse standardized connection URIs (e.g., an MQTT source might be given as a URI like `mqtt://broker:1883?topic=...`, and RTSP streams with optional parameters). This uniform approach makes configuring sources and destinations very straightforward.
- **Lightweight and Flexible**: The framework itself is lightweight (primarily Python code with minimal overhead). You can use Contanos for simple one-container deployments or orchestrate multiple containers together. Because communication is via standard protocols (like MQTT or HTTP/RTSP), Contanos components can be mixed and matched and even integrated with non-Contanos services.

## Directory Structure

The repository is organized into the following key directories and files:

```
contanos/             # Core framework package
├── base_processor.py    # Base class for processing units (common logic for modules)
├── base_service.py      # Base class for service (main orchestrator that manages I/O and workers)
├── base_worker.py       # Base class for worker (handles model inference loop)
├── helpers/             # Helper scripts to simplify creating processes
│   ├── create_a_processor.py  # Utility to create a processor instance from config
│   └── start_a_service.py     # Utility to launch a service with given parameters
├── io/                  # Input/Output interface implementations
│   ├── mqtt_input_interface.py        # MQTT input (subscribe to topic for data)
│   ├── mqtt_output_interface.py       # MQTT output (publish results to topic)
│   ├── mqtt_sorted_input_interface.py # MQTT input that maintains order or sorting
│   ├── multi_input_interface.py       # Interface to combine multiple inputs
│   ├── rtsp_input_interface.py        # RTSP input (pull video frames from an RTSP source)
│   └── rtsp_output_interface.py       # RTSP output (stream out video/frames via RTSP or related sink)
├── utils/               # Utility functions and classes
│   ├── create_args.py       # Define and parse command-line arguments for modules
│   ├── create_configs.py    # Helpers to create config objects from raw inputs
│   ├── format_results.py    # Utility to format model results into serializable output (e.g., JSON)
│   ├── parse_config_string.py  # Parser for config strings like the MQTT/RTSP URIs
│   └── setup_logging.py     # Convenient setup for logging format and levels
└── visualizer/         # Visualization utilities for drawing on images/frames
    ├── box_drawer.py       # Draw bounding boxes and labels on images
    ├── skeleton_drawer.py  # Draw skeletal keypoints (for pose estimation)
    └── trajectory_drawer.py# Draw trajectories for tracked objects
analyzer/             # Utility scripts for development and debugging
├── mqtt_sniffer.py        # Script to subscribe to all MQTT topics ( "#" ) and log messages (useful for debugging message flows)
├── queue_monitor.py       # Script or module to monitor internal queue lengths and worker status in a running service
└── test_rtsp.py           # Simple tester for RTSP streams (to verify a camera feed is accessible)
```

Other files in the repository include:

- **`pyproject.toml`** – Build configuration for the project (used if you want to install contanos as a Python package or for development).
- **`requirements.txt`** – Python dependencies listed for the project (these are installed in the Docker images; it’s not typically needed on the host).
- **`.gitignore`** – Git ignore file for the repository.
  *(At the moment, the project does not include a separate `LICENSE` file, but the license is stated below.)*

## License

This project is released under the **MIT License**. You are free to use, modify, and distribute this software in your own projects, including for commercial purposes, as long as the terms of the MIT License are met. (The MIT license is very permissive – it basically requires including a copy of the license in any redistributed versions of this software.)

See the MIT License text below for details:

```
MIT License

Copyright (c) 2025 yyhtbs-yye

Permission is hereby granted, free of charge, to any person obtaining a copy...
```

*(Full license text would be included here or in a separate LICENSE file.)*



## Contributing and Contact Info

Contributions are welcome! Bug reports, feature requests, and pull requests help improve STRIDE.

- **Submit Issues**: If you encounter any problems or have questions, please open an issue on the GitHub repository. This helps track known issues and discussions.
- **Pull Requests**: Feel free to fork the repository and submit pull requests. Whether it’s a bug fix, new feature, or improved documentation, we will review PRs and integrate them if they align with the project goals. Before starting large changes, it might be good to open an issue to discuss your plans.
- **Project Style**: Try to follow the coding style of the project for consistency (PEP8 for Python code, and similar structure to existing modules if creating new ones). Write clear commit messages and document new code as needed.

Contact: open an issue, or reach out to the maintainer on GitHub (yyhtbs-yye).

## Acknowledgement
This work has received funding as an Open Call project under the aerOS project (”Autonomous, scalablE, tRustworthy, intelligent European meta Operating System for the IoT edgecloud continuum”), funded by the European Union’s Horizon Europe programme under grant agreement No. 101069732.

