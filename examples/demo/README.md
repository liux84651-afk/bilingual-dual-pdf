# Demo（全合成数据，不含任何受版权保护的内容）

用 10 段假文本演示整条 Markdown 后端流水线；输出见同目录 `bilingual.md` 与 `bilingual-demo.pdf`。

```bash
# 1) 重新生成示例表格图（Pillow）
python make_demo.py

# 2) 生成 Markdown（封面区居中、图表按锚点插入）
python ../../scripts/mdgen.py --work . --front-page 1 --out bilingual.md

# 3) 打印成 PDF（需要本机 Chrome/Edge）
python ../../scripts/md2pdf.py --md bilingual.md --pdf bilingual-demo.pdf

# 4) 校验
python ../../scripts/verify.py --work . --pdf bilingual-demo.pdf
```

文件说明：

| 文件 | 作用 |
|---|---|
| `segments_en.json` | 相当于 `extract.py` 的产出（这里手写，模拟抽取结果） |
| `translations.json` | 译文（含图表题注 `D01`） |
| `assets.json` + `assets/demo_table.png` | 一张合成表格图 + 双语题注 |
| `bilingual.md` | 产物：两列表格，可直接手改 |
| `bilingual-demo.pdf` | 产物：A4 双语对照 PDF |

> 真实流程里 `segments_en.json` / `assets.json` 由 `extract.py` + `crop_assets.py` 从你的 PDF 自动生成，
> 你只需要提供 `translations.json`（或交给 subagent）。
