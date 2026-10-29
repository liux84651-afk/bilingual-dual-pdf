# -*- coding: utf-8 -*-
"""segments_en.json + translations.json + assets.json -> dual.tex -> (xelatex) -> pdf

用法:
  python build_tex.py --work work [--title "英文标题"] [--compile]
     --work 目录内需有:
       segments_en.json    extract.py 产出（可含 kind="asset" 的占位）
       translations.json   {"p001": "中文", ..., "<asset_id>": "中文题注"}
       assets.json         [{"id":"A01","png":"a01.png","caption":"Table 1. ..."}]
       assets/*.png        图片
可选:
  --front-page 1        第 N 页的段落当作"封面区"居中单栏排
  --split 1100          超长段落按句号切成 <=N 字符，避免 longtable 行高溢出
  --compile             若存在 xelatex 则直接编译两遍
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
IMGSAFE = os.path.join(tempfile.gettempdir(), "dualimg")
if "_" in IMGSAFE or " " in IMGSAFE:
    IMGSAFE = r"C:\\dualtmp\\img"
os.makedirs(IMGSAFE, exist_ok=True)


def safe_image(path):
    """复制到无特殊字符目录，返回可用于 \\includegraphics 的绝对路径。"""
    if not os.path.exists(path):
        return str(path).replace("\\", "/")
    ext = os.path.splitext(path)[1].lower() or ".png"
    name = hashlib.md5(os.path.abspath(path).encode("utf-8")).hexdigest()[:12] + ext
    dst = os.path.join(IMGSAFE, name)
    if not os.path.exists(dst):
        shutil.copyfile(path, dst)
    return dst.replace("\\", "/")

TPL = os.path.join(os.path.dirname(HERE), "templates", "dual.tex")

# ---------- LaTeX 转义 ----------
_ESC = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "#": r"\#", "_": r"\_",
        "$": r"\$", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}"}

def _local_tectonic():
    """在 skill 的 _bin 目录或 workspace/_tex 下找 tectonic.exe"""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for c in (os.path.join(here, "_bin"), os.path.join(os.getcwd(), "_tex")):
        p = os.path.join(c, "tectonic.exe")
        if os.path.exists(p):
            return p
    return None


def esc(t):
    return "".join(_ESC.get(ch, ch) for ch in t)

def split_both(en, cn, limit):
    """中英各自按句切分，段数取较大者并补齐，保证续行两侧都有内容。"""
    ep = split_long(en, limit)
    if len(ep) <= 1:
        return [(en, cn)]
    ratio = (len(cn) / len(en)) if en else 1.0
    zp = split_long(cn, max(80, int(limit * ratio)))
    n = max(len(ep), len(zp))
    e = [p[0] for p in ep] + [""] * (n - len(ep))
    z = [p[0] for p in zp] + [""] * (n - len(zp))
    return list(zip(e, z))


def split_long(text, limit):
    """按句末切分超长段落，返回 [(片段, 是否续)]"""
    if len(text) <= limit:
        return [(text, False)]
    parts, buf = [], ""
    for sent in re.split(r"(?<=[.!?。！？])\s+", text):
        if buf and len(buf) + len(sent) + 1 > limit:
            parts.append(buf)
            buf = sent
        else:
            buf = (buf + " " + sent).strip()
    if buf:
        parts.append(buf)
    return [(p, i < len(parts) - 1) for i, p in enumerate(parts)]

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--title", default="")
    ap.add_argument("--front-page", type=int, default=0)
    ap.add_argument("--split", type=int, default=1100)
    ap.add_argument("--compile", action="store_true")
    ap.add_argument("--fonts-dir", default="", help="含 simsun.ttf/simhei.ttf/times*.ttf 的目录")
    ap.add_argument("--engine", default="auto", choices=["auto", "xelatex", "tectonic"])
    args = ap.parse_args(argv)

    W = os.path.abspath(args.work)
    segs = json.load(open(os.path.join(W, "segments_en.json"), encoding="utf-8"))
    trans = {}
    tp = os.path.join(W, "translations.json")
    if os.path.exists(tp):
        trans.update(json.load(open(tp, encoding="utf-8")))
    assets = []
    ap_ = os.path.join(W, "assets.json")
    if os.path.exists(ap_):
        assets = json.load(open(ap_, encoding="utf-8"))

    zh = lambda s: trans.get(s["id"], "") or ("［待译 %s］" % s["id"])

    # 资产插入点：after_segment 指定，否则按 caption 标签首次出现处
    by_after = {}
    for a in assets:
        anchor = a.get("after_segment")
        if anchor:
            by_after.setdefault(anchor, []).append(a)
    pending_labels = [a for a in assets if not a.get("after_segment")]

    body, front = [], []
    used_assets = set()
    def emit_assets(items):
        for a in items:
            png = a.get("png") or (a["id"] + ".png")
            path = png if os.path.isabs(png) else os.path.join(W, "assets", png)
            cap = a.get("caption", "")
            label = re.match(r"^(Table\s+\S+|Table\s+[A-Z]\.\d+|Fig\.\s+\S+|Figure\s+\S+)[.:]?\s*", cap)
            lab = label.group(1) if label else ""
            zh_cap = trans.get(a["id"], "") or ""
            body.append(r"\dasset{%s}{%s}{%s}" % (path.replace("\\", "/"), esc(cap), esc(zh_cap)))
            used_assets.add(a["id"])

    def flush_auto(text, cur_seg_id):
        for a in list(pending_labels):
            lab = re.match(r"^(Table\s+\S+|Fig\.\s+\S+|Figure\s+\S+)", a.get("caption", ""))
            if lab:
                token = re.sub(r"^Figure\b", "Fig", lab.group(1).rstrip(".:;,\u3002："))
                if re.search(r"\b" + re.escape(token) + r"(?!\d)", text, re.I):
                    emit_assets([a])
                pending_labels.remove(a)

    for s in segs:
        sid = s["id"]
        if s.get("kind") == "asset":
            emit_assets([{"id": sid, "png": s.get("png", sid + ".png"),
                          "caption": s.get("caption", "")}])
            continue
        if sid in by_after:
            emit_assets(by_after.pop(sid))
        en, cn = s["en"], zh(s)
        if args.front_page and s.get("page") == args.front_page:
            front.append((s.get("kind"), en, cn))
            continue
        flush_auto(en, sid)
        k = s.get("kind")
        for piece, cn_piece in split_both(en, cn, args.split):
            if k == "h2":
                body.append(r"\dheadtwo{%s}{%s}" % (esc(piece), esc(cn_piece)))
            elif k == "footnote":
                body.append(r"\dfoot{%s}{%s}" % (esc(piece), esc(cn_piece)))
            else:
                body.append(r"\dpara{%s}{%s}" % (esc(piece), esc(cn_piece)))
    for a in pending_labels:
        emit_assets([a])
    for items in by_after.values():
        emit_assets(items)

    # 封面区：首段放大居中，其余居中
    front_tex = []
    if front:
        title, authors = front[0], front[1] if len(front) > 1 else None
        front_tex.append(r"\begin{center}")
        front_tex.append(r"{\bfseries\fontsize{15}{18}\selectfont %s}\\[2pt]" % esc(title[1]))
        front_tex.append(r"{\bfseries\fontsize{15}{18}\selectfont %s}\\[8pt]" % esc(title[2]))
        rest = front[1:]
        for kind, en, cn in rest:
            size = r"\fontsize{9.4}{11.5}\selectfont"
            front_tex.append(r"%s %s\\[1pt]" % (size, esc(en)))
            front_tex.append(r"%s %s\\[5pt]" % (size, esc(cn)))
        front_tex.append(r"\end{center}")
        front_tex.append(r"\vspace{2mm}")

    if args.fonts_dir:
        fd = args.fonts_dir.replace("\\", "/").rstrip("/") + "/"
        fonts = ("\\setmainfont[Path=%s,Extension=.ttf,UprightFont=times,BoldFont=timesbd,"
                 "ItalicFont=timesi,BoldItalicFont=timesbi]{times}\n"
                 "\\setCJKmainfont[Path=%s,Extension=.ttf,UprightFont=simsun,BoldFont=simhei]{simsun}\n"
                 "\\setCJKsansfont[Path=%s,Extension=.ttf,UprightFont=simhei]{simhei}" % (fd, fd, fd))
    else:
        fonts = ("\\setmainfont{Times New Roman}\n\\setCJKmainfont{SimSun}\n"
                 "\\setCJKsansfont{SimHei}\n\\setsansfont{Arial}")
    tpl = open(TPL, encoding="utf-8").read().replace("%%FONTS%%", fonts)
    out = tpl.replace("%%FRONT%%", "\n".join(front_tex))
    out = out.replace("%%BODY%%", "\n".join(body))
    out = out.replace("\\ENHEAD", esc(args.title or (front[0][1] if front else ""))[:120].replace("_", r"\_"))
    tex = os.path.join(W, "dual.tex")
    open(tex, "w", encoding="utf-8").write(out)
    print("tex: %s  rows=%d  assets=%d  missing_translations=%d" %
          (tex, len(body), len(used_assets),
           sum(1 for s in segs if s.get("kind") not in ("asset",) and not trans.get(s["id"]))))
    if args.compile:
        exe = shutil.which("xelatex") if args.engine in ("auto", "xelatex") else None
        tex_bin = None
        if args.engine in ("auto", "tectonic"):
            tex_bin = shutil.which("tectonic") or _local_tectonic()
        if not exe and not tex_bin:
            print("找不到 xelatex / tectonic: 装 MiKTeX、TeXLive 或下载 tectonic 后重跑，"
                  "也可用 references/reportlab-engine.py 兜底")
            return 2
        build = os.path.join(IMGSAFE, "build")
        os.makedirs(build, exist_ok=True)
        shutil.copyfile(tex, os.path.join(build, "dual.tex"))
        if tex_bin:
            cmd = [tex_bin, "--keep-logs", "dual.tex"]
            runs = 1
        else:
            cmd = [exe, "-interaction=nonstopmode", "-halt-on-error", "dual.tex"]
            runs = 2
        for _ in range(runs):
            r = subprocess.run(cmd, cwd=build, capture_output=True, text=True,
                               encoding="utf-8", errors="ignore")
        pdf = os.path.join(build, "dual.pdf")
        if os.path.exists(pdf):
            shutil.copyfile(pdf, os.path.join(W, "dual.pdf"))
            pdf = os.path.join(W, "dual.pdf")
        print("pdf:", pdf if os.path.exists(pdf) else "FAILED (see dual.log)")
        if not os.path.exists(pdf):
            print(r.stdout[-1500:])
            return 3
    return 0

if __name__ == "__main__":
    sys.exit(main())
