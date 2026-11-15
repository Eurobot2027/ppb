# Legacy ROS 2 / Gazebo package

The name is retained for import/launch compatibility. It is a **2026 simulation
reference**, within a repository now targeting **Eurobot 2027**. The native
Raspberry Pi runtime is the separate [ppb_vision Humble package](../camera/ROS2.md).
Standalone Python diagnostics are also retained.

## Useful inherited development

| Subsystem | Capabilities and status |
| --- | --- |
| [vision](mam_eurobot_2026/vision/README.md) | ArUco/HSV detection, camera/world transforms, robot beacon pose; preserve algorithms and remeasure geometry |
| [localization](mam_eurobot_2026/localization/README.md) | Ground-truth/odometry TF examples; not real robot localization |
| [planning](mam_eurobot_2026/path_planning/README.md) | Nav2 staging/task/fixed-goal planning, field assets and RViz |
| [movement](mam_eurobot_2026/movement/README.md) | Nav2 FollowPath client and historical wheel/Twist demo |
| [teleop](mam_eurobot_2026/teleop/README.md) | Restored keyboard velocity commands from the unmerged ROS-sim branch |
| [task manager](mam_eurobot_2026/task_manager/README.md) | 2026 cursor/crate/pantry/nest FSM with timeouts and grasp checks |
| [gripper](mam_eurobot_2026/gripper/README.md) | Simulated joint-position teleoperation; not an ESP32 driver |
| [launch](launch/README.md) | Legacy demo composition and known coordinate failures |
| [models](models/README.md), [worlds](worlds/README.md), [URDF](urdf/README.md) | Old field/robot geometry and camera-frame example |

Use [native setup](../docs/NATIVE_SETUP.md). `package.xml` selects `ament_python`;
`setup.py` installs modules/assets and console scripts. The historical CMake file
does not describe the active build. The absent behavior-tree entry was removed;
there is no recovered behavior-tree implementation to run.

The main launch files now inherit user/desktop settings and preserve host resource
paths. Process-wide Gazebo kills and container account overrides were removed.
This does **not** repair all simulation issues: mixed plugin/message names,
ground-truth TF, old footprint/map frames and unfinished strategy remain. ROS/
Gazebo execution could not be checked on this host.

The current main robot uses a differential-drive plugin. Mecanum experiments are
preserved under [legacy](../legacy/README.md), not selected as the 2027 drivetrain.
Avoid confusing four-wheel `/omni/*` commands, `/model/simple_robot/cmd_vel` demos
and the active model's `cmd_vel` topic. Inspect model/bridge topic names before
motion. Do not attach simulation commands directly to real actuators.
