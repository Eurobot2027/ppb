"""Publish Pi/USB/replay images and matching CameraInfo through ROS 2."""
from pathlib import Path

import cv2
import numpy as np
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import Bool
from std_srvs.srv import Trigger

from camera.capture import open_camera
from camera.pi_vision import load_calibration
from .common import SENSOR_QOS, STATUS_QOS, positive, run


class CameraNode(Node):
    def __init__(self, **kwargs):
        super().__init__("camera", **kwargs)
        defaults = dict(backend="picamera2", camera_index=0, width=640, height=480,
                        fps=15.0, frame_id="front_camera_optical_frame", calibration_file="",
                        image_path="", capture_directory="", image_topic="/camera/image_raw",
                        camera_info_topic="/camera/camera_info")
        for key, value in defaults.items():
            self.declare_parameter(key, value)
        self.value = lambda name: self.get_parameter(name).value
        self.width, self.height = int(self.value("width")), int(self.value("height"))
        self.fps = positive(self.value("fps"), "fps")
        if self.width <= 0 or self.height <= 0 or not self.value("frame_id"):
            raise ValueError("Positive image dimensions and an optical frame_id are required")
        self.info = CameraInfo(width=self.width, height=self.height)
        calibration = self.value("calibration_file")
        if calibration:
            k, d = load_calibration(Path(calibration), self.width, self.height)
            # Standard ROS distortion models cover OpenCV's 4/5/8 coefficient forms.
            if d.size not in (4, 5, 8):
                raise ValueError("ROS CameraInfo requires 4, 5 or 8 distortion coefficients")
            self.info.k = k.ravel().tolist()
            self.info.d = d.tolist() if d.size != 4 else [*d.tolist(), 0.0]
            self.info.distortion_model = "rational_polynomial" if d.size == 8 else "plumb_bob"
            self.info.r = np.eye(3).ravel().tolist()
            projection = np.zeros((3, 4))
            projection[:, :3] = k
            self.info.p = projection.ravel().tolist()
        self.bridge = CvBridge()
        self.images = self.create_publisher(Image, self.value("image_topic"), SENSOR_QOS)
        self.infos = self.create_publisher(CameraInfo, self.value("camera_info_topic"), SENSOR_QOS)
        self.health = self.create_publisher(Bool, "/camera/healthy", STATUS_QOS)
        self.health.publish(Bool(data=False))
        self.latest = None
        self.capture_context = None
        self.read = None
        self.capture_directory = None
        self.capture_count = 0
        if self.value("capture_directory"):
            self.capture_directory = Path(self.value("capture_directory")).expanduser()
            self.capture_directory.mkdir(parents=True, exist_ok=False)
        backend = self.value("backend")
        if backend == "image":
            image = cv2.imread(self.value("image_path"))
            if image is None or image.shape[:2] != (self.height, self.width):
                raise ValueError("Replay image must exist and match configured width/height")
            self.read = lambda: image.copy()
        elif backend not in ("picamera2", "opencv"):
            raise ValueError("backend must be picamera2, opencv or image")
        self.create_service(Trigger, "~/save_frame", self.save_frame)
        self.timer = self.create_timer(1.0 / self.fps, self.capture)
        self.get_logger().info(f"Camera backend={backend}; frame={self.value('frame_id')}")

    def capture(self):
        try:
            if self.read is None:
                self.capture_context = open_camera(self.value("backend"), self.value("camera_index"),
                                           self.width, self.height, self.fps)
                self.read = self.capture_context.__enter__()
            frame = self.read()
            if frame is None or frame.shape[:2] != (self.height, self.width):
                raise ValueError("Captured dimensions differ from camera calibration/configuration")
            message = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
            # Retrieval-time ROS stamp, not a claim of hardware exposure timestamp.
            message.header.stamp = self.get_clock().now().to_msg()
            message.header.frame_id = self.value("frame_id")
            self.info.header = message.header
            self.latest = frame.copy()
            self.infos.publish(self.info)
            self.images.publish(message)
            self.health.publish(Bool(data=True))
        except Exception as exc:
            self.latest = None
            self.health.publish(Bool(data=False))
            self.get_logger().error(f"Camera failed: {exc}")
            self.timer.cancel()
            self.close_camera()

    def save_frame(self, request, response):
        if self.capture_directory is None or self.latest is None:
            response.success = False
            response.message = "Set a fresh capture_directory and wait for a valid frame"
            return response
        path = self.capture_directory / f"image_{self.capture_count:04d}.png"
        try:
            ok, encoded = cv2.imencode(".png", self.latest)
            if not ok:
                raise RuntimeError("Image encoding failed")
            with path.open("xb") as handle:
                handle.write(encoded.tobytes())
            self.capture_count += 1
            response.success, response.message = True, str(path)
        except (OSError, RuntimeError, cv2.error) as exc:
            response.success, response.message = False, str(exc)
        return response

    def close_camera(self):
        if self.capture_context is not None:
            context, self.capture_context = self.capture_context, None
            context.__exit__(None, None, None)
        self.read = None

    def destroy_node(self):
        self.close_camera()
        if self.context.ok():
            self.health.publish(Bool(data=False))
        return super().destroy_node()


def main(args=None):
    run(CameraNode, args)
