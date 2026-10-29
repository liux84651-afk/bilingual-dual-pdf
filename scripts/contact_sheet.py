# -*- coding: utf-8 -*-
"""Build contact sheets from rendered page PNGs.

用法: python contact_sheet.py <png 目录> [输出目录] [cols=5] [rows=3]
默认目录: <cwd>/preview
"""
import os
import sys

from PIL import Image


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.getcwd(), "preview")
    outdir = sys.argv[2] if len(sys.argv) > 2 else d
    cols = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    rows = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    if not os.path.isdir(d):
        sys.exit("目录不存在: %s" % d)
    files = sorted(f for f in os.listdir(d) if f.startswith("pg") and f.endswith(".png"))
    if not files:
        sys.exit("没有 pg*.png（先用 render_pdf.py 渲染页面）")
    imgs = [Image.open(os.path.join(d, f)) for f in files]
    per = cols * rows
    for si in range(0, len(imgs), per):
        batch = imgs[si:si + per]
        w, h = batch[0].size
        sheet = Image.new("RGB", (cols * w + (cols + 1) * 8, rows * h + (rows + 1) * 8), "white")
        for i, im in enumerate(batch):
            r, c = divmod(i, cols)
            sheet.paste(im, (8 + c * (w + 8), 8 + r * (h + 8)))
        out = os.path.join(outdir, "sheet_%d.png" % (si // per + 1))
        sheet.save(out)
        print(out, sheet.size)


if __name__ == "__main__":
    main()
