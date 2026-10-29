# 安装为 agent 技能（DSH / Claude Code / 通用）

本仓库本身就是一个"技能包"：入口为 `SKILL.md`，脚本在 `scripts/`。
不同宿主只是"把目录放到哪里被扫描"的差别。

## DSH（DeepSeek Harness）

| 位置 | 生效范围 |
|---|---|
| `~/.dsh/skills/bilingual-dual-pdf/` | 用户级，所有项目 |
| `<项目>/.dsh/skills/bilingual-dual-pdf/` | 仅当前项目 |

```powershell
# Windows
.\install.ps1                        # 默认装到 ~/.dsh/skills
.\install.ps1 -Target project        # 装到 ./.dsh/skills
.\install.ps1 -Target core           # 同时写入 ~/.dsh/AGENTS.md 的触发规则
.\install.ps1 -Uninstall
```

```bash
# macOS / Linux
./install.sh                         # 默认装到 ~/.dsh/skills
./install.sh --target project
./install.sh --target core
./install.sh --uninstall
```

> DSH 的技能格式：`<name>/SKILL.md`（YAML frontmatter 必须含 `name`、`description`）。
> 装好后重启会话或刷新技能列表即可看到 `bilingual-dual-pdf`。

## Claude Code

```powershell
.\install.ps1 -Target claude         # -> ~/.claude/skills/bilingual-dual-pdf
```
Claude Code 会扫描 `~/.claude/skills/*/SKILL.md`（同样要求 frontmatter）。

## 其他 / 手动

任何支持 "目录 + SKILL.md" 约定的宿主都可以直接：

```bash
git clone <repo> && cp -r bilingual-dual-pdf <你的技能目录>/
```

没有技能机制的宿主（例如普通 CLI 脚本调用）直接按 README 的快速开始跑脚本即可。

## 依赖

```bash
pip install -r requirements.txt
# 可选：pip install reportlab    （无 Chrome 时的兜底渲染器）
```

浏览器打印需要本地已安装 Chrome 或 Edge（脚本会自动找常见路径）。
LaTeX 后端额外需要 `xelatex` 或 `tectonic`，见 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)。

## 卸载

删除对应目录即可；若写过 `core` 规则，删掉 `~/.dsh/AGENTS.md` 中「中英对照 / 双语 PDF」那一段。
