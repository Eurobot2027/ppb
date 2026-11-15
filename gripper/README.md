# Gripper and actuator history

The filename `gripper.ino` is misleading: its current contents are a **WiFiEsp
HTTP server example** for an Arduino with ESP8266/OSOYOO shield. It uses
SoftwareSerial on pins 4/5 and serves a web page on port 80. It does not implement
a gripper action, a TCP flag receiver on port 5000, or native ESP32 firmware.
The old S8 WiFi experiment (`1e7ae69`) was explicitly reported not working.

Actual historical gripping behavior exists in the ROS simulation:
[keyboard gripper](../mam_eurobot_2026/mam_eurobot_2026/gripper/README.md),
`models/gripper`, and the task-manager FSM. These are 2026 examples using a
simulated position command and grasp feedback. The gripper branch was already
merged; no missing production gripper controller was found.

For **2027**, choose the mechanism from the new objects/rules. The old gripper,
electronics and CAD impose no design requirement. Define mechanism capabilities,
limits, command units, completion/fault feedback and timeout behavior, then add
an ESP32 implementation. Keep that adapter separate from vision, so replacing
the mechanism does not require changing marker detection. See the
[architecture](../docs/ARCHITECTURE_2027.md).
