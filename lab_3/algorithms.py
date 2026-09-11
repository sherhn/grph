import math
from typing import List, Tuple, Dict, Any

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
