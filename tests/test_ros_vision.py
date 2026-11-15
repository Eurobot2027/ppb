"""Real Humble integration tests; skipped in a non-ROS Python environment."""
import json
import time

import cv2
import numpy as np
import pytest

rclpy = pytest.importorskip('rclpy')
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from std_msgs.msg import String
from std_srvs.srv import Trigger
from vision_msgs.msg import Detection3DArray
from camera.ros.camera_node import CameraNode
from camera.ros.aruco_node import ArucoNode


def test_ros_camera_detections_capture_and_expiry(tmp_path):
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker = cv2.aruco.generateImageMarker(dictionary, 1, 160)
    frame = np.full((480, 640), 255, np.uint8)
    frame[160:320, 240:400] = marker
    image = tmp_path / 'marker.png'
    cv2.imwrite(str(image), frame)
    calibration = tmp_path / 'calibration.json'
    calibration.write_text(json.dumps(dict(schema_version=1, image_size=[640,480],
        camera_matrix=[[800,0,320],[0,800,240],[0,0,1]],dist_coeffs=[0]*5)))
    rclpy.init()
    camera = vision = probe = None
    executor = SingleThreadedExecutor()
    observations, metric = [], []
    def wait_until(condition, timeout=8):
        deadline = time.monotonic() + timeout
        while not condition() and time.monotonic() < deadline:
            executor.spin_once(timeout_sec=0.05)
        assert condition()
    try:
        camera = CameraNode(parameter_overrides=[Parameter(k,value=v) for k,v in dict(
            backend='image',image_path=str(image),calibration_file=str(calibration),
            capture_directory=str(tmp_path/'captures')).items()])
        vision = ArucoNode(parameter_overrides=[Parameter('marker_length_m',value=0.04),
            Parameter('stale_timeout_sec',value=0.3)])
        probe = Node('vision_test_probe')
        probe.create_subscription(String,'/vision/observations',lambda m:observations.append(json.loads(m.data)),1)
        probe.create_subscription(Detection3DArray,'/aruco/detections',metric.append,1)
        for node in (camera,vision,probe): executor.add_node(node)
        wait_until(lambda: any(m['frame_ok'] and m['detections'] for m in observations) and any(m.detections for m in metric))
        target = next(m for m in metric if m.detections).detections[0]
        assert target.header.frame_id == 'front_camera_optical_frame'
        assert target.results[0].pose.pose.position.z == pytest.approx(.2,abs=.003)
        client = probe.create_client(Trigger,'/camera/save_frame')
        assert client.wait_for_service(timeout_sec=2)
        future = client.call_async(Trigger.Request())
        wait_until(future.done)
        assert future.result().success
        assert (tmp_path/'captures/image_0000.png').exists()
        camera.timer.cancel()
        observations.clear()
        wait_until(lambda: any(not m['frame_ok'] for m in observations))
    finally:
        for node in (camera,vision,probe):
            if node is not None:
                executor.remove_node(node)
                node.destroy_node()
        executor.shutdown()
        rclpy.shutdown()
