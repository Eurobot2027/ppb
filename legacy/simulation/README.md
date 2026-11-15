# Local strategy/simulation experiments

`simple_robot/_model.sdf` and `simple_robot/urdf/*` are source snapshots from S7
local `feature/strategy-simulation`, tip `546ec2bfe09fb3e6d710bec04cb4805ac61142a7`.
Its two unmerged commits are `d9126c2` (WIP controller/model changes) and `546ec2b`
(additional SDF/URDF and map/build outputs). The cached origin tip `d444f86` itself
was already merged into PPB.

The inherited commit messages report unstable mecanum dynamics and incomplete
strafing. These models are not validated fixes. Mesh links include old machine/
workspace assumptions and are not made portable here; old CAD/mesh designs are
irrelevant to the selected 2027 hardware. Source is kept to explain the modeling
experiments, not to provide a runnable mechanical assembly.

Generated build/install/log/cache trees were not copied into this working folder.
Original snapshots, the alternate field map and controller/model diffs remain
recoverable from the [bundle/patches](../../docs/history/README.md). Keep the
current simulation model until a deliberate 2027 drivetrain/model revision.
