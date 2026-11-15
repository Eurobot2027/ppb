# Historical simulation models

Already inherited: 2026 arena/mat, ArUco textures, blue/yellow crates, cursor,
gripper and simple robot. World/ledge and gripper feature branches were merged;
the main robot was later simplified to differential drive. Old mecanum source
experiments are retained under [legacy simulation](../../legacy/simulation/README.md)
rather than replacing this model.

These assets describe the 2026 game and are not a 2027 robot/field design. Old CAD
is irrelevant to the current hardware choice and the separate SolidWorks branch
was not imported. The active model includes mixed Ignition/Gazebo plugin naming;
port and validate it against a single simulator release before runtime claims.

Next: derive 2027 field/target assets from official sources, choose the drivetrain,
measure inertias/contact geometry/camera extrinsics and create a coherent model
and bridge configuration. Do not infer real motor/actuator wiring from SDF topics.
