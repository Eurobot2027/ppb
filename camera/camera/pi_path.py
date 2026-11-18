"""Detect ArUco markers, plan an image-space A* route and stream annotated MJPEG."""
import argparse
from contextlib import nullcontext
import logging
import os
from pathlib import Path
import sys
import time

import cv2
import numpy as np

from .capture import camera_arguments, open_camera, validate_camera_arguments
from .path_planning import (
    GRID_STEP_PX, OBSTACLE_PADDING_PX, draw_debug_grid_overlay, draw_path_overlay,
    plan_marker_path,
)
from .pi_vision import Detector

LOG = logging.getLogger(__name__)


def annotate_route(frame, detector, start_id, goal_id, *, grid_step=GRID_STEP_PX,
                   obstacle_padding=OBSTACLE_PADDING_PX, debug_grid=False):
    """Return an overlay, pixel waypoints and an error; never reuse old detections."""
    detections = detector.detect(frame)
    markers = {item["id"]: dict(center=np.asarray(item["center_px"]),
                                corners=np.asarray(item["corners_px"]))
               for item in detections}
    overlay = frame.copy()
    for item in detections:
        corners = np.asarray(item["corners_px"], dtype=np.int32)
        cv2.polylines(overlay, [corners.reshape(-1, 1, 2)], True, (0, 255, 0), 2)
        x, y = corners[0]
        cv2.putText(overlay, str(item["id"]), (int(x), max(15, int(y) - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 180, 0), 2)

    if len(markers) != len(detections):
        path, error, debug = None, "Duplicate marker IDs; use unique markers", None
    else:
        path, error, debug = plan_marker_path(
            frame.shape, markers, start_id, goal_id, grid_step, obstacle_padding)
    if debug_grid:
        draw_debug_grid_overlay(overlay, debug)
    if error:
        cv2.putText(overlay, error, (10, 55), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0, 0, 255), 2)
    else:
        draw_path_overlay(overlay, path, start_id, goal_id)
    cv2.putText(overlay, "Image-space A* | other markers = obstacles", (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 100, 255), 1)
    return overlay, path, error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    camera_arguments(parser)
    parser.add_argument("start_id", type=int, help="Start marker ID (visible in the image)")
    parser.add_argument("goal_id", type=int, help="Goal marker ID (visible in the same image)")
    parser.add_argument("--dictionary", default="DICT_4X4_50", help="Match your printed markers")
    parser.add_argument("--grid-step-px", type=int, default=GRID_STEP_PX)
    parser.add_argument("--obstacle-padding-px", type=int, default=OBSTACLE_PADDING_PX)
    parser.add_argument("--debug-grid", action="store_true", help="Draw the grid and blocked cells")
    parser.add_argument("--jpeg-quality", type=int, default=75)
    parser.add_argument("--frames", type=int, default=0, help="Stop after N frames; 0 runs continuously")
    parser.add_argument("--image", type=Path, help="Stream one annotated image without camera hardware")
    args = parser.parse_args()
    validate_camera_arguments(parser, args)
    if min(args.start_id, args.goal_id) < 0 or args.start_id == args.goal_id:
        parser.error("start_id and goal_id must be distinct non-negative IDs")
    if args.grid_step_px < 1 or args.obstacle_padding_px < 0:
        parser.error("grid step must be positive and obstacle padding non-negative")
    if args.frames < 0 or not 1 <= args.jpeg_quality <= 100:
        parser.error("frames must be non-negative and JPEG quality between 1 and 100")
    logging.basicConfig(level=logging.INFO)
    try:
        detector = Detector(args.dictionary)
        if max(args.start_id, args.goal_id) >= len(detector.dictionary.bytesList):
            parser.error("marker IDs are outside the selected dictionary")
        if args.image:
            image = cv2.imread(str(args.image))
            if image is None:
                raise ValueError(f"Cannot read {args.image}")
            context = nullcontext(lambda: image)
        else:
            context = open_camera(args.backend, args.camera_index, args.width, args.height, args.fps)
        LOG.info("Streaming image-space route %s -> %s as MJPEG on stdout; Ctrl+C stops",
                 args.start_id, args.goal_id)
        count = 0
        with context as read:
            while True:
                started = time.monotonic()
                frame = read()
                if frame is None or frame.shape[:2] != (args.height, args.width):
                    raise ValueError("Actual frame size differs from requested size")
                overlay, _, _ = annotate_route(
                    frame, detector, args.start_id, args.goal_id,
                    grid_step=args.grid_step_px, obstacle_padding=args.obstacle_padding_px,
                    debug_grid=args.debug_grid)
                ok, jpeg = cv2.imencode(".jpg", overlay,
                                        [cv2.IMWRITE_JPEG_QUALITY, args.jpeg_quality])
                if not ok:
                    raise RuntimeError("Failed to encode preview frame")
                sys.stdout.buffer.write(jpeg.tobytes())
                sys.stdout.buffer.flush()
                count += 1
                if args.image or (args.frames and count >= args.frames):
                    break
                time.sleep(max(0, 1 / args.fps - (time.monotonic() - started)))
    except KeyboardInterrupt:
        pass
    except BrokenPipeError:
        # Avoid another broken-pipe error during Python's final stdout flush.
        with open(os.devnull, "wb") as sink:
            os.dup2(sink.fileno(), sys.stdout.fileno())
    except (ImportError, OSError, RuntimeError, ValueError, cv2.error) as exc:
        LOG.error("Preview stopped: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
