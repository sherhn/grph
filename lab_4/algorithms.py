import math
import re
import xml.etree.ElementTree as ET
from typing import List, Tuple, Dict, Any, Optional, Set
from PIL import Image, ImageDraw

COLOR_EQUATION = (65, 117, 240)    # Синий
COLOR_PARAMETRIC = (245, 108, 35)  # Оранжевый / коралловый
COLOR_BRESENHAM = (46, 175, 80)    # Зелёный
COLOR_NATIVE = (142, 68, 173)      # Фиолетовый / пурпурный
COLOR_TRIANGLE = (33, 33, 33)      # Тёмный для треугольника
COLOR_EXTENSIONS = (170, 170, 170) # Серый для продолжений сторон


def sign(v: float) -> int:
    if v > 0:
        return 1
    elif v < 0:
        return -1
    return 0

# Алгоритмы растеризации отрезков (для вывода сторон и продолжений)

def cda_line(x1: float, y1: float, x2: float, y2: float) -> List[Tuple[int, int]]:
    """Цифровой дифференциальный анализатор (ЦДА) для отрезка."""
    ix1, iy1 = int(round(x1)), int(round(y1))
    ix2, iy2 = int(round(x2)), int(round(y2))
    if ix1 == ix2 and iy1 == iy2:
        return [(ix1, iy1)]

    l = max(abs(x2 - x1), abs(y2 - y1))
    if l == 0:
        return [(ix1, iy1)]

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


def bresenham_int_line(x1: float, y1: float, x2: float, y2: float) -> List[Tuple[int, int]]:
    """Целочисленный алгоритм Брезенхема для отрезка."""
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


# Алгоритмы растеризации окружностей

def circle_equation(
    x0: float,
    y0: float,
    r: float
) -> List[Tuple[int, int]]:
    """
    Растеризация окружности по уравнению: x^2 + y^2 = R^2.
    Используется 8-октантная симметрия с вычислением y(x)
    для 0 <= x <= R/sqrt(2) (стр. 6, 13 методички).
    """
    ir = int(round(r))
    cx = int(round(x0))
    cy = int(round(y0))

    if ir <= 0:
        return [(cx, cy)]

    points_set: Set[Tuple[int, int]] = set()

    # Двухсторонняя / 8-октантная симметрия:
    # x от 0 до round(R / sqrt(2)), где наклон |dy/dx| <= 1
    limit = int(round(ir / math.sqrt(2)))
    r_sq = ir * ir
    for x in range(limit + 1):
        val = r_sq - x * x
        y = int(round(math.sqrt(val))) if val > 0 else 0
        # 8 симметричных октантов
        points_set.add((cx + x, cy + y))
        points_set.add((cx - x, cy + y))
        points_set.add((cx + x, cy - y))
        points_set.add((cx - x, cy - y))
        points_set.add((cx + y, cy + x))
        points_set.add((cx - y, cy + x))
        points_set.add((cx + y, cy - x))
        points_set.add((cx - y, cy - x))

    return list(points_set)


def circle_parametric(x0: float, y0: float, r: float) -> List[Tuple[int, int]]:
    """
    Растеризация окружности по параметрическому уравнению (стр. 2 и 14 методички):
      x = x0 + R * cos(tau)
      y = y0 + R * sin(tau)
      Шаг tau0 = 1 / R (чем больше радиус, тем меньше шаг).
    """
    ir = int(round(r))
    cx = int(round(x0))
    cy = int(round(y0))

    if ir <= 0:
        return [(cx, cy)]

    tau0 = 1.0 / ir
    points_set: Set[Tuple[int, int]] = set()

    tau = 0.0
    two_pi = 2.0 * math.pi
    while tau <= two_pi + 0.5 * tau0:
        px = int(round(x0 + r * math.cos(tau)))
        py = int(round(y0 + r * math.sin(tau)))
        points_set.add((px, py))
        tau += tau0

    return list(points_set)


def circle_bresenham(x0: float, y0: float, r: float) -> List[Tuple[int, int]]:
    """
    Классический целочисленный алгоритм Брезенхема для окружности (стр. 6-7 методички).
    Начальные значения: x=0, y=R, delta=2-2*R.
    На каждом шаге анализируются d1 = 2*(delta + y) - 1 и d2 = 2*(delta - x) - 1.
    """
    ir = int(round(r))
    cx = int(round(x0))
    cy = int(round(y0))

    if ir <= 0:
        return [(cx, cy)]

    x = 0
    y = ir
    delta = 2 - 2 * ir
    points_set: Set[Tuple[int, int]] = set()

    def add_octants(px: int, py: int):
        points_set.add((cx + px, cy + py))
        points_set.add((cx - px, cy + py))
        points_set.add((cx + px, cy - py))
        points_set.add((cx - px, cy - py))
        points_set.add((cx + py, cy + px))
        points_set.add((cx - py, cy + px))
        points_set.add((cx + py, cy - px))
        points_set.add((cx - py, cy - px))

    while x <= y:
        add_octants(x, y)
        d1 = 2 * (delta + y) - 1
        d2 = 2 * (delta - x) - 1

        if delta < 0 and d1 <= 0:
            # Горизонтальный шаг
            x += 1
            delta += 2 * x + 1
        elif delta > 0 and d2 > 0:
            # Вертикальный шаг
            y -= 1
            delta -= 2 * y + 1
        else:
            # Диагональный шаг
            x += 1
            y -= 1
            delta += 2 * (x - y)

    return list(points_set)


def circle_native_raster(x0: float, y0: float, r: float) -> List[Tuple[int, int]]:
    """
    Растеризация окружности средствами Pillow (ImageDraw.ellipse)
    для сравнения с попиксельными алгоритмами.
    """
    ir = int(round(r))
    cx = int(round(x0))
    cy = int(round(y0))

    if ir <= 0:
        return [(cx, cy)]

    box_size = 2 * ir + 7
    offset = ir + 3
    img = Image.new("L", (box_size, box_size), 0)
    draw = ImageDraw.Draw(img)

    # Отрисовываем контур окружности толщиной в 1 пиксель
    draw.ellipse(
        [(offset - ir, offset - ir), (offset + ir, offset + ir)],
        outline=255,
        width=1
    )

    points: List[Tuple[int, int]] = []
    for ly in range(box_size):
        for lx in range(box_size):
            if img.getpixel((lx, ly)) > 0:
                points.append((cx + lx - offset, cy + ly - offset))

    return points

# Геометрия треугольника и вневписанных окружностей (Вариант 12)

def calculate_triangle_excircles(
    a: float,
    b: float,
    c: float,
    raster_size: int = 80,
    margin: int = 4
) -> Dict[str, Any]:
    """
    По заданным длинам сторон a, b, c вычисляет:
    1. Проверку существования треугольника.
    2. Координаты вершин A, B, C (сторона c = AB лежит на оси X, C вычисляется по теореме косинусов).
    3. Полупериметр s и площадь S по формуле Герона.
    4. Радиусы вневписанных окружностей:
         ra = S / (s - a)
         rb = S / (s - b)
         rc = S / (s - c)
    5. Центры вневписанных окружностей в барицентрических координатах:
         Ia = (-a*A + b*B + c*C) / (b + c - a)
         Ib = (a*A - b*B + c*C) / (a + c - b)
         Ic = (a*A + b*B - c*C) / (a + b - c)
    6. Точки касания со сторонами и продолжениями сторон.
    7. Масштабирование и центрирование в растровую сетку raster_size x raster_size.
    """
    if a <= 0 or b <= 0 or c <= 0:
        return {
            "valid": False,
            "error": "Длины сторон должны быть строго положительными числами."
        }

    if a + b <= c or a + c <= b or b + c <= a:
        return {
            "valid": False,
            "error": f"Неравенство треугольника нарушено: суммы любых двух сторон должны быть больше третьей ({a:.1f}, {b:.1f}, {c:.1f})."
        }

    # 1. Начальное аналитическое размещение треугольника
    ax, ay = 0.0, 0.0
    bx, by = float(c), 0.0

    cos_a = (b * b + c * c - a * a) / (2.0 * b * c)
    cos_a = max(-1.0, min(1.0, cos_a))
    if abs(cos_a) < 1e-3:
        cos_a = 0.0
    sin_a = math.sqrt(max(0.0, 1.0 - cos_a * cos_a))

    cx = b * cos_a
    cy = b * sin_a

    # 2. Метрики треугольника
    s = (a + b + c) / 2.0
    s_minus_a = s - a
    s_minus_b = s - b
    s_minus_c = s - c

    area_sq = s * s_minus_a * s_minus_b * s_minus_c
    area = math.sqrt(max(0.0, area_sq))

    if area < 1e-9:
        return {
            "valid": False,
            "error": "Вырожденный треугольник (площадь близка к нулю)."
        }

    # Радиусы трёх вневписанных окружностей
    ra = area / s_minus_a
    rb = area / s_minus_b
    rc = area / s_minus_c

    # Центры трёх вневписанных окружностей (в декартовых координатах)
    denom_a = b + c - a  # = 2 * (s - a)
    iax = (-a * ax + b * bx + c * cx) / denom_a
    iay = (-a * ay + b * by + c * cy) / denom_a

    denom_b = a + c - b  # = 2 * (s - b)
    ibx = (a * ax - b * bx + c * cx) / denom_b
    iby = (a * ay - b * by + c * cy) / denom_b

    denom_c = a + b - c  # = 2 * (s - c)
    icx = (a * ax + b * bx - c * cx) / denom_c
    icy = (a * ay + b * by - c * cy) / denom_c

    # Направляющие единичные векторы сторон
    u_ab = ((bx - ax) / c, (by - ay) / c)
    u_ac = ((cx - ax) / b, (cy - ay) / b)
    u_bc = ((cx - bx) / a, (cy - by) / a)

    # Точки касания продолжений:
    t_ia_ab = (ax + s * u_ab[0], ay + s * u_ab[1])
    t_ib_ab = (bx - s * u_ab[0], by - s * u_ab[1])

    t_ia_ac = (ax + s * u_ac[0], ay + s * u_ac[1])
    t_ic_ac = (cx - s * u_ac[0], cy - s * u_ac[1])

    t_ib_bc = (bx + s * u_bc[0], by + s * u_bc[1])
    t_ic_bc = (cx - s * u_bc[0], cy - s * u_bc[1])

    # 3. Нахождение общего охватывающего прямоугольника (Bounding Box)
    all_x = [
        ax, bx, cx,
        iax - ra, iax + ra,
        ibx - rb, ibx + rb,
        icx - rc, icx + rc,
        t_ia_ab[0], t_ib_ab[0],
        t_ia_ac[0], t_ic_ac[0],
        t_ib_bc[0], t_ic_bc[0],
    ]
    all_y = [
        ay, by, cy,
        iay - ra, iay + ra,
        iby - rb, iby + rb,
        icy - rc, icy + rc,
        t_ia_ab[1], t_ib_ab[1],
        t_ia_ac[1], t_ic_ac[1],
        t_ib_bc[1], t_ic_bc[1],
    ]

    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    bbox_w = max_x - min_x
    bbox_h = max_y - min_y

    usable_size = raster_size - 2 * margin
    scale = usable_size / max(bbox_w, bbox_h, 1e-6)

    # Центрирование в окне растра
    offset_x = margin + (usable_size - bbox_w * scale) / 2.0 - min_x * scale
    offset_y = margin + (usable_size - bbox_h * scale) / 2.0 - min_y * scale

    # Преобразование в экранные координаты растра (с инверсией Y для математической ориентации)
    def map_pt(x: float, y: float) -> Tuple[float, float]:
        rx = offset_x + x * scale
        ry = (raster_size - 1) - (offset_y + y * scale)
        return (rx, ry)

    pt_a = map_pt(ax, ay)
    pt_b = map_pt(bx, by)
    pt_c = map_pt(cx, cy)

    pt_ia = map_pt(iax, iay)
    pt_ib = map_pt(ibx, iby)
    pt_ic = map_pt(icx, icy)

    scale_r_a = ra * scale
    scale_r_b = rb * scale
    scale_r_c = rc * scale

    # Внешние лучи-продолжения (идут строго от вершин треугольника наружу к точкам касания)
    ext_mult = 1.10
    # Линия AB: продолжение за B к точке касания Ia, и продолжение за A к точке касания Ib
    pt_ext_b_ab = map_pt(ax + s * ext_mult * u_ab[0], ay + s * ext_mult * u_ab[1])
    pt_ext_a_ab = map_pt(bx - s * ext_mult * u_ab[0], by - s * ext_mult * u_ab[1])

    # Линия AC: продолжение за C к точке касания Ia, и продолжение за A к точке касания Ic
    pt_ext_c_ac = map_pt(ax + s * ext_mult * u_ac[0], ay + s * ext_mult * u_ac[1])
    pt_ext_a_ac = map_pt(cx - s * ext_mult * u_ac[0], cy - s * ext_mult * u_ac[1])

    # Линия BC: продолжение за C к точке касания Ib, и продолжение за B к точке касания Ic
    pt_ext_c_bc = map_pt(bx + s * ext_mult * u_bc[0], by + s * ext_mult * u_bc[1])
    pt_ext_b_bc = map_pt(cx - s * ext_mult * u_bc[0], cy - s * ext_mult * u_bc[1])

    return {
        "valid": True,
        "a": a, "b": b, "c": c,
        "semiperimeter": s,
        "area": area,
        "ra": ra, "rb": rb, "rc": rc,
        "math_centers": {
            "Ia": (iax, iay),
            "Ib": (ibx, iby),
            "Ic": (icx, icy),
        },
        "raster_scale": scale,
        "raster_vertices": {
            "A": pt_a,
            "B": pt_b,
            "C": pt_c,
        },
        "circles": [
            {"id": "A", "center": pt_ia, "radius": scale_r_a, "math_r": ra, "math_center": (iax, iay), "name": "Вневписанная Ia (к стороне a)"},
            {"id": "B", "center": pt_ib, "radius": scale_r_b, "math_r": rb, "math_center": (ibx, iby), "name": "Вневписанная Ib (к стороне b)"},
            {"id": "C", "center": pt_ic, "radius": scale_r_c, "math_r": rc, "math_center": (icx, icy), "name": "Вневписанная Ic (к стороне c)"},
        ],
        "sides": [
            {"p1": pt_a, "p2": pt_b, "label": "AB (c)"},
            {"p1": pt_b, "p2": pt_c, "label": "BC (a)"},
            {"p1": pt_c, "p2": pt_a, "label": "CA (b)"},
        ],
        "extensions": [
            {"p1": pt_b, "p2": pt_ext_b_ab, "label": "Касательная AB за B"},
            {"p1": pt_a, "p2": pt_ext_a_ab, "label": "Касательная AB за A"},
            {"p1": pt_c, "p2": pt_ext_c_ac, "label": "Касательная AC за C"},
            {"p1": pt_a, "p2": pt_ext_a_ac, "label": "Касательная AC за A"},
            {"p1": pt_c, "p2": pt_ext_c_bc, "label": "Касательная BC за C"},
            {"p1": pt_b, "p2": pt_ext_b_bc, "label": "Касательная BC за B"},
        ]
    }


def load_triangle_from_svg(filepath: str, target_size: int = 60) -> Optional[List[Tuple[float, float]]]:
    """
    Считывает отрезки/треугольник из текстового файла формата SVG.
    Поддерживает элементы: <polygon>, <polyline>, <path> и 3 отрезка <line>.
    Возвращает список из трёх вершин [(x1, y1), (x2, y2), (x3, y3)].
    """
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


def triangle_sides_from_vertices(pts: List[Tuple[float, float]]) -> Tuple[float, float, float]:
    """
    Вычисляет длины сторон треугольника a, b, c по трём точкам A, B, C:
      a = dist(B, C) - сторона напротив A
      b = dist(A, C) - сторона напротив B
      c = dist(A, B) - сторона напротив C
    """
    a = math.hypot(pts[2][0] - pts[1][0], pts[2][1] - pts[1][1])
    b = math.hypot(pts[2][0] - pts[0][0], pts[2][1] - pts[0][1])
    c = math.hypot(pts[1][0] - pts[0][0], pts[1][1] - pts[0][1])
    return (round(a, 1), round(b, 1), round(c, 1))

