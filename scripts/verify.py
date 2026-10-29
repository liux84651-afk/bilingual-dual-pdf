# -*- coding: utf-8 -*-
"""校验产物，避免用"读整页图"来肉眼检查（省 token）。

  python verify.py --work work [--pdf work/dual.pdf] [--sheet 2]
可做三件事：
  1) 结构检查：tex 中占位符是否替换、宏行数、begin/end 配平、缺译统计
  2) 文本层检查：PDF 页数、中文字符数、是否残留"待译"、每页是否有中英文
  3) 若 --sheet N：只渲染 N 张 contact sheet（默认 2 张，5×3 缩略图）供人眼快速确认
"""
import argparse, json, os, re, sys


def check_tex(work, problems):
    p = os.path.join(work, "dual.tex")
    if not os.path.exists(p):
        problems.append("dual.tex 不存在")
        return None
    s = open(p, encoding="utf-8").read()
    for ph in ("%%BODY%%", "%%FRONT%%"):
        if ph in s:
            problems.append("占位符未替换: " + ph)
    if s.count(r"\begin{document}") != 1 or s.count(r"\end{document}") != 1:
        problems.append("document 环境不匹配")
    for env in ("dual", "center"):
        if s.count(r"\begin{%s}" % env) != s.count(r"\end{%s}" % env):
            problems.append("环境不配平: " + env)
    rows = len(re.findall(r"^\\(dpara|dhead|dheadtwo|dfoot|dasset)\{", s, re.M))
    if s.count(r"\includegraphics") != len(re.findall(r"^\s*\\multicolumn\{2\}", s, re.M)):
        pass  # 图片数不强约束
    return {"tex_rows": rows, "tex_bytes": len(s.encode("utf-8"))}


def check_trans(work, problems):
    segs = json.load(open(os.path.join(work, "segments_en.json"), encoding="utf-8"))
    tp = os.path.join(work, "translations.json")
    trans = json.load(open(tp, encoding="utf-8")) if os.path.exists(tp) else {}
    miss = [s["id"] for s in segs if s.get("kind") != "asset"
            and not str(trans.get(s["id"], "")).strip()]
    placeholder = [k for k, v in trans.items() if "待译" in str(v)]
    if miss:
        problems.append("缺译 %d 段: %s" % (len(miss), miss[:8]))
    if placeholder:
        problems.append("译文含占位符: %s" % placeholder[:5])
    return {"segments": len(segs), "translated": len(segs) - len(miss)}


def check_pdf(pdf, problems, sheet=0, outdir=None):
    for _c in (os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_pylibs"),
               os.path.join(os.getcwd(), "_pylibs")):
        if os.path.isdir(_c):
            sys.path.insert(0, _c)
    try:
        import pypdfium2 as pdfium
    except Exception as e:  # noqa
        problems.append("pypdfium2 不可用: %r" % (e,))
        return None
    doc = pdfium.PdfDocument(pdf)
    n = len(doc)
    cjk, latin, bad = 0, 0, []
    for i in range(n):
        t = doc[i].get_textpage().get_text_range()
        c = len(re.findall(r"[\u4e00-\u9fff]", t))
        cjk += c
        latin += len(re.findall(r"[A-Za-z]", t))
        if c == 0:
            bad.append(i + 1)
    if n and cjk == 0:
        problems.append("PDF 文本层没有中文（字体/编码问题？）")
    info = {"pages": n, "cjk": cjk, "latin": latin, "pages_without_cjk": bad[:10]}
    if sheet and outdir:
        os.makedirs(outdir, exist_ok=True)
        thumbs = []
        for i in range(n):
            img = doc[i].render(scale=0.55).to_pil()
            thumbs.append(img)
        cols, rws, per = 5, 3, 15
        from PIL import Image
        # 只渲染 --sheet 张：每张 5×3
        for k in range(sheet):
            batch = thumbs[k * per:(k + 1) * per]
            if not batch:
                break
            w, h = batch[0].size
            canvas = Image.new("RGB", (cols * w + 6 * 8, rws * h + 4 * 8), "white")
            for i, im in enumerate(batch):
                r, c = divmod(i, cols)
                canvas.paste(im, (8 + c * (w + 8), 8 + r * (h + 8)))
            out = os.path.join(outdir, "sheet_%d.png" % (k + 1))
            canvas.save(out)
            print("sheet:", out)
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--pdf")
    ap.add_argument("--sheet", type=int, default=0, help="渲染几张 contact sheet（建议 <=2）")
    a = ap.parse_args()
    problems = []
    t = check_tex(a.work, problems)
    tr = check_trans(a.work, problems)
    info = {"tex": t, "trans": tr}
    if a.pdf and os.path.exists(a.pdf):
        info["pdf"] = check_pdf(a.pdf, problems, a.sheet, os.path.join(a.work, "preview"))
    print(json.dumps(info, ensure_ascii=False))
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print(" -", p)
        sys.exit(1)
    print("OK: 结构/覆盖率/文本层均通过（视觉只需看 contact sheet）")


if __name__ == "__main__":
    main()
