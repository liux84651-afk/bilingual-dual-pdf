# -*- coding: utf-8 -*-
"""源 PDF -> 结构化英文段落 (segments_en.json) + 图表资产框 (assets.json)。

用法:
  python extract.py --pdf src.pdf --out work [--report]      # 只输出统计，不打印正文

设计原则（省 token）：
  * 默认只打印 3~5 行统计；需要看内容用 --show N（只看前 N 段）
  * 不把整篇文本 dump 到对话；正文写进 work/outline.txt
  * 自动识别双栏、标题、脚注、图表区域；结果交由人/模型复核 assets.json
"""
import argparse, json, os, re, sys, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--show", type=int, default=0, help="打印前 N 段以便核对")
    args = ap.parse_args(argv)

    os.makedirs(args.out, exist_ok=True)
    os.environ["PDFCORE_PDF"] = os.path.abspath(args.pdf)
    import pdfcore as P

    # ---------- 页面顺序（走 /Pages 树，不依赖硬编码） ----------
    order = []
    root = None
    for num, body in P.objects.items():
        if b"/Type /Catalog" in body:
            root = num
            break
    def walk(n, seen=None):
        seen = seen or set()
        if n in seen:
            return
        seen.add(n)
        v = P.get(n)
        if not isinstance(v, dict):
            return
        kids = v.get("/Kids")
        if kids is None:
            order.append(n)
            return
        for k in kids:
            if isinstance(k, P.Ref):
                walk(k.num, seen)
    if root is not None:
        cat = P.get(root)
        pr = cat.get("/Pages")
        if isinstance(pr, P.Ref):
            walk(pr.num)
    if not order:
        order = sorted(n for n, b in P.objects.items()
                       if b"/Type /Page" in b and b"/Type /Pages" not in b)

    SKIP = re.compile(r"^(\d{1,3}$|D\.S\.|Contents lists available|Technological Forecasting|"
                      r"journal homep|at ScienceDirect|& Social Change|sevier\.com/locate)")
    HEAD = re.compile(r"^(\d+(\.\d+)*\.?\s+[A-Z“]|Appendix$|References$|Declaration of |"
                      r"CRediT |Data availability|Acknowledg)")

    def rows_of(runs):
        runs = sorted(runs, key=lambda r: (-r["y"], r["x"]))
        rows = []
        for r in runs:
            eff = r["sz"] * r.get("sc", 1.0)
            tol = max(1.2, 0.4 * eff)
            for row in rows:
                if abs(row["y"] - r["y"]) <= tol:
                    row["runs"].append(r)
                    break
            else:
                rows.append({"y": r["y"], "runs": [r]})
        rows.sort(key=lambda x: -x["y"])
        out = []
        for row in rows:
            row["runs"].sort(key=lambda r: r["x"])
            parts, prev_end, eff = [], None, 0.0
            for r in row["runs"]:
                eff = max(eff, r["sz"] * r.get("sc", 1.0))
                if prev_end is not None:
                    gap = r["x"] - prev_end
                    if gap > 0.16 * eff and not parts[-1].endswith(" ") and not r["t"].startswith(" "):
                        parts.append(" ")
                parts.append(r["t"])
                prev_end = r["x"] + r.get("w", 0.0)
            txt = re.sub(r"[ \t]+", " ", "".join(parts)).strip()
            if txt:
                out.append({"y": round(row["y"], 2), "x0": round(row["runs"][0]["x"], 2),
                            "x1": round(prev_end or 0, 2), "eff": round(eff, 2),
                            "bold": sum(1 for r in row["runs"] if r.get("b")) > 0.6 * len(row["runs"]),
                            "text": txt})
        return out

    def dehyphen(a, b):
        if a.endswith("-") and len(a) > 2 and a[-2].isalpha() and b[:1].islower():
            return a[:-1] + b
        return a + " " + b

    def paragraphs(rows):
        if not rows:
            return []
        left = min(r["x0"] for r in rows)
        gaps = [rows[i]["y"] - rows[i + 1]["y"] for i in range(len(rows) - 1)]
        gaps = [g for g in gaps if 0 < g < 40]
        lead = sorted(gaps)[len(gaps) // 2] if gaps else 10.5
        out, cur, prev = [], None, None
        for r in rows:
            head = bool(r["bold"]) or bool(HEAD.match(r["text"]))
            indent = r["x0"] - left
            new = (cur is None or head or cur["head"] or indent > 4.0
                   or (prev is not None and prev - r["y"] > lead * 1.45))
            if new:
                cur = {"head": head, "parts": [r["text"]]}
                out.append(cur)
            else:
                cur["parts"].append(r["text"])
            prev = r["y"]
        res = []
        for b in out:
            t = b["parts"][0]
            for nxt in b["parts"][1:]:
                t = dehyphen(t, nxt)
            res.append({"kind": "head" if b["head"] else "para",
                        "text": re.sub(r"\s+", " ", t).strip()})
        return res

    # ---------- 逐页：分栏 / 行 / 段 ----------
    segs, assets, page_h = [], [], None
    for pi, pnum in enumerate(order):
        pd = P.get(pnum)
        mb = pd.get("/MediaBox") or [0, 0, 595.28, 841.89]
        page_h = float(mb[3])
        page_w = float(mb[2])
        runs = P.page_runs(pnum)
        if not runs:
            continue
        # 分栏：按 x0 直方图找最大空隙（落在中间 30%~70% 宽度内）
        xs = sorted(r["x"] for r in runs)
        cand, best = None, 0.0
        for i in range(1, len(xs)):
            gap = xs[i] - xs[i - 1]
            if gap > best and page_w * 0.30 < xs[i] < page_w * 0.70:
                best, cand = gap, (xs[i - 1] + xs[i]) / 2
        cols = [runs] if not cand or best < 8 else \
               [[r for r in runs if r["x"] < cand], [r for r in runs if r["x"] >= cand]]

        # 资产：Form XObject（图）按 Do 处的 CTM 求实际落位 + 小字号块（表）
        def mul(m, n):
            a, b, c, d, e, f = m
            A, B, C, D, E, F = n
            return [a * A + b * C, a * B + b * D, c * A + d * C, c * B + d * D,
                    e * A + f * C + E, e * B + f * D + F]
        def apply(m, pt):
            x, y = pt
            return (x * m[0] + y * m[2] + m[4], x * m[1] + y * m[3] + m[5])

        res_d = pd.get("/Resources")
        res_d = P.get(res_d.num) if isinstance(res_d, P.Ref) else res_d
        xod = {}
        if isinstance(res_d, dict):
            xo = res_d.get("/XObject")
            xo = P.get(xo.num) if isinstance(xo, P.Ref) else xo
            for name, ref in (xo or {}).items():
                if isinstance(ref, P.Ref):
                    xod[name] = P.get(ref.num)
        contents = pd.get("/Contents")
        clist = [contents.num] if isinstance(contents, P.Ref) else \
                [c.num for c in contents if isinstance(c, P.Ref)]
        buf = b"".join(P.raw_stream(c) for c in clist)
        ctm, stack, operands = [1, 0, 0, 1, 0, 0], [], []
        page_assets = []
        for m in P.tok_re.finditer(buf):
            kind, tok = m.lastgroup, m.group()
            if kind in ("ws", "comment"):
                continue
            if kind == "num":
                try:
                    operands.append(float(tok))
                except Exception:
                    operands.append(0.0)
                continue
            if kind in ("name", "str", "hex", "arr"):
                operands.append(tok)
                continue
            op = tok.decode("latin-1")
            if op == "q":
                stack.append(ctm[:])
            elif op == "Q":
                if stack:
                    ctm = stack.pop()
            elif op == "cm":
                try:
                    ctm = mul([float(v) for v in operands[-6:]], ctm)
                except Exception:
                    pass
            elif op == "Do":
                nm = operands[-1].decode("latin-1") if operands and isinstance(operands[-1], bytes) else ""
                d = xod.get(nm)
                if isinstance(d, dict) and d.get("/Subtype") == "/Form" and "/OL" not in nm:
                    bb = [float(v) for v in (d.get("/BBox") or [0, 0, 1, 1])]
                    mm = mul([float(v) for v in (d.get("/Matrix") or [1, 0, 0, 1, 0, 0])], ctm)
                    pts = [apply(mm, (bb[0], bb[1])), apply(mm, (bb[2], bb[3]))]
                    xs_ = [p[0] for p in pts]
                    ys_ = [p[1] for p in pts]
                    w_, h_ = abs(xs_[1] - xs_[0]), abs(ys_[1] - ys_[0])
                    if w_ * h_ > 4000:
                        page_assets.append({"kind": "figure", "page": pi + 1, "caption": "",
                                            "x0": round(min(xs_), 1), "x1": round(max(xs_), 1),
                                            "y0": round(min(ys_), 1), "y1": round(max(ys_), 1)})
            operands = []

        # 小字号块 -> 表；并把落在资产框内的行从正文剔除
        small = []
        for col in cols:
            for r in rows_of(col):
                if r["eff"] <= 7.4:
                    small.append(r)
        small.sort(key=lambda r: -r["y"])
        blocks = []
        for r in small:
            if blocks and (blocks[-1]["y0"] - 1) <= r["y"] and (blocks[-1]["y0"] - r["y"]) < 15 \
                    and r["x0"] < blocks[-1]["x1"] + 20 and r["x1"] > blocks[-1]["x0"] - 20:
                b = blocks[-1]
                b["x0"] = min(b["x0"], r["x0"]); b["x1"] = max(b["x1"], r["x1"])
                b["y0"] = r["y"] - 0.3 * r["eff"]
                if re.match(r"^(Table|Fig\.|Figure)\s", r["text"]):
                    b["caption"] = r["text"]
            else:
                cap = r["text"] if re.match(r"^(Table|Fig\.|Figure)\s", r["text"]) else ""
                blocks.append({"kind": "table", "page": pi + 1, "caption": cap,
                               "x0": r["x0"], "x1": r["x1"],
                               "y1": r["y"] + 0.8 * r["eff"], "y0": r["y"] - 0.3 * r["eff"],
                               "y": r["y"]})
        for b in blocks:
            b.pop("y", None)
            has_cap = bool(re.match(r"^(Table)\\s", b["caption"] or ""))
            if has_cap or ((b["y1"] - b["y0"]) > 40 and (b["x1"] - b["x0"]) > 150):
                page_assets.append(b)
        assets.extend(page_assets)

        def in_asset(r):
            if pi == 0:   # 首页（题名/摘要/关键词）不做资产排除，交给人工重整
                return False
            for a in page_assets:
                if a["x0"] - 6 <= r["x0"] <= a["x1"] + 6 and a["y0"] - 4 <= r["y"] <= a["y1"] + 4:
                    return True
            return False

        body_rows, foot_rows = [], []
        for col in cols:
            rows = rows_of(col)
            for r in rows:
                if SKIP.match(r["text"]) or in_asset(r):
                    continue
                if r["eff"] <= 7.3 and r["y"] < 180:
                    foot_rows.append(r)
                else:
                    body_rows.append(r)
            for b in paragraphs([r for r in rows if SKIP.match(r["text"]) is None
                                 and not in_asset(r)
                                 and not (r["eff"] <= 7.3 and r["y"] < 180)]):
                segs.append({"kind": "h2" if b["kind"] == "head" else "para",
                             "page": pi + 1, "en": b["text"]})
        for b in paragraphs(foot_rows):
            segs.append({"kind": "footnote", "page": pi + 1, "en": b["text"]})

    # ---------- 稳定 id + 输出 ----------
    for i, s in enumerate(segs):
        s["id"] = "p%03d" % (i + 1)
    json.dump(segs, open(os.path.join(args.out, "segments_en.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(assets, open(os.path.join(args.out, "assets.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    with open(os.path.join(args.out, "outline.txt"), "w", encoding="utf-8") as f:
        for s in segs:
            f.write("[%s|%s|p%s] %s\n" % (s["id"], s["kind"], s["page"], s["en"]))

    chars = sum(len(s["en"]) for s in segs)
    print("pages=%d segments=%d chars=%d assets=%d" %
          (len(order), len(segs), chars, len(assets)))
    print("out: %s/segments_en.json / assets.json / outline.txt" % args.out)
    print("assets 需人工核对 bbox（见 assets.json）；正文不要打印，按需 --show")
    if args.show:
        for s in segs[:args.show]:
            print("%s %-8s %s" % (s["id"], s["kind"], s["en"][:100]))


if __name__ == "__main__":
    main()
