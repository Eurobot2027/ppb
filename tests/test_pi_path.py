"""Image-space route geometry and the camera-free MJPEG CLI."""
from contextlib import contextmanager
from pathlib import Path
import subprocess
import sys

import cv2
import numpy as np
import pytest

from camera.path_planning import astar_path, plan_marker_path, simplify_path
from camera import pi_path
from camera.pi_path import annotate_route
from camera.pi_vision import Detector

ROOT = Path(__file__).resolve().parents[1]


def scene(ids=(1, 2, 3)):
    image = np.full((480, 640, 3), 255, np.uint8)
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    for marker_id, x in zip(ids, (40, 520, 280)):
        if hasattr(cv2.aruco, "generateImageMarker"):
            marker = cv2.aruco.generateImageMarker(dictionary, marker_id, 80)
        else:
            marker = cv2.aruco.drawMarker(dictionary, marker_id, 80)
        image[200:280, x:x + 80] = cv2.cvtColor(marker, cv2.COLOR_GRAY2BGR)
    return image


def test_astar_finds_shortest_grid_route_around_obstacle():
    occupancy = np.zeros((3, 3), np.uint8)
    occupancy[1, 1] = 1
    path = astar_path(occupancy, (0, 1), (2, 1))
    assert path[0] == (0, 1) and path[-1] == (2, 1)
    assert all(not occupancy[y, x] for x, y in path)
    assert sum(np.hypot(b[0] - a[0], b[1] - a[1])
               for a, b in zip(path, path[1:])) == pytest.approx(4)
    diagonal = astar_path(np.zeros((5, 5), np.uint8), (0, 0), (4, 3))
    assert sum(np.hypot(b[0] - a[0], b[1] - a[1])
               for a, b in zip(diagonal, diagonal[1:])) == pytest.approx(1 + 3 * np.sqrt(2))


@pytest.mark.parametrize("occupancy,start,goal", [
    ([[0, 1], [1, 0]], (0, 0), (1, 1)),  # No diagonal corner cutting.
    ([[1, 0], [0, 0]], (0, 0), (1, 1)),  # Blocked start.
    ([[0, 0], [0, 1]], (0, 0), (1, 1)),  # Blocked goal.
    ([[0, 1, 0], [0, 1, 0]], (0, 0), (2, 0)),  # Full barrier.
    ([[0]], (-1, 0), (0, 0)),  # Invalid endpoint.
])
def test_astar_rejects_blocked_unreachable_or_invalid_endpoints(occupancy, start, goal):
    assert astar_path(np.array(occupancy, np.uint8), start, goal) is None


def test_rendered_markers_detour_and_missing_marker_clears_route():
    detector = Detector("DICT_4X4_50")
    image = scene()
    overlay, path, error = annotate_route(image, detector, 1, 2, debug_grid=True)
    assert error is None
    assert path[0] == pytest.approx((79, 239), abs=1)
    assert path[-1] == pytest.approx((559, 239), abs=1)
    assert any(y < 176 or y > 303 for x, y in path)
    # Check the entire displayed polyline against the actual blocked grid.
    detections = detector.detect(image)
    markers = {d["id"]: dict(center=np.array(d["center_px"]),
                             corners=np.array(d["corners_px"])) for d in detections}
    _, _, debug = plan_marker_path(image.shape, markers, 1, 2)
    for a, b in zip(path, path[1:]):
        for x, y in np.linspace(a, b, 200):
            assert not debug["occupancy"][int(y) // 12, int(x) // 12]
    assert not np.array_equal(overlay, image)
    blank = np.full_like(image, 255)
    _, missing_path, error = annotate_route(blank, detector, 1, 2)
    assert missing_path is None and "not visible" in error
    _, missing_path, error = annotate_route(scene((1,)), detector, 1, 2)
    assert missing_path is None and "not visible" in error


def test_duplicate_ids_make_route_ambiguous():
    _, path, error = annotate_route(scene((1, 2, 1)), Detector("DICT_4X4_50"), 1, 2)
    assert path is None and "Duplicate" in error


def test_partial_cells_close_endpoints_and_overlapping_padding():
    def marker(x, y):
        return dict(center=np.array([x, y]),
                    corners=np.array([[x - 1, y - 1], [x + 1, y - 1],
                                      [x + 1, y + 1], [x - 1, y + 1]]))

    markers = {1: marker(1, 1), 2: marker(4, 4)}
    path, error, _ = plan_marker_path((17, 17, 3), markers, 1, 2)
    assert error is None and path == [(1, 1), (4, 4)]
    markers[2] = marker(16, 16)
    path, error, debug = plan_marker_path((17, 17, 3), markers, 1, 2)
    assert error is None and debug["occupancy"].shape == (2, 2)
    assert all(0 <= x < 17 and 0 <= y < 17 for x, y in path)
    markers[3] = marker(8, 8)
    path, error, _ = plan_marker_path((17, 17, 3), markers, 1, 2)
    assert path is None and "No obstacle-free path" in error
    assert simplify_path([(0, 0), (5, 1), (10, 6)]) == [(0, 0), (5, 1), (10, 6)]


def test_cli_streams_only_a_decodable_jpeg_and_rejects_bad_input(tmp_path):
    image_path = tmp_path / "markers.png"
    assert cv2.imwrite(str(image_path), scene())
    command = [sys.executable, "-m", "camera.pi_path", "1", "2", "--image", str(image_path)]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, check=True, timeout=10)
    assert result.stdout.startswith(b"\xff\xd8") and result.stdout.endswith(b"\xff\xd9")
    image = cv2.imdecode(np.frombuffer(result.stdout, np.uint8), cv2.IMREAD_COLOR)
    assert image.shape == (480, 640, 3)
    assert b"Streaming image-space route" in result.stderr
    for options in (["--width", "1280"], ["--grid-step-px", "0"],
                    ["--obstacle-padding-px", "-1"], ["--frames", "-1"],
                    ["--jpeg-quality", "101"], ["--dictionary", "DICT_INVALID"]):
        result = subprocess.run(command + options, cwd=ROOT, capture_output=True, timeout=10)
        assert result.returncode != 0
        assert result.stdout == b""


@pytest.mark.parametrize("capture_fails", [False, True])
def test_live_loop_releases_capture_on_limit_or_failure(monkeypatch, capsysbinary, capture_fails):
    released, reads = [], []

    @contextmanager
    def replay(*args):
        def read():
            if capture_fails and reads:
                raise RuntimeError("Camera disconnected")
            reads.append(True)
            return scene()

        try:
            yield read
        finally:
            released.append(True)

    monkeypatch.setattr(pi_path, "open_camera", replay)
    monkeypatch.setattr(sys, "argv", ["pi_path", "1", "2", "--frames", "3", "--fps", "100"])
    assert pi_path.main() == (1 if capture_fails else 0)
    output = capsysbinary.readouterr().out
    assert output.count(b"\xff\xd8") == (1 if capture_fails else 3)
    assert released == [True]


def test_cli_player_disconnect_exits_without_traceback(tmp_path):
    image_path = tmp_path / "markers.png"
    assert cv2.imwrite(str(image_path), scene())
    with subprocess.Popen([sys.executable, "-m", "camera.pi_path", "1", "2",
                           "--image", str(image_path)], cwd=ROOT,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        process.stdout.close()
        assert process.wait(timeout=10) == 0
        assert b"Traceback" not in process.stderr.read()
