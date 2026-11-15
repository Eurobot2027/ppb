"""Headless Pi-camera ArUco observations, optionally forwarded to an ESP32 TCP server."""
import argparse
from contextlib import nullcontext
import json
import logging
from pathlib import Path
import socket
import time
import uuid

import cv2
import numpy as np

from .aruco import (
    create_aruco_dictionary, create_detector_parameters, detect_markers, estimate_marker_pose,
)
from .capture import camera_arguments, open_camera, validate_camera_arguments

LOG = logging.getLogger(__name__)


def load_calibration(path, width, height):
    data = json.loads(path.read_text())
    if data.get("schema_version") != 1 or data.get("image_size") != [width, height]:
        raise ValueError("Calibration schema/resolution mismatch; recalibrate this camera mode")
    matrix = np.asarray(data["camera_matrix"], dtype=np.float64)
    distortion = np.asarray(data["dist_coeffs"], dtype=np.float64)
    if (matrix.shape != (3, 3) or distortion.ndim != 1 or distortion.size not in (4, 5, 8, 12, 14)
            or not np.isfinite(matrix).all() or not np.isfinite(distortion).all()
            or matrix[0, 0] <= 0 or matrix[1, 1] <= 0
            or not np.allclose(matrix[2], [0, 0, 1])):
        raise ValueError("Invalid calibration intrinsics/distortion")
    return matrix, distortion


class Detector:
    def __init__(self, dictionary_name, calibration=None, marker_length=None):
        if not hasattr(cv2, "aruco") or not dictionary_name.startswith("DICT_"):
            raise ValueError("OpenCV ArUco support and a DICT_* dictionary are required")
        value = getattr(cv2.aruco, dictionary_name, None)
        if not isinstance(value, int):
            raise ValueError(f"Unknown ArUco dictionary: {dictionary_name}")
        self.dictionary = create_aruco_dictionary(value)
        self.parameters = create_detector_parameters()
        self.calibration = calibration
        self.marker_length = marker_length

    def detect(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = detect_markers(gray, self.dictionary, self.parameters)
        observations = []
        if ids is None:
            return observations
        for points, marker_id in zip(corners, ids.flatten()):
            points = points.reshape(4, 2).astype(np.float32)
            item = dict(id=int(marker_id), center_px=points.mean(axis=0).tolist(),
                        corners_px=points.tolist(), pose=None)
            if self.calibration is not None:
                matrix, distortion = self.calibration
                ok, rvec, tvec = estimate_marker_pose(points, self.marker_length, matrix, distortion)
                if ok and np.isfinite(rvec).all() and np.isfinite(tvec).all() and tvec.ravel()[2] > 0:
                    item["pose"] = dict(rvec_rad=rvec.ravel().tolist(), tvec_m=tvec.ravel().tolist())
            observations.append(item)
        return observations


class ObservationClient:
    """Bounded network waits; drop unsent observations instead of replaying a queue."""
    def __init__(self, host, port):
        self.host, self.port = host, port
        self.sock = None
        self.retry_after = 0.0

    def close(self):
        if self.sock is not None:
            self.sock.close()
            self.sock = None

    def send(self, payload):
        if self.sock is None and time.monotonic() < self.retry_after:
            return False
        try:
            if self.sock is None:
                self.sock = socket.create_connection((self.host, self.port), timeout=0.2)
                self.sock.settimeout(0.2)
            self.sock.sendall(payload)
            return True
        except OSError as exc:
            LOG.warning("Observation link unavailable: %s", exc)
            self.close()
            self.retry_after = time.monotonic() + 1
            return False


def encode_observation(session, seq, frame_ok, width, height, detections, calibrated, read_ns,
                       *, frame_id="camera_optical", source_stamp=None):
    message = dict(v=1, type="vision", session=session, seq=seq, read_monotonic_ns=read_ns,
                   frame=frame_id, frame_ok=frame_ok, calibrated=calibrated,
                   image_size=[width, height], detections=detections)
    if source_stamp is not None:
        message["source_stamp"] = source_stamp
    payload = (json.dumps(message, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    if len(payload) > 65536:
        raise ValueError("Observation exceeds 65536-byte protocol limit")
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    camera_arguments(parser)
    parser.add_argument("--image", type=Path, help="Process one image without camera hardware")
    parser.add_argument("--dictionary", default="DICT_4X4_50", help="Bench default; confirm 2027 rules")
    parser.add_argument("--calibration", type=Path, help="Measured JSON from camera.calibrate")
    parser.add_argument("--marker-length-m", type=float, help="Measured black-square side, same for all IDs")
    parser.add_argument("--esp32-host", help="Optional observation receiver; no motor commands")
    parser.add_argument("--esp32-port", type=int, default=5000)
    parser.add_argument("--frames", type=int, default=0, help="Stop after N frames; 0 runs continuously")
    args = parser.parse_args()
    validate_camera_arguments(parser, args)
    if args.frames < 0 or not 1 <= args.esp32_port <= 65535:
        parser.error("frames must be non-negative and port between 1 and 65535")
    if args.calibration and (args.marker_length_m is None or not 0 < args.marker_length_m < float("inf")):
        parser.error("calibrated pose requires a positive finite --marker-length-m")
    if args.marker_length_m is not None and not args.calibration:
        parser.error("--marker-length-m requires --calibration")
    logging.basicConfig(level=logging.INFO)
    calibration = load_calibration(args.calibration, args.width, args.height) if args.calibration else None
    detector = Detector(args.dictionary, calibration, args.marker_length_m)
    client = ObservationClient(args.esp32_host, args.esp32_port) if args.esp32_host else None
    session, seq = uuid.uuid4().hex, 0

    def emit(ok, detections, read_ns):
        nonlocal seq
        payload = encode_observation(session, seq, ok, args.width, args.height, detections,
                                     calibration is not None, read_ns)
        seq += 1
        print(payload.decode().rstrip(), flush=True)
        if client:
            client.send(payload)

    try:
        if args.image:
            image = cv2.imread(str(args.image))
            if image is None:
                raise ValueError(f"Cannot read {args.image}")
            context = nullcontext(lambda: image)
        else:
            context = open_camera(args.backend, args.camera_index, args.width, args.height, args.fps)
        with context as read:
            while True:
                started = time.monotonic()
                frame = read()
                read_ns = time.monotonic_ns()
                if frame.shape[:2] != (args.height, args.width):
                    raise ValueError("Actual frame size differs from requested size/calibration")
                emit(True, detector.detect(frame), read_ns)
                if args.image or (args.frames and seq >= args.frames):
                    break
                time.sleep(max(0, 1 / args.fps - (time.monotonic() - started)))
    except KeyboardInterrupt:
        pass
    finally:
        try:
            emit(False, [], time.monotonic_ns())
        finally:
            if client:
                client.close()


if __name__ == "__main__":
    main()
