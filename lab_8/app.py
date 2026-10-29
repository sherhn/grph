"""Графический интерфейс для аффинных преобразований и интерполяции изображений."""

import math
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional, Dict, Tuple
import numpy as np
from PIL import Image, ImageTk, ImageDraw

import algorithms
from algorithms import TransformParams


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Лабораторная работа №8 — Аффинные преобразования и интерполяция изображений")

        # Адаптивный просторный размер окна под разрешение экрана
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        win_w = min(1480, max(1200, int(screen_w * 0.75)))
        win_h = min(940, max(780, int(screen_h * 0.80)))
        pos_x = max(0, (screen_w - win_w) // 2)
        pos_y = max(0, (screen_h - win_h) // 2)
        self.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
        self.minsize(1050, 680)

        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self.style.configure("Status.TLabel", font=("Helvetica", 9))
        self.style.configure("Header.TLabel", font=("Helvetica", 10, "bold"))
        self.style.configure("SubHeader.TLabel", font=("Helvetica", 9, "bold"))

        self.source_image: Optional[Image.Image] = None
        self.transformed_images: Dict[str, Image.Image] = {}
        self.transformed_timings: Dict[str, float] = {}

        self.var_scale_x = tk.DoubleVar(value=1.0)
        self.var_scale_y = tk.DoubleVar(value=1.0)
        self.var_lock_aspect = tk.BooleanVar(value=True)
        self.var_angle = tk.DoubleVar(value=0.0)
        self.var_shear_x = tk.DoubleVar(value=0.0)
        self.var_shear_y = tk.DoubleVar(value=0.0)
        self.var_fit_bbox = tk.BooleanVar(value=True)
        self.var_bg_color = tk.StringVar(value="Белый")
        self.var_save_target = tk.StringVar(value="bicubic")

        self._update_job: Optional[str] = None
        self._is_updating = False

        self._build_layout()
        self._load_default_pattern()

    def _build_layout(self):
        main_container = ttk.Frame(self)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left_frame = ttk.Frame(main_container, width=380)
        left_frame.pack_propagate(False)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        right_frame = ttk.Frame(main_container)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_sidebar(left_frame)
        self._build_overview(right_frame)
        self._build_status_bar()

    def _build_sidebar(self, parent: ttk.Frame):
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)

        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")
            elif event.delta:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<Button-4>", _on_mousewheel)
        canvas.bind("<Button-5>", _on_mousewheel)
        canvas.bind("<MouseWheel>", _on_mousewheel)

        # Изображение
        img_lf = ttk.LabelFrame(scrollable_frame, text=" Изображение ", padding=8)
        img_lf.pack(fill=tk.X, padx=2, pady=(0, 8))

        row_btn = ttk.Frame(img_lf)
        row_btn.pack(fill=tk.X, pady=2)
        ttk.Button(row_btn, text="📂 Открыть файл...", command=self._on_open_file).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
        ttk.Button(row_btn, text="🎨 Тест", command=self._load_default_pattern).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(3, 0))

        self.lbl_img_info = ttk.Label(img_lf, text="Размер: 0 x 0 px", font=("Helvetica", 9))
        self.lbl_img_info.pack(fill=tk.X, pady=(4, 0))

        # Параметры преобразования
        tf_lf = ttk.LabelFrame(scrollable_frame, text=" Параметры преобразования ", padding=8)
        tf_lf.pack(fill=tk.X, padx=2, pady=(0, 8))

        # Масштаб X
        row_sx = ttk.Frame(tf_lf)
        row_sx.pack(fill=tk.X, pady=2)
        ttk.Label(row_sx, text="Масштаб Sx:", width=13).pack(side=tk.LEFT)
        self.lbl_val_sx = ttk.Label(row_sx, text="1.00", width=5)
        self.lbl_val_sx.pack(side=tk.RIGHT)
        scale_sx_slider = ttk.Scale(
            row_sx, from_=0.1, to=3.5, variable=self.var_scale_x,
            command=self._on_scale_x_change
        )
        scale_sx_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        # Масштаб Y
        row_sy = ttk.Frame(tf_lf)
        row_sy.pack(fill=tk.X, pady=2)
        ttk.Label(row_sy, text="Масштаб Sy:", width=13).pack(side=tk.LEFT)
        self.lbl_val_sy = ttk.Label(row_sy, text="1.00", width=5)
        self.lbl_val_sy.pack(side=tk.RIGHT)
        scale_sy_slider = ttk.Scale(
            row_sy, from_=0.1, to=3.5, variable=self.var_scale_y,
            command=self._on_scale_y_change
        )
        scale_sy_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        cb_aspect = ttk.Checkbutton(
            tf_lf, text="Сохранять пропорции (Sx = Sy)",
            variable=self.var_lock_aspect,
            command=self._on_toggle_aspect
        )
        cb_aspect.pack(anchor=tk.W, pady=2)

        # Угол поворота
        row_rot = ttk.Frame(tf_lf)
        row_rot.pack(fill=tk.X, pady=2)
        ttk.Label(row_rot, text="Поворот θ (°):", width=13).pack(side=tk.LEFT)
        self.lbl_val_rot = ttk.Label(row_rot, text="0.0°", width=5)
        self.lbl_val_rot.pack(side=tk.RIGHT)
        rot_slider = ttk.Scale(
            row_rot, from_=-180.0, to=180.0, variable=self.var_angle,
            command=self._on_angle_change
        )
        rot_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        # Скос X
        row_kx = ttk.Frame(tf_lf)
        row_kx.pack(fill=tk.X, pady=2)
        ttk.Label(row_kx, text="Скос Kx:", width=13).pack(side=tk.LEFT)
        self.lbl_val_kx = ttk.Label(row_kx, text="0.00", width=5)
        self.lbl_val_kx.pack(side=tk.RIGHT)
        kx_slider = ttk.Scale(
            row_kx, from_=-1.5, to=1.5, variable=self.var_shear_x,
            command=self._on_shear_x_change
        )
        kx_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        # Скос Y
        row_ky = ttk.Frame(tf_lf)
        row_ky.pack(fill=tk.X, pady=2)
        ttk.Label(row_ky, text="Скос Ky:", width=13).pack(side=tk.LEFT)
        self.lbl_val_ky = ttk.Label(row_ky, text="0.00", width=5)
        self.lbl_val_ky.pack(side=tk.RIGHT)
        ky_slider = ttk.Scale(
            row_ky, from_=-1.5, to=1.5, variable=self.var_shear_y,
            command=self._on_shear_y_change
        )
        ky_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        cb_bbox = ttk.Checkbutton(
            tf_lf, text="Подгонять размер холста под результат",
            variable=self.var_fit_bbox,
            command=self._schedule_update
        )
        cb_bbox.pack(anchor=tk.W, pady=2)

        row_bg = ttk.Frame(tf_lf)
        row_bg.pack(fill=tk.X, pady=3)
        ttk.Label(row_bg, text="Цвет фона:", width=13).pack(side=tk.LEFT)
        cb_bg = ttk.Combobox(
            row_bg, textvariable=self.var_bg_color,
            values=["Белый", "Черный", "Серый"],
            width=11, state="readonly"
        )
        cb_bg.pack(side=tk.LEFT)
        cb_bg.bind("<<ComboboxSelected>>", lambda e: self._schedule_update())

        # Пресеты
        preset_lf = ttk.LabelFrame(scrollable_frame, text=" Пресеты ", padding=8)
        preset_lf.pack(fill=tk.X, padx=2, pady=(0, 8))

        p_r1 = ttk.Frame(preset_lf)
        p_r1.pack(fill=tk.X, pady=2)
        ttk.Button(p_r1, text="Сброс 1:1", command=self._preset_reset).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
        ttk.Button(p_r1, text="Масштаб 2x", command=lambda: self._preset_scale(2.0)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
        ttk.Button(p_r1, text="Масштаб 0.5x", command=lambda: self._preset_scale(0.5)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)

        p_r2 = ttk.Frame(preset_lf)
        p_r2.pack(fill=tk.X, pady=2)
        ttk.Button(p_r2, text="Поворот 30°", command=lambda: self._preset_rotate(30.0)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
        ttk.Button(p_r2, text="Поворот 45°", command=lambda: self._preset_rotate(45.0)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
        ttk.Button(p_r2, text="Скос Kx=0.4", command=lambda: self._preset_shear(0.4, 0.0)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)

        p_r3 = ttk.Frame(preset_lf)
        p_r3.pack(fill=tk.X, pady=2)
        ttk.Button(p_r3, text="Поворот 25° + Скос 0.3 + Масштаб 1.2", command=self._preset_combo).pack(fill=tk.X, expand=True, padx=1)

        # Сохранение
        save_lf = ttk.LabelFrame(scrollable_frame, text=" Сохранение ", padding=8)
        save_lf.pack(fill=tk.X, padx=2, pady=(0, 4))

        ttk.Label(save_lf, text="Что сохранить:").pack(anchor=tk.W, pady=(0, 2))
        ttk.Radiobutton(save_lf, text="Бикубическая интерполяция", variable=self.var_save_target, value="bicubic").pack(anchor=tk.W, pady=1)
        ttk.Radiobutton(save_lf, text="Билинейная интерполяция", variable=self.var_save_target, value="bilinear").pack(anchor=tk.W, pady=1)
        ttk.Radiobutton(save_lf, text="Ближайший сосед", variable=self.var_save_target, value="nearest").pack(anchor=tk.W, pady=1)
        ttk.Radiobutton(save_lf, text="Коллаж 2x2 (Исходное + 3 метода)", variable=self.var_save_target, value="collage").pack(anchor=tk.W, pady=1)

        ttk.Button(save_lf, text="💾 Сохранить изображение...", command=self._on_save_file).pack(fill=tk.X, pady=(6, 2))

    def _build_overview(self, parent: ttk.Frame):
        self.frame_overview = ttk.Frame(parent)
        self.frame_overview.pack(fill=tk.BOTH, expand=True)

        self.frame_overview.rowconfigure(0, weight=1, uniform="rows")
        self.frame_overview.rowconfigure(1, weight=1, uniform="rows")
        self.frame_overview.columnconfigure(0, weight=1, uniform="cols")
        self.frame_overview.columnconfigure(1, weight=1, uniform="cols")

        # Оригинал
        f_orig = ttk.LabelFrame(self.frame_overview, text=" Исходное изображение ", padding=6)
        f_orig.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self.can_orig = tk.Canvas(f_orig, bg="#ffffff", highlightthickness=0)
        self.can_orig.pack(fill=tk.BOTH, expand=True)
        self.can_orig.bind("<Motion>", lambda e: self._on_canvas_hover(e, "orig"))

        # Ближайший сосед
        f_near = ttk.LabelFrame(self.frame_overview, text=" Ближайший сосед (Nearest Neighbor) ", padding=6)
        f_near.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        self.can_near = tk.Canvas(f_near, bg="#ffffff", highlightthickness=0)
        self.can_near.pack(fill=tk.BOTH, expand=True)
        self.can_near.bind("<Motion>", lambda e: self._on_canvas_hover(e, "near"))

        # Билинейная
        f_bilin = ttk.LabelFrame(self.frame_overview, text=" Билинейная интерполяция (Bilinear) ", padding=6)
        f_bilin.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        self.can_bilin = tk.Canvas(f_bilin, bg="#ffffff", highlightthickness=0)
        self.can_bilin.pack(fill=tk.BOTH, expand=True)
        self.can_bilin.bind("<Motion>", lambda e: self._on_canvas_hover(e, "bilin"))

        # Бикубическая
        f_bicub = ttk.LabelFrame(self.frame_overview, text=" Бикубическая интерполяция (Лагранж 16 точек) ", padding=6)
        f_bicub.grid(row=1, column=1, sticky="nsew", padx=4, pady=4)
        self.can_bicub = tk.Canvas(f_bicub, bg="#ffffff", highlightthickness=0)
        self.can_bicub.pack(fill=tk.BOTH, expand=True)
        self.can_bicub.bind("<Motion>", lambda e: self._on_canvas_hover(e, "bicub"))

        for can in [self.can_orig, self.can_near, self.can_bilin, self.can_bicub]:
            can.bind("<Configure>", lambda e: self._redraw_overview_canvases())

    def _build_status_bar(self):
        status_frame = ttk.Frame(self, relief=tk.SUNKEN, padding=(6, 3))
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.lbl_status_main = ttk.Label(
            status_frame, text="Готов к работе", style="Status.TLabel"
        )
        self.lbl_status_main.pack(side=tk.LEFT)

        self.lbl_status_coords = ttk.Label(
            status_frame, text="X: - | Y: - | RGB: -", style="Status.TLabel"
        )
        self.lbl_status_coords.pack(side=tk.RIGHT)

    def _on_scale_x_change(self, val_str):
        sx = float(val_str)
        self.lbl_val_sx.config(text=f"{sx:.2f}")
        if self.var_lock_aspect.get():
            self.var_scale_y.set(sx)
            self.lbl_val_sy.config(text=f"{sx:.2f}")
        self._schedule_update()

    def _on_scale_y_change(self, val_str):
        sy = float(val_str)
        self.lbl_val_sy.config(text=f"{sy:.2f}")
        if self.var_lock_aspect.get():
            self.var_scale_x.set(sy)
            self.lbl_val_sx.config(text=f"{sy:.2f}")
        self._schedule_update()

    def _on_toggle_aspect(self):
        if self.var_lock_aspect.get():
            self.var_scale_y.set(self.var_scale_x.get())
            self.lbl_val_sy.config(text=f"{self.var_scale_x.get():.2f}")
            self._schedule_update()

    def _on_angle_change(self, val_str):
        deg = float(val_str)
        self.lbl_val_rot.config(text=f"{deg:+.1f}°")
        self._schedule_update()

    def _on_shear_x_change(self, val_str):
        kx = float(val_str)
        self.lbl_val_kx.config(text=f"{kx:+.2f}")
        self._schedule_update()

    def _on_shear_y_change(self, val_str):
        ky = float(val_str)
        self.lbl_val_ky.config(text=f"{ky:+.2f}")
        self._schedule_update()

    def _preset_reset(self):
        self.var_scale_x.set(1.0)
        self.var_scale_y.set(1.0)
        self.var_angle.set(0.0)
        self.var_shear_x.set(0.0)
        self.var_shear_y.set(0.0)
        self.lbl_val_sx.config(text="1.00")
        self.lbl_val_sy.config(text="1.00")
        self.lbl_val_rot.config(text="0.0°")
        self.lbl_val_kx.config(text="0.00")
        self.lbl_val_ky.config(text="0.00")
        self._schedule_update()

    def _preset_scale(self, s: float):
        self.var_scale_x.set(s)
        self.var_scale_y.set(s)
        self.lbl_val_sx.config(text=f"{s:.2f}")
        self.lbl_val_sy.config(text=f"{s:.2f}")
        self._schedule_update()

    def _preset_rotate(self, deg: float):
        self.var_angle.set(deg)
        self.lbl_val_rot.config(text=f"{deg:+.1f}°")
        self._schedule_update()

    def _preset_shear(self, kx: float, ky: float):
        self.var_shear_x.set(kx)
        self.var_shear_y.set(ky)
        self.lbl_val_kx.config(text=f"{kx:+.2f}")
        self.lbl_val_ky.config(text=f"{ky:+.2f}")
        self._schedule_update()

    def _preset_combo(self):
        self.var_scale_x.set(1.2)
        self.var_scale_y.set(1.2)
        self.var_angle.set(25.0)
        self.var_shear_x.set(0.3)
        self.var_shear_y.set(0.0)
        self.lbl_val_sx.config(text="1.20")
        self.lbl_val_sy.config(text="1.20")
        self.lbl_val_rot.config(text="+25.0°")
        self.lbl_val_kx.config(text="+0.30")
        self.lbl_val_ky.config(text="0.00")
        self._schedule_update()

    def _get_bg_rgb(self) -> Tuple[int, int, int]:
        c = self.var_bg_color.get()
        if c == "Черный":
            return (0, 0, 0)
        elif c == "Серый":
            return (128, 128, 128)
        return (255, 255, 255)

    def _load_default_pattern(self):
        self.source_image = algorithms.generate_test_pattern("shapes", width=360, height=360)
        w, h = self.source_image.size
        self.lbl_img_info.config(text=f"Размер: {w} x {h} px")
        self._apply_all_transforms()

    def _on_open_file(self):
        filepath = filedialog.askopenfilename(
            title="Выберите изображение",
            filetypes=[
                ("Все изображения", "*.png *.jpg *.jpeg *.bmp *.pbm *.ppm *.tiff"),
                ("PNG Files", "*.png"),
                ("JPEG Files", "*.jpg *.jpeg"),
                ("Bitmap Files", "*.bmp *.pbm *.ppm"),
                ("Все файлы", "*.*"),
            ]
        )
        if not filepath:
            return

        try:
            img = Image.open(filepath).convert("RGB")
            max_side = 800
            w, h = img.size
            if max(w, h) > max_side:
                scale = max_side / max(w, h)
                new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            self.source_image = img
            w, h = self.source_image.size
            self.lbl_img_info.config(text=f"Размер: {w} x {h} px")
            self._apply_all_transforms()
            self.lbl_status_main.config(text=f"Загружен файл: {filepath}")
        except Exception as ex:
            messagebox.showerror("Ошибка открытия", f"Не удалось открыть файл:\n{ex}")

    def _get_current_params(self) -> TransformParams:
        return TransformParams(
            scale_x=self.var_scale_x.get(),
            scale_y=self.var_scale_y.get(),
            angle_deg=self.var_angle.get(),
            shear_x=self.var_shear_x.get(),
            shear_y=self.var_shear_y.get(),
            fit_bbox=self.var_fit_bbox.get(),
            bg_color=self._get_bg_rgb()
        )

    def _schedule_update(self):
        if self._update_job is not None:
            self.after_cancel(self._update_job)
        self._update_job = self.after(50, self._apply_all_transforms)

    def _apply_all_transforms(self):
        if self.source_image is None or self._is_updating:
            return

        self._is_updating = True
        params = self._get_current_params()

        try:
            res_dict = algorithms.apply_all_methods(self.source_image, params)
            self.transformed_images = {}
            self.transformed_timings = {}

            for k, (img, elapsed_ms) in res_dict.items():
                self.transformed_images[k] = img
                self.transformed_timings[k] = elapsed_ms

            out_w, out_h = self.transformed_images["bicubic"].size
            self.lbl_status_main.config(
                text=f"Трансформация выполнена: Выход {out_w}x{out_h} px | Исходный: {self.source_image.width}x{self.source_image.height} px"
            )

            self._redraw_overview_canvases()

        except Exception as e:
            self.lbl_status_main.config(text=f"Ошибка трансформации: {e}")
        finally:
            self._is_updating = False
            self._update_job = None

    def _render_image_to_canvas(self, canvas: tk.Canvas, image: Image.Image, attr_name: str):
        c_w = max(50, canvas.winfo_width())
        c_h = max(50, canvas.winfo_height())
        i_w, i_h = image.size

        # Пропорциональное вписывание в доступную область холста с аккуратным отступом
        avail_w = max(10, c_w - 20)
        avail_h = max(10, c_h - 20)
        scale = min(avail_w / i_w, avail_h / i_h)

        disp_w = max(1, int(round(i_w * scale)))
        disp_h = max(1, int(round(i_h * scale)))

        disp_img = image.resize((disp_w, disp_h), Image.Resampling.BILINEAR) if abs(scale - 1.0) > 0.001 else image
        photo = ImageTk.PhotoImage(disp_img)
        setattr(self, attr_name, photo)

        canvas.delete("all")
        canvas.create_image(c_w // 2, c_h // 2, anchor=tk.CENTER, image=photo)

        setattr(canvas, "_render_info", {
            "scale": scale,
            "offset_x": c_w // 2 - disp_w // 2,
            "offset_y": c_h // 2 - disp_h // 2,
            "img_w": i_w,
            "img_h": i_h,
        })

    def _redraw_overview_canvases(self):
        if self.source_image:
            self._render_image_to_canvas(self.can_orig, self.source_image, "_photo_orig")
        if "nearest" in self.transformed_images:
            self._render_image_to_canvas(self.can_near, self.transformed_images["nearest"], "_photo_near")
        if "bilinear" in self.transformed_images:
            self._render_image_to_canvas(self.can_bilin, self.transformed_images["bilinear"], "_photo_bilin")
        if "bicubic" in self.transformed_images:
            self._render_image_to_canvas(self.can_bicub, self.transformed_images["bicubic"], "_photo_bicub")

    def _on_canvas_hover(self, event, target: str):
        canvas_map = {
            "orig": (self.can_orig, self.source_image),
            "near": (self.can_near, self.transformed_images.get("nearest")),
            "bilin": (self.can_bilin, self.transformed_images.get("bilinear")),
            "bicub": (self.can_bicub, self.transformed_images.get("bicubic")),
        }
        if target not in canvas_map:
            return

        can, img = canvas_map[target]
        if not img:
            return

        info = getattr(can, "_render_info", None)
        if not info:
            return

        scale = info["scale"]
        ox, oy = info["offset_x"], info["offset_y"]
        ix = int((event.x - ox) / scale)
        iy = int((event.y - oy) / scale)

        if 0 <= ix < info["img_w"] and 0 <= iy < info["img_h"]:
            try:
                rgb = img.getpixel((ix, iy))
                if isinstance(rgb, int):
                    rgb = (rgb, rgb, rgb)
                elif len(rgb) > 3:
                    rgb = rgb[:3]
                self.lbl_status_coords.config(text=f"X: {ix} | Y: {iy} | RGB: {rgb}")
            except Exception:
                pass
        else:
            self.lbl_status_coords.config(text="X: - | Y: - | RGB: -")

    def _on_save_file(self):
        target = self.var_save_target.get()
        if target == "collage":
            if self.source_image is None or "bicubic" not in self.transformed_images:
                messagebox.showwarning("Предупреждение", "Сначала выполните трансформацию.")
                return

            try:
                img_to_save = algorithms.create_comparison_collage(
                    self.source_image,
                    self.transformed_images["nearest"],
                    self.transformed_images["bilinear"],
                    self.transformed_images["bicubic"],
                    self.transformed_timings
                )
                name_hint = "collage_comparison"
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось создать коллаж: {e}")
                return
        else:
            img_to_save = self.transformed_images.get(target)
            name_hint = f"transform_{target}"

        if img_to_save is None:
            messagebox.showwarning("Предупреждение", "Нет доступного изображения для сохранения.")
            return

        filepath = filedialog.asksaveasfilename(
            title="Сохранить изображение",
            initialfile=f"{name_hint}.pbm",
            defaultextension=".pbm",
            filetypes=[
                ("PBM Image", "*.pbm"),
                ("PNG Image", "*.png"),
                ("JPEG Image", "*.jpg"),
                ("BMP Image", "*.bmp"),
                ("Все файлы", "*.*"),
            ]
        )
        if not filepath:
            return

        try:
            algorithms.save_image(img_to_save, filepath)
            messagebox.showinfo("Успех", f"Изображение успешно сохранено в:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Ошибка сохранения", f"Не удалось сохранить файл:\n{e}")


if __name__ == "__main__":
    app = App()
    app.mainloop()
