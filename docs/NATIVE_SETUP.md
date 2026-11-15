# Native setup without containers

The primary workflow is now **native ROS 2 Humble vision**; follow
[the ROS setup guide](../camera/ROS2.md) to build and launch `ppb_vision`.
The standalone commands below are diagnostic alternatives. `.devcontainer/` is historical;
no Docker command is needed.

## Raspberry Pi

Install Raspberry Pi OS and configure camera access/SSH using the
[official camera guide](https://www.raspberrypi.com/documentation/accessories/camera-software.html).
Use [Picamera2's system installation](https://github.com/raspberrypi/picamera2#installation).
From the repository root:

```bash
sudo apt update
sudo apt install python3-picamera2 python3-opencv python3-numpy python3-venv
rpicam-hello --list-cameras
python3 -m camera.pi_vision --frames 30
```

Optional Python isolation must expose system camera bindings:

```bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
```

Capture fresh calibration with the [camera guide](../camera/README.md); the old
`.pkl` is not valid for your Pi. Focus/sensor-mode choices depend on actual hardware.

## Desktop vision and tests

Python, NumPy and an OpenCV build with `cv2.aruco` suffice for image replay.
Repository tests also use pytest and PyYAML:

```bash
python3 -m camera.pi_vision --image /path/to/640x480.png
python3 -m pytest -q tests
```

Picamera2 is imported only for that backend. Offline tests need no ROS, Docker
or ancestor repositories.

## Optional legacy ROS / Gazebo

The inherited container used **Ubuntu 22.04 + ROS 2 Humble + Ignition Gazebo
Fortress**. Reproduce it using matching native packages on a compatible host.
See [Humble installation](https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html)
and the [Gazebo compatibility table](https://gazebosim.org/docs/fortress/ros_installation/).
This is a reproduction baseline, not the selected 2027 deployment stack.

After configuring the native ROS apt sources on that host:

```bash
sudo apt install ros-humble-desktop ros-humble-ros-gz \
  ros-humble-navigation2 ros-humble-nav2-bringup \
  ros-humble-cv-bridge ros-humble-vision-msgs ros-humble-tf-transformations \
  python3-colcon-common-extensions python3-rosdep python3-opencv python3-yaml
source /opt/ros/humble/setup.bash
# Initialize rosdep once if this machine has not already been initialized.
rosdep update
rosdep install --from-paths mam_eurobot_2026 --ignore-src -r -y
colcon build --symlink-install --packages-select mam_eurobot_2026
source install/setup.bash
ros2 launch mam_eurobot_2026 competition_arena.launch.py
```

Build from this repository root. `ament_python` / `setup.py` is the authoritative
build; the historical CMake file is not a second supported build path. The main
launches inherit your real user/desktop and no longer kill other simulators. GUI
tools still require a display. ROS/Gazebo is absent from the recovery host, so
these are reproduction instructions, not a verified simulator result.

Known blockers: mixed Ignition/Gazebo plugin naming, coordinate/map mismatches,
ground-truth localization and unfinished 2026 strategy. Read the
[package guide](../mam_eurobot_2026/README.md) before full demos. A newer ROS/Gazebo
pair needs an explicit port. Keep simulation separate from hardware control.
