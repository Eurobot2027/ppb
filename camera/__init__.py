"""Source-checkout compatibility for ``python3 -m camera.*`` diagnostics.

The installed ROS package uses the conventional camera/camera/ Python package.
"""
from pathlib import Path

__path__.append(str(Path(__file__).parent / "camera"))
