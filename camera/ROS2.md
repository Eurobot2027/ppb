# ROS 2 Humble vision

`camera/` is now the standalone **ament_python package `ppb_vision`**. Its installed
Python library lives in `camera/camera/`. The source-checkout shim keeps
`python3 -m camera.*` diagnostics available. No container is required.

## Build and launch

Use a native ROS 2 **Humble** installation. Ubuntu 22.04 is its standard Debian
binary platform. Do not install Humble Debian packages into this host's Ubuntu
26.04. An isolated native RoboStack Humble environment is another desktop option;
never mix its Python packages with an apt ROS installation.

After sourcing your Humble environment, from the repository root:

```bash
rosdep install --from-paths camera --ignore-src -r -y
colcon build --packages-select ppb_vision --symlink-install
source install/setup.bash
ros2 launch ppb_vision pi_vision.launch.py
```

ROS dependencies include rclpy, cv_bridge, message_filters, sensor_msgs, vision_msgs,
std_msgs and std_srvs. OpenCV must include ArUco. Picamera2/libcamera is a hardware
backend dependency installed separately for the selected Pi OS and Python ABI.
Raspberry Pi OS packages do not automatically work in Ubuntu 22.04 or a conda
Python. Verify `python -c 'from picamera2 import Picamera2'` in the **same** Python
that runs ROS. A compatible native libcamera/Picamera2 installation or camera
publisher is required before claiming Pi hardware support. See the official
[Picamera2 instructions](https://github.com/raspberrypi/picamera2#installation).
The camera hardware has not been tested here.

USB alternative: `backend:=opencv camera_index:=0`.
Image replay: `backend:=image image_path:=/absolute/path/to/640x480.png`.
The image backend repeatedly publishes the test frame with current retrieval stamps.

## Calibration and topics

```bash
ros2 launch ppb_vision pi_vision.launch.py \
  calibration_file:=/absolute/path/to/pi-calibration.json marker_length_m:=0.04
ros2 topic echo /vision/detections_2d
ros2 topic echo /aruco/detections
ros2 topic echo /vision/healthy
```

Marker size/dictionary are bench values to review for 2027. With no calibration
or marker size, only 2D detections are meaningful; 3D arrays remain empty.
The camera publishes matching `/camera/image_raw` and `/camera/camera_info` using
sensor-data QoS. The detector synchronizes exact stamps and preserves the source
optical frame/time in typed detection messages. Poses are camera-relative, not map
localization. Decoded-marker score 1 is not a measured confidence. The 3D box is
only the planar marker, not the full game object.

`/vision/observations` is a JSON `std_msgs/String` stream for the bridge, alongside
standard 2D/3D messages. `/camera/healthy` and `/vision/healthy` are latched booleans.
Lost, stale, mismatched or invalid frames clear detections and health. Use the same
ROS clock on image publishers/subscribers; pass `use_sim_time:=true` for ROS bags
with `/clock`. `publish_debug_image:=true` enables `/vision/debug_image`.

For an existing ROS camera, use `camera_enabled:=false` and set `image_topic` and
`camera_info_topic`. Both messages must have matching stamps, frame and dimensions.
Intrinsics must already account for crop/binning; fisheye models need a separate
adapter. No approximate calibration is substituted.

To collect calibration through ROS, launch with a new `capture_directory` and call
`ros2 service call /camera/save_frame std_srvs/srv/Trigger '{}'` for varied views.
Then run `ros2 run ppb_vision calibrate --images DIRECTORY --square-length-m 0.025
--output NEW.json`. The offline calibration/capture CLIs are also installed ROS
executables. Existing measurements are never overwritten.

## ESP32 bridge

```bash
ros2 launch ppb_vision pi_vision.launch.py \
  enable_esp32:=true esp32_host:=192.168.1.50 esp32_port:=5000
```

The separate ROS node subscribes to observations and forwards the latest over
TCP. It emits invalid observations if its input expires. `/esp32/link_available`
reports successful socket writes, not receiver acknowledgement. The existing
[protocol](../docs/ARCHITECTURE_2027.md) remains version 1 with optional
`source_stamp` (ROS sec/nanosec); `frame` now carries the actual optical frame name.
In this ROS adapter, `read_monotonic_ns` records detector receipt, not hardware
exposure. Receiver age/clock handling still needs implementation. No motor commands
or ESP32 firmware are invented by this adapter.

## Scope and validation

This supplies a ROS 2 Humble hardware-vision graph and ROS transport adapter. It
does not establish a working 2027 autonomous robot or fix the inherited Gazebo
physics/map/strategy issues. The old `mam_eurobot_2026` package remains separate;
building vision does not pull in Gazebo/Nav2. Its TF adapter can consume the new
`/aruco/detections` once real camera extrinsics/localization exist.

Tests: `python -m pytest -q tests`. The ROS integration test requires actual
Humble libraries and DDS/loopback access; it is skipped in non-ROS Python.
