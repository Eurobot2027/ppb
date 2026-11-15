# Camera-frame reference

`simple_robot_camera.urdf` is an inherited TF-only robot: `base_link ->
front_camera -> front_camera_optical_frame`. It places the camera at
`[0.12, 0, 0.20]` m with a 0.3 rad pitch and rotates into the optical convention
(x right, y down, z forward). These values describe the old simulation.

The ROS vision config now explicitly associates `/front_camera` with this optical
frame instead of silently using the external-camera frame. For the Pi robot,
measure mounting/extrinsics and use real values; do not reuse this mount pose as
calibration. Intrinsics and base-to-camera extrinsics are separate measurements.
