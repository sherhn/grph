import math
import re
import xml.etree.ElementTree as ET
from typing import List, Tuple, Dict, Any, Optional

COLOR_CDA = (127, 127, 255)
COLOR_BREZF = (255, 127, 127)
COLOR_BREZI = (127, 255, 127)
COLOR_NATIVE = (120, 120, 120)


def sign(v: float) -> int:
    if v > 0:
        return 1
    elif v < 0:
        return -1
    return 0


def cda_line(x1: float, y1: float, x2: float, y2: float) -> List[Tuple[int, int]]:
    if round(x1) == round(x2) and round(y1) == round(y2):
        return [(math.floor(x1), math.floor(y1))]

    l = max(abs(x2 - x1), abs(y2 - y1))
    if l == 0:
        return [(math.floor(x1), math.floor(y1))]

    dx = (x2 - x1) / l
    dy = (y2 - y1) / l

    x = x1 + 0.5 * sign(dx)
    y = y1 + 0.5 * sign(dy)

    points: List[Tuple[int, int]] = []
    steps = int(round(l)) + 1
    for _ in range(steps):
        points.append((math.floor(x), math.floor(y)))
        x += dx
        y += dy

    return points


def bresenham_float_line(x1: float, y1: float, x2: float, y2: float) -> List[Tuple[int, int]]:
    if round(x1) == round(x2) and round(y1) == round(y2):
        return [(math.floor(x1), math.floor(y1))]

    sx = sign(x2 - x1)
    sy = sign(y2 - y1)
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)

    if dx == 0 and dy == 0:
        return [(math.floor(x1), math.floor(y1))]

    x = x1
    y = y1
    flag = 0

    if dy > dx:
        dx, dy = dy, dx
        flag = 1

    if dx == 0:
        return [(math.floor(x1), math.floor(y1))]

    e = dy / dx - 0.5
    points: List[Tuple[int, int]] = []
    steps = int(round(dx)) + 1

    for _ in range(steps):
        points.append((math.floor(x), math.floor(y)))
        if e >= 0:
            if flag == 1:
                x += sx
            else:
                y += sy
            e -= 1.0
        if flag == 1:
            y += sy
        else:
            x += sx
        e += dy / dx

    return points


def bresenham_int_line(x1: float, y1: float, x2: float, y2: float) -> List[Tuple[int, int]]:
    ix1, iy1 = int(round(x1)), int(round(y1))
    ix2, iy2 = int(round(x2)), int(round(y2))

    if ix1 == ix2 and iy1 == iy2:
        return [(ix1, iy1)]

    sx = sign(ix2 - ix1)
    sy = sign(iy2 - iy1)
    dx = abs(ix2 - ix1)
    dy = abs(iy2 - iy1)

    x = ix1
    y = iy1
    flag = 0

    if dy > dx:
        dx, dy = dy, dx
        flag = 1

    e = 2 * dy - dx
    points: List[Tuple[int, int]] = []

    for _ in range(dx + 1):
        points.append((x, y))
        if e >= 0:
            if flag == 1:
                x += sx
            else:
                y += sy
            e -= 2 * dx
        if flag == 1:
            y += sy
        else:
            x += sx
        e += 2 * dy

    return points


def calculate_triangle_bisectors(
    ax: float, ay: float,
    bx: float, by: float,
    cx: float, cy: float
) -> Dict[str, Any]:
    a = math.hypot(cx - bx, cy - by)
    b = math.hypot(cx - ax, cy - ay)
    c = math.hypot(bx - ax, by - ay)

    eps = 1e-9

    if b + c > eps:
        lax = (b * bx + c * cx) / (b + c)
        lay = (b * by + c * cy) / (b + c)
    else:
        lax, lay = bx, by

    if a + c > eps:
        lbx = (a * ax + c * cx) / (a + c)
        lby = (a * ay + c * cy) / (a + c)
    else:
        lbx, lby = ax, ay

    if a + b > eps:
        lcx = (a * ax + b * bx) / (a + b)
        lcy = (a * ay + b * by) / (a + b)
    else:
        lcx, lcy = ax, ay

    perimeter = a + b + c
    if perimeter > eps:
        ix = (a * ax + b * bx + c * cx) / perimeter
        iy = (a * ay + b * by + c * cy) / perimeter
    else:
        ix, iy = ax, ay

    return {
        "A": (ax, ay),
        "B": (bx, by),
        "C": (cx, cy),
        "L_A": (lax, lay),
        "L_B": (lbx, lby),
        "L_C": (lcx, lcy),
        "incenter": (ix, iy),
        "sides": [
            ((ax, ay), (bx, by), "AB"),
            ((bx, by), (cx, cy), "BC"),
            ((cx, cy), (ax, ay), "CA"),
        ],
        "bisectors": [
            ((ax, ay), (lax, lay), "A-L_A"),
            ((bx, by), (lbx, lby), "B-L_B"),
            ((cx, cy), (lcx, lcy), "C-L_C"),
        ]
    }


def load_triangle_from_svg(filepath: str, target_size: int = 60) -> Optional[List[Tuple[float, float]]]:
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
    except Exception:
        return None

    raw_points: List[Tuple[float, float]] = []

    for elem in root.iter():
        tag = elem.tag.split("}")[-1].lower()

        if tag == "polygon" and "points" in elem.attrib:
            nums = [float(x) for x in re.findall(r"[-+]?(?:\d*\.\d+|\d+)", elem.attrib["points"])]
            if len(nums) >= 6:
                raw_points = [(nums[i], nums[i + 1]) for i in range(0, 6, 2)]
                break

        elif tag == "polyline" and "points" in elem.attrib:
            nums = [float(x) for x in re.findall(r"[-+]?(?:\d*\.\d+|\d+)", elem.attrib["points"])]
            if len(nums) >= 6:
                pts = [(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]
                unique_pts: List[Tuple[float, float]] = []
                for p in pts:
                    if not unique_pts or (abs(p[0] - unique_pts[-1][0]) > 1e-4 or abs(p[1] - unique_pts[-1][1]) > 1e-4):
                        unique_pts.append(p)
                if len(unique_pts) >= 3:
                    raw_points = unique_pts[:3]
                    break

        elif tag == "path" and "d" in elem.attrib:
            nums = [float(x) for x in re.findall(r"[-+]?(?:\d*\.\d+|\d+)", elem.attrib["d"])]
            if len(nums) >= 6:
                raw_points = [(nums[0], nums[1]), (nums[2], nums[3]), (nums[4], nums[5])]
                break

    if len(raw_points) < 3:
        lines = []
        for elem in root.iter():
            if elem.tag.split("}")[-1].lower() == "line":
                attrs = elem.attrib
                if all(k in attrs for k in ("x1", "y1", "x2", "y2")):
                    p1 = (float(attrs["x1"]), float(attrs["y1"]))
                    p2 = (float(attrs["x2"]), float(attrs["y2"]))
                    lines.append((p1, p2))
        if len(lines) >= 3:
            pts_set: List[Tuple[float, float]] = []
            for p1, p2 in lines[:3]:
                for pt in (p1, p2):
                    if not any(math.hypot(pt[0] - ep[0], pt[1] - ep[1]) < 1e-3 for ep in pts_set):
                        pts_set.append(pt)
            if len(pts_set) >= 3:
                raw_points = pts_set[:3]

    if len(raw_points) < 3:
        return None

    xs = [p[0] for p in raw_points]
    ys = [p[1] for p in raw_points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    w = max_x - min_x
    h = max_y - min_y

    margin = 6.0
    usable = target_size - 2 * margin

    if max_x > target_size - margin or max_y > target_size - margin or min_x < margin or min_y < margin or max(w, h) < 10:
        scale = usable / max(w, h, 1e-5)
        offset_x = margin + (usable - w * scale) / 2.0
        offset_y = margin + (usable - h * scale) / 2.0
        return [
            (
                round(offset_x + (p[0] - min_x) * scale, 1),
                round(offset_y + (p[1] - min_y) * scale, 1)
            )
            for p in raw_points
        ]

    return [(round(p[0], 1), round(p[1], 1)) for p in raw_points]
