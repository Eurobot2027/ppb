# Recovery and native vision validation

Checked on **15 November 2026**, natively on the development host. No container
was started. Host Python was 3.14.4 and OpenCV 4.10.0 with ArUco; these are test
host versions, not mandatory Raspberry Pi versions.

## Software evidence

`python3 -m pytest -q tests`: **15 passed**. Checks include:

- Real OpenCV detection of a rendered ID-1 marker and absence on a blank image.
- Calibrated pose scale against known focal length/marker dimensions.
- Rejection of wrong calibration schema, dimensions, focal lengths, distortion
  shape and nonfinite values.
- Camera calibration from rendered, tilted checkerboard images with known
  intrinsics, plus rejection of mixed resolutions and insufficient boards.
- CLI output, valid detection followed by shutdown invalidation, and invalidation
  when actual input dimensions disagree with requested dimensions.
- Two framed JSON observations delivered through a real loopback TCP server.
- Dropping unsent data and retry spacing after a connection failure.
- Separate ROS front/external camera frames and rejection of unknown topics.

The initial sandbox run blocked socket transmission; the completed native test
run used local loopback access. It contacted no external device/service.

Additional checks: Python syntax parsing, console-entry module existence,
Markdown link targets, `git diff --check`, bundle checksum/prerequisites and
restoration into an isolated temporary local clone. The archive restoration was
tested twice for idempotency, all 24 missing commit objects were checked, HEAD
was unchanged, and `git fsck --full --no-reflogs` checked object integrity.

## What still needs validation

| Area | Remaining work |
| --- | --- |
| Pi + Camera | Picamera2 acquisition, sensor modes, image channel order on actual hardware, focus/exposure, frame latency/rate, thermals |
| Vision accuracy | Real lens/mount calibration, lighting/occlusion, distance/orientation error and square-marker ambiguity |
| ESP32 | Receiver firmware, resource limits, actual WiFi reconnects/latency, clock/age strategy, telemetry and command protocol |
| Motors/sensors/actuators | Board/pin/voltage choices, local loops, direction/gains, timeout and stop behavior |
| ROS/Gazebo | Native build/launch, plugin compatibility, TF/map alignment and Nav2/FSM behavior; ROS is absent from the test host |
| 2027 | Full game-rule review, season assets/configuration, mechanism/strategy and integrated match trials |

Software tests do not establish hardware reliability, rule compliance or an
autonomous 2027 robot. Use the [ordered bring-up plan](EUROBOT_2027.md).

## ROS 2 Humble follow-up

The new `camera/` ament package is `ppb_vision`. It was built successfully with
`colcon build --packages-select ppb_vision --symlink-install` in a native,
isolated RoboStack Humble environment in `/tmp`, without containers or system
package changes. This environment uses Humble rclpy 3.3.22 and OpenCV 5.0.0.

The complete suite passed: **16 tests**, including real ROS image/CameraInfo
publication, typed metric detections with the correct optical frame and scale,
the frame-capture service and stale-frame invalidation through a ROS executor.
The original standalone tests still pass. The installed launch graph was also
smoke-tested with image replay from outside the source tree.

This supersedes the earlier statement that ROS was absent for *vision* testing.
Gazebo/Nav2 and real Pi/libcamera/ESP32 hardware remain unverified. A desktop
Humble build does not establish a compatible Pi camera OS/Python/libcamera ABI;
follow [ROS2.md](../camera/ROS2.md) before deployment.
