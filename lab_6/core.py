from PIL import Image
import math


def load_image(path):
    return Image.open(path).convert("RGB")


def move(img, move_x = 0, move_y = 0):

    move_x = min(img.width, max(move_x, 0))
    move_y = min(img.height, max(move_y, 0))

    new_img = Image.new("RGB", img.size, (240,240,240))

    for x in range(img.width - move_x):
        for y in range(img.height - move_y):
            if (move_x, move_y) < (x, y) < img.size:
                new_img.putpixel((x + move_x,y + move_y), (img.getpixel((x, y))))

    return new_img


def mirror(img):
    new_img = Image.new("RGB", img.size)

    for x in range(img.width):
        for y in range(img.height):
            new_img.putpixel((-x,y), (img.getpixel((x,y))))

    return new_img


def undo_move(img, move_x = 0, move_y = 0):
    pass


def function_transform(img):
    # i = x ** 2 / (1 + x)
    # j = y
    # x = (i + sqrt(i ** 2 + 4 * i)) / 2 (обратная функция)

    new_img = Image.new("RGB", img.size, (240,240,240))

    for i in range(img.width):
        x = round(min(img.width - 1, max(0, (i + math.sqrt(i ** 2 + 4 * i)) / 2)))
        for y in range(img.height):
            new_img.putpixel((i, y), (img.getpixel((x, y))))

    return new_img


def save_image(img, path):
    img.save(path, format="PPM")
