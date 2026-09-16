import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import ImageTk

import core

image1 = None
image2 = None
transform_result = None
overlay_result = None


def refresh_canvas(canvas, img):
    canvas.delete("all")
    if img is None:
        return
    photo = ImageTk.PhotoImage(img)
    canvas.image = photo  # чтобы не собрал сборщик мусора
    canvas.create_image(0, 0, anchor="nw", image=photo)


def on_open1():
    global image1
    path = filedialog.askopenfilename()
    if not path:
        return
    image1 = core.load_image(path)
    refresh_canvas(canvas1, image1)


def on_open2():
    global image2
    path = filedialog.askopenfilename()
    if not path:
        return
    image2 = core.load_image(path)
    refresh_canvas(canvas2, image2)


def on_transform():
    global transform_result
    if image1 is None:
        messagebox.showerror("Ошибка", "Сначала откройте изображение")
        return
    move_x = int(move_x_entry.get())
    move_y = int(move_y_entry.get())
    transform_result = core.move(image1, move_x, move_y)
    mirror_result = core.mirror(transform_result)
    refresh_canvas(canvas2, transform_result)
    refresh_canvas(canvas3, mirror_result)


def on_overlay():
    global overlay_result
    if image1 is None or image2 is None:
        messagebox.showerror("Ошибка", "Сначала откройте оба изображения")
        return
    overlay_result = core.overlay_blend(image1, image2)
    refresh_canvas(canvas4, overlay_result)


def on_save_transform():
    if transform_result is None:
        messagebox.showerror("Ошибка", "Нечего сохранять")
        return
    path = filedialog.asksaveasfilename(
        defaultextension=".ppm",
        filetypes=[("PPM файл", "*.ppm")],
    )
    if path:
        core.save_image(transform_result, path)


def on_save_overlay():
    if overlay_result is None:
        messagebox.showerror("Ошибка", "Нечего сохранять")
        return
    path = filedialog.asksaveasfilename(
        defaultextension=".ppm",
        filetypes=[("PPM файл", "*.ppm")],
    )
    if path:
        core.save_image(overlay_result, path)


root = tk.Tk()
root.title("Лабораторная работа №5")

buttons = tk.Frame(root)
buttons.pack(side="top", fill="x", padx=5, pady=5)

tk.Button(buttons, text="Открыть 1", command=on_open1).grid(row=0, column=0, padx=2)
tk.Button(buttons, text="Открыть 2", command=on_open2).grid(row=0, column=1, padx=2)
tk.Button(buttons, text="Преобразовать", command=on_transform).grid(row=0, column=2, padx=2)
tk.Button(buttons, text="Наложить", command=on_overlay).grid(row=0, column=3, padx=2)
tk.Button(buttons, text="Сохранить результат 1", command=on_save_transform).grid(row=0, column=4, padx=2)
tk.Button(buttons, text="Сохранить результат 2", command=on_save_overlay).grid(row=0, column=5, padx=2)

tk.Label(buttons, text="Сдвиг по X:").grid(row=0, column=6, padx=(10, 2))
move_x_entry = tk.Entry(buttons, width=6)
move_x_entry.insert(0, "20")
move_x_entry.grid(row=0, column=7, padx=2)

tk.Label(buttons, text="Сдвиг по Y:").grid(row=0, column=8, padx=(10, 2))
move_y_entry = tk.Entry(buttons, width=6)
move_y_entry.insert(0, "20")
move_y_entry.grid(row=0, column=9, padx=2)

canvases = tk.Frame(root)
canvases.pack(side="top", fill="both", expand=True, padx=5, pady=5)

tk.Label(canvases, text="Изображение 1").grid(row=0, column=0)
tk.Label(canvases, text="Сдвиг по X и Y").grid(row=0, column=1)
tk.Label(canvases, text="Отражение сдвинутого изображения").grid(row=0, column=2)

canvas1 = tk.Canvas(canvases, width=250, height=250, bg="gray")
canvas1.grid(row=1, column=0, padx=5, pady=5)

canvas2 = tk.Canvas(canvases, width=250, height=250, bg="gray")
canvas2.grid(row=1, column=1, padx=5, pady=5)

canvas3 = tk.Canvas(canvases, width=250, height=250, bg="gray")
canvas3.grid(row=1, column=2, padx=5, pady=5)

tk.Label(canvases, text="Результат").grid(row=2, column=0)
tk.Label(canvases, text="Результат").grid(row=2, column=1)

canvas5 = tk.Canvas(canvases, width=250, height=250, bg="gray")
canvas5.grid(row=3, column=0, padx=5, pady=5)

canvas4 = tk.Canvas(canvases, width=250, height=250, bg="gray")
canvas4.grid(row=3, column=1, padx=5, pady=5)

root.mainloop()
