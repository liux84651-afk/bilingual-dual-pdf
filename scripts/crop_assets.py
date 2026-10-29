# -*- coding: utf-8 -*-
"""assets.json + 源 PDF -> 每张图表的高清 PNG（288 dpi 裁剪）

assets.json 每项: {"id":"A01","page":4,"x0":36,"x1":558,"y0":362,"y1":716,"caption":"Table 1. ..."}
  page 为 1-based 页码；x/y 为 PDF 坐标（y 向上，与 PyMuPDF/pdfium 一致）
用法: python crop_assets.py --pdf src.pdf --work work [--scale 4]
"""
import argparse, json, os, sys

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--scale", type=float, default=4.0, help="4 => 288dpi")
    ap.add_argument("--skip-existing", action="store_true")
    a = ap.parse_args(argv)
    for _c in (os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_pylibs"),
           os.path.join(os.getcwd(), "_pylibs")):
        if os.path.isdir(_c):
            sys.path.insert(0, _c)
    import pypdfium2 as pdfium

    work = os.path.abspath(a.work)
    outdir = os.path.join(work, "assets")
    os.makedirs(outdir, exist_ok=True)
    assets = json.load(open(os.path.join(work, "assets.json"), encoding="utf-8"))
    if isinstance(assets, dict):
        assets = assets.get("assets", [])
    doc = pdfium.PdfDocument(a.pdf)
    W, H = float(doc[0].get_width()), float(doc[0].get_height())
    cache = {}
    n = 0
    for it in assets:
        png = os.path.join(outdir, (it.get("id") or "asset") + ".png")
        if a.skip_existing and os.path.exists(png):
            continue
        pno = int(it["page"]) - 1
        if pno not in cache:
            cache[pno] = doc[pno].render(scale=a.scale).to_pil()
        pil = cache[pno]
        sx, sy = pil.size[0] / W, pil.size[1] / H
        box = (int(round(it["x0"] * sx)), int(round((H - it["y1"]) * sy)),
               int(round(it["x1"] * sx)), int(round((H - it["y0"]) * sy)))
        pil.crop(box).save(png)
        it["png"] = "assets/" + os.path.basename(png)
        n += 1
    json.dump(assets, open(os.path.join(work, "assets.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("cropped %d assets -> %s (scale=%s, %d dpi)" % (n, outdir, a.scale, int(72 * a.scale)))


if __name__ == "__main__":
    main()
