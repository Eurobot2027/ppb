"""Camera backends and non-destructive calibration-image capture."""
import argparse
from contextlib import contextmanager
from pathlib import Path
import time

import cv2


@contextmanager
def open_camera(backend, index, width, height, fps):
    if backend == "picamera2":
        from picamera2 import Picamera2

        camera = Picamera2(index)
        try:
            # libcamera RGB888 is BGR byte order, as expected by OpenCV.
            camera.configure(camera.create_video_configuration(
                main={"size": (width, height), "format": "RGB888"},
                controls={"FrameRate": fps}, buffer_count=2,
            ))
            camera.start()
            time.sleep(1)  # allow exposure/white balance to settle
            yield lambda: camera.capture_array("main")
        finally:
            camera.close()
    else:
        camera = cv2.VideoCapture(index)
        try:
            if not camera.isOpened():
                raise RuntimeError(f"Cannot open OpenCV camera {index}")
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            camera.set(cv2.CAP_PROP_FPS, fps)
            camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            def read():
                ok, frame = camera.read()
                if not ok:
                    raise RuntimeError("Camera read failed")
                return frame

            yield read
        finally:
            camera.release()


def camera_arguments(parser):
    parser.add_argument("--backend", choices=["picamera2", "opencv"], default="picamera2")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=float, default=15)


def validate_camera_arguments(parser, args):
    if args.width <= 0 or args.height <= 0 or not 0 < args.fps < float("inf"):
        parser.error("width, height and fps must be positive and finite")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    camera_arguments(parser)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--count", type=int, default=25)
    parser.add_argument("--interval", type=float, default=2)
    args = parser.parse_args()
    validate_camera_arguments(parser, args)
    if args.count < 1 or not 0 <= args.interval < float("inf"):
        parser.error("count must be positive and interval non-negative and finite")
    # A fresh directory prevents accidental replacement of old measurements.
    args.output_dir.mkdir(parents=True, exist_ok=False)
    with open_camera(args.backend, args.camera_index, args.width, args.height, args.fps) as read:
        for i in range(args.count):
            frame = read()
            if not cv2.imwrite(str(args.output_dir / f"image_{i:03d}.jpg"), frame):
                raise RuntimeError("Failed to write calibration image")
            print(f"Saved image {i + 1}/{args.count}; move the board to another position")
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
