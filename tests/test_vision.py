"""Camera-free regression tests for real detection, calibration and stream output."""
import json
from pathlib import Path
import socket
import subprocess
import sys

import cv2
import numpy as np
import pytest
import yaml

from camera.calibrate import calibrate
from camera.pi_vision import Detector, ObservationClient, encode_observation, load_calibration
from mam_eurobot_2026.mam_eurobot_2026.vision.config import lookup_camera_config

ROOT = Path(__file__).resolve().parents[1]


def marker_image():
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    if hasattr(cv2.aruco, "generateImageMarker"):
        marker = cv2.aruco.generateImageMarker(dictionary, 1, 160)
    else:
        marker = cv2.aruco.drawMarker(dictionary, 1, 160)
    image = np.full((480, 640), 255, dtype=np.uint8)
    image[160:320, 240:400] = marker
    return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)


def test_detect_marker_and_absence_without_fabricating_metric_pose():
    detector = Detector("DICT_4X4_50")
    detections = detector.detect(marker_image())
    assert [d["id"] for d in detections] == [1]
    assert detections[0]["center_px"] == pytest.approx([319.5, 239.5], abs=1)
    assert detections[0]["pose"] is None
    assert detector.detect(np.full((480, 640, 3), 255, np.uint8)) == []


def test_metric_pose_has_correct_scale_and_positive_depth():
    matrix = np.array([[800., 0, 320], [0, 800, 240], [0, 0, 1]])
    detector = Detector("DICT_4X4_50", (matrix, np.zeros(5)), 0.04)
    pose = detector.detect(marker_image())[0]["pose"]
    # A 4 cm square spanning ~160 pixels with f=800 lies ~20 cm from camera.
    assert pose["tvec_m"] == pytest.approx([0, 0, 0.2], abs=0.003)


def test_wrong_dictionary_name_is_rejected():
    with pytest.raises(ValueError, match="dictionary"):
        Detector("DICT_NOT_A_REAL_DICTIONARY")


def calibration_data():
    return dict(schema_version=1, image_size=[640, 480],
                camera_matrix=[[800, 0, 320], [0, 800, 240], [0, 0, 1]], dist_coeffs=[0] * 5)


@pytest.mark.parametrize("change", [
    {"image_size": [1280, 720]}, {"schema_version": 99},
    {"dist_coeffs": [0, 0]}, {"dist_coeffs": [float("nan")] * 5},
    {"camera_matrix": [[-800, 0, 320], [0, 800, 240], [0, 0, 1]]},
])
def test_invalid_calibration_is_rejected(tmp_path, change):
    data = calibration_data()
    data.update(change)
    path = tmp_path / "calibration.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_calibration(path, 640, 480)


def test_valid_calibration_loads(tmp_path):
    path = tmp_path / "calibration.json"
    path.write_text(json.dumps(calibration_data()))
    matrix, distortion = load_calibration(path, 640, 480)
    assert matrix.shape == (3, 3)
    assert distortion.shape == (5,)


def test_calibrate_synthetic_checkerboards_recovers_intrinsics(tmp_path):
    # Render known planar boards through a calibrated pinhole camera, then solve
    # from images exactly as a user does. This checks dimensions and corner order.
    square = 0.025
    board = np.zeros((420, 540), dtype=np.uint8)
    for y in range(7):
        for x in range(9):
            board[y * 60:(y + 1) * 60, x * 60:(x + 1) * 60] = 255 * ((x + y) % 2)
    k = np.array([[800., 0, 320], [0, 800, 240], [0, 0, 1]])
    world = np.array([[0, 0, 0], [9 * square, 0, 0],
                      [9 * square, 7 * square, 0], [0, 7 * square, 0]], dtype=np.float64)
    src = np.float32([[0, 0], [539, 0], [539, 419], [0, 419]])
    for i in range(15):
        rvec = np.array([0.10 + (i % 5) * .08, -.3 + (i % 3) * .18, -.15 + i * .02])
        tvec = np.array([-.14 + (i % 3) * .025, -.10 + (i % 4) * .015, .62 + (i % 5) * .035])
        corners, _ = cv2.projectPoints(world, rvec, tvec, k, np.zeros(5))
        h = cv2.getPerspectiveTransform(src, corners.reshape(4, 2).astype(np.float32))
        frame = cv2.warpPerspective(board, h, (640, 480), borderValue=200)
        assert cv2.imwrite(str(tmp_path / f"board_{i:02d}.png"), frame)
    result = calibrate(tmp_path, 8, 6, square)
    assert len(result["images"]) >= 10
    assert result["image_size"] == [640, 480]
    assert result["rms_px"] < 0.5
    assert result["camera_matrix"][0][0] == pytest.approx(800, rel=0.06)
    assert result["camera_matrix"][1][1] == pytest.approx(800, rel=0.06)


def test_calibration_rejects_mixed_resolutions_and_no_boards(tmp_path):
    cv2.imwrite(str(tmp_path / "a.png"), np.zeros((480, 640), np.uint8))
    with pytest.raises(ValueError, match="at least 10"):
        calibrate(tmp_path, 8, 6, .025)
    cv2.imwrite(str(tmp_path / "b.png"), np.zeros((240, 320), np.uint8))
    with pytest.raises(ValueError, match="Mixed image sizes"):
        calibrate(tmp_path, 8, 6, .025)


def test_cli_observation_then_shutdown_and_input_failure(tmp_path):
    path = tmp_path / "marker.png"
    cv2.imwrite(str(path), marker_image())
    result = subprocess.run([sys.executable, "-m", "camera.pi_vision", "--image", str(path)],
                            cwd=ROOT, text=True, capture_output=True, check=True)
    messages = [json.loads(line) for line in result.stdout.splitlines()]
    assert len(messages) == 2
    assert messages[0]["detections"][0]["id"] == 1
    assert messages[0]["frame_ok"] is True
    assert messages[0]["seq"] == 0
    assert messages[1]["seq"] == 1
    assert messages[0]["session"] == messages[1]["session"]
    assert messages[1]["frame_ok"] is False and messages[1]["detections"] == []
    failure = subprocess.run([sys.executable, "-m", "camera.pi_vision", "--image", str(path),
                              "--width", "1280"], cwd=ROOT, text=True, capture_output=True)
    assert failure.returncode != 0
    assert json.loads(failure.stdout)["frame_ok"] is False


def test_stream_transport_framing():
    # Real loopback TCP server; never connects to an external device/service.
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.settimeout(1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    client = ObservationClient(*listener.getsockname())
    payload = encode_observation("s", 0, True, 640, 480, [], False, 100)
    try:
        assert client.send(payload)
        assert client.send(payload)
        receiver, _ = listener.accept()
        with receiver:
            receiver.settimeout(1)
            with receiver.makefile("rb") as stream:
                assert json.loads(stream.readline())["frame_ok"] is True
                assert json.loads(stream.readline())["seq"] == 0
    finally:
        client.close()
        listener.close()


def test_link_failure_drops_data_then_reconnects(monkeypatch):
    now, attempts, delivered = [0.0], [], []

    class Connection:
        def settimeout(self, timeout):
            pass

        def sendall(self, payload):
            delivered.append(payload)

        def close(self):
            pass

    def connect(address, timeout):
        attempts.append(address)
        if len(attempts) == 1:
            raise OSError("offline")
        return Connection()

    monkeypatch.setattr(socket, "create_connection", connect)
    monkeypatch.setattr("camera.pi_vision.time.monotonic", lambda: now[0])
    client = ObservationClient("esp32", 5000)
    assert not client.send(b"old\n")
    now[0] = 0.5
    assert not client.send(b"also-old\n")
    assert len(attempts) == 1
    now[0] = 1.1
    assert client.send(b"latest\n")
    assert delivered == [b"latest\n"]
    client.close()


def test_front_and_external_cameras_have_distinct_frames():
    cfg = yaml.safe_load((ROOT / "mam_eurobot_2026/mam_eurobot_2026/vision/vision_settings.yaml").read_text())
    assert lookup_camera_config(cfg, "/front_camera")["frame_id"] == "front_camera_optical_frame"
    assert lookup_camera_config(cfg, "/top_camera/image_3")["frame_id"] == "observation_device_optical_frame"
    with pytest.raises(ValueError, match="No camera/frame"):
        lookup_camera_config(cfg, "/unconfigured_camera")
