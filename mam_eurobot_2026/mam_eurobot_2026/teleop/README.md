# Recovered keyboard teleoperation

Recovered from unmerged `1-ros-sim`, commit `60c93b7`. The arrow-key controller
publishes `geometry_msgs/Twist`; idle timeout/other keys and exit publish zero.
This recovery installs the executable correctly and makes the command topic
configurable. It requires a POSIX interactive terminal.

After the native ROS package build, in a separate terminal:

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run mam_eurobot_2026 teleop_keyboard
```

Arrow keys move/turn, `q` quits. Defaults are 0.3 m/s forward and 1 rad/s turn.
Choose the topic that actually matches your simulated model/bridge:

```bash
ros2 run mam_eurobot_2026 teleop_keyboard --ros-args \
  -p command_topic:=/model/simple_robot/cmd_vel
```

The old launcher's hard-coded source path and compiled caches were not restored.
This is a simulation/manual-test aid, not an ESP32 driver or 2027 motion stack.
Hardware must independently expire commands if a publisher/terminal fails.
