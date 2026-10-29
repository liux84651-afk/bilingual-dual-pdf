# -*- coding: utf-8 -*-
"""从 TTC 字体集合中导出单个 TrueType 字体（无需 fontTools）。

XeLaTeX / Tectonic 用文件路径引用字体时，.ttc 集合容易出问题（FontIndex 支持不一致）。
本工具把 ttc 中第 N 个字体重建成独立 .ttf，供 fontspec 的 Path/Extension 方式加载。

用法: python ttc2ttf.py simsun.ttc out\simsun.ttf [--index 0]
"""
import argparse, struct, sys


def read_ttc(data, index):
    tag = data[:4]
    if tag != b"ttcf":
        # 已是单字体
        return data
    ver, num = struct.unpack(">II", data[4:12])
    offs = struct.unpack(">%dI" % num, data[12:12 + 4 * num])
    if index >= num:
        raise SystemExit("index out of range: %d >= %d" % (index, num))
    return data[offs[index]:]


def sfnt_tables(font):
    ver, numTables = struct.unpack(">IH", font[0:6])
    tables = []
    for i in range(numTables):
        off = 12 + 16 * i
        tag, chk, toff, tlen = struct.unpack(">4sIII", font[off:off + 16])
        tables.append((tag, chk, toff, tlen))
    return ver, tables


def build_ttf(font, drop=()):
    ver, tables = sfnt_tables(font)
    tables = [t for t in tables if t[0] not in drop]
    n = len(tables)
    # 搜索参数
    entry = 1
    while entry * 2 <= n:
        entry *= 2
    search = entry * 16
    rng = search * 2 - 16
    esel = entry.bit_length() - 1
    out = bytearray(struct.pack(">IHHHH", ver, n, search, esel, rng))
    dir_off = 12
    data_off = 12 + 16 * n
    body = bytearray()
    records = bytearray()
    for tag, chk, toff, tlen in tables:
        off = data_off + len(body)
        records += struct.pack(">4sIII", tag, chk, off, tlen)
        chunk = font[toff:toff + tlen]
        body += chunk
        pad = (-len(body)) % 4
        body += b"\0" * pad
    out += records + body
    return bytes(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--index", type=int, default=0)
    a = ap.parse_args()
    data = open(a.src, "rb").read()
    font = read_ttc(data, a.index)
    ttf = build_ttf(font)
    open(a.dst, "wb").write(ttf)
    print("ok: %s (%d bytes, index=%d)" % (a.dst, len(ttf), a.index))


if __name__ == "__main__":
    main()
