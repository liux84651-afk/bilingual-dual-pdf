# -*- coding: utf-8 -*-
"""Render a PDF's pages to PNGs for visual verification.

用法: python render_pdf.py <src.pdf> <outdir> [scale=2.0] [pages=1,3,5]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for _c in (os.path.join(HERE, "_pylibs"), os.path.join(HERE, "..", "_pylibs"),
           os.path.join(os.getcwd(), "_pylibs")):
    if os.path.isdir(_c):
        sys.path.insert(0, _c)

try:
    import pypdfium2 as pdfium
except ImportError:
    sys.exit("缺少 pypdfium2：pip install pypdfium2（或运行 install.ps1 自动安装）")


def main():
    if len(sys.argv) < 3:
        sys.exit("用法: python render_pdf.py <src.pdf> <outdir> [scale] [pages]")
    src, outdir = sys.argv[1], sys.argv[2]
    scale = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
    pages = [int(x) for x in sys.argv[4].split(",")] if len(sys.argv) > 4 else None
    os.makedirs(outdir, exist_ok=True)
    doc = pdfium.PdfDocument(src)
    print("pages:", len(doc))
    idx = range(len(doc)) if not pages else [p - 1 for p in pages]
    for i in idx:
        img = doc[i].render(scale=scale).to_pil()
        p = os.path.join(outdir, "pg%02d.png" % (i + 1))
        img.save(p)
        print(p, img.size)


if __name__ == "__main__":
    main()
