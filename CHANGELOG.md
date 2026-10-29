# Changelog

## 0.1.2

修复「一行式安装」在 Windows PowerShell 5.1 下不可用的问题。

- `.ps1` 改为 **ASCII-only、无 BOM**：`irm .../bootstrap.ps1 | iex` 不再因 BOM 字符导致 `param()` 解析失败
- 安装脚本提示信息改为英文（中文文档保留在 README / docs / install.sh）
- 依赖安装仍然自动进行（装进 `<skill>/_pylibs`）

## 0.1.1

一行式安装 + 可移植性修复。

- 新增 `bootstrap.ps1` / `bootstrap.sh`：一条命令完成下载 → 安装 → 装依赖（`irm ... | iex` / `curl ... | bash`）
- `install.ps1` / `install.sh` 自动把 `pypdfium2`、`Pillow` 装进技能自带 `_pylibs`（不再要求找对解释器）
- 修复 `.ps1` 中文编码问题（改为 UTF-8 with BOM，Windows PowerShell 5.1 可正常解析）
- 移除脚本中硬编码的开发者路径（`render_pdf.py`、`contact_sheet.py`、`pdfcore.py`、`reportlab-engine.py`
  改为基于 cwd / 脚本目录）
- README：加 CI / License / Python 徽章、"一行安装"与"没有 AI agent 怎么办"章节
- LICENSE 填入作者；新增 `.gitattributes` 的 `*.ps1 eol=crlf`

## 0.1.0

首个公开版本。

- 抽取：纯 Python PDF 解析（FlateDecode / ToUnicode / 内容流 / CTM），自动识别双栏、标题、脚注、表格块、图片落位
- 裁图：pypdfium2 288 dpi，按 `assets.json` bbox 裁剪，支持 `after_segment` 精确插入
- 翻译：chunk 切分 → 多 subagent 并行 → 合并并校验 id 覆盖
- 排版：
  - Markdown 两列表格 + Chrome/Edge headless 打印（默认，实测 29 页 A4）
  - LaTeX `longtable` 模板 + Tectonic/xelatex（可选）
  - reportlab canvas 引擎（无浏览器/无 TeX 兜底，实测 27 页）
- 校验：结构 + 缺译 + PDF 文本层 + 1~2 张 contact sheet
- 安装：`install.ps1` / `install.sh`（DSH 用户级/项目级、Claude Code、写入全局触发规则）
