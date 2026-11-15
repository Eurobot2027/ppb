# Focused software checks

Run `python3 -m pytest -q tests` from the repository root. Requires pytest,
NumPy, PyYAML and OpenCV with ArUco. No camera, ROS, ESP32 or container is needed.

Tests exercise rendered ArUco detection and metric scale, blank frames, invalid
calibration/resolution, image-based checkerboard calibration, CLI shutdown/error
observations, real stream framing, dropped-data/retry behavior and distinct ROS
front/external camera frames. They establish software behavior, not hardware
accuracy, WiFi performance or robot autonomy. See [validation](../docs/VALIDATION.md).

`test_ros_vision.py` runs real Humble nodes with a rendered image: synchronized
camera/calibration messages, typed 3D output, frame capture and watchdog clearing.
It is skipped when rclpy is unavailable. In the native Humble environment the
complete suite passes 16 tests; DDS/local TCP access is required.
