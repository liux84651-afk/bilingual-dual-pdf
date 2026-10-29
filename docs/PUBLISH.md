# 发布到 GitHub

仓库目录已经准备好（含 `.gitignore`、CI、示例、预览图），只差推送。共 3 步。

## 方式 A：装好 Git 后手动推送（推荐）

### 1. 初始化并提交

```bash
cd bilingual-dual-pdf
git init -b main
git add .
git commit -m "feat: bilingual dual-PDF skill v0.1.0"
```

### 2. 在 GitHub 建一个空仓库

- 打开 https://github.com/new
- Repository name：`bilingual-dual-pdf`
- 选 **Public**，**不要**勾选 "Add a README / .gitignore / license"（避免冲突）
- 创建后复制仓库地址

### 3. 推送

```bash
git remote add origin https://github.com/<你的用户名>/bilingual-dual-pdf.git
git push -u origin main
git tag -a v0.1.0 -m "first public release" && git push --tags
```

> 首次推送会要求登录：用 **GitHub Personal Access Token**（Settings → Developer settings →
> Personal access tokens → Fine-grained tokens，权限勾 `Contents: Read and write`）作为密码；
> 或安装 GitHub CLI 后 `gh auth login`，再用 `gh repo create --public --source=. --push`。

## 方式 B：GitHub Desktop（不想碰命令行）

1. File → Add local repository → 选中本目录
2. 它会提示 "create a repository" → 创建
3. Publish repository → 取消 "Keep this code private"

## 方式 C：先给别人一个 zip

```powershell
Compress-Archive -Path .\bilingual-dual-pdf\* -DestinationPath .\bilingual-dual-pdf-v0.1.0.zip
```

对方解压后：`pip install pypdfium2` → 按 README 快速开始即可；作为技能用则
`./install.ps1`（Windows）或 `./install.sh`（macOS/Linux）。

## 发布前检查清单

- [ ] `LICENSE` 里的 `<YOUR NAME>` 换成你的名字/ID
- [ ] `README.md` 顶部预览图 `docs/preview.png` 正常显示
- [ ] `SKILL.md` frontmatter 的 `description` 能让人一眼看懂用途
- [ ] 仓库里**没有**含版权的论文原文/译文（`examples/demo` 全是合成内容）
- [ ] `.gitignore` 生效（不会把 `work/`、`_pylibs/`、`*.log` 提交上去）
- [ ] Actions 跑通（push 后在 Actions 页看 CI）

## 仓库建议设置

| 项 | 建议 |
|---|---|
| About / 描述 | `Side-by-side bilingual PDF from any PDF — row-aligned, low token cost` |
| Topics | `pdf`, `translation`, `bilingual`, `llm`, `agent-skill`, `markdown`, `latex` |
| Releases | 打 `v0.1.0` tag，附 zip |
| License | MIT（如需其他协议，改 `LICENSE` 与 README 末尾） |
