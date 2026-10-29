# 安装 bilingual-dual-pdf 技能（Windows PowerShell）
#
# 用法:
#   .\install.ps1                    # 用户级 DSH: ~/.dsh/skills/，并自动装依赖
#   .\install.ps1 -Target project    # 项目级: ./.dsh/skills/
#   .\install.ps1 -Target claude     # ~/.claude/skills/
#   .\install.ps1 -Target core       # 用户级 + 写入 ~/.dsh/AGENTS.md 触发规则
#   .\install.ps1 -NoDeps            # 跳过自动安装 pypdfium2/Pillow
#   .\install.ps1 -Uninstall
param(
  [ValidateSet("user", "project", "claude", "core")]
  [string]$Target = "user",
  [switch]$Uninstall,
  [switch]$NoDeps
)

$ErrorActionPreference = "Stop"
$src  = Split-Path -Parent $MyInvocation.MyCommand.Path
$name = "bilingual-dual-pdf"

function Get-Dest([string]$t) {
  switch ($t) {
    "user"    { Join-Path $env:USERPROFILE ".dsh\skills\$name" }
    "project" { Join-Path (Get-Location) ".dsh\skills\$name" }
    "claude"  { Join-Path $env:USERPROFILE ".claude\skills\$name" }
    "core"    { Join-Path $env:USERPROFILE ".dsh\skills\$name" }
  }
}

# 优先使用 DSH 自带的 Python（agent 实际调用的那个），其次 PATH 上的 python
function Find-Python {
  $cands = @()
  $cands += (Join-Path $env:USERPROFILE ".dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe")
  $cands += (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe")
  $onPath = Get-Command python -ErrorAction SilentlyContinue
  if ($onPath) { $cands += $onPath.Source }
  foreach ($c in $cands) { if ($c -and (Test-Path $c)) { return $c } }
  return $null
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
Write-Host "[1/3] 已安装到: $dest"

# 依赖装进技能自带 _pylibs（脚本会自动加入 sys.path），不污染全局环境
if (-not $NoDeps) {
  $py = Find-Python
  if (-not $py) {
    Write-Warning "[2/3] 未找到 Python。请手动安装 Python 3.10+ 后执行:"
    Write-Warning "      python -m pip install --target `"$dest\_pylibs`" pypdfium2 Pillow"
  } else {
    $lib = Join-Path $dest "_pylibs"
    New-Item -ItemType Directory -Force -Path $lib | Out-Null
    Write-Host "[2/3] 安装依赖到 $lib"
    Write-Host "      使用: $py"
    & $py -m pip install --no-cache-dir --quiet --upgrade --target $lib pypdfium2 Pillow
    if ($LASTEXITCODE -ne 0) {
      Write-Warning "      自动安装失败，请手动执行:"
      Write-Warning "      & `"$py`" -m pip install --target `"$lib`" pypdfium2 Pillow"
    } else {
      $libf = $lib -replace '\\', '/'
      & $py -c "import sys;sys.path.insert(0,'$libf');import pypdfium2,PIL;print('      deps ok, Pillow',PIL.__version__)"
    }
  }
} else {
  Write-Host "[2/3] 跳过依赖安装 (-NoDeps)"
}

if ($Target -eq "core") {
  $agents = Join-Path $env:USERPROFILE ".dsh\AGENTS.md"
  $marker = "bilingual-dual-pdf"
  # 用数组拼装，避免 here-string 在部分 PowerShell 版本下的解析问题
  $ruleLines = @(
    '',
    '## 中英对照 / 双语 PDF —— 一律走 `bilingual-dual-pdf` skill',
    '',
    '当用户提供**一个 PDF** 并要求「中英对照 / 双语对照 / 左边英文右边中文 / 逐段对照」时，必须：',
    '1. 先加载 `bilingual-dual-pdf` 技能，按其五步流水线执行（extract → crop_assets → translate_chunks + subagent → mdgen/md2pdf → verify）；',
    '2. 默认 Markdown 后端，交付 `<主题>_中英对照.md` + `<主题>_中英对照.pdf`；',
    '3. 不把正文 dump 进对话，读图最多 1~2 张 contact sheet，翻译交给 subagent 并行。',
    '例外：扫描件（无文本层）需先 OCR。',
    ''
  )
  $rule = $ruleLines -join "`r`n"
  if ((Test-Path $agents) -and (Select-String -Path $agents -Pattern $marker -SimpleMatch -Quiet)) {
    Write-Host "[3/3] AGENTS.md 已包含规则，跳过"
  } else {
    Add-Content -Path $agents -Value $rule -Encoding UTF8
    Write-Host "[3/3] 已写入触发规则: $agents"
  }
} else {
  Write-Host "[3/3] 完成"
}

Write-Host ""
Write-Host "下一步：重启会话（技能列表出现 $name），然后对 agent 说："
Write-Host "  「用 $name 把这个 PDF 做成中英对照」"
