from glob import glob
from setuptools import find_packages, setup

setup(
    name="ppb_vision",
    version="0.1.0",
    packages=find_packages(),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/ppb_vision"]),
        ("share/ppb_vision", ["package.xml"]),
        ("share/ppb_vision/launch", glob("launch/*.launch.py")),
        ("share/ppb_vision/config", glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    zip_safe=False,
    maintainer="PPB Eurobot team",
    maintainer_email="liendomf@univ-smb.fr",
    description="ROS 2 Humble vision for the Eurobot 2027 Raspberry Pi",
    license="Apache-2.0",
    entry_points={"console_scripts": [
        "camera_node = camera.ros.camera_node:main",
        "aruco_node = camera.ros.aruco_node:main",
        "esp32_bridge = camera.ros.esp32_bridge:main",
        "capture = camera.capture:main",
        "calibrate = camera.calibrate:main",
        "vision_cli = camera.pi_vision:main",
    ]},
)
