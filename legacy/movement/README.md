# Unmerged go-to-goal experiment

`path_follower.py` is copied verbatim from S7/S8 `feature/path-follower`,
`f593fd892d7bfb56902d3a2bee66008901cec11f`. It subscribes to a `Pose2D` goal on
`/goal`, rotates toward it and publishes four wheel speeds on `/omni/*`.

It is not a path follower using odometry: it estimates position by integrating
commanded wheel rad/s as if they were metres/s, and similarly treats wheel rotation
speed as robot yaw rate. Wheel radius/geometry, slip and sensor feedback are
missing. Goal orientation is ignored, and shutdown has no explicit stop/finally
path. It targets an old wheel-bridge model, not the current differential-drive
simulation or an ESP32.

It is intentionally not registered as an executable or launched automatically.
Reuse the staged rotate/translate idea only after deriving the selected drivetrain
kinematics and using measured odometry/vision with timeouts/stops. The newer
Nav2 FollowPath client remains in the active legacy package.
