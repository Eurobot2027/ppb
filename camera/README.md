# Native Raspberry Pi vision

This is the **ROS 2 Humble package `ppb_vision`** for Eurobot 2027. Start with
[ROS 2 setup, launch and topics](ROS2.md). It runs natively without Docker or Gazebo.
The standalone commands below remain diagnostic/calibration alternatives. Runtime
Python code is installed from `camera/camera/`. Raspberry Pi Camera capture uses Picamera2/libcamera;
USB cameras can use the optional OpenCV backend.

## Inherited advances

S8 `feature/vision-gripper` (`de90c8f`, merged into `5c855cf`) brought real-camera
experiments here. These files survived the fork:

| File | Advancement | Limit before reuse |
| --- | --- | --- |
| `camera_calibration.py` | 8×6 inner-corner checkerboard, subpixel refinement, saved intrinsics/distortion | GUI/V4L2; fixed camera index 2; deletes its capture directory on a new run |
| `cv_test.py` | Interactive ArUco pose, axes and image-space A* demo | GUI/V4L2; fixed capture assumptions and approximate intrinsics fallback |
| `aruco_pose_viewer.py` | CLI capture options, headless mode, snapshots, old/new OpenCV API support and PnP fallback | V4L2/MJPG; guesses intrinsics if calibration is missing |
| `aruco_tcp_flag_sender.py` | Target-ID visibility, periodic `0\n`/`1\n`, reconnects and failure clearing | Arduino-oriented protocol; not ESP32 firmware or a pose stream |
| `calibration_images/`, `camera_calibration.pkl` | Historical measurements | Not calibration for your Pi camera |

S8 milestones: `75015d2` (real-camera scripts), `7017a28` (ID 1 flag), `1e7ae69`
(WiFi shield test, explicitly reported unsuccessful), `d9bb85e` (TCP flag sender).
Commit messages show development, not hardware reliability. The
[ROS vision guide](../mam_eurobot_2026/mam_eurobot_2026/vision/README.md) describes
the separate world/localization pipeline.

## New native tools

| Module | Purpose |
| --- | --- |
| `camera.capture` | Fresh unannotated photos; refuses an existing capture directory |
| `camera.calibrate` | Offline checkerboard calibration to JSON with dimensions/RMS; refuses to overwrite |
| `camera.pi_vision` | Headless ArUco observations, optional measured pose and optional TCP output |
| `camera.pi_path` | ArUco-to-ArUco A* overlay streamed as MJPEG for SSH viewing |

The detector reuses dictionary/detection/pose helpers from `aruco_pose_viewer.py`,
including their OpenCV compatibility support. It does not use the inherited
approximate-intrinsics fallback or unpickle old measurements.

## Install and check capture

On Raspberry Pi OS, use matching system camera packages:

```bash
sudo apt update
sudo apt install python3-picamera2 python3-opencv python3-numpy python3-venv
rpicam-hello --list-cameras
python3 -c "import cv2; from picamera2 import Picamera2; print(cv2.__version__, hasattr(cv2, 'aruco'))"
```

The final value must be `True`. Package builds vary by OS; check ArUco support
before replacing system OpenCV with pip. For optional Python isolation, use
`python3 -m venv --system-site-packages .venv` so system libcamera/Picamera2 bindings
remain visible. No pip packages are needed for this Pi path. SSH is sufficient;
a desktop/VNC session is unnecessary.

Run commands from the **repository root**:

```bash
python3 -m camera.pi_vision --width 640 --height 480 --fps 15 --frames 100
```

Without calibration, detections contain IDs, pixel centers/corners and `pose: null`.
A valid empty frame has `frame_ok: true` and `detections: []`. Stopping or a
capture/processing error produces a final invalid observation when output remains
possible. A killed process cannot send it; the receiver must expire old data.

For a USB camera:

```bash
python3 -m camera.pi_vision --backend opencv --camera-index 0 --frames 100
```

Picamera2 uses `RGB888` for OpenCV's BGR byte ordering. Start at 640×480 and measure
performance; 15 FPS is a requested rate, not a hardware performance guarantee.

## Stream an ArUco route to your laptop

`camera.pi_path` reuses the A* planner from `cv_test.py`, now shared in
`camera.path_planning`, and the detector/capture helpers used by `camera.pi_vision`.
Stop other camera processes first. With this checkout updated on the Pi, run in
your laptop's local Bash terminal (VS Code command palette:
**Terminal: Create New Integrated Terminal (Local)**):

```bash
ssh -T team4@raspberrypi.local \
  'cd "$HOME/Desktop/ppb" && /usr/bin/python3 -m camera.pi_path 1 2 --backend picamera2 --camera-index 0 --width 640 --height 480 --fps 15' \
  | ffplay -loglevel warning -f mjpeg -framerate 15 \
      -fflags nobuffer -flags low_delay -probesize 32768 -analyzeduration 1 \
      -framedrop -sync ext -an -i -
```

Replace the host, repository path and example start/goal IDs `1 2` as needed.
Both markers must be visible together. The default dictionary is `DICT_4X4_50`;
`--dictionary` must match the printed markers. All IDs must be unique in the image.

The cyan route is the shortest path on an eight-neighbor pixel grid. Other detected
markers become rectangular obstacles with padding; diagonals cannot cut blocked
corners. Missing targets, ambiguous IDs or an unreachable goal clear the route
and show a message. `--debug-grid` shows blocked cells. `--grid-step-px` (default
12) and `--obstacle-padding-px` (default 24) control the image-space map.

This is a visual demo for a view of the planning surface, ideally from above.
It cannot recognize unmarked obstacles or turn perspective-distorted pixels into
a metric robot route. No calibration or guessed poses are used, and no motor
commands are sent. A physical route needs measured geometry and robot clearance.

Stdout contains only concatenated annotated JPEGs; diagnostics go to stderr.
Ctrl+C stops the stream. MJPEG uses more bandwidth than H.264; lower `--jpeg-quality`
(default 75) or `--fps` if needed, matching the player's `-framerate` to `--fps`.
For camera-free replay, `--image /path/to/640x480.png` emits one annotated JPEG;
`--frames N` limits a live run. Pi capture and WiFi latency still need hardware
validation for this new script.

## Calibrate your actual Pi camera

1. Fix the mount, lens/focus, resolution and crop. Measure the checkerboard square
   side. Defaults mean **8×6 inner corners** (9×7 squares), not 8×6 squares.
2. Capture 20–30 sharp views with different tilts/distances, including image edges.
   Move the board during the two-second interval. Choose a new directory:

   ```bash
   python3 -m camera.capture --output-dir camera/runs/pi-640x480-a --count 25
   python3 -m camera.calibrate --images camera/runs/pi-640x480-a \
     --cols 8 --rows 6 --square-length-m 0.025 \
     --output camera/runs/pi-640x480-a.json
   ```

3. Inspect photos and RMS. At least ten detected boards are required. Low RMS
   alone does not prove distance accuracy; measure pose errors independently at
   near/far distances and field corners. Record camera/lens/focus, crop, exposure
   and mount alongside calibration. Runtime captures under `camera/runs/` are ignored
   by Git; deliberately export approved calibration/dataset artifacts if needed.
4. Measure the ArUco **black square side** in metres, then run:

   ```bash
   python3 -m camera.pi_vision \
     --calibration camera/runs/pi-640x480-a.json --marker-length-m 0.04
   ```

These sizes are bench examples, not 2027 specifications. Resolution mismatches
are rejected. Matching dimensions cannot detect a different crop/focus/lens;
recalibrate when these change. All IDs currently use the same supplied marker
length; mixed physical sizes need per-ID configuration before using metric poses.

`tvec_m` locates the marker origin in the camera optical frame: **x right, y down,
z forward**. `rvec_rad` is a Rodrigues rotation vector, not Euler angles or robot
heading. It is not a world-coordinate robot pose. Square-marker ambiguity and
poor observations remain possible; tracking, fusion and reprojection rejection
are not implemented in the Pi tool.

## Offline diagnosis and remote delivery

```bash
python3 -m camera.pi_vision --image /path/to/frame.png --width 640 --height 480
python3 -m camera.pi_vision --frames 100 > /tmp/vision.jsonl
python3 -m camera.pi_vision --esp32-host 192.168.1.50 --esp32-port 5000
```

Supply the actual receiver address. ESP32 firmware must implement the
[observation protocol](../docs/ARCHITECTURE_2027.md); the old HTTP sketch and binary
flag protocol are incompatible. Observations do not command motors. Stdout gets
the same JSON stream; diagnostics go to stderr. Connect/send waits are limited
to 0.2 seconds each, retry attempts are spaced by one second and unsent
observations are dropped. Use a numeric IP address; hostname lookup uses the OS
resolver and is not covered by the socket timeout. Slow networking can still reduce capture rate.
Acknowledgements and reverse telemetry are not implemented.

## Next vision work

- Confirm the 2027 dictionary, IDs, sizes and camera-placement permissions.
- Decide onboard vs fixed external camera; the inherited robot beacon tracker
  assumes external geometry.
- Measure camera-to-base extrinsics/map landmarks, then fuse with ESP32 odometry.
- Record missed detections, false IDs, metric error, latency, reconnect/camera-loss
  behavior and representative regression images on the actual Pi.
- Add focus/exposure controls, quality rejection and per-ID sizes as field results
  justify them. An ID-1 observation must not directly trigger a grip/motor action.

Sources: [Raspberry Pi camera software](https://www.raspberrypi.com/documentation/accessories/camera-software.html),
[Picamera2 installation](https://github.com/raspberrypi/picamera2#installation),
[Picamera2 manual](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf),
[OpenCV ArUco](https://docs.opencv.org/4.x/d5/dae/tutorial_aruco_detection.html).

## ROS 2 runtime layout

The production entry points are `ros2 run ppb_vision camera_node`, `aruco_node`
and `esp32_bridge`, composed by `ros2 launch ppb_vision pi_vision.launch.py`.
The ROS-independent modules above now live under `camera/camera/`, with ROS
adapters under `camera/camera/ros/`. Full commands and limitations are in
[ROS2.md](ROS2.md). This keeps image-processing behavior shared between installed
ROS nodes and offline diagnostics.
