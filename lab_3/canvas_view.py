import math
import tkinter as tk
from typing import Dict, List, Tuple, Optional, Callable
from PIL import Image, ImageTk, ImageDraw

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
