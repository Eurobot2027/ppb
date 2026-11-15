# Eurobot 2027 adaptation and next steps

The target is **2027**. The inherited 2026 hazelnut-crate/cursor/pantry/nest
strategy, mat, landmarks and mechanics are not a 2027 specification.

## Rules baseline

On **15 November 2026**, the [official 2027 page](https://www.eurobot.org/eurobot-contest/eurobot-2027/)
lists general/game rules in English, French and Spanish and playground mat files.
Rules are published; do not wait for an assumed future release. The English
approval checklist is still labelled forthcoming on that page.

- [General rules, English](https://www.eurobot.org/wp-content/uploads/2026/10/Eurobot_General_Rules_SR_EN.pdf),
  whose cover says official 1.4.
- [2027 game rules, English](https://www.eurobot.org/wp-content/uploads/2026/10/Eurobot2027_Rules_EN.pdf).
- Use the official page for updated revisions and mat/checklist downloads. Record
  exact document revisions, dates and checksums for design decisions.

This recovery did **not** complete a clause-by-clause review of the game PDF:
the browser could not retrieve the large file and native network access was
unavailable. No new 2027 object IDs, marker sizes, scoring rules or camera
permissions have been asserted or encoded here.

## Decisions to record before hardware design

| Decision | Where to apply it |
| --- | --- |
| Field dimensions, origin/axes, side mirroring, starting poses | New season-specific map/world configuration |
| Legal markers, sizes, placement and visual targets | Vision configuration and labelled image dataset |
| Permitted camera placement and remote-link arrangement | Architecture with rule references |
| Objects, contact geometry, mechanisms and scoring | New actuator design/strategy; old CAD/gripper not binding |
| Envelope, power, stop/start and beacon constraints | Electronics/mechanics requirements |
| Match timing, end conditions and priorities | New FSM with timeouts and recovery |

Keep `mam_eurobot_2026` as the legacy package name while using it for reference.
Renaming alone would not convert its assets/algorithms to 2027. Add actual 2027
constants as season configuration after reviewing rules; do not replace historical
values with guesses.

## Ordered bring-up plan

1. **Rules and inventory:** record revisions, Pi/camera/lens, mounting (onboard or
   external), ESP32 variant, network, drivetrain, sensors and power. Decide reuse.
2. **Capture/calibration:** follow [camera/README.md](../camera/README.md). Establish
   repeatable sharp images and independent pose-error measurements at real working
   distances, with resolution/crop/focus recorded.
3. **Vision data/performance:** collect real 2027 targets with lighting/occlusion
   variation. Measure misses, false IDs, pose error, rate, latency and thermal
   behavior. Set thresholds from robot accuracy/stopping needs, not arbitrary FPS.
4. **ESP32 logging receiver:** implement framed observations, reconnects, bounded
   buffering and age handling first, with no actuators connected.
5. **Local control/telemetry:** add encoder sampling, drivers, motor loops, sensor
   validity, expiry and stops. Retune/reassess PID. Bench-check direction,
   saturation, lost sensors and lost Pi/link before navigation.
6. **Localization:** measure camera-to-base/marker-to-base extrinsics; select a map
   frame; fuse vision/encoders and reject stale/poor observations. Gazebo truth and
   commanded-speed integration are not real localization.
7. **2027 navigation/actions:** replace maps, objects, goals and manipulation.
   Keep ROS 2 Humble as selected; choose navigation/control components after Pi resource measurements.
   Use actuator feedback; an observed ID must not directly trigger movement.
8. **Trials:** replay frames, run short field sequences, then full matches. Include
   Pi/ESP32 restart, WiFi loss, unplugged camera, blocked actuators and low power.
   Capture logs and resolve inherited coordinate issues before autonomy claims.

The first milestone is **reliable calibrated Pi vision plus a logging-only ESP32
link**. Full strategy follows measurable observation/control/localization behavior.
