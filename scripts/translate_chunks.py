# -*- coding: utf-8 -*-
"""切分待译段落 -> chunk 文件（交给 subagent 并行翻译）；之后合并并校验覆盖率。

  1) 切分: python translate_chunks.py split  --work work [--parts 3]
     -> work/chunk1.txt ... ；每段格式:  <<p001>>英文原文
  2) subagent 输出 work/trans_1.json ...  {"p001":"……"}
  3) 合并: python translate_chunks.py merge  --work work
     -> work/translations.json （并报告缺失/多余 id）
"""
import argparse, json, os, re, sys


def load_segs(work):
    segs = json.load(open(os.path.join(work, "segments_en.json"), encoding="utf-8"))
    return [s for s in segs if s.get("kind") != "asset"]


def cmd_split(a):
    segs = load_segs(a.work)
    assets = []
    ap = os.path.join(a.work, "assets.json")
    if os.path.exists(ap):
        assets = json.load(open(ap, encoding="utf-8"))
        assets = assets if isinstance(assets, list) else assets.get("assets", [])
    items = [(s["id"], s["en"]) for s in segs]
    items += [(x["id"], "caption:" + x.get("caption", "")) for x in assets if x.get("caption")]
    total = sum(len(t) for _, t in items)
    parts = max(1, a.parts)
    target = total / parts
    buckets, cur, acc = [[]], 0, 0
    for it in items:
        if len(buckets) < parts and acc > target * 0.55 and acc + len(it[1]) > target:
            buckets.append([])
            acc = 0
        buckets[-1].append(it)
        acc += len(it[1])
    for i, b in enumerate(buckets, 1):
        with open(os.path.join(a.work, "chunk%d.txt" % i), "w", encoding="utf-8") as f:
            for sid, txt in b:
                f.write("<<%s>>%s\n\n" % (sid, txt))
    print("split: %d 段 / %d 字符 -> %d 个 chunk（%s）" %
          (len(items), total, len(buckets), a.work))


def cmd_merge(a):
    want = [s["id"] for s in load_segs(a.work)]
    ap = os.path.join(a.work, "assets.json")
    if os.path.exists(ap):
        assets = json.load(open(ap, encoding="utf-8"))
        assets = assets if isinstance(assets, list) else assets.get("assets", [])
        want += [x["id"] for x in assets if x.get("caption")]
    merged, extra = {}, []
    for fn in sorted(os.listdir(a.work)):
        if re.fullmatch(r"trans_\d+\.json", fn):
            d = json.load(open(os.path.join(a.work, fn), encoding="utf-8"))
            for k, v in d.items():
                if k in merged and merged[k] != v:
                    print("conflict:", k, fn)
                merged[k] = v
    missing = [k for k in want if not str(merged.get(k, "")).strip()]
    extra = [k for k in merged if k not in want]
    json.dump(merged, open(os.path.join(a.work, "translations.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("merge: %d/%d 已译; missing=%d extra=%d -> translations.json" %
          (len(want) - len(missing), len(want), len(missing), len(extra)))
    if missing:
        print("missing ids:", missing[:20])
    if extra:
        print("extra ids:", extra[:20])


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("split", "merge"):
        p = sub.add_parser(name)
        p.add_argument("--work", required=True)
        p.add_argument("--parts", type=int, default=3)
    a = ap.parse_args()
    (cmd_split if a.cmd == "split" else cmd_merge)(a)


if __name__ == "__main__":
    main()
