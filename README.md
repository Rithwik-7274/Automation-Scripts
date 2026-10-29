# Automation Scripts

This repository contains the cross-platform automation and telemetry scripts developed for our research project which executes isolated benchmarking workloads and captures 1Hz hardware telemetry across Windows 11 and Linux to evaluate OS-level scheduler efficiency and hardware power-gating.

## Repository Structure

```text
.
├── Linux/
│   ├── linux_runner.py
│   ├── results/                 # Empty directory for telemetry outputs
│   ├── simultaneous_test.py
│   ├── Speedometer/             # Empty directory for speedometer benchmark files
│   ├── speedometer_test.py
│   └── unigine_test.py
├── Windows/
│   ├── Executables/             # Empty directory for binaries (mpv, 7z, etc.)
│   ├── results/                 # Empty directory for telemetry outputs
│   ├── simultaneous_test.py
│   ├── Speedometer/             # Empty directory for speedometer benchmark files
│   ├── speedometer_test.py
│   └── windows_runner.py
├── tuya_logger.py
└── README.md
```

## System Architecture & Telemetry

To ensure instantaneous component-level power integration without introducing a high observer effect, the data pipelines utilize native OS tools.

* **Linux:** Utilizes `turbostat` for CPU package wattage and `perf` for kernel scheduler context switches.
* **Windows 11:** Utilizes AMD's `AMDuProfCLI` for CPU frequency/power and `typeperf` for Windows kernel context switches.
* **Conditional dGPU Polling:** Continuously polling the NVIDIA dGPU via `nvidia-smi` prevents the hardware from entering deep sleep (D3Cold). Therefore, `nvidia-smi` is only executed during GPU-bound workloads. During idle or CPU-bound tests on Linux, the script bypasses `nvidia-smi` entirely, instead polling the virtual filesystem (`/sys/bus/pci/devices/`) to verify runtime suspension without waking the hardware.

## Automated Workload Pipeline

The master runners execute a sequential suite, enforcing 10-minute thermal stabilization periods between benchmarks to ensure identical thermal starting conditions.

1. **System Idle:** 10-minute baseline capture.
2. **Speedometer:** Automated via Selenium. On Windows, Hibbiki's stable Chromium build is utilized to prevent background developer terminals from spawning and consuming CPU cycles.
3. **MPV Hardware Decode:** 1080p GPU-accelerated video playback.
4. **Geekbench (CPU & Compute):** Compute and CPU stress tests.
5. **7-Zip Compression:** Multi-threaded CPU saturation.
6. **Unigine Heaven:** Native 3D rendering stress test.
7. **Dual Stress:** Simultaneous CPU and dGPU saturation.

## Engineering Constraints & Automation Solutions

* **Headless Network Gating:** Geekbench fails silently without network access, but continuous background Wi-Fi polling corrupts idle power telemetry. The scripts use `nmcli` and `netsh` to enable the network exactly 20 seconds prior to execution to establish a connection, and disable it immediately after the run concludes. On Linux, these commands were added to `sudo visudo` to prevent permission timeouts during headless execution.
* **GUI State Management & Orphaned Process Cleanup:** Because the standard version of Unigine Heaven lacks command-line execution arguments, the scripts utilize `pyautogui` to physically manipulate the GUI to start the benchmark and save the score. Afterward, aggressive `killall` commands target both `heaven_x64` and `browser_x64` to guarantee background rendering processes are destroyed before the next test begins.
* **I/O Buffering & Process Termination:** On Windows, forcefully terminating subprocesses caused data loss due to I/O buffering. The architecture replaces aggressive termination with graceful `CTRL_C_EVENT` interrupts, allowing processes to clean up and flush buffer contents to the disk.
* **IoT Polling & Network Resilience:** The Tuya smart plug logger initially suffered from fatal crashes due to IP shifting and silent network timeouts<sup></sup>. The automation was hardened by overriding `tinytuya`'s default auto-discovery, actively catching dictionary payload errors, and infinitely looping until reconnection to minimise silent crashes.
* **Hardware State Anomalies & OS Migration:** Initial testing on CachyOS revealed the NVIDIA dGPU failed to reliably enter the `d3cold` ACPI state despite custom `udev` rules<sup></sup>. This has necessitated an architectural migration to Fedora to leverage more stable drivers and gain native compatibility with AMD's `AMDuProf` for accurate telemetry mapping<sup></sup>.
