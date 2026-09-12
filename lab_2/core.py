from PIL import Image, ImageDraw
import math

WHITE = (255, 255, 255)
GRAPH = (255, 0, 0)
AXIS = (0, 0, 0)


def create_image(width, height, color=WHITE):
    return Image.new("RGB", (width, height), color)


def load_image(path):
    return Image.open(path).convert("RGB")


def bottom_left_vertex(x0, y0, h):
    dx = h / math.sqrt(3)
    return (int(x0 - dx), int(y0 + h))


def inside_equilateral_triangle(px, py, x0, y0, h):
    # точка не выше вершины и не ниже основания
    if not (y0 <= py <= y0 + h):
        return False
    # точка между боковыми сторонами
    return abs(px - x0) <= (py - y0) / math.sqrt(3)


def copy_fragment(dest_img, src_img, h):

    width = min(dest_img.width, src_img.width)
    height = min(dest_img.height, src_img.height)

    # исходный треугольник (вершина и высота)
    x_0 = width // 2
    y_0 = height // 2

    # левый нижний угол (основание) исходного треугольника
    left_x, left_y = bottom_left_vertex(x_0, y_0, h)

    # куда переносим этот угол на новом изображении: левый нижний угол картинки
    margin = 10
    target_x = margin
    target_y = height - margin

    # смещение, которое переносит исходный треугольник в целевой угол
    distance_x = target_x - left_x
    distance_y = target_y - left_y

    for x in range(width):
        for y in range(height):
            if inside_equilateral_triangle(x, y, x_0, y_0, h):
                nx, ny = x + distance_x, y + distance_y
                if 0 <= nx < width and 0 <= ny < height:
                    dest_img.putpixel((nx, ny), src_img.getpixel((x, y)))

    return dest_img, src_img


def draw_axes(img):
    width, height = img.size
    cy = height // 2

    def line(x0, y0, x1, y1):
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for i in range(steps + 1):
            t = i / steps
            x = round(x0 + (x1 - x0) * t)
            y = round(y0 + (y1 - y0) * t)
            if 0 <= x < width and 0 <= y < height:
                img.putpixel((x, y), AXIS)

    # ось OY (вертикальная) со стрелкой вверх
    line(10, height - 10, 10, 10)
    line(5, 20, 10, 10)
    line(15, 20, 10, 10)

    # ось OX (горизонтальная) со стрелкой вправо
    line(8, cy, width - 10, cy)
    line(width - 20, cy - 5, width - 10, cy)
    line(width - 20, cy + 5, width - 10, cy)

    # деления на OY с шагом 10 пикселей
    for i in range((height - 40) // 20 + 1):
        line(10, cy + i * 10, 8, cy + i * 10)
        line(10, cy - i * 10, 8, cy - i * 10)

    # деления на OX с шагом 10 пикселей
    for i in range((width - 40) // 10 + 1):
        line((i + 1) * 10, cy, (i + 1) * 10, cy + 2)

    # подписи 0, x, y
    draw = ImageDraw.Draw(img)
    draw.text((1, cy + 1), "0", fill=AXIS)
    draw.text((width - 20, cy + 6), "x", fill=AXIS)
    draw.text((20, 1), "y", fill=AXIS)

    return img


def draw_function(img):
    width, height = img.size
    cy = height // 2
    scale_x = 10
    scale_y = cy - 20

    def point(x):
        arg = x / scale_x
        y = cy - round(((1 / arg) ** 2) * scale_y)
        return x + 10, y

    prev_x, prev_y = point(1)

    for x in range(2, width - 10):
        xi, yi = point(x)

        # соединяем предыдущую точку графика с текущей отрезком
        steps = max(abs(xi - prev_x), abs(yi - prev_y), 1)
        for i in range(steps + 1):
            t = i / steps
            px = round(prev_x + (xi - prev_x) * t)
            py = round(prev_y + (yi - prev_y) * t)
            if 0 <= px < width and 0 <= py < height:
                img.putpixel((px, py), GRAPH)

        prev_x, prev_y = xi, yi

    return img


def save_image(img, path):
    """Сохраняет изображение в файл на диске в формате Netpbm (PPM)."""
    img.save(path, format="PPM")
