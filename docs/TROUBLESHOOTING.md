# 排错手册

## 1. 抽取阶段

| 现象 | 原因 | 处理 |
|---|---|---|
| 段落两栏文字交错成乱码 | 脚注/表格本身也是双栏，先合并再成段 | 先按列分组再调 `paragraphs()`（本仓库已实现） |
| 表格内容混进正文 | 表格文字字号与正文接近，没被识别为资产 | 收紧 `assets.json` 的 bbox，或降低"小字号"阈值 |
| 表格尾部跑到脚注里 | 表格延伸到 y<180 | 判定顺序改为"落在资产框内优先排除" |
| 标题被下一个标题吞掉 | 跨行标题合并条件过宽 | 只在"下一段 < 45 字符或小写开头"时合并 |
| `pypdfium2` 打不开 PDF | 路径含中文/特殊字符 | 先复制到 ASCII 路径（`C:\work\source.pdf`） |
| 抽取结果为空 | 扫描件，无文本层 | 需要先 OCR（本工具不含） |

## 2. 裁图 / 资产

- `crop_assets.py` 的坐标是 PDF 坐标（左下原点，y 向上）；写错方向会裁到空白。
- 图表框太小/太大：改 `assets.json` 单条 `x0/x1/y0/y1`，重跑即可（`--skip-existing` 可只补缺的）。
- 图片被复制到临时目录并按哈希命名（`md2pdf`/`build_tex` 自动做），避免 LaTeX/浏览器对中文路径、下划线敏感。

## 3. Markdown → PDF

| 现象 | 处理 |
|---|---|
| 图表全被追加到文末 | 题注锚点没匹配：标签要**去掉结尾句点**，`Fig.`↔`Figure` 双向兼容，`(?!\d)` 防 `Fig. 1` 命中 `Fig. 10` |
| 输出 PDF < 5KB / 空白 | Chrome 打印失败：检查浏览器路径、`--user-data-dir` 临时目录、页面是否加载完（`--virtual-time-budget`） |
| 中文变方块 | 系统缺中文字体（Windows 自带 SimSun；Linux 装 `fonts-noto-cjk`） |
| 一段被拆到两页 | 检查 `tr { page-break-inside: avoid }` 是否被自定义 CSS 覆盖 |
| 左右不齐 | 确认 `table-layout: fixed` + `td { vertical-align: top }` + 两列等宽 |

## 4. LaTeX 后端（可选，坑最多）

### 4.1 xelatex（TeX Live / MiKTeX）

```bash
xelatex -interaction=nonstopmode dual.tex   # 跑两遍
```

- 必须能加载 CJK 字体：`ctex` 默认用系统字体（Windows 下 `fontset=windows`）；
  Linux/macOS 需先装中文字体并 `\setCJKmainfont{...}`。
- 路径不要有下划线/空格/中文；图片脚本已复制到安全目录。

### 4.2 Tectonic（免安装，推荐给 CI）

```powershell
$env:TECTONIC_CACHE_DIR="C:\tex_cache"        # 必须是 ASCII 路径
tectonic.exe -X compile dual.tex --keep-logs --outdir out
```

实测结论：

- ❌ **中文路径 / 中文缓存目录** → `os error 5`(拒绝访问)、`os error 123`(路径语法错误)
- ✅ 外部字体必须用**相对路径**：`\setmainfont[Path=fonts/]{times.ttf}`；
  写成绝对路径会生成 `[...]/OT` 解析错误
- ✅ `simhei.ttf`、`times*.ttf` 这类**单字体 TTF** 可直接用
- ❌ `simsun.ttc`（字体集合）不可用；`scripts/ttc2ttf.py` 转出的 TTF 仍可能被 XeTeX 拒绝
  （`The font "simsun" cannot be found`）→ 建议改用 Noto Serif SC / 思源宋体 OTF
- ⚠ `ctexart` 默认 `fontset` 会抢先加载系统字体，需 `\documentclass[fontset=none]{ctexart}` 再自己设

## 5. 校验阶段

```bash
python scripts/verify.py --work work --pdf work/bilingual-md.pdf --sheet 2
```

- 报"缺译 N 段"：把列出的 id 补进 `translations.json`（或在 `trans_N.json` 里补）
- 报"pages_without_cjk"：通常是参考文献图页、纯图页——正常
- 缩略图 `work/preview/sheet_*.png`：只看这个，不要逐页读大图（省 token）
