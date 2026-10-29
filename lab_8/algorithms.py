"""Аффинные преобразования и интерполяция изображений."""

import math
import time
from dataclasses import dataclass
from typing import Tuple, Dict, Any, Optional, Literal
import numpy as np
from PIL import Image, ImageDraw


@dataclass
class TransformParams:
    scale_x: float = 1.0
    scale_y: float = 1.0
    angle_deg: float = 0.0
    shear_x: float = 0.0
    shear_y: float = 0.0
    fit_bbox: bool = True
    bg_color: Tuple[int, int, int] = (255, 255, 255)


def lagrange_basis(t: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Кубические базисные полиномы Лагранжа для сетки {-1, 0, 1, 2}."""
    t_m1 = t - 1.0
    t_p1 = t + 1.0
    t_m2 = t - 2.0

    l_m1 = -t * t_m1 * t_m2 / 6.0
    l_0 = t_p1 * t_m1 * t_m2 / 2.0
    l_1 = -t * t_p1 * t_m2 / 2.0
    l_2 = t * t_p1 * t_m1 / 6.0

    return l_m1, l_0, l_1, l_2


def build_linear_affine_matrix(
    scale_x: float,
    scale_y: float,
    angle_deg: float,
    shear_x: float,
    shear_y: float
) -> np.ndarray:
    """Линейная часть преобразования: A = R(theta) * K(shear) * S(scale)."""
    s_mat = np.array([
        [scale_x, 0.0],
        [0.0, scale_y]
    ], dtype=np.float64)

    k_mat = np.array([
        [1.0, shear_x],
        [shear_y, 1.0]
    ], dtype=np.float64)

    rad = math.radians(angle_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    r_mat = np.array([
        [cos_a, -sin_a],
        [sin_a, cos_a]
    ], dtype=np.float64)

    return r_mat @ k_mat @ s_mat


def compute_geometry(
    w_in: int,
    h_in: int,
    params: TransformParams
) -> Tuple[np.ndarray, np.ndarray, int, int]:
    """Расчет размеров выходного растра и матриц прямого/обратного отображения."""
    a_mat = build_linear_affine_matrix(
        params.scale_x, params.scale_y,
        params.angle_deg,
        params.shear_x, params.shear_y
    )

    det = np.linalg.det(a_mat)
    if abs(det) < 1e-9:
        raise ValueError("Вырожденное преобразование (определитель близок к 0).")

    c_in = np.array([w_in / 2.0, h_in / 2.0], dtype=np.float64)
    corners_local = np.array([
        [-w_in / 2.0, -h_in / 2.0],
        [ w_in / 2.0, -h_in / 2.0],
        [-w_in / 2.0,  h_in / 2.0],
        [ w_in / 2.0,  h_in / 2.0],
    ], dtype=np.float64)

    t_corners = corners_local @ a_mat.T

    if params.fit_bbox:
        min_xy = np.min(t_corners, axis=0)
        max_xy = np.max(t_corners, axis=0)
        w_out = max(1, int(np.ceil(max_xy[0] - min_xy[0])))
        h_out = max(1, int(np.ceil(max_xy[1] - min_xy[1])))
    else:
        w_out, h_out = w_in, h_in

    c_out = np.array([w_out / 2.0, h_out / 2.0], dtype=np.float64)

    shift_fwd = c_out - (a_mat @ c_in)
    forward_m = np.eye(3, dtype=np.float64)
    forward_m[:2, :2] = a_mat
    forward_m[:2, 2] = shift_fwd

    a_inv = np.linalg.inv(a_mat)
    shift_inv = c_in - (a_inv @ c_out)
    inverse_m = np.eye(3, dtype=np.float64)
    inverse_m[:2, :2] = a_inv
    inverse_m[:2, 2] = shift_inv

    return forward_m, inverse_m, w_out, h_out


def interpolate_nearest(
    img_arr: np.ndarray,
    x_coords: np.ndarray,
    y_coords: np.ndarray,
    bg_color: Tuple[int, int, int] = (255, 255, 255)
) -> np.ndarray:
    """Интерполяция методом ближайшего соседа."""
    h_in, w_in = img_arr.shape[:2]
    h_out, w_out = x_coords.shape

    x_idx = np.rint(x_coords).astype(np.int64)
    y_idx = np.rint(y_coords).astype(np.int64)
    valid = (x_idx >= 0) & (x_idx < w_in) & (y_idx >= 0) & (y_idx < h_in)

    out = np.empty((h_out, w_out, 3), dtype=np.uint8)
    out[:] = bg_color
    out[valid] = img_arr[y_idx[valid], x_idx[valid]]
    return out


def interpolate_bilinear(
    img_arr: np.ndarray,
    x_coords: np.ndarray,
    y_coords: np.ndarray,
    bg_color: Tuple[int, int, int] = (255, 255, 255)
) -> np.ndarray:
    """Билинейная интерполяция по 4 соседним отсчетам."""
    h_in, w_in = img_arr.shape[:2]
    h_out, w_out = x_coords.shape

    valid = (x_coords >= 0.0) & (x_coords <= float(w_in - 1)) & \
            (y_coords >= 0.0) & (y_coords <= float(h_in - 1))

    l = np.floor(x_coords).astype(np.int64)
    k = np.floor(y_coords).astype(np.int64)

    a = (x_coords - l).astype(np.float64)
    b = (y_coords - k).astype(np.float64)

    l0 = np.clip(l, 0, w_in - 1)
    l1 = np.clip(l + 1, 0, w_in - 1)
    k0 = np.clip(k, 0, h_in - 1)
    k1 = np.clip(k + 1, 0, h_in - 1)

    w00 = ((1.0 - a) * (1.0 - b))[..., None]
    w10 = (a * (1.0 - b))[..., None]
    w01 = ((1.0 - a) * b)[..., None]
    w11 = (a * b)[..., None]

    f00 = img_arr[k0, l0].astype(np.float64)
    f10 = img_arr[k0, l1].astype(np.float64)
    f01 = img_arr[k1, l0].astype(np.float64)
    f11 = img_arr[k1, l1].astype(np.float64)

    interp = w00 * f00 + w10 * f10 + w01 * f01 + w11 * f11

    out = np.empty((h_out, w_out, 3), dtype=np.uint8)
    out[:] = bg_color
    out[valid] = np.clip(np.rint(interp[valid]), 0, 255).astype(np.uint8)
    return out


def interpolate_bicubic(
    img_arr: np.ndarray,
    x_coords: np.ndarray,
    y_coords: np.ndarray,
    bg_color: Tuple[int, int, int] = (255, 255, 255)
) -> np.ndarray:
    """Бикубическая интерполяция по окрестности 4x4 (полином Лагранжа 16 отсчетов)."""
    h_in, w_in = img_arr.shape[:2]
    h_out, w_out = x_coords.shape

    valid = (x_coords >= 0.0) & (x_coords <= float(w_in - 1)) & \
            (y_coords >= 0.0) & (y_coords <= float(h_in - 1))

    l = np.floor(x_coords).astype(np.int64)
    k = np.floor(y_coords).astype(np.int64)

    a = (x_coords - l).astype(np.float64)
    b = (y_coords - k).astype(np.float64)

    la = lagrange_basis(a)
    lb = lagrange_basis(b)
    offsets = [-1, 0, 1, 2]

    accum = np.zeros((h_out, w_out, 3), dtype=np.float64)
    for j_idx, dj in enumerate(offsets):
        yj = np.clip(k + dj, 0, h_in - 1)
        row_sum = np.zeros((h_out, w_out, 3), dtype=np.float64)
        for i_idx, di in enumerate(offsets):
            xi = np.clip(l + di, 0, w_in - 1)
            row_sum += img_arr[yj, xi].astype(np.float64) * la[i_idx][..., None]
        accum += row_sum * lb[j_idx][..., None]

    out = np.empty((h_out, w_out, 3), dtype=np.uint8)
    out[:] = bg_color
    out[valid] = np.clip(np.rint(accum[valid]), 0, 255).astype(np.uint8)
    return out


INTERPOLATION_METHODS = {
    "nearest": ("Ближайший сосед", interpolate_nearest),
    "bilinear": ("Билинейная", interpolate_bilinear),
    "bicubic": ("Бикубическая (Лагранж 16 точек)", interpolate_bicubic),
}


def apply_affine_transform(
    image: Image.Image,
    params: TransformParams,
    method: Literal["nearest", "bilinear", "bicubic"] = "bilinear"
) -> Tuple[Image.Image, float]:
    """Применяет аффинное преобразование с выбранным методом интерполяции."""
    img_arr = np.array(image.convert("RGB"), dtype=np.uint8)
    h_in, w_in = img_arr.shape[:2]

    _, inverse_m, w_out, h_out = compute_geometry(w_in, h_in, params)

    grid_u, grid_v = np.meshgrid(
        np.arange(w_out, dtype=np.float64),
        np.arange(h_out, dtype=np.float64)
    )

    x_coords = inverse_m[0, 0] * grid_u + inverse_m[0, 1] * grid_v + inverse_m[0, 2]
    y_coords = inverse_m[1, 0] * grid_u + inverse_m[1, 1] * grid_v + inverse_m[1, 2]

    interp_fn = INTERPOLATION_METHODS.get(method, INTERPOLATION_METHODS["bilinear"])[1]

    t_start = time.perf_counter()
    out_arr = interp_fn(img_arr, x_coords, y_coords, bg_color=params.bg_color)
    elapsed_ms = (time.perf_counter() - t_start) * 1000.0

    return Image.fromarray(out_arr), elapsed_ms


def apply_all_methods(
    image: Image.Image,
    params: TransformParams
) -> Dict[str, Tuple[Image.Image, float]]:
    """Применяет преобразование всеми 3 методами интерполяции."""
    img_arr = np.array(image.convert("RGB"), dtype=np.uint8)
    h_in, w_in = img_arr.shape[:2]

    _, inverse_m, w_out, h_out = compute_geometry(w_in, h_in, params)

    grid_u, grid_v = np.meshgrid(
        np.arange(w_out, dtype=np.float64),
        np.arange(h_out, dtype=np.float64)
    )

    x_coords = inverse_m[0, 0] * grid_u + inverse_m[0, 1] * grid_v + inverse_m[0, 2]
    y_coords = inverse_m[1, 0] * grid_u + inverse_m[1, 1] * grid_v + inverse_m[1, 2]

    results = {}
    for key, (_, fn) in INTERPOLATION_METHODS.items():
        t0 = time.perf_counter()
        arr = fn(img_arr, x_coords, y_coords, bg_color=params.bg_color)
        t1 = time.perf_counter()
        results[key] = (Image.fromarray(arr), (t1 - t0) * 1000.0)

    return results


def calculate_metrics(
    original_arr: np.ndarray,
    restored_arr: np.ndarray,
    mask: Optional[np.ndarray] = None
) -> Dict[str, float]:
    """Вычисляет MSE, PSNR и MAE между двумя изображениями."""
    diff = original_arr.astype(np.float64) - restored_arr.astype(np.float64)

    if mask is not None and np.any(mask):
        diff_masked = diff[mask]
        mse = float(np.mean(diff_masked ** 2))
        mae = float(np.mean(np.abs(diff_masked)))
    else:
        mse = float(np.mean(diff ** 2))
        mae = float(np.mean(np.abs(diff)))

    psnr = float("inf") if mse < 1e-12 else 10.0 * math.log10((255.0 ** 2) / mse)
    return {"mse": mse, "psnr": psnr, "mae": mae}


def compute_difference_map(
    original_arr: np.ndarray,
    restored_arr: np.ndarray,
    amplification: float = 5.0
) -> Image.Image:
    """Создает цветовую карту различий с усилением ошибки."""
    diff = np.abs(original_arr.astype(np.float64) - restored_arr.astype(np.float64))
    diff_gray = np.mean(diff, axis=-1)
    diff_amp = np.clip(diff_gray * amplification, 0, 255).astype(np.uint8)

    h, w = diff_amp.shape
    cmap = np.zeros((h, w, 3), dtype=np.uint8)
    val = diff_amp.astype(np.float64) / 255.0

    cmap[..., 0] = np.clip(val * 2.0 * 255.0, 0, 255).astype(np.uint8)
    cmap[..., 1] = np.clip((1.0 - np.abs(val - 0.5) * 2.0) * 255.0, 0, 255).astype(np.uint8)
    cmap[..., 2] = np.clip((1.0 - val * 2.0) * 255.0, 0, 255).astype(np.uint8)
    cmap[diff_amp == 0] = 20

    return Image.fromarray(cmap)


def evaluate_round_trip(
    image: Image.Image,
    params: TransformParams
) -> Dict[str, Any]:
    """Цикл восстановления T -> T^{-1} для всех методов."""
    orig_rgb = image.convert("RGB")
    orig_arr = np.array(orig_rgb, dtype=np.uint8)
    w_orig, h_orig = orig_rgb.size

    fwd_dict = apply_all_methods(orig_rgb, params)
    fwd_m, _, _, _ = compute_geometry(w_orig, h_orig, params)

    grid_x, grid_y = np.meshgrid(
        np.arange(w_orig, dtype=np.float64),
        np.arange(h_orig, dtype=np.float64)
    )
    x_in_fwd = fwd_m[0, 0] * grid_x + fwd_m[0, 1] * grid_y + fwd_m[0, 2]
    y_in_fwd = fwd_m[1, 0] * grid_x + fwd_m[1, 1] * grid_y + fwd_m[1, 2]

    results = {}
    for key in ["nearest", "bilinear", "bicubic"]:
        fwd_img, fwd_time = fwd_dict[key]
        fwd_arr = np.array(fwd_img, dtype=np.uint8)
        w_fwd, h_fwd = fwd_img.size

        interp_fn = INTERPOLATION_METHODS[key][1]
        t0 = time.perf_counter()
        restored_arr = interp_fn(fwd_arr, x_in_fwd, y_in_fwd, bg_color=params.bg_color)
        inv_time = (time.perf_counter() - t0) * 1000.0

        mask_valid = (x_in_fwd >= 2) & (x_in_fwd < w_fwd - 2) & (y_in_fwd >= 2) & (y_in_fwd < h_fwd - 2)
        metrics = calculate_metrics(orig_arr, restored_arr, mask=mask_valid)
        diff_map = compute_difference_map(orig_arr, restored_arr, amplification=6.0)

        results[key] = {
            "forward_img": fwd_img,
            "forward_time": fwd_time,
            "restored_img": Image.fromarray(restored_arr),
            "inverse_time": inv_time,
            "total_time": fwd_time + inv_time,
            "metrics": metrics,
            "diff_map": diff_map,
        }

    return results


def generate_test_pattern(pattern_type: str = "shapes", width: int = 400, height: int = 400) -> Image.Image:
    """Генерация тестового растрового изображения."""
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    if pattern_type == "shapes":
        draw.rectangle([0, 0, width, height], fill=(250, 250, 250))
        draw.rectangle([30, 30, 150, 150], fill=(230, 50, 50), outline=(120, 0, 0), width=2)
        draw.ellipse([220, 30, 360, 170], fill=(50, 160, 240), outline=(10, 80, 160), width=2)
        draw.polygon([(100, 220), (160, 350), (40, 350)], fill=(50, 200, 80), outline=(20, 120, 40), width=2)

        cx, cy = 290, 280
        pts = []
        for i in range(10):
            r = 70 if i % 2 == 0 else 30
            ang = math.radians(i * 36 - 90)
            pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        draw.polygon(pts, fill=(240, 190, 30), outline=(160, 110, 10), width=2)

    elif pattern_type == "grid_circles":
        for y in range(height):
            v = int(240 + 15 * math.sin(y / 20.0))
            draw.line([(0, y), (width - 1, y)], fill=(v, v, 255))

        step = 25
        for x in range(0, width, step):
            draw.line([(x, 0), (x, height)], fill=(200, 200, 200), width=1)
        for y in range(0, height, step):
            draw.line([(0, y), (width, y)], fill=(200, 200, 200), width=1)

        cx, cy = width // 2, height // 2
        for r in range(15, min(cx, cy) - 20, 14):
            color = (20, 20, 180) if (r // 14) % 2 == 0 else (220, 40, 40)
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=2)

        for deg in range(0, 360, 15):
            rad = math.radians(deg)
            r_max = min(cx, cy) - 25
            ex = int(cx + r_max * math.cos(rad))
            ey = int(cy + r_max * math.sin(rad))
            draw.line([(cx, cy), (ex, ey)], fill=(30, 120, 30), width=1)

    elif pattern_type == "text_lines":
        draw.rectangle([0, 0, width, height], fill=(245, 248, 252))
        y_pos = 20
        for w in [1, 2, 3, 5, 8]:
            draw.line([(20, y_pos), (width - 20, y_pos)], fill=(0, 0, 0), width=w)
            y_pos += w + 12
        for i in range(12):
            draw.line([(30 + i * 25, y_pos + 10), (70 + i * 25, y_pos + 90)], fill=(180, 20, 60), width=1 + (i % 3))
        y_pos += 110
        draw.text((25, y_pos), "INTERPOLATION BENCHMARK", fill=(0, 0, 120))
        y_pos += 24
        draw.text((25, y_pos), "Nearest Neighbor vs Bilinear vs Bicubic", fill=(40, 40, 40))

    elif pattern_type == "checkerboard":
        tile = 20
        for i in range(0, width, tile):
            for j in range(0, height, tile):
                if ((i // tile) + (j // tile)) % 2 == 0:
                    c = int(255 * (i / width))
                    draw.rectangle([i, j, i + tile, j + tile], fill=(c, 40, 255 - c))
                else:
                    draw.rectangle([i, j, i + tile, j + tile], fill=(245, 245, 245))

    return img
