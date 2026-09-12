from PIL import Image
import math


def load_image(path):
    return Image.open(path).convert("RGB")


def log_brightness(img):
    h, s, v = img.convert("HSV").split()

    width, height = v.size
    v_new_img = Image.new("L", (width, height))

    c = 255 / math.log(1 + 255)  # c = V_max / log(1 + V_max)

    # V_new = c * log(1 + V)
    for y in range(height):
        for x in range(width):
            old_value = v.getpixel((x, y))
            new_value = int(c * math.log(1 + old_value))
            v_new_img.putpixel((x, y), new_value)

    return Image.merge("HSV", (h, s, v_new_img)).convert("RGB")


def overlay_channel(c_new, w, h, c1, c2):
    for x in range(w):
        for y in range(h):
            v1 = c1.getpixel((x, y))
            v2 = c2.getpixel((x, y))
            c_new.putpixel((x, y), (v1 * v2) // 255 if v1 < 128 else 255 - ((255 - v1) * (255 - v2)) // 255)


def overlay_blend(img1, img2):
    r1, g1, b1 = img1.split()
    r2, g2, b2 = img2.split()

    width = min(img1.width, img2.width)
    height = min(img1.height, img2.height)

    new_img = Image.new("RGB", (width, height))
    r_new, g_new, b_new = new_img.split()

    overlay_channel(r_new, width, height, r1, r2)
    overlay_channel(g_new, width, height, g1, g2)
    overlay_channel(b_new, width, height, b1, b2)

    return Image.merge("RGB", (r_new, g_new, b_new)).convert("RGB")


def save_image(img, path):
    """Сохраняет изображение в файл на диске в формате Netpbm (PPM)."""
    img.save(path, format="PPM")
