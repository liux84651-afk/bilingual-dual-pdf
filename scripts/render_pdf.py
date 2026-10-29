# -*- coding: utf-8 -*-
"""Render a PDF's pages to PNGs for visual verification."""
import os, sys
WS = r"C:\Users\LIUXINYU\Desktop\专利相似性"
sys.path.insert(0, os.path.join(WS, "_pylibs"))
import pypdfium2 as pdfium

src = sys.argv[1]
outdir = sys.argv[2]
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
