# Gripper Nodes

## Recovery and 2027 status

The gripper branch (`86f02b1` in S8, earlier `423357d` in S7) is already merged.
Its simulated position-controlled joint, keyboard toggle and bridges are a
reference for actuator commands, not firmware for the real 2027 mechanism.

The [root gripper sketch](../../../gripper/README.md) is actually an old WiFiEsp
HTTP example and has no gripper control. Old gripper geometry/electronics/CAD can
be discarded for the new game. Define ESP32 capabilities, limits, completion and
fault feedback once the mechanism is selected. Keep image processing independent
of the actuator implementation.

Reference for the ROS 2 nodes in `mam_eurobot_2026/gripper`: what each one does, its topics/parameters, and how to launch it.

## gripper_keyboard
- **Node**: `gripper_keyboard` – keyboard teleop that toggles the gripper open/close.
- **Inputs**: keypresses `g` (toggle) and `q` (quit).
- **Outputs**: publishes `std_msgs/Float64` to `command_topic` (default `/gripper/cmd_pos`).
- **Key parameters**: `command_topic`, `open_position`, `closed_position`.
- **Run**:
  ```bash
  ros2 run mam_eurobot_2026 gripper_keyboard
  ```
