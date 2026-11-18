"""Image-space A* and overlays extracted from camera/cv_test.py.

Only visible marker boxes are obstacles. Pixel routes are not metric robot paths.
"""
import heapq

import cv2
import numpy as np

# Image-space demo defaults, unrelated to field geometry or robot dimensions.
GRID_STEP_PX = 12
OBSTACLE_PADDING_PX = 24


def clamp_cell(cell, grid_width, grid_height):
    # Keep a cell inside the valid grid range so later indexing cannot go out of bounds.
    x = min(max(cell[0], 0), grid_width - 1)
    y = min(max(cell[1], 0), grid_height - 1)
    return (x, y)


def point_to_cell(point, grid_step, grid_width, grid_height):
    # Convert a pixel location in the image into a planning cell index.
    cell = (int(point[0] / grid_step), int(point[1] / grid_step))
    return clamp_cell(cell, grid_width, grid_height)


def cell_to_point(cell, grid_step):
    # Convert a planning cell back to the pixel coordinates of that cell's center.
    x = int(cell[0] * grid_step + grid_step / 2)
    y = int(cell[1] * grid_step + grid_step / 2)
    return (x, y)


def create_occupancy_grid(frame_shape, markers, start_id, goal_id,
                          grid_step=GRID_STEP_PX, obstacle_padding=OBSTACLE_PADDING_PX):
    # Build a binary occupancy grid over the camera image:
    # 0 = free space, 1 = blocked space.
    #
    # The planner uses this grid as its map. Other markers become obstacles, while
    # the chosen start and goal markers are left free so the path can begin and end there.
    frame_height, frame_width = frame_shape[:2]
    if grid_step < 1 or obstacle_padding < 0 or frame_width < 1 or frame_height < 1:
        raise ValueError("Positive frame/grid dimensions and non-negative padding required")
    grid_width = (frame_width + grid_step - 1) // grid_step
    grid_height = (frame_height + grid_step - 1) // grid_step
    occupancy = np.zeros((grid_height, grid_width), dtype=np.uint8)
    obstacle_bounds = []

    for marker_id, marker in markers.items():
        # The start and goal are targets, not obstacles.
        if marker_id in {start_id, goal_id}:
            continue

        corners = marker["corners"]

        # Compute a padded bounding box around each obstacle marker in pixel space.
        # Padding makes the planner behave more conservatively around obstacles.
        min_xy = np.floor(np.min(corners, axis=0) - obstacle_padding).astype(int)
        max_xy = np.ceil(np.max(corners, axis=0) + obstacle_padding).astype(int)

        # Convert the padded pixel box into grid coordinates so we can mark blocked cells.
        min_cell = point_to_cell(min_xy, grid_step, grid_width, grid_height)
        max_cell = point_to_cell(max_xy, grid_step, grid_width, grid_height)

        # Fill the rectangle of blocked cells covered by this padded obstacle.
        occupancy[min_cell[1] : max_cell[1] + 1, min_cell[0] : max_cell[0] + 1] = 1

        # Save the bounds so the optional debug overlay can show exactly what was blocked.
        obstacle_bounds.append(
            {
                "marker_id": marker_id,
                "min_xy": min_xy,
                "max_xy": max_xy,
                "min_cell": min_cell,
                "max_cell": max_cell,
            }
        )

    return occupancy, grid_width, grid_height, obstacle_bounds


def heuristic(cell, goal):
    # A* uses straight-line distance to the goal as its heuristic estimate.
    return np.hypot(goal[0] - cell[0], goal[1] - cell[1])


def astar_path(occupancy, start_cell, goal_cell):
    # Standard A* graph search over the occupancy grid.
    #
    # Each cell is a node. The planner can move to 8 neighbors:
    # horizontal, vertical, and diagonal.
    neighbors = [
        (-1, -1), (0, -1), (1, -1),
        (-1, 0),            (1, 0),
        (-1, 1),  (0, 1),   (1, 1),
    ]
    height, width = occupancy.shape
    for x, y in (start_cell, goal_cell):
        if not (0 <= x < width and 0 <= y < height) or occupancy[y, x]:
            return None
    open_heap = [(heuristic(start_cell, goal_cell), 0.0, start_cell)]
    came_from = {}
    g_score = {start_cell: 0.0}
    visited = set()

    while open_heap:
        # Pop the cell with lowest estimated total cost = real cost so far + heuristic.
        _, current_cost, current = heapq.heappop(open_heap)
        if current in visited:
            continue
        visited.add(current)

        if current == goal_cell:
            # Reconstruct the path by walking backward from goal to start.
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        for dx, dy in neighbors:
            nx = current[0] + dx
            ny = current[1] + dy

            # Ignore neighbors outside the grid.
            if not (0 <= nx < width and 0 <= ny < height):
                continue

            # Ignore blocked cells.
            if occupancy[ny, nx]:
                continue

            # A diagonal must not cut through a blocked corner.
            if dx and dy and (occupancy[current[1], nx] or occupancy[ny, current[0]]):
                continue

            # Diagonal steps cost sqrt(2), straight steps cost 1.
            step_cost = np.hypot(dx, dy)
            candidate_cost = current_cost + step_cost
            neighbor = (nx, ny)

            # Only keep this new route if it improves the best cost known for that cell.
            if candidate_cost >= g_score.get(neighbor, float("inf")):
                continue

            came_from[neighbor] = current
            g_score[neighbor] = candidate_cost
            priority = candidate_cost + heuristic(neighbor, goal_cell)
            heapq.heappush(open_heap, (priority, candidate_cost, neighbor))

    return None


def simplify_path(points):
    # A* returns many small cell-by-cell steps. For display, we keep only the key
    # turning points so the overlay looks like a clean route instead of a jagged trace.
    if len(points) <= 2:
        return points

    simplified = [points[0]]
    for idx in range(1, len(points) - 1):
        before = np.asarray(points[idx]) - points[idx - 1]
        after = np.asarray(points[idx + 1]) - points[idx]
        # Keep every real turn, including small turns near the marker centers.
        if before[0] * after[1] != before[1] * after[0] or np.dot(before, after) <= 0:
            simplified.append(points[idx])

    simplified.append(points[-1])
    return simplified


def plan_marker_path(frame_shape, markers, start_id, goal_id,
                     grid_step=GRID_STEP_PX, obstacle_padding=OBSTACLE_PADDING_PX):
    # This is the main planning function used by the live loop.
    #
    # It creates the occupancy grid, converts the start and goal marker centers
    # into cells, runs A*, and converts the resulting cell path back to pixel points.
    if start_id not in markers or goal_id not in markers:
        return None, "Start or goal marker not visible", None

    occupancy, grid_width, grid_height, obstacle_bounds = create_occupancy_grid(
        frame_shape,
        markers,
        start_id,
        goal_id,
        grid_step,
        obstacle_padding,
    )

    start_point = markers[start_id]["center"]
    goal_point = markers[goal_id]["center"]
    start_cell = point_to_cell(start_point, grid_step, grid_width, grid_height)
    goal_cell = point_to_cell(goal_point, grid_step, grid_width, grid_height)

    path_cells = astar_path(occupancy, start_cell, goal_cell)
    if path_cells is None:
        debug_info = {
            "occupancy": occupancy,
            "grid_width": grid_width,
            "grid_height": grid_height,
            "obstacle_bounds": obstacle_bounds,
            "start_cell": start_cell,
            "goal_cell": goal_cell,
            "grid_step": grid_step,
        }
        return None, "No obstacle-free path found", debug_info

    height, width = frame_shape[:2]
    path_points = [tuple(min(v, limit - 1) for v, limit in
                         zip(cell_to_point(cell, grid_step), (width, height)))
                   for cell in path_cells]

    # Replace the first and last cell centers with the actual marker centers so the
    # drawn path touches the visible start and goal markers more naturally.
    start_point = tuple(np.asarray(start_point, dtype=int))
    goal_point = tuple(np.asarray(goal_point, dtype=int))
    if len(path_points) == 1:
        path_points = [start_point, goal_point]
    else:
        path_points[0] = start_point
        path_points[-1] = goal_point
    debug_info = {
        "occupancy": occupancy,
        "grid_width": grid_width,
        "grid_height": grid_height,
        "obstacle_bounds": obstacle_bounds,
        "start_cell": start_cell,
        "goal_cell": goal_cell,
        "grid_step": grid_step,
    }
    return simplify_path(path_points), None, debug_info


def draw_path_overlay(frame, path_points, start_id, goal_id):
    # Draw the planned route as a polyline on top of the camera image.
    if not path_points or len(path_points) < 2:
        return frame

    polyline = np.array(path_points, dtype=np.int32).reshape((-1, 1, 2))
    cv2.polylines(frame, [polyline], False, (255, 255, 0), 3)

    for point in path_points[1:-1]:
        cv2.circle(frame, point, 4, (255, 200, 0), -1)

    cv2.putText(
        frame,
        f"Path {start_id} -> {goal_id}",
        (20, 70),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 0),
        2,
    )
    return frame


def draw_debug_grid_overlay(frame, debug_info):
    # Optional debug visualization that makes the planner's internal map visible:
    # blocked cells, the underlying grid, padded obstacle boxes, and start/goal cells.
    if debug_info is None:
        return frame

    overlay = frame.copy()
    grid_step = debug_info.get("grid_step", GRID_STEP_PX)
    occupancy = debug_info["occupancy"]
    grid_height, grid_width = occupancy.shape

    for cell_y in range(grid_height):
        for cell_x in range(grid_width):
            if not occupancy[cell_y, cell_x]:
                continue

            # Paint every blocked grid cell in orange so the occupancy map is easy to see.
            x0 = cell_x * grid_step
            y0 = cell_y * grid_step
            x1 = min(x0 + grid_step, frame.shape[1] - 1)
            y1 = min(y0 + grid_step, frame.shape[0] - 1)
            cv2.rectangle(overlay, (x0, y0), (x1, y1), (0, 90, 255), -1)

    # Blend the blocked-cell overlay with the camera image so the scene stays visible.
    cv2.addWeighted(overlay, 0.22, frame, 0.78, 0, frame)

    # Draw the full planning grid for explanation/debugging purposes.
    for x in range(0, frame.shape[1], grid_step):
        cv2.line(frame, (x, 0), (x, frame.shape[0] - 1), (70, 70, 70), 1)
    for y in range(0, frame.shape[0], grid_step):
        cv2.line(frame, (0, y), (frame.shape[1] - 1, y), (70, 70, 70), 1)

    for obstacle in debug_info["obstacle_bounds"]:
        # Outline the padded obstacle region in pixel space so it is obvious how the
        # original marker area was enlarged before planning.
        min_xy = tuple(obstacle["min_xy"])
        max_xy = tuple(obstacle["max_xy"])
        cv2.rectangle(frame, min_xy, max_xy, (0, 165, 255), 2)
        cv2.putText(
            frame,
            f"pad {obstacle['marker_id']}",
            (min_xy[0], max(min_xy[1] - 6, 15)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 165, 255),
            1,
        )

    # Mark the start and goal cells used by the planner.
    start_point = cell_to_point(debug_info["start_cell"], grid_step)
    goal_point = cell_to_point(debug_info["goal_cell"], grid_step)
    cv2.circle(frame, start_point, 6, (0, 255, 0), -1)
    cv2.circle(frame, goal_point, 6, (0, 255, 255), -1)
    cv2.putText(
        frame,
        "Debug grid: blocked cells in orange, padded obstacle boxes outlined",
        (20, frame.shape[0] - 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2,
    )
    return frame


