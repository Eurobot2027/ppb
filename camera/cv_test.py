import argparse
import os
import pickle

import cv2
import cv2.aruco as aruco
import numpy as np

from camera.path_planning import (
    GRID_STEP_PX, OBSTACLE_PADDING_PX, astar_path, cell_to_point, clamp_cell,
    create_occupancy_grid, draw_debug_grid_overlay, draw_path_overlay, heuristic,
    plan_marker_path, point_to_cell, simplify_path,
)

# Camera capture settings used for the live display window.
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
CAMERA_INDEX = 2

# Default ArUco setup. The dictionary must match the printed markers you use.
DEFAULT_ARUCO_DICT_ID = aruco.DICT_4X4_50
DEFAULT_MARKER_LENGTH = 0.018  # meters


def parse_args():
    # Read the start and goal marker IDs from the command line so the same script
    # can be reused for different path planning demonstrations.
    parser = argparse.ArgumentParser(
        description="Detect ArUco markers, estimate pose, and plan an image-space path."
    )
    parser.add_argument("start_id", type=int, help="ArUco marker ID for the start point")
    parser.add_argument("goal_id", type=int, help="ArUco marker ID for the goal point")
    parser.add_argument(
        "--debug-grid",
        action="store_true",
        help="Show the planning grid and padded obstacle areas on the camera overlay",
    )
    return parser.parse_args()


def create_aruco_dictionary(dictionary_id):
    # OpenCV exposes different helper names depending on version. This keeps the
    # script compatible with older and newer bindings.
    if hasattr(aruco, "getPredefinedDictionary"):
        return aruco.getPredefinedDictionary(dictionary_id)
    return aruco.Dictionary_get(dictionary_id)


def create_detector_parameters():
    # DetectorParameters stores thresholds and tuning values used by the ArUco detector.
    if hasattr(aruco, "DetectorParameters_create"):
        return aruco.DetectorParameters_create()
    return aruco.DetectorParameters()


def detect_markers(gray, dictionary, parameters):
    # Detect candidate 4-corner marker shapes and decode their IDs from the grayscale image.
    return aruco.detectMarkers(gray, dictionary, parameters=parameters)


def estimate_marker_pose(corners, marker_length, camera_matrix, dist_coeffs):
    # Pose estimation returns the rotation and translation of one marker relative
    # to the camera. We pass one marker at a time to get one rvec/tvec pair back.
    rvecs, tvecs, _ = aruco.estimatePoseSingleMarkers(
        np.array([corners], dtype=np.float32),
        marker_length,
        camera_matrix,
        dist_coeffs,
    )
    if rvecs is None or tvecs is None or len(rvecs) == 0:
        return False, None, None
    return True, rvecs[0], tvecs[0]


def rotation_vector_to_yaw_z(rvec):
    # Convert the compact Rodrigues rotation vector into a rotation matrix, then
    # extract yaw around Z so we can display a simple orientation angle.
    rotation_matrix, _ = cv2.Rodrigues(rvec)
    yaw_z = np.arctan2(rotation_matrix[1, 0], rotation_matrix[0, 0])
    return np.degrees(yaw_z)


def draw_axes(frame, camera_matrix, dist_coeffs, rvec, tvec, axis_length):
    # Define a tiny 3D coordinate frame anchored at the marker center, project it
    # into the image, and draw the X/Y/Z axes on the live camera frame.
    axis_points = np.float32(
        [
            [0, 0, 0],
            [axis_length, 0, 0],
            [0, axis_length, 0],
            [0, 0, axis_length],
        ]
    )
    imgpts, _ = cv2.projectPoints(axis_points, rvec, tvec, camera_matrix, dist_coeffs)
    imgpts = np.int32(imgpts)

    origin = tuple(imgpts[0].ravel())
    frame = cv2.line(frame, origin, tuple(imgpts[1].ravel()), (0, 0, 255), 3)
    frame = cv2.line(frame, origin, tuple(imgpts[2].ravel()), (0, 255, 0), 3)
    frame = cv2.line(frame, origin, tuple(imgpts[3].ravel()), (255, 0, 0), 3)
    return frame


# Parse command-line options once at startup.
args = parse_args()

# Try to load the real camera calibration so pose estimation uses measured intrinsics.
if os.path.exists("camera_calibration.pkl"):
    print("Loading calibration from camera_calibration.pkl...")
    with open("camera_calibration.pkl", "rb") as f:
        calibration_data = pickle.load(f)
    camera_matrix = calibration_data["camera_matrix"]
    dist_coeffs = calibration_data["dist_coeffs"]
    reprojection_error = calibration_data["reprojection_error"]
    marker_length = calibration_data.get("marker_length_m", DEFAULT_MARKER_LENGTH)
    dictionary_id = calibration_data.get("aruco_dictionary", DEFAULT_ARUCO_DICT_ID)
    print(f"✓ Calibration loaded (reprojection error: {reprojection_error:.4f})")
else:
    # Fall back to a rough pinhole camera model if no calibration file exists.
    # This keeps the demo running, but the pose numbers will be less accurate.
    print("WARNING: No calibration found. Using default camera parameters.")
    print("Run camera_calibration.py to generate calibration data.")
    focal_length = 960
    cx = FRAME_WIDTH / 2
    cy = FRAME_HEIGHT / 2
    camera_matrix = np.array(
        [
            [focal_length, 0, cx],
            [0, focal_length, cy],
            [0, 0, 1],
        ],
        dtype=float,
    )
    dist_coeffs = np.zeros((4, 1))
    marker_length = DEFAULT_MARKER_LENGTH
    dictionary_id = DEFAULT_ARUCO_DICT_ID

# Build the detector once so it can be reused for every frame.
aruco_dict = create_aruco_dictionary(dictionary_id)
parameters = create_detector_parameters()

print(f"Planning path from marker {args.start_id} to marker {args.goal_id}")
print(f"Opening camera {CAMERA_INDEX}...")
cap = cv2.VideoCapture(CAMERA_INDEX)
if not cap.isOpened():
    print(f"Error: Cannot open camera {CAMERA_INDEX}")
    raise SystemExit(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

# Main live-processing loop:
# 1. grab a frame
# 2. detect markers
# 3. estimate pose for each marker
# 4. build a path from start marker to goal marker
# 5. draw overlays and show the result
while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Failed to grab frame")
        break

    # ArUco detection works on grayscale images.
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    marker_corners, marker_ids, _ = detect_markers(gray, aruco_dict, parameters)

    # This dictionary stores the image-space geometry needed by the path planner.
    detected_markers = {}

    if marker_ids is not None and len(marker_ids) > 0:
        # Draw marker outlines and IDs as detected by OpenCV.
        aruco.drawDetectedMarkers(frame, marker_corners, marker_ids)

        for corners, marker_id in zip(marker_corners, marker_ids.flatten()):
            image_points = corners.reshape(4, 2).astype(np.float32)
            success, rvec, tvec = estimate_marker_pose(
                image_points,
                marker_length,
                camera_matrix,
                dist_coeffs,
            )

            # The marker center and corners are stored even if pose estimation fails,
            # because the path planner only needs the marker geometry in the image.
            marker_center = np.mean(image_points, axis=0)
            detected_markers[int(marker_id)] = {
                "corners": image_points,
                "center": marker_center,
            }

            if not success:
                continue

            # Draw pose information only when OpenCV successfully estimates it.
            frame = draw_axes(frame, camera_matrix, dist_coeffs, rvec, tvec, marker_length * 0.75)
            position = tvec.flatten()
            yaw_z = rotation_vector_to_yaw_z(rvec)

            text_lines = [
                f"ID: {marker_id}",
                f"X: {position[0]:.3f}m Y: {position[1]:.3f}m Z: {position[2]:.3f}m",
                f"Yaw Z: {yaw_z:.1f}deg",
            ]

            center_int = marker_center.astype(int)
            y_offset = center_int[1] - 35
            for index, text in enumerate(text_lines):
                cv2.putText(
                    frame,
                    text,
                    (center_int[0] - 95, y_offset + index * 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    2,
                )

        # Plan a path in image space from the chosen start marker to the chosen goal marker.
        path_points, path_error, debug_info = plan_marker_path(
            frame.shape,
            detected_markers,
            args.start_id,
            args.goal_id,
        )

        # Optional debug overlay that reveals the occupancy grid and padded obstacles.
        if args.debug_grid:
            frame = draw_debug_grid_overlay(frame, debug_info)

        if path_points is not None:
            frame = draw_path_overlay(frame, path_points, args.start_id, args.goal_id)
        else:
            # If a route cannot be produced, tell the user why on the live image.
            cv2.putText(
                frame,
                path_error,
                (20, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2,
            )
    else:
        # No markers visible at all, so neither pose estimation nor planning can run.
        cv2.putText(
            frame,
            "Show 4x4 ArUco markers to estimate pose and plan a path",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 255),
            2,
        )

    # Show the final composited frame and exit when ESC is pressed.
    cv2.imshow("ArUco Marker Pose and Path", frame)
    if cv2.waitKey(1) & 0xFF == 27:
        break

# Release camera resources and close the OpenCV window on exit.
cap.release()
cv2.destroyAllWindows()
