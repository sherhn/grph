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
    savepath = filedialog.asksaveasfilename()
    if savepath:
        result.save(savepath)
