# -*- coding: utf-8 -*-
"""PDF text extraction using custom parser (no external libs)."""
import re, zlib, os, json, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
WS = r"C:\Users\LIUXINYU\Desktop\专利相似性"
PDF = os.environ.get("PDFCORE_PDF") or os.path.join(WS, "source.pdf")
data = open(PDF, "rb").read()

class Ref:
    __slots__ = ("num",)
    def __init__(self, n): self.num = n
    def __repr__(self): return "Ref(%d)" % self.num

class Parser:
    def __init__(self, buf):
        self.b = buf; self.i = 0; self.n = len(buf)
    def ws(self):
        while self.i < self.n and self.b[self.i] in b" \t\r\n\x00\x0c":
            self.i += 1
    def parse(self):
        self.ws()
        if self.i >= self.n: return None
        b = self.b
        if b[self.i:self.i+2] == b"<<": return self.dict()
        if b[self.i] == 0x5B: return self.array()
        if b[self.i] == 0x2F: return self.name()
        if b[self.i:self.i+4] == b"true": self.i += 4; return True
        if b[self.i:self.i+5] == b"false": self.i += 5; return False
        if b[self.i:self.i+4] == b"null": self.i += 4; return None
        if b[self.i] == 0x28: return self.string()
        if b[self.i] == 0x3C: return self.hexstring()
        m = re.match(rb"([+-]?\d+)\s+(\d+)\s+R\b", b[self.i:self.i+40])
        if m: self.i += m.end(); return Ref(int(m.group(1)))
        m = re.match(rb"[+-]?[\d.]+", b[self.i:self.i+40])
        if m:
            s = m.group(0); self.i += m.end()
            return float(s) if b"." in s else int(s)
        self.i += 1
        return None
    def dict(self):
        self.i += 2; d = {}
        while True:
            self.ws()
            if self.i >= self.n: return d
            if self.b[self.i:self.i+2] == b">>": self.i += 2; return d
            k = self.parse()
            if not isinstance(k, str):
                if self.i >= self.n: return d
                continue
            d[k] = self.parse()
    def array(self):
        self.i += 1; a = []
        while True:
            self.ws()
            if self.i >= self.n: return a
            if self.b[self.i] == 0x5D: self.i += 1; return a
            a.append(self.parse())
    def name(self):
        self.i += 1; s = self.i
        while self.i < self.n and self.b[self.i] not in b" \t\r\n\x00\x0c/[]<>(){}%":
            self.i += 1
        raw = self.b[s:self.i]
        raw = re.sub(rb"#([0-9A-Fa-f]{2})", lambda m: bytes([int(m.group(1), 16)]), raw)
        return "/" + raw.decode("latin-1")
    def string(self):
        self.i += 1; depth = 1; out = bytearray(); b = self.b
        while self.i < self.n:
            c = b[self.i]
            if c == 0x5C:
                self.i += 1
                if self.i >= self.n: break
                e = b[self.i]
                if e in b"nrtbf":
                    out += {0x6E: b"\n", 0x72: b"\r", 0x74: b"\t", 0x62: b"\b", 0x66: b"\f"}[e]; self.i += 1
                elif e in b"01234567":
                    o = bytearray()
                    while len(o) < 3 and self.i < self.n and b[self.i] in b"01234567":
                        o.append(b[self.i]); self.i += 1
                    out.append(int(o, 8) & 0xFF)
                elif e == 0x0A:
                    self.i += 1
                else:
                    out.append(e); self.i += 1
                continue
            if c == 0x28:
                depth += 1; out.append(c); self.i += 1; continue
            if c == 0x29:
                depth -= 1; self.i += 1
                if depth == 0: break
                out.append(c); continue
            out.append(c); self.i += 1
        return out.decode("latin-1")
    def hexstring(self):
        self.i += 1; s = self.i
        while self.i < self.n and self.b[self.i] != 0x3E: self.i += 1
        h = re.sub(rb"[^0-9A-Fa-f]", b"", self.b[s:self.i]); self.i += 1
        if len(h) % 2: h += b"0"
        return bytes.fromhex(h.decode()).decode("latin-1")

obj_re = re.compile(rb"(\d+)\s+(\d+)\s+obj")
objects, streams = {}, {}
for m in obj_re.finditer(data):
    num = int(m.group(1)); start = m.end()
    end = data.find(b"endobj", start)
    if end < 0: continue
    body = data[start:end]; objects[num] = body
    sm = re.search(rb"stream\r?\n", body)
    if sm:
        e = body.rfind(b"endstream")
        if e > 0:
            streams[num] = (body[:sm.start()], body[sm.end():e])

def raw_stream(n):
    d, raw = streams[n]
    if b"/FlateDecode" in d:
        try: return zlib.decompress(raw)
        except Exception:
            try: return zlib.decompressobj().decompress(raw)
            except Exception: return b""
    return raw

_cache = {}
def get(n):
    if n in _cache: return _cache[n]
    b = objects.get(n)
    if b is None: return None
    v = Parser(b).parse()
    _cache[n] = v
    return v

def res_get(v, key):
    if isinstance(v, Ref): return get(v.num)
    return v

# ---------- ToUnicode CMap ----------
def parse_cmap(cmbytes):
    m = {}
    txt = cmbytes.decode("latin-1")
    # bfchar
    for blk in re.findall(r"beginbfchar(.*?)endbfchar", txt, re.S):
        for src, dst in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]*)>", blk):
            m[int(src, 16)] = hexstr_to_unicode(dst)
    for blk in re.findall(r"beginbfrange(.*?)endbfrange", txt, re.S):
        for lo, hi, rest in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(\[[^\]]*\]|<[0-9A-Fa-f]*>)", blk, re.S):
            lo_i, hi_i = int(lo, 16), int(hi, 16)
            if rest.startswith("["):
                items = re.findall(r"<([0-9A-Fa-f]*)>", rest)
                for k, it in enumerate(items):
                    if lo_i + k <= hi_i:
                        m[lo_i + k] = hexstr_to_unicode(it)
            else:
                base = rest.strip("<>")
                start = hexstr_to_unicode(base)
                for k in range(hi_i - lo_i + 1):
                    if not start: continue
                    m[lo_i + k] = start[:-1] + chr(ord(start[-1]) + k) if len(start) == 1 else start
    return m

def hexstr_to_unicode(h):
    if not h: return ""
    try:
        bs = bytes.fromhex(h if len(h) % 2 == 0 else h + "0")
    except ValueError:
        return ""
    try:
        return bs.decode("utf-16-be")
    except Exception:
        return bs.decode("latin-1", "ignore")

# ---------- Fonts ----------
def load_simple_widths(fd):
    fc = fd.get("/FirstChar", 0) or 0
    ws = fd.get("/Widths")
    if isinstance(ws, Ref): ws = get(ws.num)
    out = {}
    if isinstance(ws, list):
        for i, v in enumerate(ws):
            if isinstance(v, (int, float)): out[int(fc) + i] = float(v)
    miss = 0.0
    fdsc = fd.get("/FontDescriptor")
    if isinstance(fdsc, Ref): fdsc = get(fdsc.num)
    if isinstance(fdsc, dict):
        miss = float(fdsc.get("/MissingWidth", 0) or 0)
    return out, (miss or 500.0)

def load_cid_widths(fd):
    out = {}
    dw = 1000.0
    df = fd.get("/DescendantFonts")
    if isinstance(df, Ref): df = get(df.num)
    if isinstance(df, list) and df:
        d0 = df[0]
        if isinstance(d0, Ref): d0 = get(d0.num)
        if isinstance(d0, dict):
            try: dw = float(d0.get("/DW", 1000))
            except Exception: dw = 1000.0
            W = d0.get("/W")
            if isinstance(W, Ref): W = get(W.num)
            if isinstance(W, list):
                i = 0
                while i < len(W):
                    c = W[i]
                    if not isinstance(c, (int, float)):
                        i += 1; continue
                    if i + 1 >= len(W):
                        break
                    nxt = W[i + 1]
                    if isinstance(nxt, list):
                        for k, v in enumerate(nxt):
                            if isinstance(v, (int, float)): out[int(c) + k] = float(v)
                        i += 2
                    elif i + 2 < len(W) and isinstance(nxt, (int, float)) and isinstance(W[i + 2], (int, float)):
                        for cc in range(int(c), int(nxt) + 1):
                            out[cc] = float(W[i + 2])
                        i += 3
                    else:
                        i += 1
    return out, dw

font_cache = {}
def font_info(refnum):
    if refnum in font_cache: return font_cache[refnum]
    fd = get(refnum)
    info = {"cmap": {}, "two": False, "simple": None, "w": {}, "dw": 500.0,
            "base": "", "bold": False, "italic": False}
    if not isinstance(fd, dict):
        font_cache[refnum] = info; return info
    sub = fd.get("/Subtype")
    if sub == "/Type0":
        info["two"] = True
        info["w"], info["dw"] = load_cid_widths(fd)
    else:
        info["w"], info["dw"] = load_simple_widths(fd)
    tu = fd.get("/ToUnicode")
    if isinstance(tu, Ref):
        info["cmap"] = parse_cmap(raw_stream(tu.num))
    base = fd.get("/BaseFont") or ""
    if isinstance(base, str):
        info["base"] = base
        info["bold"] = ("Bold" in base) or ("bold" in base) or ("Semibold" in base)
        info["italic"] = ("Italic" in base) or ("Oblique" in base)
    else:
        info["base"] = ""
        info["bold"] = False
        info["italic"] = False
    enc = fd.get("/Encoding")
    if isinstance(enc, dict):
        diffs = enc.get("/Differences")
        if isinstance(diffs, list):
            code = 0; dm = {}
            for item in diffs:
                if isinstance(item, int): code = item
                elif isinstance(item, str):
                    dm[code] = glyph_to_uni(item); code += 1
            info["simple"] = dm
    font_cache[refnum] = info
    return info

GLYPHS = {
    "space": " ", "exclam": "!", "quotedbl": '"', "numbersign": "#", "dollar": "$",
    "percent": "%", "ampersand": "&", "quotesingle": "'", "parenleft": "(",
    "parenright": ")", "asterisk": "*", "plus": "+", "comma": ",", "hyphen": "-",
    "period": ".", "slash": "/", "zero": "0", "one": "1", "two": "2", "three": "3",
    "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "colon": ":", "semicolon": ";", "less": "<", "equal": "=", "greater": ">",
    "question": "?", "at": "@", "bracketleft": "[", "backslash": "\\",
    "bracketright": "]", "asciicircum": "^", "underscore": "_", "grave": "`",
    "braceleft": "{", "bar": "|", "braceright": "}", "asciitilde": "~",
    "quoteright": "\u2019", "quoteleft": "\u2018", "quotedblleft": "\u201c",
    "quotedblright": "\u201d", "endash": "\u2013", "emdash": "\u2014",
    "bullet": "\u2022", "minus": "\u2212", "fi": "fi", "fl": "fl", "ff": "ff",
    "ffi": "ffi", "ffl": "ffl", "dotlessi": "\u0131", "germandbls": "\u00df",
}
def glyph_to_uni(name):
    if name.startswith("/"): name = name[1:]
    if name in GLYPHS: return GLYPHS[name]
    if len(name) == 1: return name
    m = re.match(r"uni([0-9A-Fa-f]{4})", name)
    if m: return chr(int(m.group(1), 16))
    return ""

# ---------- content stream tokenizer ----------
tok_re = re.compile(rb"""
   (?P<ws>[\s\x00]+)
 | (?P<comment>%[^\r\n]*)
 | (?P<num>[+-]?(?:\d+\.\d*|\.\d+|\d+))
 | (?P<name>/[^\s\x00/\[\]<>(){}%]*)
 | (?P<str>\((?:[^()\\]|\\.|\((?:[^()\\]|\\.)*\))*\))
 | (?P<hex><[0-9A-Fa-f\s]*>)
 | (?P<arr>[\[\]])
 | (?P<op>[A-Za-z'"*]+)
""", re.X | re.S)

def unescape_pdf_string(s):
    s = s[1:-1]
    out = bytearray(); i = 0
    while i < len(s):
        c = s[i]
        if c == 0x5C and i + 1 < len(s):
            e = s[i+1]
            if e in b"nrtbf":
                out += {0x6E: b"\n", 0x72: b"\r", 0x74: b"\t", 0x62: b"\b", 0x66: b"\f"}[e]; i += 2
            elif e in b"01234567":
                o = bytearray(); j = i + 1
                while len(o) < 3 and j < len(s) and s[j] in b"01234567":
                    o.append(s[j]); j += 1
                out.append(int(o, 8) & 0xFF); i = j
            elif e in b"\r\n":
                i += 2
            else:
                out.append(e); i += 2
        else:
            out.append(c); i += 1
    return bytes(out)

def decode_codes(fi, raw):
    """Return (text, width_in_1000ths_of_em)."""
    if fi["two"]:
        out = []; wid = 0.0
        wmap = fi["w"]; dw = fi["dw"]
        for i in range(0, len(raw) - 1, 2):
            code = (raw[i] << 8) | raw[i + 1]
            ch = fi["cmap"].get(code)
            out.append(ch if ch is not None else "")
            wid += wmap.get(code, dw)
        return "".join(out), wid
    out = []; wid = 0.0
    wmap = fi["w"]; dw = fi["dw"]
    for c in raw:
        ch = fi["cmap"].get(c)
        if ch is None and fi["simple"]:
            ch = fi["simple"].get(c)
        if ch is None:
            ch = chr(c) if 32 <= c < 127 else ""
        out.append(ch)
        wid += wmap.get(c, dw)
    return "".join(out), wid

# ---------- pages ----------
page_order = [1742, 1, 47, 94, 140, 162, 186, 202, 216, 272, 297, 312, 333, 413, 657]

def page_runs(pnum):
    pd = get(pnum)
    res = res_get(pd.get("/Resources"), "/Resources")
    resd = get(res.num) if isinstance(res, Ref) else res
    fonts = {}
    if isinstance(resd, dict):
        fdict = resd.get("/Font")
        if isinstance(fdict, Ref): fdict = get(fdict.num)
        if isinstance(fdict, dict):
            for k, v in fdict.items():
                if isinstance(v, Ref): fonts[k] = v.num
    contents = pd.get("/Contents")
    if isinstance(contents, Ref): clist = [contents.num]
    elif isinstance(contents, list): clist = [c.num for c in contents if isinstance(c, Ref)]
    else: clist = []
    buf = b"".join(raw_stream(c) for c in clist)
    runs = []
    cur_font = None; cur_size = 12.0
    Tm = [1, 0, 0, 1, 0, 0]; Tlm = Tm[:]
    TL = 0.0
    ctm = [1, 0, 0, 1, 0, 0]
    gstack = []
    operands = []

    def mul(m, n):
        a, b, c, d, e, f = m
        A, B, C, D, E, F = n
        return [a * A + b * C, a * B + b * D, c * A + d * C, c * B + d * D,
                e * A + f * C + E, e * B + f * D + F]

    def dev(x, y):
        return (x * ctm[0] + y * ctm[2] + ctm[4], x * ctm[1] + y * ctm[3] + ctm[5])
    for m in tok_re.finditer(buf):
        kind = m.lastgroup
        tok = m.group()
        if kind == "ws" or kind == "comment": continue
        if kind == "arr":
            operands.append(tok); continue
        if kind == "num":
            try:
                operands.append(float(tok))
            except Exception:
                operands.append(0.0)
            continue
        if kind in ("name", "str", "hex"):
            operands.append(tok); continue
        op = tok.decode("latin-1")
        if op == "q":
            gstack.append(ctm[:])
        elif op == "Q":
            if gstack: ctm = gstack.pop()
        elif op == "cm":
            try:
                m6 = [float(v) for v in operands[-6:]]
                ctm = mul(m6, ctm)
            except Exception: pass
        elif op == "BT":
            Tm = [1, 0, 0, 1, 0, 0]; Tlm = Tm[:]
        elif op == "Tf":
            try:
                cur_font = operands[-2].decode("latin-1") if isinstance(operands[-2], bytes) else None
                cur_size = float(operands[-1]) if not isinstance(operands[-1], bytes) else cur_size
            except Exception: pass
        elif op == "TL":
            try: TL = float(operands[-1])
            except Exception: pass
        elif op == "Td":
            try:
                tx, ty = float(operands[-2]), float(operands[-1])
                Tlm = [Tlm[0], Tlm[1], Tlm[2], Tlm[3], Tlm[4] + tx*Tlm[0] + ty*Tlm[2], Tlm[5] + tx*Tlm[1] + ty*Tlm[3]]
                Tm = Tlm[:]
            except Exception: pass
        elif op == "TD":
            try:
                tx, ty = float(operands[-2]), float(operands[-1])
                TL = -ty
                Tlm = [Tlm[0], Tlm[1], Tlm[2], Tlm[3], Tlm[4] + tx*Tlm[0] + ty*Tlm[2], Tlm[5] + tx*Tlm[1] + ty*Tlm[3]]
                Tm = Tlm[:]
            except Exception: pass
        elif op == "Tm":
            try:
                Tlm = [float(v) for v in operands[-6:]]
                Tm = Tlm[:]
            except Exception: pass
        elif op == "T*":
            Tlm[4] += -TL*Tlm[2]; Tlm[5] += -TL*Tlm[3]; Tm = Tlm[:]
        elif op in ("Tj", "TJ", "'", '"'):
            if op == "'":
                Tlm[4] += -TL*Tlm[2]; Tlm[5] += -TL*Tlm[3]; Tm = Tlm[:]
            texts = []
            if op in ("Tj", "'", '"'):
                s = operands[-1]
                if s.startswith(b"("): texts.append(unescape_pdf_string(s))
                elif s.startswith(b"<"): texts.append(bytes.fromhex(re.sub(rb"[^0-9A-Fa-f]", b"", s[1:-1]).decode().ljust(2, "0")))
            else:  # TJ array: operands may include arr markers
                pending = b""
                for o in operands:
                    if isinstance(o, bytes) and o.startswith(b"("):
                        pending += unescape_pdf_string(o)
                    elif isinstance(o, bytes) and o.startswith(b"<"):
                        pending += bytes.fromhex(re.sub(rb"[^0-9A-Fa-f]", b"", o[1:-1]).decode().ljust(2, "0"))
                if pending: texts.append(pending)
            fi = font_info(fonts.get(cur_font, -1)) if cur_font else {"cmap": {}, "two": False, "simple": None}
            for t in texts:
                s, wid = decode_codes(fi, t)
                if s:
                    dx_, dy_ = dev(Tm[4], Tm[5])
                    sc = abs(Tm[0]) * abs(ctm[0]) or 1.0
                    runs.append({"x": round(dx_, 2), "y": round(dy_, 2), "t": s,
                                 "sz": cur_size, "w": round(wid / 1000.0 * cur_size * sc, 2),
                                 "sc": round(sc, 4), "b": bool(fi.get("bold")),
                                 "i": bool(fi.get("italic"))})
        operands = []
    return runs

def main():
    allpages = []
    for pi, pnum in enumerate(page_order):
        runs = page_runs(pnum)
        allpages.append({"page": pi + 1, "obj": pnum, "runs": runs})
        print("page", pi + 1, "runs", len(runs), "chars", sum(len(r["t"]) for r in runs))
    json.dump(allpages, open(os.path.join(WS, "_tools", "runs.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print("saved runs.json")


if __name__ == "__main__":
    main()
