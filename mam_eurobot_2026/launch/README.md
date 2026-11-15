# Launch Files

## Native operation and recovery status

Use [native setup](../../docs/NATIVE_SETUP.md); no container is required. The
competition, test-arena and path-planning demos now inherit the host user/display
and preserve existing model search paths. Removed forced `/home/rosdev`, VNC `:1`,
container graphics-library paths and global `pkill -9` calls. The staging planner
executable now matches the installed console script. These files have been
syntax-checked, not run with ROS/Gazebo on the recovery host.

The unmerged `1-ros-sim` keyboard controller is restored as an installed
`teleop_keyboard` command; its old launch file was not copied because its source
path fallback was invalid. Run keyboard teleop in a real terminal, separately
from the simulator. There is no automatic hardware startup.

All worlds/maps/actions below remain **2026**. The existing model mixes old/new
simulator plugin names and the upstream coordinate failures below remain open.
Do not launch every demo together; they can publish competing TF and commands.
For Pi vision use [camera](../../camera/README.md), which needs neither a display
nor this simulation. `robot_pose_from_beacon` is not started by the vision launch;
start it explicitly only after configuring its external-camera geometry.

Reference for the ROS 2 launch files in `mam_eurobot_2026/launch`: what each one starts and what it expects to already be running.

## competition_arena.launch.py
- **Purpose**: Starts Gazebo (Ignition) competition world, spawns the robot, bridges core topics, and opens RViz.
- **Starts**: Gazebo world, robot spawn, camera bridges (`/front_camera`, `/top_camera/image_3`), clock bridge, cmd_vel bridge, gripper bridge, robot_state_publisher, RViz.
- **Prereqs**: None (this is the base sim bringup).

## dammy_localization.launch.py
- **Purpose**: Bridges Gazebo pose to ROS and publishes `map -> base_link` TF using ground-truth pose.
- **Starts**: `ros_gz_bridge` pose bridge and `gt_pose_to_map_tf`.
- **Prereqs**:
  - `competition_arena.launch.py` (or any Gazebo sim publishing `/model/simple_robot/pose`).

## vision_detection.launch.py
- **Purpose**: Runs vision pipeline (color detection, cursor estimation, ArUco detection).
- **Starts**: `color_detector`, `world_to_topcamera`, `estimate_cursor_position`, `aruco_detector`.
- **Prereqs**:
  - `competition_arena.launch.py` (camera topics `/front_camera` and `/top_camera/image_3`).
  - TF chain from localization (`map -> base_link`) for `world_to_topcamera`/cursor projection.

## task_manager_fsm.launch.py
- **Purpose**: Runs task manager FSM + Nav2 planner/controller + path following pipeline.
- **Starts**: map_server, planner_server, controller_server, lifecycle_manager, `detected_crates_tf`, `task_goal_path_planner`, `path_follow_client`, `task_manager_fsm`, static TF `map -> world`.
- **Prereqs**:
  - `competition_arena.launch.py` (robot + sim time).
  - `dammy_localization.launch.py` (or any localization providing `map -> base_link`).
  - `vision_detection.launch.py` (provides `/aruco/detections` and `/world_coordinate/cursor`).

## pathplanning_demo.launch.py
- **Purpose**: Nav2 planner demo that plans to nearest staging pose and visualizes in RViz.
- **Starts**: map_server, planner_server, lifecycle_manager, `staging_path_planner`, RViz.
- **Prereqs**:
  - `competition_arena.launch.py` (sim time + robot).
  - `dammy_localization.launch.py` (or any localization providing `map -> base_link`).

## fixed_goal_path_follow.launch.py
- **Purpose**: Nav2 map/planner/controller + a fixed-goal planner + FollowPath client for quick testing.
- **Starts**: map_server, planner_server, controller_server, lifecycle_manager, `fixed_goal_path_planner`, `path_follow_client`.
- **Prereqs**:
  - `competition_arena.launch.py` (sim time + robot).
  - `dammy_localization.launch.py` (or any localization providing `map -> base_link`)

## ISSUES
`task_manager_fsm.launch` does not work well. At first robot should generate a path to the cursor, but it cannot though it can fetch cursor position.  
We tested with `fixed_goal_path_follow.launch` but it sometimes fails to generate the path.  
Sometimes I saw error appearing that robot/target position is out of area, although the robot is on start position. So I think there is a mismatch for coordinate between gazebo and nav2.
