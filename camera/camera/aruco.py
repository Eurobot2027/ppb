"""ROS-independent ArUco helpers recovered from the legacy pose viewer."""
import cv2
import cv2.aruco as aruco
import numpy as np


def create_aruco_dictionary(dictionary_id):
    if hasattr(aruco, "getPredefinedDictionary"):
        return aruco.getPredefinedDictionary(dictionary_id)
    return aruco.Dictionary_get(dictionary_id)


def create_detector_parameters():
    if hasattr(aruco, "DetectorParameters_create"):
        return aruco.DetectorParameters_create()
    return aruco.DetectorParameters()


def detect_markers(gray, dictionary, parameters):
    if hasattr(aruco, "detectMarkers"):
        return aruco.detectMarkers(gray, dictionary, parameters=parameters)
    detector = aruco.ArucoDetector(dictionary, parameters)
    return detector.detectMarkers(gray)


def estimate_marker_pose(corners, marker_length, camera_matrix, dist_coeffs):
    if hasattr(aruco, "estimatePoseSingleMarkers"):
        rvecs, tvecs, _ = aruco.estimatePoseSingleMarkers(
            np.array([corners], dtype=np.float32),
            marker_length,
            camera_matrix,
            dist_coeffs,
        )
        if rvecs is None or tvecs is None or len(rvecs) == 0:
            return False, None, None
        return True, rvecs[0], tvecs[0]

    half = marker_length / 2.0
    object_points = np.array(
        [
            [-half, half, 0.0],
            [half, half, 0.0],
            [half, -half, 0.0],
            [-half, -half, 0.0],
        ],
        dtype=np.float32,
    )
    solve_flag = getattr(cv2, "SOLVEPNP_IPPE_SQUARE", cv2.SOLVEPNP_ITERATIVE)
    success, rvec, tvec = cv2.solvePnP(
        object_points,
        np.asarray(corners, dtype=np.float32),
        camera_matrix,
        dist_coeffs,
        flags=solve_flag,
    )
    if not success:
        return False, None, None
    return True, rvec, tvec


