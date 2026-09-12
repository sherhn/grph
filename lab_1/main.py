from PIL import Image
import numpy as np
from tkinter import filedialog

filepath = filedialog.askopenfilename()
if filepath:
    img = Image.open(filepath)
    array = np.array(img)

    array[0][0] = [64, 64, 127, 255]
    array[0][-1] = [127, 64, 127, 255]
    array[-1][-1] = [127, 127, 64, 255]


    result = Image.fromarray(array)
    savepath = filedialog.asksaveasfilename(
        defaultextension=".pbm",
        filetypes=[("PBM файл", "*.pbm")]
    )
    if savepath:
        with open(savepath, "w") as f:
            f.write("P3\n")
            f.write(f"{array.shape[1]} {array.shape[0]}\n")
            f.write("255\n")
            for row in array:
                for pixel in row:
                    f.write(f"{pixel[0]} {pixel[1]} {pixel[2]} ")
                f.write("\n")