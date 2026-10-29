# 工作流与数据契约

五个阶段，每阶段产物落盘，可单独重跑。

## 目录契约

```
work/
  segments_en.json     # [{id, kind, page, en}]  kind: title/authors/affil/meta/doi/kw/abstract/h1/h2/para/footnote/asset
  assets.json          # [{id, page, x0,x1,y0,y1, caption, png?, after_segment?}]
  assets/*.png         # 裁好的图表（288 dpi）
  chunk1..N.txt        # 翻译分块（<<id>>原文）
  trans_1..N.json      # {id: 译文}
  translations.json    # 合并结果（含图表题注）
  bilingual.md         # 两列表格：| 原文 | 译文 |
  bilingual.html       # md2pdf 中间产物（可手动改 CSS 再打印）
  bilingual-md.pdf     # 成品
  dual.tex / dual.pdf  # LaTeX 后端的产物（可选）
  preview/sheet_*.png  # 校验用缩略图
```

## 1. 抽取 `extract.py`

- 页面顺序：走 `/Pages` 树（不依赖硬编码页码）
- 文本：自研解析（zlib + ToUnicode + 内容流 + CTM），得到每个 run 的 `x, y, 宽度, 字号, 粗体`
- 分栏：按 x0 直方图找中间区域最大空隙
- 行：按 y 聚类（容差 0.4×字号），按 x 排序拼接，用真实字宽判断是否补空格
- 段：缩进 > 4pt、行距 > 1.45 倍、或上级是标题 → 新段；行尾连字符去掉后拼接
- 标题：粗体，或匹配 `^\d+(\.\d+)*\.?\s+[A-Z]`
- 脚注：字号 ≤ 7.3 且 y < 180，**且不在图表框内**
- 图表框：Form XObject 的 BBox×Matrix×CTM 求实际落位；小字号行聚成"表格块"
- 首页（题名/摘要）不做资产排除，交给人工重整为封面区（`--front-page 1`）

> 只打印 3 行统计；正文写 `outline.txt`。**永远不要把它打印进对话。**

## 2. 裁图 `crop_assets.py`

`assets.json` 的 `x0/x1/y0/y1` 是 PDF 坐标（y 向上）。脚本按 `--scale 4`（288 dpi）渲染整页再裁剪。
`after_segment` 可指定插入位置，否则按题注标签在正文中首次出现处插入。

## 3. 翻译 `translate_chunks.py`

- `split --parts 3`：按字符数均衡切块，输出 `chunkN.txt`
- 每个 subagent 只拿到自己那份 + 术语表，回写 `trans_N.json`
- `merge`：合并所有 `trans_*.json`，比对 `segments_en.json` 的 id 集合，列出 missing / extra / 冲突

术语表与保留规则（引用、数字、缩写、公式片段）写在 `SKILL.md` 里，直接复制给 subagent。

## 4. 排版

### 4.1 Markdown + 浏览器（默认）

`mdgen.py` 生成两列表格（约定见 SKILL.md §2 第 4 步），`md2pdf.py` 转 HTML 后用 Chrome headless 打印：

```css
@page { size: A4; margin: 14mm 13mm; }
table { width:100%; table-layout:fixed; border-collapse:collapse; }
td    { width:50%; vertical-align:top; text-align:justify; }
tr    { page-break-inside:avoid; }
```

`vertical-align:top` + `table-layout:fixed` = 一行两格顶边对齐；`page-break-inside:avoid` = 一段不跨页。

### 4.2 LaTeX（可选）

`build_tex.py` 生成 `longtable` + 两个 `p{0.482\textwidth}` 列；图片复制到无特殊字符目录并按哈希命名。

## 5. 校验 `verify.py`

机器校验替代肉眼：Markdown/TeX 结构、缺译 id、PDF 页数、中文文本层字符数、无中文的页；
`--sheet 2` 只渲染 2 张 5×3 缩略图供人眼确认。

## 常见改造点

| 需求 | 改哪里 |
|---|---|
| 调字号/行距/边距 | `md2pdf.py` 的 `CSS` 字符串 |
| 改标题层级样式 | `md2pdf.py` 的 `tr.head td` |
| 表格/图跨栏宽度 | `figure img { max-width }` / `max-height` |
| 中文字体 | CSS `font-family`（Chrome 用系统字体） |
| 段落切分策略 | `extract.py` 的 `paragraphs()` |
| 图表框识别 | `extract.py` 中小字号块聚类阈值 |
