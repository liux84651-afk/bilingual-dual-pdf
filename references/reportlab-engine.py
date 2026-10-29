# -*- coding: utf-8 -*-
"""Build the bilingual (EN left / ZH right) comparison PDF with reportlab."""
import json, os, re, sys
WS = os.getcwd()  # 改为你的工作目录
sys.path.insert(0, os.path.join(WS, "_pylibs"))
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import Color, black, HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth

D = os.path.join(WS, "_tools")
W = os.path.join(WS, "_work")
ASSETS = os.path.join(W, "assets")

# ---------------- fonts ----------------
FONTS = {
    "EN": (r"C:\Windows\Fonts\times.ttf", None),
    "EN-B": (r"C:\Windows\Fonts\timesbd.ttf", None),
    "EN-I": (r"C:\Windows\Fonts\timesi.ttf", None),
    "ZH": (r"C:\Windows\Fonts\simsun.ttc", 0),
    "ZH-B": (r"C:\Windows\Fonts\simhei.ttf", None),
}
for name, (path, idx) in FONTS.items():
    if idx is None:
        pdfmetrics.registerFont(TTFont(name, path))
    else:
        pdfmetrics.registerFont(TTFont(name, path, subfontIndex=idx))

PAGE_W, PAGE_H = A4
ML, MR = 37, 37
MT, MB = 44, 40
CONTENT_W = PAGE_W - ML - MR
GAP = 22
COL_W = (CONTENT_W - GAP) / 2.0
EN_X = ML
ZH_X = ML + COL_W + GAP

BODY = 8.6
LEAD = 11.2
CAP = 7.5
CAPLEAD = 9.4
H1 = 10.8
H1LEAD = 13.4
H2 = 9.6
H2LEAD = 12.2
TITLE = 15.5
TITLELEAD = 18.5

GREY = HexColor("#666666")
LIGHT = HexColor("#999999")

# ---------------- text metrics / wrapping ----------------
CJK_RE = re.compile(r"[\u3000-\u303f\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff00-\uffef]")
NO_START = "，。、；：？！）】》”’%‰·》〉」』,.;:?!)]}"
NO_END = "（【《“‘([{"

def is_cjk(ch):
    return bool(CJK_RE.match(ch))

def tw(t, font, size):
    try:
        return stringWidth(t, font, size)
    except Exception:
        return 0.5 * size * len(t)

def wrap_en(text, font, size, width):
    """Greedy word wrap."""
    words = text.split()
    if not words:
        return [""]
    space = tw(" ", font, size)
    lines, cur, curw = [], [], 0.0
    for w in words:
        ww = tw(w, font, size)
        add = ww if not cur else space + ww
        if cur and curw + add > width:
            lines.append(" ".join(cur))
            cur, curw = [w], ww
        else:
            cur.append(w)
            curw += add
    if cur:
        lines.append(" ".join(cur))
    return lines

def zh_tokens(text):
    """Split into atoms: CJK chars individually, latin words, numbers, spaces."""
    toks = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if is_cjk(ch):
            toks.append(ch)
            i += 1
        elif ch.isspace():
            toks.append(" ")
            i += 1
        else:
            j = i
            while j < n and not is_cjk(text[j]) and not text[j].isspace():
                j += 1
            toks.append(text[i:j])
            i = j
    return toks

def join_tokens(toks):
    out = ""
    for t in toks:
        if t == " ":
            if out and not out.endswith(" "):
                out += " "
        else:
            out += t
    return out

def wrap_zh(text, font, size, width):
    toks = zh_tokens(text)
    # collapse runs of spaces, strip ends
    norm = []
    for t in toks:
        if t == " ":
            if norm and norm[-1] != " ":
                norm.append(" ")
        else:
            norm.append(t)
    while norm and norm[0] == " ":
        norm.pop(0)
    while norm and norm[-1] == " ":
        norm.pop()
    if not norm:
        return [""]
    space_w = tw(" ", font, size)
    lines, cur, curw = [], [], 0.0
    for t in norm:
        ww = space_w if t == " " else tw(t, font, size)
        if cur and curw + ww > width:
            if t == " ":
                lines.append(join_tokens(cur))
                cur, curw = [], 0.0
                continue
            if t[0] in NO_START and len([x for x in cur if x != " "]) > 1:
                cur.append(t)
                curw += ww
                lines.append(join_tokens(cur))
                cur, curw = [], 0.0
                continue
            while cur and cur[-1] != " " and cur[-1][-1] in NO_END and len(cur) > 1:
                t = cur.pop() + t
                curw = sum(space_w if x == " " else tw(x, font, size) for x in cur)
            while cur and cur[-1] == " ":
                cur.pop()
                curw = sum(space_w if x == " " else tw(x, font, size) for x in cur)
            lines.append(join_tokens(cur))
            cur, curw = [t], ww
        else:
            cur.append(t)
            curw += ww
    if cur:
        lines.append(join_tokens(cur))
    return lines

def draw_line_just(c, x, y, text, font, size, width, last=False, lang="EN"):
    """Draw one line; justify to width unless last line of paragraph."""
    if not text:
        return
    if lang == "EN":
        parts = text.split()
        if not parts:
            return
        space = tw(" ", font, size)
        natural = sum(tw(p, font, size) for p in parts) + space * (len(parts) - 1)
        if last or len(parts) < 2 or natural >= width or (width - natural) > 0.30 * width:
            c.setFont(font, size)
            c.drawString(x, y, " ".join(parts))
            return
        extra = width - natural
        gap = extra / (len(parts) - 1)
        cx = x
        c.setFont(font, size)
        for p in parts:
            c.drawString(cx, y, p)
            cx += tw(p, font, size) + space + gap
    else:
        toks = zh_tokens(text)
        norm = []
        for t in toks:
            if t == " ":
                if norm and norm[-1] != " ":
                    norm.append(" ")
            else:
                norm.append(t)
        while norm and (norm[0] == " " or norm[-1] == " "):
            if norm and norm[0] == " ":
                norm.pop(0)
            if norm and norm[-1] == " ":
                norm.pop()
        if not norm:
            return
        widths = [tw(" ", font, size) if t == " " else tw(t, font, size) for t in norm]
        natural = sum(widths)
        n_gaps = len(norm) - 1
        if last or n_gaps <= 0 or natural >= width or (width - natural) > 0.30 * width:
            c.setFont(font, size)
            c.drawString(x, y, "".join(norm))
            return
        stretch = [i for i in range(n_gaps)
                   if norm[i] != " " and norm[i + 1] != " "
                   and not (norm[i + 1][0] in NO_START)
                   and norm[i][-1] not in "（【《“‘"
                   and norm[i + 1][0] not in "）】》”’"]
        if not stretch:
            stretch = [i for i in range(n_gaps) if norm[i] != " " and norm[i + 1] != " "
                       and not (norm[i + 1][0] in NO_START)]
        extra = width - natural
        c.setFont(font, size)
        cx = x
        if not stretch:
            c.drawString(x, y, "".join(norm))
            return
        add = extra / len(stretch)
        stretch_set = set(stretch)
        for i, t in enumerate(norm):
            if t != " ":
                c.drawString(cx, y, t)
            cx += widths[i]
            if i in stretch_set:
                cx += add

# ---------------- document state ----------------
segs = json.load(open(os.path.join(D, "segments_final.json"), encoding="utf-8"))

trans = {}
for i in (1, 2, 3):
    p = os.path.join(W, "trans_%d.json" % i)
    if os.path.exists(p):
        try:
            trans.update(json.load(open(p, encoding="utf-8")))
        except Exception as e:
            print("trans load failed", p, e)
print("loaded translations:", len(trans))
for extra in ("trans_4_fixed.json", "trans_fix.json"):
    p = os.path.join(W, extra)
    if os.path.exists(p):
        trans.update(json.load(open(p, encoding="utf-8")))
        print("loaded", extra)

PLACEHOLDER = os.environ.get("PLACEHOLDER", "1") == "1"

def zh_of(seg):
    if seg["kind"] == "asset":
        t = trans.get(seg["id"], "")
        if t.startswith("caption:"):
            t = t[len("caption:"):].strip()
        return t or ("［图表说明待译］" if not PLACEHOLDER else seg["caption_en"])
    t = trans.get(seg["id"], "")
    if t.strip():
        return t
    if seg.get("zh_fixed"):
        return seg["zh_fixed"]
    return seg.get("en", "")

# ---- filter out table-cell text that was captured as "footnote" segments ----
pages_lines = json.load(open(os.path.join(D, "pages_lines.json"), encoding="utf-8"))
def real_footnote(seg):
    pg = seg.get("page")
    if pg is None:
        return False
    rows = []
    for col in pages_lines[pg - 1]["columns"]:
        rows.extend(col)
    low = [r for r in rows if r["eff"] <= 7.4 and r["y"] < 180]
    head = re.sub(r"\s+", " ", seg.get("en", ""))[:28]
    for r in low:
        if re.sub(r"\s+", " ", r["text"])[:28].startswith(head[:20]):
            return True
    return False

class Doc:
    def __init__(self, path):
        self.c = canvas.Canvas(path, pagesize=A4)
        self.c.setTitle("A text-embedding-based approach to measuring patent-to-patent technological similarity — 中英对照版")
        self.c.setAuthor("Hain, Jurowetzki, Buchmann, Wolf")
        self.page = 0
        self.new_page(first=True)

    def new_page(self, first=False):
        if self.page > 0:
            self.footer()
            self.c.showPage()
        self.page += 1
        self.y = PAGE_H - MT
        if not first:
            self.header()

    def header(self):
        c = self.c
        c.setFont("EN", 6.9)
        c.setFillColor(GREY)
        c.drawString(ML, PAGE_H - 26, "A text-embedding-based approach to measuring patent-to-patent technological similarity")
        c.setFont("ZH", 6.9)
        c.drawRightString(PAGE_W - MR, PAGE_H - 26, "中英对照版  ·  Bilingual Edition")
        c.setStrokeColor(LIGHT)
        c.setLineWidth(0.4)
        c.line(ML, PAGE_H - 30, PAGE_W - MR, PAGE_H - 30)
        c.setFillColor(black)
        self.y = PAGE_H - MT

    def footer(self):
        c = self.c
        c.setFont("EN", 8)
        c.setFillColor(GREY)
        c.drawCentredString(PAGE_W / 2.0, 26, str(self.page))

    def space(self, h):
        self.y -= h

    def row(self, en, zh, font_en="EN", font_zh="ZH", size=BODY, lead=LEAD,
            bold=False, justify=True, pad_bottom=3.4, keep_with_next=0):
        """Draw an aligned bilingual row. Returns False if it did not fit."""
        fen = font_en
        fzh = font_zh
        en_lines = wrap_en(en, fen, size, COL_W)
        zh_lines = wrap_zh(zh, fzh, size, COL_W)
        n = max(len(en_lines), len(zh_lines))
        h = n * lead + pad_bottom
        if self.y - h < MB:
            # try to move to next page
            self.new_page()
            if self.y - h < MB:
                return False
        c = self.c
        top = self.y
        for i in range(n):
            base = top - (i + 1) * lead + (lead - size) * 0.42
            if i < len(en_lines):
                draw_line_just(c, EN_X, base, en_lines[i], fen, size, COL_W,
                               last=(i == len(en_lines) - 1) or not justify, lang="EN")
            if i < len(zh_lines):
                draw_line_just(c, ZH_X, base, zh_lines[i], fzh, size, COL_W,
                               last=(i == len(zh_lines) - 1) or not justify, lang="ZH")
        self.y -= h
        return True

    def heading(self, en, zh, level=1):
        size = H1 if level == 1 else H2
        lead = H1LEAD if level == 1 else H2LEAD
        above = 9 if level == 1 else 7
        below = 3.0
        en_n = len(wrap_en(en, "EN-B", size, COL_W))
        zh_n = len(wrap_zh(zh, "ZH-B", size, COL_W))
        h = max(en_n, zh_n) * lead
        # keep heading together with at least two following body lines
        if self.y - (above + h + 2 * LEAD + 6) < MB:
            self.new_page()
        self.y -= above
        self.row(en, zh, font_en="EN-B", font_zh="ZH-B", size=size, lead=lead,
                 justify=False, pad_bottom=below)
        self.y -= 1.5

    def caption(self, en, zh):
        self.row(en, zh, font_en="EN", font_zh="ZH", size=CAP, lead=CAPLEAD,
                 justify=True, pad_bottom=2.0)

    def asset(self, seg):
        path = os.path.join(ASSETS, seg["id"] + ".png")
        if not os.path.exists(path):
            return
        from reportlab.lib.utils import ImageReader
        img = ImageReader(path)
        iw, ih = img.getSize()
        x0, ybot, x1, ytop = seg["crop"]
        nat_w = (x1 - x0)
        nat_h = (ytop - ybot)
        scale = min(CONTENT_W / nat_w, 1.30)
        w = nat_w * scale
        h = nat_h * scale
        cap_en_lines = wrap_en(seg["caption_en"], "EN", CAP, COL_W)
        cap_zh_lines = wrap_zh(zh_of(seg), "ZH", CAP, COL_W)
        cap_n = max(len(cap_en_lines), len(cap_zh_lines))
        cap_h = cap_n * CAPLEAD + 3.0
        if self.y - (h + cap_h + 8) < MB:
            self.new_page()
            if h + cap_h + 8 > self.y - MB:
                # shrink to fit page
                avail = self.y - MB - cap_h - 10
                if avail > 40:
                    scale2 = avail / nat_h
                    w = nat_w * scale2
                    h = nat_h * scale2
                else:
                    return
        self.y -= 6
        x = ML + (CONTENT_W - w) / 2.0
        self.c.drawImage(path, x, self.y - h, width=w, height=h, mask="auto")
        self.y -= (h + 5)
        top = self.y
        for i in range(cap_n):
            base = top - (i + 1) * CAPLEAD + (CAPLEAD - CAP) * 0.42
            if i < len(cap_en_lines):
                draw_line_just(self.c, EN_X, base, cap_en_lines[i], "EN", CAP, COL_W,
                               last=(i == len(cap_en_lines) - 1), lang="EN")
            if i < len(cap_zh_lines):
                draw_line_just(self.c, ZH_X, base, cap_zh_lines[i], "ZH", CAP, COL_W,
                               last=(i == len(cap_zh_lines) - 1), lang="ZH")
        self.y -= cap_h

    def refs_image(self, seg, idx):
        pass

# ---- targeted content repairs ----
REPAIR_EN = ("academic publications (e.g. Franceschini et al., 2016), research grant descriptions "
             "(e.g. Freyman et al., 2016), product manuals (e.g. Jeong et al., 2021), and various "
             "types of web data such as technology blogs (e.g. Jurowetzki and Hain, 2014) or firm "
             "websites (e.g. Kinne and Axenbeck, 2020).")
REPAIR_ZH = ("学术出版物（如 Franceschini et al., 2016）、研究资助说明书（如 Freyman et al., 2016）、"
             "产品手册（如 Jeong et al., 2021），以及各类网络数据，例如技术博客（如 Jurowetzki and Hain, "
             "2014）或企业网站（如 Kinne and Axenbeck, 2020）。")
EXTRA_AFTER = [
    ("h1", "Declaration of Competing Interest", "利益冲突声明"),
    ("para", "The authors declare no conflict of interest.", "作者声明不存在利益冲突。"),
    ("h1", "Appendix", "附录"),
]

def is_dup_caption(seg):
    if seg["kind"] != "footnote":
        return False
    t = seg.get("en", "").strip()
    return bool(re.match(r"^(Fig\.|Figure|Table)\s", t))

# ---------------- build ----------------
OUT = os.path.join(W, "bilingual.pdf")
doc = Doc(OUT)
c = doc.c

pending_extra = []
for s in segs:
    k = s["kind"]
    if k == "pagebreak" or k == "refs":
        continue
    for kind, en, zh in pending_extra:
        if kind == "h1":
            doc.heading(en, zh, level=1)
        else:
            doc.row(en, zh, pad_bottom=3.2)
    pending_extra = []
    if "research grant Declaration of Competing Interest" in s.get("en", ""):
        doc.row(REPAIR_EN, REPAIR_ZH, pad_bottom=4.0)
        pending_extra = list(EXTRA_AFTER)
        continue
    if is_dup_caption(s):
        continue
    if s.get("en", "").strip() in ("Figure A.3", "Figure A.1", "Figure A.2", "Fig. A.3"):
        continue
    if k == "title":
        en, zh = s["en"], zh_of(s)
        en_lines = wrap_en(en, "EN-B", TITLE, CONTENT_W)
        zh_lines = wrap_zh(zh, "ZH-B", TITLE, CONTENT_W)
        for ln in en_lines:
            c.setFont("EN-B", TITLE)
            c.drawCentredString(PAGE_W / 2.0, doc.y - TITLE, ln)
            doc.y -= TITLELEAD
        for ln in zh_lines:
            c.setFont("ZH-B", TITLE)
            c.drawCentredString(PAGE_W / 2.0, doc.y - TITLE, ln)
            doc.y -= TITLELEAD
        doc.y -= 8
        continue
    if k in ("authors", "affil", "meta", "doi"):
        size = 10.4 if k == "authors" else 8.6
        zh = zh_of(s)
        en_flat = re.sub(r"[\s\W]+", "", s["en"]).lower()
        zh_flat = re.sub(r"[\s\W]+", "", zh).lower()
        en_lines = wrap_en(s["en"], "EN", size, CONTENT_W)
        for ln in en_lines:
            c.setFont("EN", size)
            c.drawCentredString(PAGE_W / 2.0, doc.y - size, ln)
            doc.y -= size * 1.34
        if en_flat != zh_flat:
            zh_lines = wrap_zh(zh, "ZH", size - 0.4, CONTENT_W)
            for ln in zh_lines:
                c.setFont("ZH", size - 0.4)
                c.drawCentredString(PAGE_W / 2.0, doc.y - size + 1, ln)
                doc.y -= (size - 0.4) * 1.44
        doc.y -= 3
        continue
    if k == "kwlabel":
        doc.y -= 5
        doc.row("Keywords:", zh_of(s), "EN-B", "ZH-B", size=8.8, lead=11.4, justify=False, pad_bottom=2)
        continue
    if k == "kw":
        doc.row(s["en"], zh_of(s), size=8.4, lead=10.8, justify=True, pad_bottom=3)
        continue
    if k == "abstractlabel":
        doc.y -= 4
        doc.row("Abstract", zh_of(s), "EN-B", "ZH-B", size=8.8, lead=11.4, justify=False, pad_bottom=2)
        continue
    if k == "abstract":
        doc.row(s["en"], zh_of(s), size=8.4, lead=11.0, justify=True, pad_bottom=5)
        continue
    if k == "note":
        doc.row(s["en"], zh_of(s), size=7.4, lead=9.4, justify=True, pad_bottom=2)
        continue
    if k == "h1":
        doc.heading(s["en"], zh_of(s), level=1)
    elif k == "h2":
        doc.heading(s["en"], zh_of(s), level=2)
    elif k == "para":
        doc.row(s["en"], zh_of(s), pad_bottom=3.2)
    elif k == "footnote":
        if not real_footnote(s):
            continue
        doc.row(s["en"], zh_of(s), size=7.2, lead=9.2, pad_bottom=2)
    elif k == "asset":
        doc.asset(s)

# ---------------- references ----------------
refseg = [s for s in segs if s["kind"] == "refs"][0]
doc.new_page()
doc.heading("References", "参考文献（原文照录）", level=1)
doc.y -= 2
from reportlab.lib.utils import ImageReader
for i, cr in enumerate(refseg["ref_crops"]):
    path = os.path.join(ASSETS, "refs_%d.png" % i)
    if not os.path.exists(path):
        continue
    img = ImageReader(path)
    iw, ih = img.getSize()
    w = iw / 4.0
    h = ih / 4.0
    if doc.y - h < MB:
        doc.new_page()
    x = ML + (CONTENT_W - w) / 2.0
    c.drawImage(path, x, doc.y - h, width=w, height=h, mask="auto")
    doc.y -= (h + 8)

doc.footer()
c.save()
print("written", OUT)
