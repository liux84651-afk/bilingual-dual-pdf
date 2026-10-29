# -*- coding: utf-8 -*-
"""Build contact sheets from rendered page PNGs."""
import os, sys
WS = r"C:\Users\LIUXINYU\Desktop\专利相似性"
from PIL import Image
d = os.path.join(WS, "_work", "preview_all")
files = sorted(f for f in os.listdir(d) if f.startswith("pg") and f.endswith(".png"))
imgs = [Image.open(os.path.join(d, f)) for f in files]
cols, rows = 5, 3
per = cols * rows
for si in range(0, len(imgs), per):
    batch = imgs[si:si + per]
    w, h = batch[0].size
    sheet = Image.new("RGB", (cols * w + (cols + 1) * 8, rows * h + (rows + 1) * 8), "white")
    for i, im in enumerate(batch):
        r, c = divmod(i, cols)
        sheet.paste(im, (8 + c * (w + 8), 8 + r * (h + 8)))
    out = os.path.join(WS, "_work", "sheet_%d.png" % (si // per + 1))
    sheet.save(out)
    print(out, sheet.size)
