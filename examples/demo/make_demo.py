# -*- coding: utf-8 -*-
"""生成 demo 用的合成表格图片与 assets.json（不依赖任何外部素材）。

用法: python make_demo.py
"""
import json, os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "assets")
os.makedirs(OUT, exist_ok=True)

W, H = 1600, 620
img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)
try:
    f = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 34)
    fb = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 34)
except Exception:
    f = fb = ImageFont.load_default()

rows = [["Module type", "Rated efficiency", "Notes"],
        ["Monocrystalline", "21.5 %", "demo row 1"],
        ["Polycrystalline", "17.8 %", "demo row 2"],
        ["Thin film", "12.3 %", "demo row 3"]]
xs = [40, 520, 980]
y0, rh = 30, 120
d.rectangle([20, y0, W - 20, H - 30], outline="black", width=3)
d.line([20, y0 + rh, W - 20, y0 + rh], fill="black", width=2)
for ri, row in enumerate(rows):
    yy = y0 + ri * rh + 34
    for ci, cell in enumerate(row):
        d.text((xs[ci], yy), cell, fill="black", font=(fb if ri == 0 else f))
for k in (3, 4):
    d.line([20, y0 + rh * k - rh, W - 20, y0 + rh * k - rh], fill="gray", width=1)
img.save(os.path.join(OUT, "demo_table.png"))

assets = [{
    "id": "D01", "page": 2,
    "caption": "Table 1. Rated efficiency of three module types.",
    "png": "assets/demo_table.png",
}]
json.dump(assets, open(os.path.join(HERE, "assets.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("demo assets ready ->", os.path.join(OUT, "demo_table.png"))
