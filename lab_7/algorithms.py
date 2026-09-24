import math
import numpy as np
import scipy.ndimage as ndi
from PIL import Image
from typing import Tuple, Optional, Dict, Any

# Таблица 1: Распространённые матрицы свёртки линейных фильтров

GAUSSIAN_5X5 = np.array([
    [0,  1,  2,  1, 0],
    [1,  6, 10,  6, 1],
    [2, 10, 16, 10, 2],
    [1,  6, 10,  6, 1],
    [0,  1,  2,  1, 0],
], dtype=np.float64)

LOG_5X5 = np.array([
    [-1, -2, -3, -2, -1],
    [-2,  0,  4,  0, -2],
    [-3,  4, 16,  4, -3],
    [-2,  0,  4,  0, -2],
    [-1, -2, -3, -2, -1],
], dtype=np.float64)

LAPLACIAN_4 = np.array([
    [ 0, -1,  0],
    [-1,  4, -1],
    [ 0, -1,  0]
], dtype=np.float64)

LAPLACIAN_8 = np.array([
    [-1, -1, -1],
    [-1,  8, -1],
    [-1, -1, -1]
], dtype=np.float64)

SOBEL_X = np.array([
    [-1, 0, 1],
    [-2, 0, 2],
    [-1, 0, 1]
], dtype=np.float64)

SOBEL_Y = np.array([
    [-1, -2, -1],
    [ 0,  0,  0],
    [ 1,  2,  1]
], dtype=np.float64)


def create_gaussian_kernel(size: int = 5, sigma: float = 1.0) -> np.ndarray:
    if size % 2 == 0:
        size += 1
    radius = size // 2
    y, x = np.ogrid[-radius:radius + 1, -radius:radius + 1]
    if sigma <= 0:
        sigma = 1e-4
    kernel = (1.0 / (2.0 * math.pi * (sigma ** 2))) * np.exp(-(x ** 2 + y ** 2) / (2.0 * (sigma ** 2)))
    k_sum = np.sum(kernel)
    if k_sum > 0:
        kernel /= k_sum
    return kernel


def convolve2d(channel: np.ndarray, kernel: np.ndarray, mode: str = "reflect") -> np.ndarray:
    return ndi.convolve(channel.astype(np.float64), kernel, mode=mode)


def normalize_to_byte_range(channel: np.ndarray) -> np.ndarray:
    min_val = float(np.min(channel))
    if min_val >= 0:
        min_shift = 0.0
    else:
        min_shift = min_val

    shifted = channel - min_shift
    max_val = float(np.max(shifted))

    if max_val <= 255.0:
        scale = 1.0
    else:
        scale = 255.0 / max_val if max_val > 0 else 1.0

    result = shifted * scale
    return np.clip(result, 0, 255).astype(np.uint8)


def apply_gaussian_blur(
    image: Image.Image,
    kernel: Optional[np.ndarray] = None,
    sigma: Optional[float] = None,
    size: int = 5
) -> Image.Image:
    if kernel is None:
        if sigma is not None and sigma > 0:
            k = create_gaussian_kernel(size=size, sigma=sigma)
        else:
            k = GAUSSIAN_5X5.copy()
            k /= np.sum(k)
    else:
        k = kernel.copy()
        k_sum = np.sum(k)
        if k_sum > 0:
            k /= k_sum

    img_rgb = image.convert("RGB")
    arr = np.array(img_rgb)
    out_channels = []
    for c in range(3):
        conv_c = convolve2d(arr[:, :, c], k, mode="reflect")
        out_channels.append(np.clip(conv_c, 0, 255).astype(np.uint8))

    return Image.fromarray(np.stack(out_channels, axis=2), mode="RGB")


def apply_variant12_lpf(
    image: Image.Image,
    rect_w: int,
    rect_h: int,
    kernel: Optional[np.ndarray] = None,
    sigma: Optional[float] = None
) -> Tuple[Image.Image, Tuple[int, int, int, int]]:
    img_rgb = image.convert("RGB")
    w, h = img_rgb.size

    rw = max(1, min(w, int(rect_w)))
    rh = max(1, min(h, int(rect_h)))

    x1 = max(0, (w - rw) // 2)
    y1 = max(0, (h - rh) // 2)
    x2 = min(w, x1 + rw)
    y2 = min(h, y1 + rh)

    blurred = apply_gaussian_blur(img_rgb, kernel=kernel, sigma=sigma)

    orig_arr = np.array(img_rgb)
    blur_arr = np.array(blurred)

    result_arr = blur_arr.copy()
    result_arr[y1:y2, x1:x2] = orig_arr[y1:y2, x1:x2]

    return Image.fromarray(result_arr, mode="RGB"), (x1, y1, x2, y2)


def apply_variant12_hpf(
    image: Image.Image,
    kernel: Optional[np.ndarray] = None,
    return_channels: bool = False
):
    if kernel is None:
        k = LOG_5X5
    else:
        k = kernel

    img_rgb = image.convert("RGB")
    w, h = img_rgb.size
    mid_x = w // 2

    hsv_img = img_rgb.convert("HSV")
    h_chan, s_chan, v_chan = hsv_img.split()

    h_arr = np.array(h_chan, dtype=np.float64)
    s_arr = np.array(s_chan, dtype=np.float64)
    v_arr = np.array(v_chan, dtype=np.float64)

    norm_log_h = normalize_to_byte_range(convolve2d(h_arr, k, mode="reflect"))
    norm_log_s = normalize_to_byte_range(convolve2d(s_arr, k, mode="reflect"))
    norm_log_v = normalize_to_byte_range(convolve2d(v_arr, k, mode="reflect"))

    out_h = np.array(h_chan, dtype=np.uint8)
    out_s = np.array(s_chan, dtype=np.uint8)
    out_v = np.array(v_chan, dtype=np.uint8)

    # Левая половина: LoG применяется только для H (тон) и V (яркость)
    out_h[:, :mid_x] = norm_log_h[:, :mid_x]
    out_v[:, :mid_x] = norm_log_v[:, :mid_x]
    # out_s[:, :mid_x] остаётся исходным

    # Правая половина: LoG применяется только для S (насыщенность) и V (яркость)
    out_s[:, mid_x:] = norm_log_s[:, mid_x:]
    out_v[:, mid_x:] = norm_log_v[:, mid_x:]
    # out_h[:, mid_x:] остаётся исходным

    h_out = Image.fromarray(out_h, mode="L")
    s_out = Image.fromarray(out_s, mode="L")
    v_out = Image.fromarray(out_v, mode="L")

    res_rgb = Image.merge("HSV", (h_out, s_out, v_out)).convert("RGB")

    if return_channels:
        return res_rgb, {
            "H": h_out,
            "S": s_out,
            "V": v_out,
            "raw_h": out_h,
            "raw_s": out_s,
            "raw_v": out_v
        }
    return res_rgb


def get_hsv_channels(image: Image.Image) -> Dict[str, Image.Image]:
    hsv = image.convert("HSV")
    h, s, v = hsv.split()
    return {
        "H": h,
        "S": s,
        "V": v
    }


def save_image(img: Image.Image, filepath: str) -> None:
    ext = filepath.lower()
    if ext.endswith(".pbm"):
        img.convert("RGB").save(filepath, format="PPM")
    elif ext.endswith((".jpg", ".jpeg")):
        img.convert("RGB").save(filepath, format="JPEG", quality=95)
    else:
        img.save(filepath)
