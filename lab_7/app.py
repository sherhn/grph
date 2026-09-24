import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
from PIL import Image, ImageTk, ImageDraw
from typing import Optional, Tuple

import algorithms


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Лабораторная работа №7 — Фильтрация изображений (Вариант 12)")
        self.geometry("1100x720")
        self.minsize(880, 560)

        style = ttk.Style(self)
        style.configure("Status.TLabel", font=("Helvetica", 9))
        style.configure("Header.TLabel", font=("Helvetica", 9, "bold"))

        self.source_image: Optional[Image.Image] = None
        self.lpf_image: Optional[Image.Image] = None
        self.hpf_image: Optional[Image.Image] = None
        self.last_rect_box: Optional[Tuple[int, int, int, int]] = None

        self.var_rect_w = tk.IntVar(value=160)
        self.var_rect_h = tk.IntVar(value=120)
        self.var_show_rect = tk.BooleanVar(value=True)
        self.var_save_target = tk.StringVar(value="lpf")
        self.var_active_tab = tk.StringVar(value="overview")

        self._build_layout()
        self._generate_default_image()

    def _build_layout(self):
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        left_frame = ttk.Frame(main_paned, width=330)
        left_frame.pack_propagate(False)
        main_paned.add(left_frame, weight=0)

        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)

        self._build_sidebar(left_frame)
        self._build_tabs(right_frame)
        self._build_status_bar()

    def _build_sidebar(self, parent: ttk.Frame):
        file_lf = ttk.LabelFrame(parent, text=" Изображение ", padding=8)
        file_lf.pack(fill=tk.X, padx=4, pady=(0, 6))

        ttk.Button(file_lf, text="📂 Загрузить из файла...", command=self._on_open_file).pack(fill=tk.X, pady=2)
        ttk.Button(file_lf, text="🎨 Создать тестовое", command=self._generate_default_image).pack(fill=tk.X, pady=2)

        self.lbl_img_info = ttk.Label(file_lf, text="Размер: 0 x 0", font=("Helvetica", 9))
        self.lbl_img_info.pack(fill=tk.X, pady=(4, 0))

        lpf_lf = ttk.LabelFrame(parent, text=" ФНЧ: Гауссиан вне axb ", padding=8)
        lpf_lf.pack(fill=tk.X, padx=4, pady=6)

        ttk.Label(lpf_lf, text="Прямоугольник axb без размытия:", font=("Helvetica", 9)).pack(anchor=tk.W, pady=(0, 4))

        row_w = ttk.Frame(lpf_lf)
        row_w.pack(fill=tk.X, pady=2)
        ttk.Label(row_w, text="Ширина a (px):", width=14).pack(side=tk.LEFT)
        e_w = ttk.Entry(row_w, textvariable=self.var_rect_w, width=8)
        e_w.pack(side=tk.LEFT)
        e_w.bind("<KeyRelease>", lambda e: self._safe_apply_lpf())

        row_h = ttk.Frame(lpf_lf)
        row_h.pack(fill=tk.X, pady=2)
        ttk.Label(row_h, text="Высота b (px):", width=14).pack(side=tk.LEFT)
        e_h = ttk.Entry(row_h, textvariable=self.var_rect_h, width=8)
        e_h.pack(side=tk.LEFT)
        e_h.bind("<KeyRelease>", lambda e: self._safe_apply_lpf())

        btn_preset_frame = ttk.Frame(lpf_lf)
        btn_preset_frame.pack(fill=tk.X, pady=4)
        ttk.Button(btn_preset_frame, text="50% размера", command=lambda: self._set_rect_percent(0.5)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
        ttk.Button(btn_preset_frame, text="70% размера", command=lambda: self._set_rect_percent(0.7)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)

        ttk.Checkbutton(lpf_lf, text="Показывать контур axb", variable=self.var_show_rect, command=self._refresh_lpf_views).pack(anchor=tk.W, pady=2)

        save_lf = ttk.LabelFrame(parent, text=" Сохранение ", padding=8)
        save_lf.pack(fill=tk.X, padx=4, pady=6)

        ttk.Label(save_lf, text="Что сохранить:").pack(anchor=tk.W, pady=(0, 2))
        ttk.Radiobutton(save_lf, text="Результат ФНЧ (Гауссиан)", variable=self.var_save_target, value="lpf").pack(anchor=tk.W)
        ttk.Radiobutton(save_lf, text="Результат ФВЧ (Лапласиан гауссиана)", variable=self.var_save_target, value="hpf").pack(anchor=tk.W)

        ttk.Button(save_lf, text="💾 Сохранить изображение...", command=self._on_save_file).pack(fill=tk.X, pady=(6, 2))

    def _build_tabs(self, parent: ttk.Frame):
        tab_bar = ttk.Frame(parent)
        tab_bar.pack(fill=tk.X, padx=2, pady=(0, 6))

        b_over = ttk.Radiobutton(
            tab_bar, text="Обзор (3 в 1)", variable=self.var_active_tab,
            value="overview", style="Toolbutton", command=self._switch_tab
        )
        b_over.pack(side=tk.LEFT, padx=3)

        b_lpf = ttk.Radiobutton(
            tab_bar, text="ФНЧ (Гауссиан)", variable=self.var_active_tab,
            value="lpf", style="Toolbutton", command=self._switch_tab
        )
        b_lpf.pack(side=tk.LEFT, padx=3)

        b_hpf = ttk.Radiobutton(
            tab_bar, text="ФВЧ (LoG в HSV)", variable=self.var_active_tab,
            value="hpf", style="Toolbutton", command=self._switch_tab
        )
        b_hpf.pack(side=tk.LEFT, padx=3)

        self.tab_container = ttk.Frame(parent)
        self.tab_container.pack(fill=tk.BOTH, expand=True)
        self.tab_container.rowconfigure(0, weight=1)
        self.tab_container.columnconfigure(0, weight=1)

        # 1. Вкладка Обзор
        self.tab_overview = ttk.Frame(self.tab_container)
        self.tab_overview.grid(row=0, column=0, sticky="nsew")
        self._build_overview_tab(self.tab_overview)

        # 2. Вкладка ФНЧ
        self.tab_lpf = ttk.Frame(self.tab_container)
        self.tab_lpf.grid(row=0, column=0, sticky="nsew")
        self.lbl_tab_lpf = ttk.Label(self.tab_lpf, anchor="center")
        self.lbl_tab_lpf.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # 3. Вкладка ФВЧ
        self.tab_hpf = ttk.Frame(self.tab_container)
        self.tab_hpf.grid(row=0, column=0, sticky="nsew")
        self.lbl_tab_hpf = ttk.Label(self.tab_hpf, anchor="center")
        self.lbl_tab_hpf.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.tab_overview.tkraise()

    def _switch_tab(self):
        target = self.var_active_tab.get()
        if target == "overview":
            self.tab_overview.tkraise()
        elif target == "lpf":
            self.tab_lpf.tkraise()
        elif target == "hpf":
            self.tab_hpf.tkraise()

    def _build_overview_tab(self, parent: ttk.Frame):
        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        f_src = ttk.LabelFrame(paned, text=" Исходное ")
        paned.add(f_src, weight=1)
        self.lbl_over_src = ttk.Label(f_src, anchor="center")
        self.lbl_over_src.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        f_lpf = ttk.LabelFrame(paned, text=" ФНЧ (вне axb) ")
        paned.add(f_lpf, weight=1)
        self.lbl_over_lpf = ttk.Label(f_lpf, anchor="center")
        self.lbl_over_lpf.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        f_hpf = ttk.LabelFrame(paned, text=" ФВЧ (LoG HSV) ")
        paned.add(f_hpf, weight=1)
        self.lbl_over_hpf = ttk.Label(f_hpf, anchor="center")
        self.lbl_over_hpf.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

    def _build_status_bar(self):
        status_frame = ttk.Frame(self, relief=tk.SUNKEN, padding=(6, 3))
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.lbl_status = ttk.Label(status_frame, text="Готово", style="Status.TLabel")
        self.lbl_status.pack(side=tk.LEFT)

    def _make_preview_photo(
        self,
        img: Image.Image,
        max_w: int,
        max_h: int,
        draw_rect_box: Optional[Tuple[int, int, int, int]] = None,
        draw_mid_line: bool = False
    ) -> ImageTk.PhotoImage:
        iw, ih = img.size
        scale = min(max_w / iw, max_h / ih, 1.0)
        dw = max(1, int(round(iw * scale)))
        dh = max(1, int(round(ih * scale)))

        if scale != 1.0:
            disp_img = img.resize((dw, dh), Image.BILINEAR)
        else:
            disp_img = img.copy()

        if draw_rect_box is not None and self.var_show_rect.get():
            x1, y1, x2, y2 = draw_rect_box
            rx1 = int(round(x1 * scale))
            ry1 = int(round(y1 * scale))
            rx2 = int(round(x2 * scale))
            ry2 = int(round(y2 * scale))
            draw = ImageDraw.Draw(disp_img)
            draw.rectangle([rx1, ry1, rx2, ry2], outline=(255, 0, 0), width=2)

        if draw_mid_line:
            mid_x = int(round((iw // 2) * scale))
            draw = ImageDraw.Draw(disp_img)
            draw.line([(mid_x, 0), (mid_x, dh)], fill=(0, 255, 255), width=2)

        return ImageTk.PhotoImage(disp_img)

    def _set_label_image(self, label: ttk.Label, photo: ImageTk.PhotoImage):
        label.configure(image=photo)
        label.image = photo

    def _update_all_labels(self):
        if self.source_image is None or self.lpf_image is None or self.hpf_image is None:
            return

        rect_box = self.last_rect_box if self.var_show_rect.get() else None

        over_w, over_h = 240, 620
        full_w, full_h = 740, 620

        # Обзор
        photo_src = self._make_preview_photo(self.source_image, over_w, over_h, draw_rect_box=rect_box)
        self._set_label_image(self.lbl_over_src, photo_src)

        photo_lpf = self._make_preview_photo(self.lpf_image, over_w, over_h, draw_rect_box=rect_box)
        self._set_label_image(self.lbl_over_lpf, photo_lpf)

        photo_hpf = self._make_preview_photo(self.hpf_image, over_w, over_h, draw_mid_line=True)
        self._set_label_image(self.lbl_over_hpf, photo_hpf)

        # Отдельные вкладки
        photo_tab_lpf = self._make_preview_photo(self.lpf_image, full_w, full_h, draw_rect_box=rect_box)
        self._set_label_image(self.lbl_tab_lpf, photo_tab_lpf)

        photo_tab_hpf = self._make_preview_photo(self.hpf_image, full_w, full_h, draw_mid_line=True)
        self._set_label_image(self.lbl_tab_hpf, photo_tab_hpf)

    def _refresh_lpf_views(self):
        if self.lpf_image is None or self.source_image is None:
            return

        rect_box = self.last_rect_box if self.var_show_rect.get() else None
        over_w, over_h = 240, 620
        full_w, full_h = 740, 620

        photo_src = self._make_preview_photo(self.source_image, over_w, over_h, draw_rect_box=rect_box)
        self._set_label_image(self.lbl_over_src, photo_src)

        photo_lpf = self._make_preview_photo(self.lpf_image, over_w, over_h, draw_rect_box=rect_box)
        self._set_label_image(self.lbl_over_lpf, photo_lpf)

        photo_tab_lpf = self._make_preview_photo(self.lpf_image, full_w, full_h, draw_rect_box=rect_box)
        self._set_label_image(self.lbl_tab_lpf, photo_tab_lpf)

    def _safe_apply_lpf(self):
        try:
            self._on_apply_lpf()
        except (tk.TclError, ValueError):
            pass

    def _set_rect_percent(self, frac: float):
        if self.source_image is None:
            return
        w, h = self.source_image.size
        self.var_rect_w.set(max(1, int(round(w * frac))))
        self.var_rect_h.set(max(1, int(round(h * frac))))
        self._on_apply_lpf()

    def _generate_default_image(self):
        w, h = 320, 240
        arr = np.zeros((h, w, 3), dtype=np.uint8)

        # Градиентный фон
        for y in range(h):
            for x in range(w):
                arr[y, x] = [
                    int(120 + 80 * (x / w)),
                    int(140 + 80 * (y / h)),
                    int(200 - 100 * ((x + y) / (w + h)))
                ]

        img = Image.fromarray(arr, mode="RGB")
        draw = ImageDraw.Draw(img)

        # Геометрические фигуры разного цвета
        draw.rectangle([40, 40, 140, 140], fill=(230, 60, 60), outline=(255, 255, 255), width=2)
        draw.ellipse([170, 50, 270, 150], fill=(50, 200, 80), outline=(255, 255, 255), width=2)
        draw.polygon([(80, 170), (160, 220), (240, 170)], fill=(240, 200, 40), outline=(0, 0, 0), width=2)
        draw.rectangle([110, 80, 210, 180], fill=None, outline=(30, 30, 220), width=3)

        self._load_and_process_all(img, f"Тестовое изображение ({w} x {h} px)")

    def _on_open_file(self):
        filepath = filedialog.askopenfilename(
            title="Выберите изображение",
            filetypes=[
                ("Все изображения", "*.png *.jpg *.jpeg *.bmp *.pbm *.ppm *.pgm"),
                ("PNG Image", "*.png"),
                ("JPEG Image", "*.jpg *.jpeg"),
                ("BMP Image", "*.bmp"),
                ("PBM/PPM Netpbm", "*.pbm *.ppm *.pgm"),
                ("Все файлы", "*.*")
            ]
        )
        if not filepath:
            return
        try:
            img = Image.open(filepath).convert("RGB")
            self._load_and_process_all(img, f"Загружен файл: {filepath}")
        except Exception as e:
            messagebox.showerror("Ошибка загрузки", f"Не удалось открыть файл:\n{str(e)}")

    def _load_and_process_all(self, img: Image.Image, status_msg: str):
        self.source_image = img
        w, h = img.size
        self.lbl_img_info.config(text=f"Размер: {w} x {h} px")

        rw = max(1, w // 2)
        rh = max(1, h // 2)
        self.var_rect_w.set(rw)
        self.var_rect_h.set(rh)

        # Рассчитываем оба фильтра
        self.lpf_image, self.last_rect_box = algorithms.apply_variant12_lpf(
            self.source_image,
            rect_w=rw,
            rect_h=rh
        )
        self.hpf_image = algorithms.apply_variant12_hpf(self.source_image)

        # Создаем превью и кешируем их в стандартных Label
        self._update_all_labels()
        self.lbl_status.config(text=f"{status_msg} | Готово.")

    def _on_apply_lpf(self):
        if self.source_image is None:
            return
        try:
            rw = self.var_rect_w.get()
            rh = self.var_rect_h.get()
        except (tk.TclError, ValueError):
            rw, rh = self.source_image.width // 2, self.source_image.height // 2

        self.lpf_image, self.last_rect_box = algorithms.apply_variant12_lpf(
            self.source_image,
            rect_w=rw,
            rect_h=rh
        )
        self._refresh_lpf_views()
        self.lbl_status.config(text="ФНЧ пересчитан.")

    def _on_save_file(self):
        target = self.var_save_target.get()
        if target == "lpf":
            img_to_save = self.lpf_image
            name_hint = "lpf_gaussian"
        else:
            img_to_save = self.hpf_image
            name_hint = "hpf_log_hsv"

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
                ("Все файлы", "*.*")
            ]
        )
        if not filepath:
            return

        try:
            algorithms.save_image(img_to_save, filepath)
            messagebox.showinfo("Успех", f"Изображение успешно сохранено в:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Ошибка сохранения", f"Не удалось сохранить файл:\n{str(e)}")


if __name__ == "__main__":
    app = App()
    app.mainloop()
