---
name: bilingual-dual-pdf
description: 把一篇论文/报告 PDF 做成"左原文 / 右译文"逐段严格对照的双语 PDF（图表、题注、脚注同排对照），并尽量少花 token。Use when the user asks for 中英对照 / 双语对照 PDF、side-by-side bilingual translation PDF、"左边英文右边中文" 排版，或要把一篇外文 PDF 逐段译成中文并对照排版。
---

# 双语逐段对照 PDF（省 token 版）

目标产物：**A4 纵向，左栏英文（或原文），右栏中文译文，每一行 = 一个原文段落**，两栏顶边对齐；
表格 / 插图在对应位置跨两栏居中，下方一行是"英文题注 | 中文题注"；脚注同样成对；参考文献原文照录。

## 0. 硬性省 token 规则（先读这条）

| 事项 | 规则 |
|---|---|
| 读图 | **全程最多 2 张图**：把全部页面压成 1~2 张 5×3 contact sheet（`verify.py --sheet 2`），只在发现具体缺陷时才单独读 1 页。禁止"读整页看看效果" |
| 正文 | **永远不把抽取的正文打印进对话**。`extract.py` 只输出 3 行统计；要核对用 `--show 3` 看前 3 段 |
| 脚本 | 用本 skill 自带脚本，**不要重新现场写排版引擎**（这一步最烧 token；上一版现场写 PDF 引擎花了 ~3 万 token，用 LaTeX 模板只要 ~1 千） |
| 翻译 | 用 subagent 并行（3 份），每个只给 chunk 文件路径 + 术语表；**不要在主对话里贴长译文** |
| 排查 | 每次只读命令输出的最后 20~30 行；用 `verify.py` 做机器校验，不靠肉眼 |
| 重跑 | 只重跑受影响的一步；抽取结果（segments/assets/translations）落盘复用 |

经验值：一篇 15 页双栏论文，整条流水线 **~8k–12k token**（上一版现场开发式做法约 30k+）。

## 1. 环境

- Python 3.10+
- 依赖 `pypdfium2`：`pip install -r requirements.txt`；或把已装好的 `_pylibs/` 放到技能根目录（脚本会自动加入 `sys.path`）
- 可选 `reportlab`（无浏览器/无 TeX 时的兜底渲染器）
- 排版后端三选一（见下方表格）
- 检查：`python -c "import pypdfium2"`；确认本机 Chrome/Edge 路径

## 2. 五步流水线

```powershell
$py = "C:\Users\LIUXINYU\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
$S  = "<skill 路径>\scripts"
$W  = "C:\dualwork"          # 工作目录：Markdown 后端无限制；LaTeX 后端要求 ASCII、无下划线
```

### 排版后端怎么选（默认 Markdown）

| 后端 | 命令 | 适用 | 状态 |
|---|---|---|---|
| **Markdown + Chrome 打印（默认）** | `mdgen.py` → `md2pdf.py` | 需要**可编辑源**、不装 TeX、快速出片 | ✅ 已验证（A4 29 页，严格双栏逐段对齐） |
| LaTeX（Tectonic / xelatex） | `build_tex.py --compile` | 出版级排版，可接受装 TeX | ⚠ 可选，见 §6（Tectonic 需 ASCII 路径 + 直接可用的 TTF） |
| reportlab canvas 引擎 | `references/reportlab-engine.py` | 无 Chrome、无 TeX 的纯离线兜底 | ✅ 已验证（27 页） |

Markdown 后端一次产出两份：`bilingual.md`（两列表格，可直接手改重排）+ `bilingual-md.pdf`（Chrome 打印）。

### 第 1 步：抽取 → segments_en.json
```powershell
& $py "$S\extract.py" --pdf "<源.pdf>" --out $W
```
输出 `segments_en.json`（`{id,kind,page,en}`）、`assets.json`（图表 bbox 初稿）、`outline.txt`（正文，供按需查阅）。
- 自动做：分栏切分、行聚类、段落/标题启发式、脚注（y<180 且不在图表框内）、图表框（Form XObject 落位 + 小字号块）。
- **只看它的 3 行统计**。章节标题顺序是否 1→2→2.1→… 单调，可用一行命令核对：
  `python -c "import json;print([s['en'][:24] for s in json.load(open('$W/segments_en.json')) if s['kind']=='h2'][:12])"`

### 第 2 步：裁图
```powershell
& $py "$S\crop_assets.py" --pdf "<源.pdf>" --work $W
```
若某张图/表切歪了（漏行、带上题注）：只改 `assets.json` 里那一条的 `x0/x1/y0/y1` 再跑 `--skip-existing` 之外的一遍。
`assets.json` 支持 `"after_segment": "p123"` 精确指定插入位置；否则按题注标签（Table 5 / Fig. 3）首次出现处自动插入。

### 第 3 步：翻译（交给 subagent）
```powershell
& $py "$S\translate_chunks.py" split --work $W --parts 3
#  spawn 3 个 subagent，各读 $W\chunk<i>.txt，写 $W\trans_<i>.json
& $py "$S\translate_chunks.py" merge --work $W
& $py "$S\verify.py" --work $W        # 机器校验覆盖率，缺译会列出 id
```
subagent prompt 要点（照抄）：
- 逐段译成**学术中文**；`<<id>>` 为段 id，输出 `{"p001":"……"}`；
- **保留**：`(Author, Year)`、数字/百分比/单位/URL/DOI、缩写（IPC/CPC/PATSTAT/NLP/SAO/EV/TFIDF/UMAP/HDBSCAN）、公式片段（`sim_i`、`s_i,j`、`∑m`）；
- 保留图表题注里的 `Table 1.` / `Fig. 3.` 标签；
- 术语表随任务给出（同一文件内统一）；
- 用 `write` 工具写 JSON；自查 key 集合与 chunk 一致。
- 若段文本本身是公式碎片（无实义），照抄原文即可。

### 第 4 步：排版（Markdown 默认路径）
```powershell
& $py "$S\mdgen.py"  --work $W --front-page 1          # -> $W\bilingual.md（两列表格）
& $py "$S\md2pdf.py" --md "$W\bilingual.md" --pdf "$W\bilingual-md.pdf"   # -> HTML -> Chrome 打印
```
- `--front-page 1`：第 1 页段落按"封面区"居中排（标题放大）。
- `mdgen.py` 的约定：普通行 `| 原文 | 译文 |`；**两端加粗** = 标题行；`<sup>` = 脚注行；`![]()` 独占一段 = 跨栏图；以 `Table/Fig./表/图` 开头的行 = 题注行。
- **图表插入锚点**：`assets.json` 里 `after_segment` 可精确指定；否则按题注标签（`Table 5` / `Fig. 3`）在正文中首次出现处插入——注意 `Fig.`/`Figure` 两种写法都要匹配，且标签要去掉结尾句点（`Table 1.` → `Table 1`），否则永远匹配不到（本 skill 已处理）。
- `md2pdf.py` 用 Chrome/Edge headless 打印：A4、1.3~1.4cm 边距、表格 50/50 两列、`vertical-align:top` 保证**逐段顶边对齐**、两端对齐；图片 `max-width:100%` 跨栏居中。
- 兜底：无 Chrome 时只生成 HTML，浏览器手动"打印为 PDF"即可。

### 第 4 步（可选）：LaTeX 出版级排版
```powershell
& $py "$S\build_tex.py" --work $W --title "<英文标题>" --front-page 1 --compile
```
- 需要 `xelatex` 或 `tectonic`；`--fonts-dir <ASCII目录>` 指定字体（见 §6）。
- 产物 `$W\dual.tex` → `dual.pdf`。

### 第 5 步：校验 + 一次人眼确认
```powershell
& $py "$S\verify.py" --work $W --pdf "$W\bilingual-md.pdf" --sheet 2
```
机器校验：Markdown 结构（若同时有 tex 也会查）、缺译、PDF 页数、中文文本层字符数、无中文的页。
然后**只看 1~2 张 contact sheet**（`$W\preview\sheet_*.png`），确认无错位/溢出即可交付。

## 3. 排版规则

### 3.1 Markdown + Chrome（默认，已验证）
- `table{table-layout:fixed}` + 两个 50% `td` + `vertical-align:top`：**一行=一个原文段落对，两格顶边对齐**，行高取较高者。
- `td{text-align:justify}` 两端对齐；`tr{page-break-inside:avoid}` 保证一段不被拆页。
- 标题行加粗放大；题注行 7.4pt；脚注 6.9pt；图片 `figure{margin:5pt 0}` 跨栏居中。
- 中文字体用系统 `SimSun`、西文 `Times New Roman`（CSS font-family 直接写即可，Chrome 会调用系统字体）。

### 3.2 LaTeX 模板（可选）
- `longtable` + 两个 `p{0.482\textwidth}` 列：同样一行一对、自动分页。
- 宏：`\dpara{EN}{ZH}`、`\dheadtwo`、`\dfoot`、`\dasset{图}{EN题注}{ZH题注}`。

## 4. 已知坑（都是上一版踩过的）

1. **双栏 + 通栏表/图交错**：表格文字按字号（≤7.4）识别后要按 y 区间从正文剔除，否则表格内容会混进正文段落。
2. **Table 延伸到页面底部 y<180**：会被误判成脚注 → 用"落在资产框内"优先排除。
3. **脚注本身也是双栏**：脚注行要先按列分组再成段，否则两栏文字交错成乱码。
4. **标题跨行**：`2. Technological similarity: … state of the` + `field` 要合并；但不要把下一个 `2.1.` 标题也吞进来（合并条件用"下一段短于 45 字符或小写开头"）。
5. **id 必须稳定**：抽取→人工修完结构后，翻译按 id 走；之后只改文字不改 id，**不要重新编号**，否则译文全错位。
6. **PDF 中文路径**：`pypdfium2` 打不开含中文的路径时，先把源 PDF 复制到 ASCII 路径。
7. **LaTeX 特殊字符**：`& % # _ $ { } ~ ^ \` 必须转义；图片路径不要有 `_` 和空格（脚本已自动处理）。
8. **参考文献**：不翻译时最稳的是"原文区域裁图 + 双语标题"，或单栏小字照录；不要硬译。
9. **图表锚点匹配（Markdown 后端）**：题注标签要脱敏——去结尾句点、`Figure`↔`Fig.` 双向兼容、`(?!\d)` 防止 `Fig. 1` 命中 `Fig. 10`。否则资产会全被追加到文末。
10. **Chrome 打印**：必须 `--user-data-dir=<临时目录>`，否则会和用户正在跑的 Chrome 抢配置；`--no-pdf-header-footer` 去掉页眉页脚；输出体积过小（<5KB）说明打印失败。

## 5. 交付

- 文件命名：`中英对照_<主题>_双语版.pdf`（Markdown 后端：`..._Markdown版.pdf` + 同名 `.md`）
- 汇报里说明：页数、对照方式（逐段顶对齐）、图表/脚注/参考文献的处理方式、以及"公式行两侧一致、未翻译"的说明。
- 产物目录：`$W\`（segments / assets / translations / bilingual.md / bilingual-md.pdf）——改完 MD 只要重跑 `md2pdf.py` 即可重出 PDF。

## 6. 可选：LaTeX / 兜底引擎

**Tectonic（免安装 xelatex，已实测可跑）**
```powershell
# 1) 下载解压 tectonic.exe 到 <work 同级>\bin（单文件，无需 UAC）
# 2) 字体：必须放 ASCII 目录并**相对路径**引用；Tectonic 只接受可解析的外部字体文件
#    已实测：simhei.ttf（原始 TTF）✅ ；simsun.ttc ❌（需 ttc2ttf.py 转换，转换结果 XeTeX 会报 "font cannot be found"）
# 3) 编译
$env:TECTONIC_CACHE_DIR="C:\tex_cache";   # 目录必须 ASCII
tectonic.exe -X compile dual.tex --keep-logs --outdir out
```
坑：① 工作目录/缓存/输出目录**不能含中文**（否则 `os error 5 / 123`）；② `\setCJKmainfont[Path=fonts/]{x.ttf}` 用**相对路径**，绝对路径会生成 `[...]/OT` 报错；③ `ctexart` 默认 `fontset` 会抢先加载系统字体，要写 `\documentclass[fontset=none]{ctexart}` 再自己设字体。

**reportlab 兜底**：`references/reportlab-engine.py`（无 Chrome / 无 TeX 时可用，已实测 27 页）。
