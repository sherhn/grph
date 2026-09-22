import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import ImageTk

import core

new_image = None
source_image = None


def refresh_canvas(canvas, img):
    canvas.delete("all")
    if img is None:
        return
    photo = ImageTk.PhotoImage(img)
    canvas.image = photo  # чтобы не собрал сборщик мусора
    canvas.create_image(0, 0, anchor="nw", image=photo)


def on_create():
    global new_image
    try:
        width = int(entry_width.get())
        height = int(entry_height.get())
    except ValueError:
        messagebox.showerror("Ошибка", "Ширина и высота должны быть целыми числами")
        return
    new_image = core.create_image(width, height)
    refresh_canvas(canvas1, new_image)


def on_open():
    global source_image
    path = filedialog.askopenfilename()
    if not path:
        return
    source_image = core.load_image(path)
    refresh_canvas(canvas2, source_image)


def on_transfer():
    global new_image, source_image
    if new_image is None or source_image is None:
        messagebox.showerror("Ошибка", "Сначала создайте новое изображение и откройте исходное")
        return
    try:
        h = int(entry_h.get())
    except ValueError:
        messagebox.showerror("Ошибка", "Высота должна быть целым числом")
        return
    new_image, source_image = core.copy_fragment(new_image, source_image, h)
    refresh_canvas(canvas1, new_image)
    refresh_canvas(canvas2, source_image)


def on_axes():
    global new_image
    if new_image is None:
        messagebox.showerror("Ошибка", "Сначала создайте новое изображение")
        return
    new_image = core.draw_axes(new_image)
    refresh_canvas(canvas1, new_image)


def on_graph():
    global new_image
    if new_image is None:
        messagebox.showerror("Ошибка", "Сначала создайте новое изображение")
        return
    new_image = core.draw_function(new_image)
    refresh_canvas(canvas1, new_image)


def on_save():
    global new_image
    if new_image is None:
        messagebox.showerror("Ошибка", "Нечего сохранять")
        return
    path = filedialog.asksaveasfilename(
        title="Сохранить рисунок в файл",
        defaultextension=".pbm",
        filetypes=[
            ("PBM Image", "*.pbm"),
            ("PNG Image", "*.png"),
            ("BMP Image", "*.bmp"),
            ("JPEG Image", "*.jpg"),
            ("All Files", "*.*"),
        ],
    )
    if not path:
        return
    try:
        if path.lower().endswith(".pbm"):
            new_image.convert("RGB").save(path, format="PPM")
        elif path.lower().endswith(".jpg") or path.lower().endswith(".jpeg"):
            new_image.convert("RGB").save(path)
        else:
            new_image.save(path)
        messagebox.showinfo("Успех", f"Изображение успешно сохранено в:\n{path}")
    except Exception as e:
        messagebox.showerror("Ошибка сохранения", f"Не удалось сохранить файл:\n{str(e)}")


root = tk.Tk()
root.title("Лабораторная работа №2")

controls = tk.Frame(root)
controls.pack(side="top", fill="x", padx=5, pady=5)

tk.Label(controls, text="Ширина").grid(row=0, column=0)
entry_width = tk.Entry(controls, width=6)
entry_width.insert(0, "300")
entry_width.grid(row=0, column=1)

tk.Label(controls, text="Высота").grid(row=0, column=2)
entry_height = tk.Entry(controls, width=6)
entry_height.insert(0, "300")
entry_height.grid(row=0, column=3)

tk.Label(controls, text="Высота треугольника").grid(row=1, column=0)
entry_h = tk.Entry(controls, width=6)
entry_h.insert(0, "50")
entry_h.grid(row=1, column=1)

buttons = tk.Frame(root)
buttons.pack(side="top", fill="x", padx=5, pady=5)

tk.Button(buttons, text="Создать", command=on_create).grid(row=0, column=0, padx=2)
tk.Button(buttons, text="Открыть", command=on_open).grid(row=0, column=1, padx=2)
tk.Button(buttons, text="Перенести", command=on_transfer).grid(row=0, column=2, padx=2)
tk.Button(buttons, text="Оси", command=on_axes).grid(row=0, column=3, padx=2)
tk.Button(buttons, text="График", command=on_graph).grid(row=0, column=4, padx=2)
tk.Button(buttons, text="Сохранить", command=on_save).grid(row=0, column=5, padx=2)

canvases = tk.Frame(root)
canvases.pack(side="top", fill="both", expand=True, padx=5, pady=5)

tk.Label(canvases, text="Новое изображение (Image1)").grid(row=0, column=0)
tk.Label(canvases, text="Исходное изображение (Image2)").grid(row=0, column=1)

canvas1 = tk.Canvas(canvases, width=300, height=300, bg="gray")
canvas1.grid(row=1, column=0, padx=5)

canvas2 = tk.Canvas(canvases, width=300, height=300, bg="gray")
canvas2.grid(row=1, column=1, padx=5)

root.mainloop()
