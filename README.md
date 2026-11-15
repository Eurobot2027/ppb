# PPB — Eurobot 2027

Polytech Annecy-Chambéry robot project, inherited from **jon-snowbot (S8)** and
**mam_eurobot_2026_T1 (S7)**. The target competition is **Eurobot 2027**. Existing
ROS package names, field maps, crate/cursor strategy and simulated robot describe
2026; they are references to adapt, not a finished 2027 robot.

The intended hardware is a **Raspberry Pi + Raspberry Pi Camera** for vision,
connected remotely to an **ESP32** that controls motors/actuators and reads sensors.
Development and vision run **natively on ROS 2 Humble, without a container**.
The `ppb_vision` package in `camera/` provides the hardware vision graph; standalone
Python entry points remain available for diagnostics. Old gripper/electronics designs may be replaced; obsolete SolidWorks
CAD has deliberately not been recovered.

## What was recovered and improved

- Audited every local branch, cached remote branch and all five S7 stashes in both
  ancestor repositories. Preserved **24 commits absent from this fork**, plus the
  source ref inventory and reviewable patches. The archive travels with this
  checkout and does not depend on the old directories remaining available.
  Restored 40 branch snapshot refs under `legacy-s7/...` / `legacy-s8/...` and
  five stash refs without switching or merging the current branch.
- Confirmed that the main vision advances **were already merged**: ArUco pose
  estimation, checkerboard calibration, HSV detection, camera/world transforms,
  external-camera robot localization, headless viewing and TCP visibility flags.
- Added native **Picamera2** capture, calibration and detection, with JSON
  observations and optional TCP delivery. Metric pose requires measured
  intrinsics and marker size; detection can run without calibration.
- Corrected ROS front-camera frame selection: `/front_camera` detections no longer
  silently inherit the external observation camera's frame.
- Restored keyboard teleoperation as an installed ROS executable. Preserved the
  unmerged go-to-goal controller and simulation experiments separately because
  their movement estimates and models are not validated for real hardware.
- Removed container-user paths, forced VNC display settings and process-killing
  commands from the main legacy launch files. Corrected a planner executable name
  and removed an entry pointing to a nonexistent behavior tree.

See the [recovery report](docs/RECOVERY.md) for evidence, branch decisions,
limitations and the distinction between inherited, recovered and newly added work.

## Run vision first

Source your native ROS 2 Humble environment, then from the repository root:

```bash
rosdep install --from-paths camera --ignore-src -r -y
colcon build --packages-select ppb_vision --symlink-install
source install/setup.bash
ros2 launch ppb_vision pi_vision.launch.py
```

See [ROS 2 setup and topics](camera/ROS2.md) for Pi/libcamera compatibility,
calibration, USB/image replay, the frame-capture service and optional ESP32 bridge.
Actual Pi capture and ESP32 firmware still need hardware validation.

## Documentation by subsystem

| Folder / guide | Contents |
| --- | --- |
| [camera](camera/README.md) | Pi setup, calibration, detection and inherited scripts |
| [2027 architecture](docs/ARCHITECTURE_2027.md) | Pi/ESP32 roles, observation protocol and missing firmware |
| [2027 adaptation plan](docs/EUROBOT_2027.md) | Official rule sources and ordered implementation plan |
| [native setup](docs/NATIVE_SETUP.md) | Pi setup and optional native ROS/Gazebo build |
| [recovery archive](docs/history/README.md) | Branch/stash inventory and restoration commands |
| [legacy ROS package](mam_eurobot_2026/README.md) | Simulation status and subsystem links |
| [electronics](electronics/README.md) | Existing documents and ESP32 redesign considerations |
| [gripper](gripper/README.md) | Historical sketch status and replacement interface |
| [ultrasonic sensor](<ultrasonic sensor/README.md>) | PID progression, limitations and ESP32 porting |
| [recovered experiments](legacy/README.md) | Unmerged code outside the active runtime |
| [tools](tools/README.md) | Reproducible history capture and restoration |

## What to do next

1. Review the published [Eurobot 2027 rules](https://www.eurobot.org/eurobot-contest/eurobot-2027/)
   and record target objects, markers, camera placement, field frame and robot
   constraints in the [adaptation plan](docs/EUROBOT_2027.md).
2. Select the Pi/camera model, fix mounting/focus and capture fresh calibration
   at the exact runtime resolution and crop.
3. Measure detection and pose errors under field lighting; retain images and logs.
4. Implement the ESP32 receiver, sensor telemetry, local motor loops, command
   expiry and stop behavior. TCP output here is **observation data**; working
   ESP32 firmware and motor-control integration are still to implement.
5. Choose the 2027 drivetrain/end effector, then adapt localization, maps and
   strategy. Old CAD, pin assignments, PID gains and crate logic are historical.

Checks: `python3 -m pytest -q tests`. See [validation](docs/VALIDATION.md) for scope
and hardware/ROS limitations.
