import math
import os
import random
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict, List, Tuple, Optional, Callable

from PIL import Image, ImageTk, ImageDraw

pkg_dir = os.path.dirname(os.path.abspath(__file__))
if pkg_dir not in sys.path:
    sys.path.insert(0, pkg_dir)

from algorithms import (
    COLOR_CDA,
    COLOR_BREZF,
    COLOR_BREZI,
    cda_line,
    bresenham_float_line,
    bresenham_int_line,
    calculate_triangle_bisectors,
)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Лабораторная работа №3 — Растеризация отрезков (Вариант 12)")
        self.geometry("920x640")
        self.minsize(760, 480)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Status.TLabel", font=("Helvetica", 9))

        self.var_ax = tk.DoubleVar(value=8.0)
        self.var_ay = tk.DoubleVar(value=52.0)
        self.var_bx = tk.DoubleVar(value=52.0)
        self.var_by = tk.DoubleVar(value=52.0)
        self.var_cx = tk.DoubleVar(value=26.0)
        self.var_cy = tk.DoubleVar(value=8.0)

        self.show_triangle_sides = tk.BooleanVar(value=True)
        self.show_triangle_bisectors = tk.BooleanVar(value=True)

        self.algo_cda_var = tk.BooleanVar(value=True)
        self.algo_brezf_var = tk.BooleanVar(value=True)
        self.algo_brezi_var = tk.BooleanVar(value=True)
        self.algo_native_var = tk.BooleanVar(value=True)

        self._build_layout()
        self._update_and_render()

    def _build_layout(self):
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        left_frame = ttk.Frame(main_paned, width=320)
        left_frame.pack_propagate(False)
        main_paned.add(left_frame, weight=0)

        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)

        self._build_sidebar(left_frame)

        self.canvas_view = RasterCanvasView(
            right_frame,
            width=600,
            height=600,
            raster_size=60,
            on_pixel_hover=self._on_pixel_hovered
        )
        self.canvas_view.pack(fill=tk.BOTH, expand=True)

        self._build_status_bar()

    def _build_sidebar(self, parent: ttk.Frame):
        tri_lf = ttk.LabelFrame(parent, text=" Параметры треугольника ", padding=8)
        tri_lf.pack(fill=tk.X, padx=4, pady=(0, 6))

        for lbl, var_x, var_y in [
            ("Вершина A:", self.var_ax, self.var_ay),
            ("Вершина B:", self.var_bx, self.var_by),
            ("Вершина C:", self.var_cx, self.var_cy),
        ]:
            row = ttk.Frame(tri_lf)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=lbl, width=11, font=("Helvetica", 9, "bold")).pack(side=tk.LEFT)
            ttk.Label(row, text="X:").pack(side=tk.LEFT, padx=(2, 2))
            e_x = ttk.Entry(row, textvariable=var_x, width=6)
            e_x.pack(side=tk.LEFT)
            e_x.bind("<KeyRelease>", lambda e: self._safe_update())
            ttk.Label(row, text="Y:").pack(side=tk.LEFT, padx=(6, 2))
            e_y = ttk.Entry(row, textvariable=var_y, width=6)
            e_y.pack(side=tk.LEFT)
            e_y.bind("<KeyRelease>", lambda e: self._safe_update())

        preset_frame1 = ttk.Frame(tri_lf)
        preset_frame1.pack(fill=tk.X, pady=(6, 2))
        ttk.Button(preset_frame1, text="Прямоугольный", command=self._set_right_triangle, width=14).pack(side=tk.LEFT,
                                                                                                         padx=1)
        ttk.Button(preset_frame1, text="Равносторонний", command=self._set_equilateral_triangle, width=14).pack(
            side=tk.LEFT, padx=1)

        preset_frame2 = ttk.Frame(tri_lf)
        preset_frame2.pack(fill=tk.X, pady=2)
        ttk.Button(preset_frame2, text="Тупоугольный", command=self._set_obtuse_triangle, width=14).pack(side=tk.LEFT,
                                                                                                         padx=1)
        ttk.Button(preset_frame2, text="Случайный", command=self._set_random_triangle, width=14).pack(side=tk.LEFT,
                                                                                                      padx=1)

        cb_frame = ttk.Frame(tri_lf)
        cb_frame.pack(fill=tk.X, pady=(6, 2))
        ttk.Checkbutton(
            cb_frame, text="Стороны", variable=self.show_triangle_sides, command=self._update_and_render
        ).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Checkbutton(
            cb_frame, text="Биссектрисы", variable=self.show_triangle_bisectors, command=self._update_and_render
        ).pack(side=tk.LEFT)

        algo_lf = ttk.LabelFrame(parent, text=" Алгоритмы растеризации ", padding=8)
        algo_lf.pack(fill=tk.X, padx=4, pady=6)

        algos = [
            ("ЦДА (DDA)", self.algo_cda_var, "#7F7FFF", "cda"),
            ("Брезенхем вещественный", self.algo_brezf_var, "#FF7F7F", "brezf"),
            ("Брезенхем целочисленный", self.algo_brezi_var, "#7FFF7F", "brezi"),
            ("Встроенный (Canvas.line)", self.algo_native_var, "#787878", "native"),
        ]

        for name, var, hex_col, key in algos:
            row = ttk.Frame(algo_lf)
            row.pack(fill=tk.X, pady=3)

            chip = tk.Canvas(row, width=16, height=16, bg=hex_col, highlightthickness=1, highlightbackground="#666666")
            chip.pack(side=tk.LEFT, padx=(0, 6))

            cb = ttk.Checkbutton(
                row,
                text=name,
                variable=var,
                command=lambda k=key, v=var: self.canvas_view.set_layer_visibility(k, v.get())
            )
            cb.pack(side=tk.LEFT)

        # file_lf = ttk.LabelFrame(parent)
        # file_lf.pack(fill=tk.X, padx=4)
        ttk.Button(parent, text="Сохранить рисунок", command=self._save_image_dialog).pack(fill=tk.X, pady=2)

    def _build_status_bar(self):
        status_frame = ttk.Frame(self, relief=tk.SUNKEN, padding=(6, 3))
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.lbl_status = ttk.Label(status_frame, text="Готово", style="Status.TLabel")
        self.lbl_status.pack(side=tk.LEFT)

        self.lbl_coords = ttk.Label(status_frame, text="Пиксель: (0, 0)", style="Status.TLabel")
        self.lbl_coords.pack(side=tk.RIGHT)

    def _set_right_triangle(self):
        self.var_ax.set(8.0)
        self.var_ay.set(52.0)
        self.var_bx.set(52.0)
        self.var_by.set(52.0)
        self.var_cx.set(8.0)
        self.var_cy.set(8.0)
        self._update_and_render()

    def _set_equilateral_triangle(self):
        cx, cy, r = 30.0, 32.0, 22.0
        self.var_cx.set(round(cx, 1))
        self.var_cy.set(round(cy - r, 1))
        self.var_ax.set(round(cx - r * math.sin(math.pi / 3), 1))
        self.var_ay.set(round(cy + r * math.cos(math.pi / 3), 1))
        self.var_bx.set(round(cx + r * math.sin(math.pi / 3), 1))
        self.var_by.set(round(cy + r * math.cos(math.pi / 3), 1))
        self._update_and_render()

    def _set_obtuse_triangle(self):
        self.var_ax.set(6.0)
        self.var_ay.set(52.0)
        self.var_bx.set(54.0)
        self.var_by.set(52.0)
        self.var_cx.set(16.0)
        self.var_cy.set(32.0)
        self._update_and_render()

    def _set_random_triangle(self):
        margin = 6
        max_v = self.canvas_view.raster_w - margin
        self.var_ax.set(random.randint(margin, max_v))
        self.var_ay.set(random.randint(margin, max_v))
        self.var_bx.set(random.randint(margin, max_v))
        self.var_by.set(random.randint(margin, max_v))
        self.var_cx.set(random.randint(margin, max_v))
        self.var_cy.set(random.randint(margin, max_v))
        self._update_and_render()

    def _on_pixel_hovered(self, x: int, y: int):
        self.lbl_coords.config(text=f"Пиксель: ({x}, {y})")

    def _safe_update(self):
        try:
            self._update_and_render()
        except (tk.TclError, ValueError):
            pass

    def _update_and_render(self):
        ax, ay = self.var_ax.get(), self.var_ay.get()
        bx, by = self.var_bx.get(), self.var_by.get()
        cx, cy = self.var_cx.get(), self.var_cy.get()

        tri = calculate_triangle_bisectors(ax, ay, bx, by, cx, cy)

        segments: List[Tuple[Tuple[float, float], Tuple[float, float], str]] = []
        if self.show_triangle_sides.get():
            segments.extend(tri["sides"])
        if self.show_triangle_bisectors.get():
            segments.extend(tri["bisectors"])

        cda_pixels: List[Tuple[int, int]] = []
        brezf_pixels: List[Tuple[int, int]] = []
        brezi_pixels: List[Tuple[int, int]] = []

        for (p1, p2, _) in segments:
            cda_pixels.extend(cda_line(p1[0], p1[1], p2[0], p2[1]))
            brezf_pixels.extend(bresenham_float_line(p1[0], p1[1], p2[0], p2[1]))
            brezi_pixels.extend(bresenham_int_line(p1[0], p1[1], p2[0], p2[1]))

        self.canvas_view.set_layer_pixels("cda", cda_pixels, COLOR_CDA)
        self.canvas_view.set_layer_pixels("brezf", brezf_pixels, COLOR_BREZF)
        self.canvas_view.set_layer_pixels("brezi", brezi_pixels, COLOR_BREZI)
        self.canvas_view.set_native_segments(segments)

        self.lbl_status.config(
            text=f"Разрешение: {self.canvas_view.raster_w}x{self.canvas_view.raster_h} | Отрезков: {len(segments)} | Пикселей: {len(brezi_pixels)}"
        )

    def _save_image_dialog(self):
        filename = filedialog.asksaveasfilename(
            title="Сохранить рисунок",
            defaultextension=".png",
            filetypes=[
                ("PNG Image", "*.png"),
                ("BMP Image", "*.bmp"),
                ("JPEG Image", "*.jpg"),
                ("All Files", "*.*"),
            ]
        )
        if filename:
            try:
                img = self.canvas_view.render_to_image()
                scaled_img = img.resize((img.width * 10, img.height * 10), Image.NEAREST)
                if filename.lower().endswith(".jpg") or filename.lower().endswith(".jpeg"):
                    rgb_img = Image.new("RGB", scaled_img.size, (255, 255, 255))
                    rgb_img.paste(scaled_img, mask=scaled_img.split()[3])
                    rgb_img.save(filename)
                else:
                    scaled_img.save(filename)
                messagebox.showinfo("Успех", f"Изображение успешно сохранено в:\n{filename}")
            except Exception as e:
                messagebox.showerror("Ошибка сохранения", f"Не удалось сохранить файл:\n{str(e)}")


COLOR_CDA = (127, 127, 255)
COLOR_BREZF = (255, 127, 127)
COLOR_BREZI = (127, 255, 127)
COLOR_NATIVE = (120, 120, 120)


class RasterCanvasView(tk.Frame):
    def __init__(
            self,
            master: tk.Widget,
            width: int = 600,
            height: int = 600,
            raster_size: int = 60,
            on_pixel_hover: Optional[Callable[[int, int], None]] = None,
            **kwargs
    ):
        super().__init__(master, **kwargs)
        self.canvas_width = width
        self.canvas_height = height
        self.on_pixel_hover = on_pixel_hover

        self.raster_w = raster_size
        self.raster_h = raster_size
        self.pixel_size = 10.0

        self.layers: Dict[str, Dict[Tuple[int, int], Tuple[int, int, int]]] = {
            "cda": {},
            "brezf": {},
            "brezi": {},
        }
        self.layer_visible: Dict[str, bool] = {
            "cda": True,
            "brezf": True,
            "brezi": True,
            "native": True,
        }

        self.native_segments: List[Tuple[Tuple[float, float], Tuple[float, float], str]] = []
        self.tk_img: Optional[ImageTk.PhotoImage] = None

        self._build_ui()
        self._bind_events()

    def _build_ui(self):
        self.canvas = tk.Canvas(
            self,
            width=self.canvas_width,
            height=self.canvas_height,
            bg="#f0f0f0",
            highlightthickness=1,
            highlightbackground="#cccccc"
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

    def _bind_events(self):
        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<Motion>", self._on_motion)

    def set_layer_pixels(self, layer_name: str, pixels: List[Tuple[int, int]], color: Tuple[int, int, int]):
        if layer_name in self.layers:
            self.layers[layer_name] = {pt: color for pt in pixels}
        self.redraw()

    def set_layer_visibility(self, layer_name: str, visible: bool):
        self.layer_visible[layer_name] = visible
        self.redraw()

    def set_native_segments(self, segments: List[Tuple[Tuple[float, float], Tuple[float, float], str]]):
        self.native_segments = list(segments)
        self.redraw()

    def _recalc_pixel_size(self):
        c_w = self.canvas.winfo_width() or self.canvas_width
        c_h = self.canvas.winfo_height() or self.canvas_height
        size = min(c_w / self.raster_w, c_h / self.raster_h)
        self.pixel_size = max(4.0, size)

    def _raster_to_screen(self, rx: float, ry: float) -> Tuple[float, float]:
        return rx * self.pixel_size, ry * self.pixel_size

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

        if self.layer_visible.get("native", False) and self.native_segments:
            for (p1, p2, _) in self.native_segments:
                draw.line([(p1[0], p1[1]), (p2[0], p2[1])], fill=COLOR_NATIVE + (255,), width=1)

        for layer_key in ["cda", "brezf", "brezi"]:
            if self.layer_visible.get(layer_key, False):
                pixels = self.layers.get(layer_key, {})
                for (px, py), col in pixels.items():
                    if 0 <= px < self.raster_w and 0 <= py < self.raster_h:
                        img.putpixel((px, py), col + (255,))

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

        self.canvas.create_rectangle(0, 0, disp_w, disp_h, outline="#888888", width=1, tags="border")


if __name__ == "__main__":
    app = App()
    app.mainloop()
