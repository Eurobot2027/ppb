# Ancestor development recovery

Audit date: **15 November 2026**. Starting PPB HEAD:
`d34076c3f7e9021185f19c5a881da0dcc9c69c53` (`testing`), based on S8/main
`5c855cf5e7fb65be8010d61b204ff233d0eefcc6`.

## Scope and evidence

Read-only inspection covered both local ancestor repositories:

- S8: `/run/media/retphilo/Data1/Uni/Polytech/S8/Eurobot/jon-snowbot`
  (`https://github.com/Eurobot-2026/jon-snowbot.git`).
- S7: `/run/media/retphilo/Data1/Uni/Polytech/S7/Eurobot/Eurobot/mam_eurobot_2026_T1`
  (`https://github.com/KarimSherry/mam_eurobot_2026_T1.git`).

Inspected local branches, cached remote-tracking branches, commit ancestry,
changed files, working-tree status and **all five S7 stash entries**, including
their index-parent commits. No network fetch from GitHub was performed, so this
is a recovery of the available local snapshots, not a claim that no additional
server branches exist. The S8 checkout had an untracked `.codex` file; it was not
project development and was not copied. S7 was clean. PPB's untracked `.vscode/`
and `testing.txt` were left alone.

The recovery has also been applied to PPB's Git metadata: 40 branch snapshot refs
under `legacy-s7/...` / `legacy-s8/...` and five `refs/legacy-stashes/s7/*` refs.
Current `testing` HEAD, the index and original `origin` remote were not replaced;
neither source repository was modified. The code/documentation changes remain
uncommitted for review.

[INVENTORY.md](history/INVENTORY.md) lists all **46 source refs**, full hashes are
in [refs.json](history/refs.json). The obsolete SolidWorks branch is explicitly
excluded. The remaining 45 refs identify **24 distinct commits not reachable
from starting PPB HEAD**. This includes stashes, index snapshots and old text
placeholders, not 24 independent finished features.

The [incremental bundle](history/ancestors.bundle) preserves missing commit
objects and ancestry against PPB's existing history; it is about 0.6 MB.
[Patches](history/patches/) expose source changes without checking out old branches.
Generated build/install/log/cache files are filtered from the readable patches.
Original snapshots remain in the bundle for exact recovery, including historical
generated files. No old SolidWorks tree is imported into the working source.

## What was actually missing

| Development | Source / evidence | Recovery decision |
| --- | --- | --- |
| Keyboard ROS teleoperation | `1-ros-sim`: `c441fb2`, `60c93b7` | Restored `teleop/teleop_keyboard.py`, registered a real console executable and added configurable command topic. Did not restore the old launcher's broken source-path fallback or bytecode. |
| Go-to-goal wheel controller | `feature/path-follower`: `f593fd8` | Preserved exact source in `legacy/movement/path_follower.py`; not enabled for hardware. It integrates wheel rad/s as linear distance and has no encoder/vision feedback. |
| Local mecanum/model experiments | S7 local `feature/strategy-simulation`, ahead of cached origin by `d9126c2`, `546ec2b` | Preserved patches/history and source SDF/xacro references under `legacy/simulation/`. Not merged over the newer differential-drive model. Old mesh/CAD designs are not adopted for 2027. |
| Localization branch | `415fcba` | Only creates an empty localization `__init__.py`; current project already has actual localization modules. No missing localization algorithm was found there. |
| Ignore rules | `e413293` | Carried forward useful build/cache exclusion as native `.gitignore` updates, retaining existing rules. |
| Test/strategy placeholder branch | `9dfd501` and six ancestors | Preserved history/patches only. Text files contain `ros` and a reminder to write strategy, not a hidden strategy implementation. |
| SolidWorks designs | `8921e5d` | Audited by ref/change list, deliberately excluded at the user's request. |

The S7/S8 copies of the same ref are recorded separately. Local and remote tips
are not interchangeable: S7 local strategy has two commits absent from its cached
remote, and gripper/main/path-planning tips differ between the repositories.

## Stash findings

| S7 stash | Hash | Content and disposition |
| --- | --- | --- |
| 0 | `db90f3b` | Twist-based mecanum demo. Same controller content already appears in PPB's movement folder; preserved snapshot, no downgrade. |
| 1 | `28602f8` | One-line mat adjustment; historical geometry, preserved only. |
| 2 | `809dc79` | `MAC = True` to `False` for planning launch. Replaced both branches' environment hacks with native inheritance instead. |
| 3 | `2b9f675` | Mixed wheel/Twist strafing, velocity bridge and model changes; experimental, preserved only. |
| 4 | `c458cd5` | Line-ending-only changes to early templates/placeholders; no semantic diff with `--ignore-space-at-eol`. Preserved original snapshot. |

Stash index parents account for some of the 24 commits. They are archived as
objects as well, not applied to this worktree.

## Vision advances already carried into main

These are inherited developments retained and documented, not newly discovered
unmerged implementations:

| Capability | Evidence / location | Current limitations |
| --- | --- | --- |
| Simulated ArUco targets/detection | `4396c65`, `171b5c5`, `cdaccaa`; ROS `vision/aruco_detector.py` | 2026 target IDs/dimensions, detection stability issue documented upstream |
| HSV segmentation | `5905edb`, `2bfa3de`; `color_detector.py` | Fixed game color assumptions; GUI usage |
| Fixed-camera/world pose | `237ece3`; `world_to_topcamera.py` | Known landmark and fixed camera; approximate intrinsics fallback in legacy code |
| Cursor projection | `3c9ff8d`, `5e4943c`; `estimate_cursor_position.py` | 2026 cursor geometry/height and projection constraints |
| Camera/base TF and detections in map | `4e1a96f`, `689cf8d`; URDF and `detected_crates_tf.py` | Extrinsics must be measured; choose one coherent frame tree |
| Robot pose from external camera | Current `robot_pose_from_beacon.py` and robot YAML | Requires known external camera pose plus marker-to-base transform; not onboard localization |
| Real-camera calibration and headless viewing | S8 `75015d2` through `de90c8f`; `camera/` | RDK/V4L2 assumptions and old calibration |
| Network visibility flag | S8 `d9bb85e`; `aruco_tcp_flag_sender.py` | Only presence, no pose/ACK; old Arduino target |

The named ArUco, color, gripper, path-planning, world and ledge feature tips are
already ancestors of PPB. Losing their branch labels did not lose those merged
changes. None of the inspected unmerged branch/stash changes adds a newer vision
pipeline beyond what was already inherited.

## New work in this recovery

- Native Picamera2/OpenCV capture and fresh-directory image collection.
- Non-destructive JSON checkerboard calibration with size checks.
- Headless ArUco observation entry point and optional framed JSON TCP sender;
  metric poses require calibration/marker size and exact runtime dimensions.
- Explicit ROS front-camera frame config and rejection of unknown topics.
- Native environment handling in competition/test/planning launch files; removed
  global process kills, container-home overrides and fixed VNC display assumptions.
- Restored teleop console entry, fixed staging planner executable spelling,
  removed the nonexistent `behavior_tree.strategy_tree` console entry.
- Subsystem guides, 2027 architecture/roadmap and focused regression checks.

These changes do not finish ESP32 firmware, a 2027 strategy or a simulator port.
See [validation](VALIDATION.md), [native setup](NATIVE_SETUP.md), and the
[ordered next steps](EUROBOT_2027.md).

## ROS 2 Humble follow-up

At the user's request, native hardware vision is now an independent ROS 2 Humble
package (`ppb_vision`), with shared offline helpers, Image/CameraInfo publication,
synchronized standard detections, health/watchdogs, frame-capture service, optional
ROS-to-ESP32 TCP observations and an installed launch file. See
[ROS setup](../camera/ROS2.md) and [updated validation](VALIDATION.md).
Generated build/package/cache/log/bag and local editor files are ignored; the
source archive, recovery patches and historical calibration fixtures stay tracked.
