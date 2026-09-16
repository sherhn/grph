import math
import os
import random
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict, List, Tuple, Optional, Callable, Any

from PIL import Image, ImageTk, ImageDraw

pkg_dir = os.path.dirname(os.path.abspath(__file__))
if pkg_dir not in sys.path:
    sys.path.insert(0, pkg_dir)

from algorithms import (
    COLOR_EQUATION,
    COLOR_PARAMETRIC,
    COLOR_BRESENHAM,
    COLOR_NATIVE,
    COLOR_TRIANGLE,
    COLOR_EXTENSIONS,
    cda_line,
    bresenham_int_line,
    circle_equation,
    circle_parametric,
    circle_bresenham,
    circle_native_raster,
    calculate_triangle_excircles,
    load_triangle_from_svg,
    triangle_sides_from_vertices,
)


class RasterCanvasView(tk.Frame):
    """
    Виджет растрового холста с поддержкой отображения попиксельной сетки,
    нескольких алгоритмических слоёв, геометрических отрезков и интерактивного масштабирования.
    """
    def __init__(
        self,
        master: tk.Widget,
        width: int = 620,
        height: int = 620,
        raster_size: int = 80,
        on_pixel_hover: Optional[Callable[[int, int], None]] = None,
        **kwargs
    ):
        super().__init__(master, **kwargs)
        self.canvas_width = width
        self.canvas_height = height
        self.on_pixel_hover = on_pixel_hover

        self.raster_w = raster_size
        self.raster_h = raster_size
        self.pixel_size = 7.0
        self.show_grid = True

        # Слои пикселей для каждого алгоритма: Dict[Tuple[int, int], Tuple[int, int, int]]
        self.layers: Dict[str, Dict[Tuple[int, int], Tuple[int, int, int]]] = {
            "equation": {},
            "parametric": {},
            "bresenham": {},
            "native": {},
        }
        self.layer_visible: Dict[str, bool] = {
            "equation": True,
            "parametric": True,
            "bresenham": True,
            "native": False,
        }

        self.sides: List[Dict[str, Any]] = []
        self.extensions: List[Dict[str, Any]] = []
        self.markers: List[Tuple[Tuple[float, float], str, Tuple[int, int, int]]] = []
        self.labels: List[Tuple[Tuple[float, float], str, str]] = []
        self.tk_img: Optional[ImageTk.PhotoImage] = None

        self._build_ui()
        self._bind_events()

    def _build_ui(self):
        self.canvas = tk.Canvas(
            self,
            width=self.canvas_width,
            height=self.canvas_height,
            bg="#fbfbfb",
            highlightthickness=1,
            highlightbackground="#d0d0d0"
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

    def _bind_events(self):
        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<Motion>", self._on_motion)

    def set_raster_size(self, size: int):
        self.raster_w = size
        self.raster_h = size
        self._recalc_pixel_size()
        self.redraw()

    def set_layer_pixels(self, layer_name: str, pixels: List[Tuple[int, int]], color: Tuple[int, int, int]):
        if layer_name in self.layers:
            self.layers[layer_name] = {pt: color for pt in pixels}

    def set_layer_visibility(self, layer_name: str, visible: bool):
        self.layer_visible[layer_name] = visible
        self.redraw()

    def set_geometry(
        self,
        sides: List[Dict[str, Any]],
        extensions: List[Dict[str, Any]],
        markers: List[Tuple[Tuple[float, float], str, Tuple[int, int, int]]],
        labels: List[Tuple[Tuple[float, float], str, str]]
    ):
        self.sides = list(sides)
        self.extensions = list(extensions)
        self.markers = list(markers)
        self.labels = list(labels)
        self.redraw()

    def _recalc_pixel_size(self):
        c_w = self.canvas.winfo_width() or self.canvas_width
        c_h = self.canvas.winfo_height() or self.canvas_height
        size = min(c_w / self.raster_w, c_h / self.raster_h)
        self.pixel_size = max(3.0, size)

    def _screen_to_raster(self, sx: float, sy: float) -> Tuple[float, float]:
        return sx / self.pixel_size, sy / self.pixel_size

    def _on_motion(self, event):
        rx, ry = self._screen_to_raster(event.x, event.y)
        if self.on_pixel_hover:
            self.on_pixel_hover(int(math.floor(rx)), int(math.floor(ry)))

    def _on_resize(self, event):
        if event.width > 50 and event.height > 50:
            self._recalc_pixel_size()
            self.redraw()

    def render_to_image(self) -> Image.Image:
        img = Image.new("RGBA", (self.raster_w, self.raster_h), (255, 255, 255, 255))
        draw = ImageDraw.Draw(img)

        # 1. Внешние продолжения сторон к точкам касания (пунктирный эффект)
        for ext in self.extensions:
            p1, p2 = ext["p1"], ext["p2"]
            pts = cda_line(p1[0], p1[1], p2[0], p2[1])
            for px, py in pts:
                if 0 <= px < self.raster_w and 0 <= py < self.raster_h:
                    if (px + py) % 2 == 0:
                        img.putpixel((px, py), COLOR_EXTENSIONS + (255,))

        # 2. Стороны треугольника (строго отрезки между вершинами A-B, B-C, C-A)
        for side in self.sides:
            p1, p2 = side["p1"], side["p2"]
            pts = bresenham_int_line(p1[0], p1[1], p2[0], p2[1])
            for px, py in pts:
                if 0 <= px < self.raster_w and 0 <= py < self.raster_h:
                    img.putpixel((px, py), COLOR_TRIANGLE + (255,))

        # 3. Слои алгоритмов окружностей
        order = ["native", "equation", "parametric", "bresenham"]
        for layer_key in order:
            if self.layer_visible.get(layer_key, False):
                pixels = self.layers.get(layer_key, {})
                for (px, py), col in pixels.items():
                    if 0 <= px < self.raster_w and 0 <= py < self.raster_h:
                        img.putpixel((px, py), col + (255,))

        # 4. Маркеры центров (крестик 5 пикселей)
        for (mx, my), m_name, m_color in self.markers:
            imx, imy = int(round(mx)), int(round(my))
            offsets = [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]
            for dx, dy in offsets:
                px, py = imx + dx, imy + dy
                if 0 <= px < self.raster_w and 0 <= py < self.raster_h:
                    img.putpixel((px, py), m_color + (255,))

        return img

    def redraw(self):
        self.canvas.delete("all")
        self._recalc_pixel_size()

        base_img = self.render_to_image()
        disp_w = int(round(self.raster_w * self.pixel_size))
        disp_h = int(round(self.raster_h * self.pixel_size))

        display_img = base_img.resize((disp_w, disp_h), Image.NEAREST)
        self.tk_img = ImageTk.PhotoImage(display_img)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img, tags="raster")

        # Опциональная координатная сетка пикселей
        if self.show_grid and self.pixel_size >= 5.0:
            for x in range(self.raster_w + 1):
                sx = x * self.pixel_size
                self.canvas.create_line(sx, 0, sx, disp_h, fill="#ececec", width=1, tags="grid")
            for y in range(self.raster_h + 1):
                sy = y * self.pixel_size
                self.canvas.create_line(0, sy, disp_w, sy, fill="#ececec", width=1, tags="grid")

        # Текстовые метки вершин A, B, C и центров Ia, Ib, Ic
        for (lx, ly), label_str, color_hex in self.labels:
            sx = int(round(lx * self.pixel_size + self.pixel_size / 2))
            sy = int(round(ly * self.pixel_size + self.pixel_size / 2))
            self.canvas.create_text(
                sx + 10, sy - 8,
                text=label_str,
                fill=color_hex,
                font=("Helvetica", 10, "bold"),
                tags="label"
            )

        # Внешняя граница холста
        self.canvas.create_rectangle(0, 0, disp_w, disp_h, outline="#999999", width=1, tags="border")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Лабораторная работа № 4 — Растеризация окружностей (Вариант 12)")
        self.geometry("1060x720")
        self.minsize(860, 560)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Status.TLabel", font=("Helvetica", 9))
        style.configure("Header.TLabel", font=("Helvetica", 10, "bold"))
        style.configure("Info.TLabel", font=("Helvetica", 9))

        # Параметры треугольника (стороны a, b, c)
        self.var_side_a = tk.DoubleVar(value=28.28)
        self.var_side_b = tk.DoubleVar(value=20.0)
        self.var_side_c = tk.DoubleVar(value=20.0)

        # Геометрические элементы
        self.show_sides_var = tk.BooleanVar(value=True)
        self.show_extensions_var = tk.BooleanVar(value=True)
        self.show_centers_var = tk.BooleanVar(value=True)

        # Алгоритмы окружностей
        self.algo_eq_var = tk.BooleanVar(value=True)
        self.algo_param_var = tk.BooleanVar(value=True)
        self.algo_brez_var = tk.BooleanVar(value=True)
        self.algo_native_var = tk.BooleanVar(value=False)

        # Настройки растра (всегда 80)
        self.raster_size = 80
        self.show_grid_var = tk.BooleanVar(value=True)

        self._build_layout()
        self._update_and_render()

    def _build_layout(self):
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        left_container = ttk.Frame(main_paned, width=380)
        left_container.pack_propagate(False)
        main_paned.add(left_container, weight=0)

        right_container = ttk.Frame(main_paned)
        main_paned.add(right_container, weight=1)

        self._build_sidebar(left_container)

        # Правая панель: CanvasView
        self.canvas_view = RasterCanvasView(
            right_container,
            width=640,
            height=640,
            raster_size=self.raster_size,
            on_pixel_hover=self._on_pixel_hovered
        )
        self.canvas_view.pack(fill=tk.BOTH, expand=True)

        self._build_status_bar()

    def _build_sidebar(self, parent: ttk.Frame):
        canvas_scroll = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas_scroll.yview)
        scrollable_frame = ttk.Frame(canvas_scroll)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas_scroll.configure(scrollregion=canvas_scroll.bbox("all"))
        )
        canvas_scroll.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas_scroll.configure(xscrollcommand=None, yscrollcommand=scrollbar.set)

        canvas_scroll.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 1. Панель параметров треугольника
        self.tri_frame = ttk.LabelFrame(scrollable_frame, text=" Параметры треугольника (стороны) ", padding=6)
        self.tri_frame.pack(fill=tk.X, padx=4, pady=(2, 4))

        for lbl, var in [
            ("Сторона a (напротив A):", self.var_side_a),
            ("Сторона b (напротив B):", self.var_side_b),
            ("Сторона c (напротив C):", self.var_side_c),
        ]:
            row = ttk.Frame(self.tri_frame)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=lbl, width=22).pack(side=tk.LEFT)
            entry = ttk.Entry(row, textvariable=var, width=8)
            entry.pack(side=tk.RIGHT)
            entry.bind("<KeyRelease>", lambda e: self._safe_update())

        preset_lbl = ttk.Label(self.tri_frame, text="Готовые пресеты треугольников:", font=("Helvetica", 8, "italic"))
        preset_lbl.pack(anchor=tk.W, pady=(5, 2))

        p_row1 = ttk.Frame(self.tri_frame)
        p_row1.pack(fill=tk.X, pady=1)
        ttk.Button(p_row1, text="Прямоугольный", width=17, command=lambda: self._set_sides(28.28, 20.0, 20.0)).pack(side=tk.LEFT, padx=1)
        ttk.Button(p_row1, text="Равносторонний", width=17, command=lambda: self._set_sides(20, 20, 20)).pack(side=tk.LEFT, padx=1)

        p_row2 = ttk.Frame(self.tri_frame)
        p_row2.pack(fill=tk.X, pady=1)
        ttk.Button(p_row2, text="Равнобедренный", width=17, command=lambda: self._set_sides(20.0, 20.0, 24.0)).pack(side=tk.LEFT, padx=1)
        ttk.Button(p_row2, text="Остроугольный", width=17, command=lambda: self._set_sides(13, 14, 15)).pack(side=tk.LEFT, padx=1)

        p_row3 = ttk.Frame(self.tri_frame)
        p_row3.pack(fill=tk.X, pady=1)
        ttk.Button(p_row3, text="Тупоугольный", width=17, command=lambda: self._set_sides(10, 12, 19)).pack(side=tk.LEFT, padx=1)
        ttk.Button(p_row3, text="Случайный", width=17, command=self._set_random_triangle).pack(side=tk.LEFT, padx=1)

        ttk.Button(self.tri_frame, text="📂 Импорт отрезков из SVG...", command=self._import_svg_dialog).pack(fill=tk.X, pady=(5, 2))

        geo_cb_frame = ttk.Frame(self.tri_frame)
        geo_cb_frame.pack(fill=tk.X, pady=(6, 2))
        ttk.Checkbutton(geo_cb_frame, text="Стороны", variable=self.show_sides_var, command=self._update_and_render).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Checkbutton(geo_cb_frame, text="Касательные", variable=self.show_extensions_var, command=self._update_and_render).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Checkbutton(geo_cb_frame, text="Центры", variable=self.show_centers_var, command=self._update_and_render).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Checkbutton(geo_cb_frame, text="Сетка", variable=self.show_grid_var, command=self._on_grid_toggle).pack(side=tk.LEFT)

        # 2. Выбор алгоритмов растеризации окружности
        algo_frame = ttk.LabelFrame(scrollable_frame, text=" Алгоритмы растеризации окружностей ", padding=6)
        algo_frame.pack(fill=tk.X, padx=4, pady=4)

        algos_info = [
            ("По уравнению (x²+y²=R²)", self.algo_eq_var, "#4175F0", "equation"),
            ("Параметрическое (1/R)", self.algo_param_var, "#F56C23", "parametric"),
            ("Брезенхем (целочисленный)", self.algo_brez_var, "#2EAF50", "bresenham"),
            ("Встроенный (Pillow/Canvas)", self.algo_native_var, "#8E44AD", "native"),
        ]

        for name, var, hex_col, key in algos_info:
            row = ttk.Frame(algo_frame)
            row.pack(fill=tk.X, pady=2)

            chip = tk.Canvas(row, width=14, height=14, bg=hex_col, highlightthickness=1, highlightbackground="#555")
            chip.pack(side=tk.LEFT, padx=(0, 5))

            cb = ttk.Checkbutton(
                row,
                text=name,
                variable=var,
                command=lambda k=key, v=var: self._on_algo_toggle(k, v.get())
            )
            cb.pack(side=tk.LEFT)

        # 3. Сохранение рисунка
        btn_frame = ttk.Frame(scrollable_frame)
        btn_frame.pack(fill=tk.X, padx=4, pady=(8, 4))

        ttk.Button(btn_frame, text="💾 Сохранить рисунок в PBM...", command=self._save_image_dialog).pack(fill=tk.X, pady=2)

    def _build_status_bar(self):
        status_frame = ttk.Frame(self, relief=tk.SUNKEN, padding=(6, 3))
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.lbl_status = ttk.Label(status_frame, text="Готово", style="Status.TLabel")
        self.lbl_status.pack(side=tk.LEFT)

        self.lbl_coords = ttk.Label(status_frame, text="Пиксель: (0, 0)", style="Status.TLabel")
        self.lbl_coords.pack(side=tk.RIGHT)


    def _on_algo_toggle(self, key: str, visible: bool):
        self.canvas_view.set_layer_visibility(key, visible)

    def _on_grid_toggle(self):
        self.canvas_view.show_grid = self.show_grid_var.get()
        self.canvas_view.redraw()

    def _on_pixel_hovered(self, x: int, y: int):
        self.lbl_coords.config(text=f"Пиксель: ({x}, {y})")

    def _set_sides(self, a: float, b: float, c: float):
        self.var_side_a.set(a)
        self.var_side_b.set(b)
        self.var_side_c.set(c)
        self._update_and_render()

    def _set_random_triangle(self):
        a = random.randint(12, 30)
        b = random.randint(12, 30)
        min_c = abs(a - b) + 2
        max_c = a + b - 2
        if min_c <= max_c:
            c = random.randint(min_c, max_c)
            self._set_sides(float(a), float(b), float(c))

    def _safe_update(self):
        try:
            self._update_and_render()
        except (tk.TclError, ValueError):
            pass

    def _update_and_render(self):
        rs = self.canvas_view.raster_w

        a = self.var_side_a.get()
        b = self.var_side_b.get()
        c = self.var_side_c.get()

        geom = calculate_triangle_excircles(a, b, c, raster_size=rs, margin=4)
        if not geom["valid"]:
            self.lbl_status.config(text=f"Ошибка: {geom['error']}")
            return

        circles = geom["circles"]
        sides_to_draw = geom["sides"] if self.show_sides_var.get() else []
        extensions_to_draw = geom["extensions"] if self.show_extensions_var.get() else []

        markers_to_draw = []
        labels_to_draw = []

        # Подписи вершин треугольника A, B, C (без жирных синих точек)
        v_pts = geom["raster_vertices"]
        for v_name, v_coord in v_pts.items():
            labels_to_draw.append((v_coord, v_name, "#1020A0"))

        # Метки центров вневписанных окружностей Ia, Ib, Ic (красные крестики)
        if self.show_centers_var.get():
            for c_info in circles:
                m_label = f"I{c_info['id'].lower()}"
                markers_to_draw.append((c_info["center"], m_label, (210, 20, 20)))
                labels_to_draw.append((c_info["center"], m_label, "#D21414"))

        self.canvas_view.set_geometry(sides_to_draw, extensions_to_draw, markers_to_draw, labels_to_draw)

        # Вычисление пикселей окружностей по каждому алгоритму
        eq_pixels: List[Tuple[int, int]] = []
        param_pixels: List[Tuple[int, int]] = []
        brez_pixels: List[Tuple[int, int]] = []
        native_pixels: List[Tuple[int, int]] = []

        for c_info in circles:
            cx, cy = c_info["center"]
            cr = c_info["radius"]
            eq_pixels.extend(circle_equation(cx, cy, cr))
            param_pixels.extend(circle_parametric(cx, cy, cr))
            brez_pixels.extend(circle_bresenham(cx, cy, cr))
            native_pixels.extend(circle_native_raster(cx, cy, cr))

        self.canvas_view.set_layer_pixels("equation", eq_pixels, COLOR_EQUATION)
        self.canvas_view.set_layer_pixels("parametric", param_pixels, COLOR_PARAMETRIC)
        self.canvas_view.set_layer_pixels("bresenham", brez_pixels, COLOR_BRESENHAM)
        self.canvas_view.set_layer_pixels("native", native_pixels, COLOR_NATIVE)

        set_brez = set(brez_pixels)
        set_param = set(param_pixels)
        set_eq = set(eq_pixels)

        self.lbl_status.config(
            text=f"Сетка: {rs}x{rs} | Брезенхем: {len(set_brez)} px | Параметрич.: {len(set_param)} px | Уравнение: {len(set_eq)} px"
        )

        self.canvas_view.redraw()

    def _save_image_dialog(self):
        filename = filedialog.asksaveasfilename(
            title="Сохранить рисунок в файл PBM",
            defaultextension=".pbm",
            filetypes=[("PBM Image (*.pbm)", "*.pbm")]
        )
        if filename:
            try:
                if not filename.lower().endswith(".pbm"):
                    filename += ".pbm"
                img = self.canvas_view.render_to_image()
                scale_factor = 10
                scaled_img = img.resize(
                    (img.width * scale_factor, img.height * scale_factor),
                    Image.NEAREST
                )
                scaled_img.convert("RGB").save(filename, format="PPM")
                messagebox.showinfo("Успех", f"Изображение успешно сохранено в формате PBM:\n{filename}")
            except Exception as e:
                messagebox.showerror("Ошибка сохранения", f"Не удалось сохранить файл:\n{str(e)}")

    def _import_svg_dialog(self):
        filename = filedialog.askopenfilename(
            title="Выберите SVG файл с отрезками",
            filetypes=[("SVG файлы (*.svg)", "*.svg"), ("Все файлы (*.*)", "*.*")]
        )
        if filename:
            pts = load_triangle_from_svg(filename, target_size=self.canvas_view.raster_w)
            if pts and len(pts) >= 3:
                a, b, c = triangle_sides_from_vertices(pts)
                self.var_side_a.set(a)
                self.var_side_b.set(b)
                self.var_side_c.set(c)
                self._update_and_render()
                messagebox.showinfo(
                    "Успех импорта SVG",
                    f"Из SVG файла успешно считаны отрезки треугольника:\n"
                    f"Вершины: A{pts[0]}, B{pts[1]}, C{pts[2]}\n"
                    f"Вычисленные стороны:\n"
                    f"  a = {a:.1f}\n"
                    f"  b = {b:.1f}\n"
                    f"  c = {c:.1f}"
                )
            else:
                messagebox.showwarning(
                    "Ошибка импорта",
                    "В файле не найден треугольник (<polygon>, <polyline>, <path> или 3 отрезка <line>)."
                )


if __name__ == "__main__":
    app = App()
    app.mainloop()
