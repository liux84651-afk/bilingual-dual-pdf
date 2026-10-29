# -*- coding: utf-8 -*-
"""segments_en.json + translations.json + assets.json -> 双语文档.md（GFM 两列表格）

用法: python mdgen.py --work C:\\dualwork [--title "..."] [--front-page 1]

产出的 Markdown 约定（md2pdf.py 依赖这些约定）：
  | 英文单元格 | 中文单元格 |            普通段落行
  | **英文小标题** | **中文小标题** |      两端都以 ** 包裹 => 标题行
  ![](assets/x.png)                       图片独占一段 => 跨栏图
  | Table 1. … | 表 1. … |                 题注行（以 Table/Fig./表/图 开头）
"""
import argparse, json, os, re


def esc_md(t):
    return str(t).replace("|", "\\|").replace("\n", " ").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--title", default="")
    ap.add_argument("--front-page", type=int, default=0)
    ap.add_argument("--out", default="", help="输出 md 路径，默认 <work>/bilingual.md")
    a = ap.parse_args()
    W = os.path.abspath(a.work)
    segs = json.load(open(os.path.join(W, "segments_en.json"), encoding="utf-8"))
    trans = {}
    tp = os.path.join(W, "translations.json")
    if os.path.exists(tp):
        trans = json.load(open(tp, encoding="utf-8"))
    assets = []
    ap_ = os.path.join(W, "assets.json")
    if os.path.exists(ap_):
        assets = json.load(open(ap_, encoding="utf-8"))
        assets = assets if isinstance(assets, list) else assets.get("assets", [])

    # 资产插入点：after_segment 优先，否则按题注标签首次出现处
    auto = [x for x in assets if not x.get("after_segment")]
    by_after = {}
    for x in assets:
        if x.get("after_segment"):
            by_after.setdefault(x["after_segment"], []).append(x)

    out = []
    front = []

    def emit_asset(x):
        png = x.get("png", "")
        png = png.replace("\\", "/")
        cap_en = x.get("caption", "") or ""
        cap_zh = trans.get(x.get("id", ""), "") or ""
        out.append("")
        out.append("![](%s)" % png)
        out.append("")
        out.append("| %s | %s |" % (esc_md(cap_en), esc_md(cap_zh)))

    def maybe_auto(text):
        for x in list(auto):
            lab = re.match(r"^(Table\s+\S+|Fig\.\s+\S+|Figure\s+\S+)", x.get("caption", ""))
            if lab:
                token = lab.group(1).rstrip(".:;,\u3002：")
                cands = {token, re.sub(r"^Figure\b", "Fig", token),
                         re.sub(r"^Fig\.\s*", "Figure ", token)}
                if any(re.search(r"\b" + re.escape(c) + r"(?!\d)", text, re.I) for c in cands):
                    emit_asset(x)
                    auto.remove(x)

    for s in segs:
        sid = s["id"]
        if s.get("kind") == "asset":
            emit_asset({"id": sid, "png": s.get("png", ""), "caption": s.get("caption", "")})
            continue
        if sid in by_after:
            for x in by_after.pop(sid):
                emit_asset(x)
        en, zh = s["en"], trans.get(sid, "") or ""
        if a.front_page and s.get("page") == a.front_page:
            front.append((s.get("kind"), en, zh))
            continue
        maybe_auto(en)
        if s.get("kind") == "h2" or s.get("kind") == "h1":
            out.append("| **%s** | **%s** |" % (esc_md(en), esc_md(zh)))
        elif s.get("kind") == "footnote":
            out.append("| <sup>%s</sup> | <sup>%s</sup> |" % (esc_md(en), esc_md(zh)))
        else:
            out.append("| %s | %s |" % (esc_md(en), esc_md(zh)))
    for x in auto:
        emit_asset(x)
    for lst in by_after.values():
        for x in lst:
            emit_asset(x)

    head = ["<!-- 由 bilingual-dual-pdf/mdgen.py 生成：两列表格 = 左原文 / 右译文 -->", ""]
    if front:
        title_en, title_zh = front[0][1], front[0][2]
        head.append("# %s" % title_en)
        if title_zh:
            head.append("")
            head.append("# %s" % title_zh)
        head.append("")
        for kind, en, zh in front[1:]:
            same = (not zh) or zh.strip() == en.strip()
            if kind == "authors":
                head.append("**%s**" % esc_md(en))
                if not same:
                    head.append("")
                    head.append("%s" % esc_md(zh))
            elif kind.endswith("label"):
                lab = esc_md(en) + ("" if same else "　｜　" + esc_md(zh))
                head.append("#### %s" % lab)
            elif kind == "abstract":
                head.append("> %s" % esc_md(en))
                if not same:
                    head.append("")
                    head.append("> %s" % esc_md(zh))
            elif kind in ("affil", "meta", "doi"):
                head.append("%s" % esc_md(en))
                if not same:
                    head.append("%s" % esc_md(zh))
            else:
                head.append("%s" % esc_md(en))
                if not same:
                    head.append("")
                    head.append("%s" % esc_md(zh))
            head.append("")
        head.append("---")
        head.append("")
    head.append("| English (original) | 中文（译文） |")
    head.append("| --- | --- |")
    md = "\n".join(head + out) + "\n"
    dst = a.out or os.path.join(W, "bilingual.md")
    open(dst, "w", encoding="utf-8").write(md)
    rows = sum(1 for x in out if x.startswith("| "))
    print("md: %s  rows=%d  assets=%d  bytes=%d" % (dst, rows, len(assets), len(md.encode("utf-8"))))


if __name__ == "__main__":
    main()
