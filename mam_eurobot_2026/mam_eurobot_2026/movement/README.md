# Movement Nodes

## Recovery and 2027 status

The Nav2 client below is already merged. `wheel_controller.py` is a historical
Twist demo publishing to `/model/simple_robot/cmd_vel`; its content also exists in
S7 stash 0 (`db90f3b`). The active main model is differential drive, so the
mecanum/strafe wording is not a supported hardware capability.

The genuinely missing `feature/path-follower` (`f593fd8`) controller was recovered
to [legacy/movement](../../../legacy/movement/README.md). It integrates commanded
wheel speeds without wheel geometry/feedback and is deliberately not installed
for use. The useful unmerged keyboard controller is now available in
[teleop](../teleop/README.md).

For 2027, select the drivetrain, derive its kinematics and implement local encoder
loops on ESP32. Send expiring high-level commands from the Pi only through an
explicit hardware adapter; bring measured odometry back. No current node here
controls an ESP32. Verify model/bridge topic names before simulation movement.
See [architecture](../../../docs/ARCHITECTURE_2027.md).

Reference for the ROS 2 nodes in `mam_eurobot_2026/movement`: what each one does, its topics/parameters, and how to launch it.

## path_follow_client
- **Node**: `path_follow_client` – listens for `nav_msgs/Path` messages and forwards them to Nav2's FollowPath action.
- **Inputs**:
  - `/planned_path` (`nav_msgs/Path` by default).
- **Outputs**: FollowPath action requests to `/follow_path` by default.
- **Key parameters**: `path_topic`, `follow_action`, `controller_id`, `goal_checker_id`, `progress_checker_id`, `cancel_on_new_path`.
- **Notes**: If `cancel_on_new_path` is true, a new path cancels the current FollowPath goal before sending the next one. `progress_checker_id` is declared but currently not set on the goal.
- **Run**:
  ```bash
  ros2 run mam_eurobot_2026 path_follow_client
  ```
