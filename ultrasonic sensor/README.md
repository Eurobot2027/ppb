# Ultrasonic sensing and PID development

S8 `ultrasonic-sensor-pid` (`149cc17`) is already merged into PPB. Its sketches and
video survived the fork; there was no additional unmerged PID branch to recover.
These are Arduino bench experiments, **not ESP32 firmware** or validated robot
navigation. The 2027 robot may use different sensors/drivers.

## Progression

| Folder | Development |
| --- | --- |
| `1. ultrasonic` | Trigger/echo time-of-flight measurement and serial distance output |
| `2. PID_1st iteration` | Signed motor output around a 20 cm target, bounded integral and basic output dead zone |
| `3. pid_Plotter_Final` | Five-reading average, filtered derivative, integral/output limits, minimum PWM, dead zone, direction-change hold time and plotter traces |
| `PID Video` | Historical demonstration, not quantitative acceptance evidence |

The final sketch separates P/I/D contributions for diagnosis, uses a 25 ms echo
timeout, rejects implausible distances and stops on bad readings. These are useful
control ideas to carry into local embedded loops.

## Issues before an ESP32 port

- `error = setPoint - distance` gives a **negative** error when the object is far
  away; comments claiming the opposite are incorrect. Confirm physical motor and
  sensor direction before selecting the sign of the controller.
- The first PID iteration returns on an out-of-range reading without explicitly
  stopping, potentially retaining the previous motor output. Do not adopt it as
  fault handling. The final version does stop on those readings.
- Integral state survives invalid readings; the distance average starts with
  artificial setpoint samples. Review reset/reacquisition behavior and initial
  filter bias. Integral clamping is not full actuator-aware anti-windup.
- `pulseIn` and delays block the loop. A comment calls it 20 Hz, but actual period
  includes echo waiting and work. Use measured timing and bounded acquisition.
- Plotter `PWM_output` is recomputed from PID output and can disagree with actual
  output when direction hold stops the motor. Log the actual commanded driver state.
- AVR pin numbers 9/10/5/6/7, `analogWrite` assumptions, minimum PWM, gains and
  direction conventions must be revisited for the selected ESP32/driver.
- Verify sensor echo voltage against ESP32 input specifications; do not copy
  wiring blindly. Confirm units when sending telemetry (old code uses cm).

Next: choose sensors, implement timestamped validity/status telemetry and local
motor control on ESP32, measure noise/latency, then retune with the actual robot.
Keep stop/expiry behavior local to the ESP32 and test missing echoes, saturation
and lost Pi/link. See [architecture](../docs/ARCHITECTURE_2027.md).
