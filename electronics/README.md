# Electronics: historical evidence and the 2027 redesign

S8 `electronics-documentation` (`2b4572c`) is already merged in PPB. It added
`JON-SNOWBOT_Electronics_Documentation.pdf`, `BOM.xlsx`, `EUROBOT.kicad_sch` and
`robocup.kicad_sch`. The fork did not lose these files. They remain reference
documents, not an approved 2027 BOM, ESP32 pinout or wiring specification.

The new direction is a Pi for vision and an ESP32 for motors, actuators and
sensors. Existing electronics can be replaced if unsuitable. No recovered branch
contains a ready Pi/ESP32 controller stack; the old WiFi test belongs to an
Arduino/ESP8266 shield and was reported unsuccessful in its commit message.

## Reuse decisions

| Retain as knowledge | Reassess for 2027 |
| --- | --- |
| Documentation/BOM/schematic history | All pin mappings, board assumptions, connectors and driver ratings |
| Power/driver/sensor design questions | Pi power stability, motor/actuator power, current peaks and grounding |
| Prior bench observations | Actual ESP32 variant, I/O voltage compatibility, encoder inputs and PWM API |
| Local control principles | Stop/start circuitry and competition requirements from the current rules |

These files were inventoried; their schematics and BOM have **not** been
electrically revalidated. Do not order/build directly from the old BOM.

Next: select boards/drivers/sensors, record voltage and current requirements,
design power/stop behavior, allocate ESP32 pins and interfaces, then produce a
new schematic/BOM with the exact board revisions. Bench-test local sensing and
stopping before connecting the Pi control path. See the
[architecture](../docs/ARCHITECTURE_2027.md) and [2027 plan](../docs/EUROBOT_2027.md).
