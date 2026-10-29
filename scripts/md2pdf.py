# -*- coding: utf-8 -*-
"""Markdown（两列对照表）-> HTML -> PDF（用 Chrome/Edge headless 打印）

用法:
  python md2pdf.py --md C:\\dualwork\\bilingual.md [--pdf out.pdf] [--chrome <msedge/chrome 路径>]

约定（与 mdgen.py 一致）：
  | a | b |                 普通对照行
  | **a** | **b** |         标题行（两端加粗）
  | <sup>..</sup> | ... |   脚注行
  ![](png)                  跨栏图（独占一段）
  | Table 1. … | 表1. … |   题注行
其余 Markdown 段落（# 标题、**作者** 等）按居中/正文排版。
"""
import argparse, html, os, re, shutil, subprocess, sys, tempfile


def find_browser(explicit=""):
    cands = [explicit] if explicit else []
    for p in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"):
        cands.append(p)
    for c in cands:
        if c and os.path.exists(c):
            return c
    return shutil.which("chrome") or shutil.which("msedge")


def inline_md(t):
    """极简 inline markdown: **粗体**、*斜体*、`code`；保留 <sup> 等白名单标签"""
    t = html.escape(t, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    for tag in ("sup", "br", "b", "i", "code"):
        t = t.replace("&lt;%s&gt;" % tag, "<%s>" % tag)
        t = t.replace("&lt;/%s&gt;" % tag, "</%s>" % tag)
    return t


def split_row(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    cells, buf, i = [], "", 0
    while i < len(line):
        ch = line[i]
        if ch == "\\" and i + 1 < len(line) and line[i + 1] == "|":
            buf += "|"
            i += 2
            continue
        if ch == "|":
            cells.append(buf)
            buf = ""
        else:
            buf += ch
        i += 1
    cells.append(buf)
    return [c.strip() for c in cells]


CSS = """
@page { size: A4; margin: 14mm 13mm 13mm 13mm; }
* { box-sizing: border-box; }
body { margin:0; font-family: "Times New Roman","SimSun",serif; font-size:8.4pt; line-height:1.34; color:#111; }
h1 { font-size:15pt; text-align:center; margin:0 0 2pt 0; line-height:1.2; }
h2.zh-title { font-size:14pt; text-align:center; margin:0 0 8pt 0; }
.front { text-align:center; margin:2pt 0 5pt 0; }
.front .zh { color:#333; }
.abs { text-align:justify; margin:2pt 0 4pt 0; padding:0 4mm; }
.abs .zh { color:#333; }
hr { border:0; border-top:.5pt solid #bbb; margin:8pt 0; }
table { width:100%; border-collapse:collapse; table-layout:fixed; }
td { width:50%; vertical-align:top; padding:0 0 3.2pt 0; text-align:justify;
     word-break:break-word; overflow-wrap:anywhere; }
td.en { padding-right:6mm; }
td.zh { padding-left:6mm; border-left:.3pt solid #e6e6e6; }
tr.head td { font-weight:bold; font-size:9.6pt; line-height:1.28; padding-top:6pt; padding-bottom:2.6pt; }
tr.cap td { font-size:7.4pt; line-height:1.3; color:#222; }
tr.foot td { font-size:6.9pt; line-height:1.26; color:#333; }
.lbl { font-weight:bold; font-size:8.6pt; margin:6pt 0 1pt 0; }
figure { margin:5pt 0 2pt 0; page-break-inside:avoid; }
figure img { display:block; max-width:100%; max-height:235mm; margin:0 auto; }
tr { page-break-inside:avoid; }
"""


def md_to_html(md, title=""):
    lines = md.splitlines()
    body, i = [], 0
    in_table = False
    table_rows = []

    def flush_table():
        nonlocal in_table, table_rows
        if not table_rows:
            in_table = False
            return
        rows_html = []
        for cells, kind in table_rows:
            if kind == "sep":
                continue
            cls = ""
            if kind == "head":
                cls = ' class="head"'
            elif kind == "cap":
                cls = ' class="cap"'
            elif kind == "foot":
                cls = ' class="foot"'
            a = inline_md(cells[0]) if len(cells) > 0 else ""
            b = inline_md(cells[1]) if len(cells) > 1 else ""
            rows_html.append('<tr%s><td class="en">%s</td><td class="zh">%s</td></tr>' % (cls, a, b))
        body.append("<table>%s</table>" % "".join(rows_html))
        in_table = False
        table_rows = []

    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if s.startswith("|"):
            if not in_table:
                in_table = True
                table_rows = []
            cells = split_row(s)
            if all(re.fullmatch(r":?-{2,}:?", c or "-") for c in cells):
                table_rows.append((cells, "sep"))
            else:
                both_bold = all(c.strip().startswith("**") and c.strip().endswith("**") for c in cells if c.strip())
                sup = any(c.strip().startswith("<sup>") for c in cells if c.strip())
                cap = bool(re.match(r"^(Table|Fig\.|Figure|表|图)\s*", cells[0].strip()) if cells else False)
                kind = "head" if both_bold and not sup else ("foot" if sup else ("cap" if cap else "row"))
                table_rows.append((cells, kind))
            i += 1
            continue
        flush_table()
        if not s or s.startswith("<!--"):
            i += 1
            continue
        m = re.fullmatch(r"!\[\]\((.+?)\)", s)
        if m:
            src = m.group(1).strip()
            body.append('<figure><img src="%s"></figure>' % html.escape(src, quote=True))
            i += 1
            continue
        if s.startswith("# "):
            t = s[2:].strip()
            i += 1
            nxt = lines[i].strip() if i < len(lines) else ""
            if nxt.startswith("# "):
                body.append('<h1>%s</h1><h2 class="zh-title">%s</h2>' % (inline_md(t), inline_md(nxt[2:].strip())))
                i += 1
            else:
                body.append('<h1>%s</h1>' % inline_md(t))
            continue
        if s.startswith("#### "):
            body.append('<div class="lbl">%s</div>' % inline_md(s[5:].strip()))
            i += 1
            continue
        if s.startswith("> "):
            body.append('<div class="abs">%s</div>' % inline_md(s[2:].strip()))
            i += 1
            continue
        if s == "---":
            body.append("<hr>")
            i += 1
            continue
        body.append('<div class="front">%s</div>' % inline_md(s))
        i += 1
    flush_table()
    return ("<!doctype html><html><head><meta charset='utf-8'><title>%s</title><style>%s</style></head>"
            "<body>%s</body></html>" % (html.escape(title), CSS, "\n".join(body)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", required=True)
    ap.add_argument("--pdf", default="")
    ap.add_argument("--chrome", default="")
    ap.add_argument("--keep-html", action="store_true")
    a = ap.parse_args()
    md_path = os.path.abspath(a.md)
    work = os.path.dirname(md_path)
    md = open(md_path, encoding="utf-8").read()
    out_html = os.path.join(work, "bilingual.html")
    open(out_html, "w", encoding="utf-8").write(md_to_html(md, os.path.basename(md_path)))
    print("html:", out_html)

    pdf = a.pdf or os.path.join(work, "bilingual-md.pdf")
    pdf = os.path.abspath(pdf)
    browser = find_browser(a.chrome)
    if not browser:
        print("找不到 Chrome/Edge，已生成 HTML；可用浏览器手动打印为 PDF")
        return 2
    # 用临时 profile，避免占用用户配置
    tmp = tempfile.mkdtemp(prefix="mdpdf_")
    cmd = [browser, "--headless=new", "--disable-gpu", "--no-sandbox",
           "--no-pdf-header-footer", "--print-to-pdf-no-header",
           "--virtual-time-budget=20000",
           "--user-data-dir=" + tmp,
           "--print-to-pdf=" + pdf,
           "file:///" + out_html.replace("\\", "/")]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    ok = os.path.exists(pdf) and os.path.getsize(pdf) > 5000
    print("pdf:", pdf if ok else "FAILED")
    if not ok:
        print((r.stderr or r.stdout)[-1200:])
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
