"""Native ROS 2 Humble vision: Pi/USB/replay camera -> detections -> optional TCP."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    defaults = dict(backend="picamera2", camera_index="0", width="640", height="480", fps="15.0",
                    frame_id="front_camera_optical_frame", calibration_file="", image_path="",
                    capture_directory="", dictionary="DICT_4X4_50", marker_length_m="0.0",
                    camera_enabled="true", image_topic="/camera/image_raw",
                    camera_info_topic="/camera/camera_info", publish_debug_image="false",
                    stale_timeout_sec="1.0", max_image_age_sec="1.0", use_sim_time="false",
                    enable_esp32="false", esp32_host="", esp32_port="5000")
    args = [DeclareLaunchArgument(name, default_value=value) for name, value in defaults.items()]

    def value(name, kind=str):
        return ParameterValue(LaunchConfiguration(name), value_type=kind)

    camera_params = {name: value(name, kind) for name, kind in dict(
        backend=str, camera_index=int, width=int, height=int, fps=float, frame_id=str,
        calibration_file=str, image_path=str, capture_directory=str, image_topic=str,
        camera_info_topic=str, use_sim_time=bool).items()}
    vision_params = {name: value(name, kind) for name, kind in dict(
        image_topic=str, camera_info_topic=str, dictionary=str, marker_length_m=float,
        publish_debug_image=bool, stale_timeout_sec=float, max_image_age_sec=float, use_sim_time=bool).items()}
    return LaunchDescription(args + [
        Node(package="ppb_vision", executable="camera_node", name="camera", output="screen",
             condition=IfCondition(LaunchConfiguration("camera_enabled")), parameters=[camera_params]),
        Node(package="ppb_vision", executable="aruco_node", name="aruco", output="screen",
             parameters=[vision_params]),
        Node(package="ppb_vision", executable="esp32_bridge", name="esp32_bridge", output="screen",
             condition=IfCondition(LaunchConfiguration("enable_esp32")),
             parameters=[dict(host=value("esp32_host"), port=value("esp32_port", int),
                              stale_timeout_sec=value("stale_timeout_sec", float))]),
    ])
