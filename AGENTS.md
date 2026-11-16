# Repository-wide agent instructions

These instructions apply to the entire repository. Follow explicit user task
instructions when they change the requested scope or project decisions. Keep this
file current when build commands, architecture or validation requirements change.
Format reference: [AGENTS.md](https://agents.md/).

## Project context

- PPB targets **Eurobot 2027**, at Polytech Annecy-Chambéry.
- Use **ROS 2 Humble**, natively, without Docker or development containers.
  `.devcontainer/` is historical reference, not the development workflow.
- The intended robot uses a Raspberry Pi and Raspberry Pi Camera for vision,
  connected remotely to an ESP32 for motors, actuators and sensor acquisition.
- Prioritize reliable vision, measured calibration, explicit interfaces and
  useful subsystem documentation. Existing gripper/electronics may be replaced;
  obsolete CAD is not a design requirement.
- The 2026 maps, marker settings, robot geometry and strategy are historical.
  Verify current official 2027 rules before adding season-specific constants;
  do not assume the old crate/cursor/pantry/nest game still applies.

## Repository map

| Path | Responsibility |
| --- | --- |
| `camera/` | Active ROS package **`ppb_vision`**, Python packaging, launch/config and camera documentation |
| `camera/camera/` | Installed Python library `camera`: shared capture, calibration, ArUco and transport helpers |
| `camera/camera/ros/` | Camera publisher, synchronized detector and optional ESP32 observation bridge |
| `camera/__init__.py` | Source-checkout compatibility for `python3 -m camera.*`; preserve installed and source imports |
| `mam_eurobot_2026/` | Separate legacy ROS package: simulation, localization, Nav2, movement and strategy references |
| `legacy/` | Recovered experiments; not enabled in the active runtime |
| `docs/history/` | Recovery inventory, manifests, incremental Git bundle and readable patches |
| `tools/` | Ancestor history capture/restoration utilities |
| `tests/` | Offline vision checks and real ROS integration test |
| `electronics/`, `gripper/`, `ultrasonic sensor/` | Historical hardware documents and sketches, with reuse limitations |

Read [README.md](README.md) and the relevant subsystem guide before editing.
Use [camera/ROS2.md](camera/ROS2.md) for the active runtime,
[docs/ARCHITECTURE_2027.md](docs/ARCHITECTURE_2027.md) for interfaces, and
[docs/RECOVERY.md](docs/RECOVERY.md) for provenance and recovery decisions.

## Environment, build and run

Run the following from the repository root **after sourcing a compatible native
Humble environment**:

```bash
rosdep install --from-paths camera --ignore-src -r -y
colcon build --packages-select ppb_vision --symlink-install
source install/setup.bash
ros2 launch ppb_vision pi_vision.launch.py
```

- Build only packages relevant to the change. Vision does not require the legacy
  Gazebo/Nav2 stack. Both packages use `ament_python` / `setup.py`; the legacy
  CMake file is not an alternative supported build path.
- Humble's standard Ubuntu Debian binary platform is Ubuntu 22.04. Inspect the
  host before installing dependencies; do not install its Debian packages into a
  different Ubuntu release or change system Python to make a build pass.
- A native isolated RoboStack Humble environment can be used for desktop tests.
  Do not mix its Python/libraries with an apt ROS environment. Temporary test
  environments are disposable, not a deployment dependency.
- Picamera2/libcamera must import in the same Python used by ROS. Do not assume
  Raspberry Pi OS bindings work with Ubuntu or conda Python. For camera-free
  checks, launch with `backend:=image image_path:=/absolute/path/to/640x480.png`;
  USB capture uses `backend:=opencv camera_index:=0`.
- Keep launch files portable: inherit the host user/display, preserve existing
  resource paths, and never kill unrelated simulator processes.

## Implementation conventions

- Match nearby Python style and keep changes focused. Reuse shared image and
  protocol helpers instead of duplicating logic in ROS nodes and diagnostic CLIs.
- Keep ROS adapters under `camera/camera/ros/`; offline helpers must remain usable
  without importing rclpy. Preserve ROS package names, installed executable names,
  source imports and installed imports unless a migration is explicitly needed.
- Declare ROS runtime dependencies in `package.xml`; install executable entry
  points and launch/config assets through `setup.py`. Do not add mandatory
  Gazebo dependencies to the hardware-vision package.
- Use ROS parameters for device, topic, frame, calibration and network settings.
  Do not hard-code a developer's home directory, camera index or ESP32 address.
- Keep standard typed ROS image/detection messages available alongside the JSON
  transport. Maintain compatible sensor-data QoS and synchronized Image/CameraInfo
  timestamps, dimensions and optical frames.

## Vision and hardware invariants

- Require measured intrinsics and marker dimensions for metric poses. Without
  calibration, publish pixel detections and empty metric results, not guessed poses.
- Preserve optical axes (x right, y down, z forward), units and timestamps.
  A Rodrigues vector is not Euler angles; a camera-relative pose is not map
  localization. Camera intrinsics and camera-to-base extrinsics are separate.
- Reject incompatible calibration/frame geometry and stale inputs. Preserve
  watchdog invalidation, empty detections and health reporting on failures.
- Capture/calibration tools must not erase existing measurements or overwrite
  datasets implicitly. Keep raw calibration frames unannotated.
- The ESP32 bridge sends **observations**, not motor commands. Successful socket
  writes are not receiver acknowledgements. Preserve message framing, bounded
  buffering, expiry and reconnect behavior; document protocol changes.
- ESP32 firmware, local control loops, telemetry and actual hardware integration
  are unfinished. Do not present old Arduino sketches as working ESP32 firmware,
  or run real actuators merely to verify software. Keep real hardware commands
  separate from replay/simulation tests.

## Validation

```bash
python3 -m pytest -q tests
git diff --check
```

- Run relevant checks for changed behavior. For ROS runtime/packaging changes,
  also build `ppb_vision` and test the installed launch from outside the source
  tree, including orderly shutdown. Use image replay when hardware is unavailable.
- `tests/test_ros_vision.py` requires actual Humble libraries and DDS access; it
  skips without rclpy. The full suite also uses local TCP. Report skips and
  environment restrictions; mocks/static parsing do not prove ROS integration.
- Add or update focused regression tests for meaningful processing, frame,
  calibration, transport and fault-handling changes. Documentation-only edits
  generally need link/command review rather than new tests.
- Prior checks are recorded in [docs/VALIDATION.md](docs/VALIDATION.md); rerun
  applicable checks rather than treating historical results as current evidence.
  Distinguish desktop/replay results from real Pi, ESP32 and Gazebo validation.

## History, generated files and documentation

- Preserve user changes and recovered source provenance. Do not bulk merge old
  branches, apply archived stashes, regenerate the historical archive, or replace
  newer code with experiments as a side effect of ordinary development.
- Do not delete or ignore `docs/history/ancestors.bundle`, `refs.json`, patches
  or historical calibration fixtures. The incremental bundle requires existing
  PPB history; consult [docs/history/README.md](docs/history/README.md).
- Keep build/install/log trees, Python packaging/cache output, local editor
  settings, runtime captures and bag recordings out of Git using `.gitignore`.
  Do not ignore source/configuration or approved calibration data indiscriminately.
- Update the dedicated folder's Markdown when behavior, setup, interfaces or
  limitations change; update the root README when the main workflow changes.
  Keep 2027 plans distinct from 2026 reference behavior.
- Never include credentials, WiFi passwords or device secrets in source or logs.
- Before finishing, summarize the change, checks performed and unresolved
  limitations. Commit/PR descriptions should describe actual resulting behavior
  and validation. Do not commit or push unless the user requests it.
