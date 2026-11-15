"""Synchronized ROS images/CameraInfo to typed detections and observations."""
import math
import time
import uuid

import cv2
import message_filters
import numpy as np
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import Bool, Header, String
from vision_msgs.msg import (
    Detection2D, Detection2DArray, Detection3D, Detection3DArray, ObjectHypothesisWithPose,
)

from camera.pi_vision import Detector, encode_observation
from .common import SENSOR_QOS, STATUS_QOS, positive, run


def intrinsics_from_info(info, image):
    if (info.width, info.height) != (image.width, image.height):
        raise ValueError("CameraInfo resolution differs from image")
    if not image.header.frame_id or info.header.frame_id != image.header.frame_id:
        raise ValueError("Image and CameraInfo need the same nonempty optical frame")
    if info.binning_x not in (0, 1) or info.binning_y not in (0, 1) or info.roi.x_offset or info.roi.y_offset:
        raise ValueError("Provide intrinsics already adjusted for the actual crop/binning")
    k = np.asarray(info.k, dtype=float).reshape(3, 3)
    if k[0, 0] == 0:
        return None  # Standard CameraInfo convention: uncalibrated.
    d = np.asarray(info.d, dtype=float)
    if (info.distortion_model not in ("plumb_bob", "rational_polynomial")
            or d.size not in (4, 5, 8) or not np.isfinite(k).all()
            or not np.isfinite(d).all() or k[0, 0] <= 0 or k[1, 1] <= 0
            or not np.allclose(k[2], [0, 0, 1])):
        raise ValueError("Unsupported or invalid CameraInfo calibration")
    return k, d


def detection_messages(header, observations, marker_length):
    pixels, metric = Detection2DArray(header=header), Detection3DArray(header=header)
    for item in observations:
        detection = Detection2D(header=header, id=str(item["id"]))
        corners = np.asarray(item["corners_px"])
        low, high = corners.min(axis=0), corners.max(axis=0)
        detection.bbox.center.position.x = float((low[0] + high[0]) / 2)
        detection.bbox.center.position.y = float((low[1] + high[1]) / 2)
        detection.bbox.size_x, detection.bbox.size_y = map(float, high - low)
        # A decoded marker identity, not a measured statistical confidence.
        result = ObjectHypothesisWithPose()
        result.hypothesis.class_id, result.hypothesis.score = str(item["id"]), 1.0
        detection.results.append(result)
        pixels.detections.append(detection)
        if item["pose"] is None:
            continue
        target = Detection3D(header=header, id=str(item["id"]))
        result = ObjectHypothesisWithPose()
        result.hypothesis.class_id, result.hypothesis.score = str(item["id"]), 1.0
        xyz = item["pose"]["tvec_m"]
        result.pose.pose.position.x, result.pose.pose.position.y, result.pose.pose.position.z = xyz
        rvec = np.asarray(item["pose"]["rvec_rad"])
        angle = float(np.linalg.norm(rvec))
        qxyz = rvec * (math.sin(angle / 2) / angle) if angle > 1e-12 else np.zeros(3)
        rotation = result.pose.pose.orientation
        rotation.x, rotation.y, rotation.z = map(float, qxyz)
        rotation.w = math.cos(angle / 2)
        target.results.append(result)
        target.bbox.center = result.pose.pose
        target.bbox.size.x = target.bbox.size.y = marker_length
        target.bbox.size.z = 0.0  # A planar marker, not the object's volume.
        metric.detections.append(target)
    return pixels, metric


class ArucoNode(Node):
    def __init__(self, **kwargs):
        super().__init__("aruco", **kwargs)
        defaults = dict(image_topic="/camera/image_raw", camera_info_topic="/camera/camera_info",
                        dictionary="DICT_4X4_50", marker_length_m=0.0,
                        stale_timeout_sec=1.0, max_image_age_sec=1.0, publish_debug_image=False)
        for key, value in defaults.items():
            self.declare_parameter(key, value)
        value = lambda name: self.get_parameter(name).value
        self.marker_length = float(value("marker_length_m"))
        if not 0 <= self.marker_length < float("inf"):
            raise ValueError("marker_length_m must be nonnegative and finite; zero disables metric pose")
        self.timeout = positive(value("stale_timeout_sec"), "stale_timeout_sec")
        self.max_age = positive(value("max_image_age_sec"), "max_image_age_sec")
        self.detector = Detector(value("dictionary"), marker_length=self.marker_length)
        self.bridge = CvBridge()
        self.pixels = self.create_publisher(Detection2DArray, "/vision/detections_2d", 1)
        self.metric = self.create_publisher(Detection3DArray, "/aruco/detections", 1)
        self.observations = self.create_publisher(String, "/vision/observations", 1)
        self.health = self.create_publisher(Bool, "/vision/healthy", STATUS_QOS)
        self.debug = self.create_publisher(Image, "/vision/debug_image", SENSOR_QOS) if value("publish_debug_image") else None
        self.session, self.seq = uuid.uuid4().hex, 0
        self.last_frame = time.monotonic()
        self.invalid = False
        self.last_header = Header(frame_id="front_camera_optical_frame")
        self.last_size = (0, 0)
        self.image_sub = message_filters.Subscriber(self, Image, value("image_topic"), qos_profile=SENSOR_QOS)
        self.info_sub = message_filters.Subscriber(self, CameraInfo, value("camera_info_topic"), qos_profile=SENSOR_QOS)
        self.sync = message_filters.TimeSynchronizer([self.image_sub, self.info_sub], 5)
        self.sync.registerCallback(self.process)
        self.create_timer(min(0.1, self.timeout / 2), self.watchdog)
        self.health.publish(Bool(data=False))

    def emit(self, header, observations, valid, calibrated, read_ns):
        pixels, metric = detection_messages(header, observations, self.marker_length)
        self.pixels.publish(pixels)
        self.metric.publish(metric)
        payload = encode_observation(self.session, self.seq, valid, *self.last_size,
                                     observations, calibrated, read_ns,
                                     frame_id=header.frame_id,
                                     source_stamp=dict(sec=header.stamp.sec, nanosec=header.stamp.nanosec))
        self.seq += 1
        self.observations.publish(String(data=payload.decode().rstrip()))
        self.health.publish(Bool(data=valid))
        self.invalid = not valid

    def process(self, image, info):
        received_ns = time.monotonic_ns()
        self.last_header, self.last_size = image.header, (image.width, image.height)
        try:
            stamp_ns = image.header.stamp.sec * 1_000_000_000 + image.header.stamp.nanosec
            age = (self.get_clock().now().nanoseconds - stamp_ns) / 1e9
            if age > self.max_age or age < -self.max_age:
                raise ValueError("Image timestamp is stale or from a different ROS clock")
            intrinsics = intrinsics_from_info(info, image)
            self.detector.calibration = intrinsics if self.marker_length > 0 else None
            frame = self.bridge.imgmsg_to_cv2(image, desired_encoding="bgr8")
            observations = self.detector.detect(frame)
            self.last_frame = time.monotonic()
            self.emit(image.header, observations, True, self.detector.calibration is not None, received_ns)
            if self.debug:
                for item in observations:
                    points = np.asarray(item["corners_px"], dtype=np.int32)
                    cv2.polylines(frame, [points], True, (0, 255, 0), 2)
                    cv2.putText(frame, str(item["id"]), tuple(points[0]), cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 255, 0), 1)
                debug = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
                debug.header = image.header
                self.debug.publish(debug)
        except Exception as exc:
            self.get_logger().error(f"Vision frame rejected: {exc}")
            self.emit(image.header, [], False, False, received_ns)

    def watchdog(self):
        if not self.invalid and time.monotonic() - self.last_frame > self.timeout:
            self.get_logger().warning("No synchronized valid camera frames; clearing vision")
            self.emit(self.last_header, [], False, False, time.monotonic_ns())

    def destroy_node(self):
        if self.context.ok():
            self.emit(self.last_header, [], False, False, time.monotonic_ns())
        return super().destroy_node()


def main(args=None):
    run(ArucoNode, args)
