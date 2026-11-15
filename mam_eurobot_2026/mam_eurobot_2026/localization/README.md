# Localization Nodes

## Recovery and 2027 status

The unmerged `feature/localization` tip `415fcba` only adds an empty package
initializer; it does not hide a missing estimator. The current real content was
already inherited: `gt_pose_to_map_tf.py`, `pose_info_filter_gz.py` and
`true_tf_from_odom.py`. They bridge/filter simulator pose or odometry into TF,
not physical camera/encoder localization.

The separate [vision robot pose node](../vision/README.md) estimates base pose
from an external camera and known marker extrinsics. Decide whether the Pi
camera is onboard or external before choosing that geometry. The legacy
`dammy_TF.py` is a placeholder, and Gazebo truth must not be used on the robot.

Next for 2027: specify map/odom/base/camera frames, measure extrinsics, add ESP32
encoder/sensor telemetry and fuse it with valid vision observations. Use one TF
publisher per link, validate timestamps and reject stale poses. Investigate the
existing map/world origin mismatch before relying on Nav2.

Reference for the ROS 2 nodes in `mam_eurobot_2026/localization`: what each one does, its topics/parameters, and how to launch it.

## gt_pose_to_map_tf
- **Node**: `gt_pose_to_map_tf` – listens to a ground-truth `geometry_msgs/Pose` and publishes a TF from `map` to `base_link` at a fixed rate.
- **Inputs**: `pose_topic` (`geometry_msgs/Pose`, default `/model/simple_robot/pose`).
- **Outputs**: TF `<map_frame>` → `<base_frame>` (defaults `map` → `base_link`).
- **Key parameters**: `pose_topic`, `map_frame`, `base_frame`, `publish_rate_hz`.
- **Notes**: Only the latest Pose is used when publishing; earlier poses received within a cycle are overwritten.
- **Run**:
  ```bash
  ros2 run mam_eurobot_2026 gt_pose_to_map_tf
  ```
