"""Calibrate from a fresh set of checkerboard photos; write portable JSON."""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def calibrate(directory, cols, rows, square_length):
    grid = np.zeros((cols * rows, 3), np.float32)
    grid[:, :2] = np.mgrid[0:cols, 0:rows].T.reshape(-1, 2) * square_length
    object_points, image_points, used = [], [], []
    size = None
    for path in sorted(directory.iterdir()):
        if path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            continue
        image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError(f"Cannot read {path}")
        current = (image.shape[1], image.shape[0])
        if size is not None and current != size:
            raise ValueError(f"Mixed image sizes: {path}")
        size = current
        found, corners = cv2.findChessboardCorners(image, (cols, rows))
        if found:
            corners = cv2.cornerSubPix(image, corners, (11, 11), (-1, -1),
                                      (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001))
            object_points.append(grid.copy())
            image_points.append(corners)
            used.append(path.name)
    if len(used) < 10:
        raise ValueError(f"Only {len(used)} usable boards; capture at least 10 varied views")
    rms, matrix, distortion, _, _ = cv2.calibrateCamera(object_points, image_points, size, None, None)
    return dict(schema_version=1, image_size=list(size), camera_matrix=matrix.tolist(),
                dist_coeffs=distortion.ravel().tolist(), rms_px=float(rms), images=used,
                checkerboard_inner_corners=[cols, rows], square_length_m=square_length)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cols", type=int, default=8, help="Inner corners, not squares")
    parser.add_argument("--rows", type=int, default=6)
    parser.add_argument("--square-length-m", type=float, required=True)
    args = parser.parse_args()
    if args.cols < 2 or args.rows < 2 or not 0 < args.square_length_m < float("inf"):
        parser.error("use at least 2x2 inner corners and a positive finite square length")
    if args.output.exists():
        parser.error("output already exists; choose a new file")
    result = calibrate(args.images, args.cols, args.rows, args.square_length_m)
    with args.output.open("x") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(f"Calibrated from {len(result['images'])} images; RMS {result['rms_px']:.3f} px")


if __name__ == "__main__":
    main()
