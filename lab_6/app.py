import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import ImageTk

import core

image = None
transform_result = None
mirror_result = None
undo_transform_result = None
undo_mirror_result = None
function_result = None


def refresh_canvas(canvas, img):
    canvas.delete("all")
    if img is None:
        return
    photo = ImageTk.PhotoImage(img)
    canvas.image = photo  # чтобы не собрал сборщик мусора
    canvas.create_image(0, 0, anchor="nw", image=photo)


def on_open1():
    global image
    path = filedialog.askopenfilename()
    if not path:
        return
    image = core.load_image(path)
    refresh_canvas(canvas1, image)


def on_transform():
    global transform_result, mirror_result
    if image is None:
        messagebox.showerror("Ошибка", "Сначала откройте изображение")
        return
    move_x = int(move_x_entry.get())
    move_y = int(move_y_entry.get())
    transform_result = core.move(image, move_x, move_y)
    mirror_result = core.mirror(image)
    refresh_canvas(canvas2, transform_result)
    refresh_canvas(canvas3, mirror_result)


def on_undo():
    global transform_result, mirror_result, undo_transform_result, undo_mirror_result
    if transform_result is None and mirror_result is None:
        messagebox.showerror("Ошибка", "Сначала преобразуйте изображения")
        return
    move_x = int(move_x_entry.get())
    move_y = int(move_y_entry.get())
    undo_transform_result = core.move(transform_result, -move_x, -move_y)
    undo_mirror_result = core.mirror(mirror_result)
    refresh_canvas(canvas4, undo_transform_result)
    refresh_canvas(canvas5, undo_mirror_result)


def on_function():
    global image, function_result
    if image is None:
        messagebox.showerror("Ошибка", "Сначала откройте изображение")
        return
    function_result = core.function_transform(image)
    refresh_canvas(canvas6, function_result)


def save_result_image(img):
    if img is None:
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
            img.convert("RGB").save(path, format="PPM")
        elif path.lower().endswith(".jpg") or path.lower().endswith(".jpeg"):
            img.convert("RGB").save(path)
        else:
            img.save(path)
        messagebox.showinfo("Успех", f"Изображение успешно сохранено в:\n{path}")
    except Exception as e:
        messagebox.showerror("Ошибка сохранения", f"Не удалось сохранить файл:\n{str(e)}")


root = tk.Tk()
root.title("Лабораторная работа №6")

buttons = tk.Frame(root)
buttons.pack(side="top", fill="x", padx=5, pady=5)

tk.Button(buttons, text="Открыть", command=on_open1).grid(row=0, column=0, padx=2)
tk.Button(buttons, text="Преобразовать", command=on_transform).grid(row=0, column=1, padx=2)
tk.Button(buttons, text="Преобразовать обратно", command=on_undo).grid(row=0, column=2, padx=2)
tk.Button(buttons, text="Функция", command=on_function).grid(row=0, column=3, padx=2)
tk.Label(buttons, text="Сдвиг по X:").grid(row=0, column=4, padx=(10, 2))
move_x_entry = tk.Entry(buttons, width=6)
move_x_entry.insert(0, "20")
move_x_entry.grid(row=0, column=5, padx=2)

tk.Label(buttons, text="Сдвиг по Y:").grid(row=0, column=6, padx=(10, 2))
move_y_entry = tk.Entry(buttons, width=6)
move_y_entry.insert(0, "20")
move_y_entry.grid(row=0, column=7, padx=2)

canvases = tk.Frame(root)
canvases.pack(side="top", fill="both", expand=True, padx=5, pady=5)


def add_panel(title, row, col, save_getter):
    tk.Label(canvases, text=title).grid(row=row, column=col)
    canvas = tk.Canvas(canvases, width=250, height=250, bg="gray")
    canvas.grid(row=row + 1, column=col, padx=5, pady=5)
    tk.Button(canvases, text="Сохранить", command=lambda: save_result_image(save_getter())).grid(
        row=row + 2, column=col, pady=(0, 5))
    return canvas


canvas1 = add_panel("Изображение 1", 0, 0, lambda: image)
canvas2 = add_panel("Сдвиг по X и Y", 0, 1, lambda: transform_result)
canvas3 = add_panel("Отражение сдвинутого изображения", 0, 2, lambda: mirror_result)
canvas5 = add_panel("Результат", 3, 0, lambda: undo_mirror_result)
canvas4 = add_panel("Результат", 3, 1, lambda: undo_transform_result)
canvas6 = add_panel("Результат", 3, 2, lambda: function_result)

root.mainloop()
