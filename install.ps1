# 安装 bilingual-dual-pdf 技能（Windows PowerShell）
# 用法:
#   .\install.ps1                    # 用户级 DSH: ~/.dsh/skills/
#   .\install.ps1 -Target project    # 项目级: ./.dsh/skills/
#   .\install.ps1 -Target claude     # ~/.claude/skills/
#   .\install.ps1 -Target core       # 装用户级 + 写入 ~/.dsh/AGENTS.md 触发规则
#   .\install.ps1 -Uninstall
param(
  [ValidateSet("user", "project", "claude", "core")]
  [string]$Target = "user",
  [switch]$Uninstall
)

$ErrorActionPreference = "Stop"
$src = Split-Path -Parent $MyInvocation.MyCommand.Path
$name = "bilingual-dual-pdf"

function Get-Dest([string]$t) {
  switch ($t) {
    "user"    { Join-Path $env:USERPROFILE ".dsh\skills\$name" }
    "project" { Join-Path (Get-Location) ".dsh\skills\$name" }
    "claude"  { Join-Path $env:USERPROFILE ".claude\skills\$name" }
    "core"    { Join-Path $env:USERPROFILE ".dsh\skills\$name" }
  }
}

$dest = Get-Dest $Target
if ($Uninstall) {
  if (Test-Path $dest) { Remove-Item $dest -Recurse -Force; Write-Host "已移除: $dest" }
  else { Write-Host "未安装: $dest" }
  exit 0
}

New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item (Join-Path $src "SKILL.md") $dest -Force
foreach ($d in @("scripts", "templates", "references")) {
  $p = Join-Path $src $d
  if (Test-Path $p) { Copy-Item $p $dest -Recurse -Force }
}
Write-Host "已安装到: $dest"

if ($Target -eq "core") {
  $agents = Join-Path $env:USERPROFILE ".dsh\AGENTS.md"
  $marker = "bilingual-dual-pdf"
  $rule = @"
## 中英对照 / 双语 PDF —— 一律走 ``bilingual-dual-pdf`` skill

当用户提供**一个 PDF** 并要求「中英对照 / 双语对照 / 左边英文右边中文 / 逐段对照」时，必须：
1. 先加载 ``bilingual-dual-pdf`` 技能，按其五步流水线执行（extract → crop_assets → translate_chunks + subagent → mdgen/md2pdf → verify）；
2. 默认 Markdown 后端，交付 ``<主题>_中英对照.md`` + ``<主题>_中英对照.pdf``；
3. 不把正文 dump 进对话，读图最多 1~2 张 contact sheet，翻译交给 subagent 并行。
例外：扫描件（无文本层）需先 OCR。
"@
  if ((Test-Path $agents) -and (Select-String -Path $agents -Pattern $marker -SimpleMatch -Quiet)) {
    Write-Host "AGENTS.md 已包含规则，跳过"
  } else {
    Add-Content -Path $agents -Value "`n$rule" -Encoding UTF8
    Write-Host "已写入触发规则: $agents"
  }
}

Write-Host "重启会话 / 刷新技能列表后即可使用（技能名: $name）"
