# Changelog

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
