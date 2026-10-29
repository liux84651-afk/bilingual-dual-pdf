# Install the bilingual-dual-pdf skill (Windows PowerShell)
#
# Usage:
#   .\install.ps1                    # user-level DSH: ~/.dsh/skills/ + auto deps
#   .\install.ps1 -Target project    # project-level: ./.dsh/skills/
#   .\install.ps1 -Target claude     # ~/.claude/skills/
#   .\install.ps1 -Target core       # user-level + append trigger rule to ~/.dsh/AGENTS.md
#   .\install.ps1 -NoDeps            # skip pypdfium2/Pillow auto-install
#   .\install.ps1 -Uninstall
#
# NOTE: this file is intentionally ASCII-only (no BOM) so that
#       `irm .../bootstrap.ps1 | iex` works in Windows PowerShell 5.1.
param(
  [ValidateSet("user", "project", "claude", "core")]
  [string]$Target = "user",
  [switch]$Uninstall,
  [switch]$NoDeps,
  [string]$Source = ""
)

$ErrorActionPreference = "Stop"
# When run from a file, use the script directory; bootstrap passes -Source explicitly.
if ($Source) { $src = $Source } else { $src = Split-Path -Parent $MyInvocation.MyCommand.Path }
$name = "bilingual-dual-pdf"

function Get-Dest([string]$t) {
  switch ($t) {
    "user"    { Join-Path $env:USERPROFILE ".dsh\skills\$name" }
    "project" { Join-Path (Get-Location) ".dsh\skills\$name" }
    "claude"  { Join-Path $env:USERPROFILE ".claude\skills\$name" }
    "core"    { Join-Path $env:USERPROFILE ".dsh\skills\$name" }
  }
}

# Prefer the Python bundled with DSH (the one the agent actually calls), then PATH python.
function Find-Python {
  $cands = @()
  $cands += (Join-Path $env:USERPROFILE ".dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe")
  $cands += (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe")
  $cands += (Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe")
  $onPath = Get-Command python -ErrorAction SilentlyContinue
  if ($onPath) { $cands += $onPath.Source }
  foreach ($c in $cands) { if ($c -and (Test-Path $c)) { return $c } }
  return $null
}

$dest = Get-Dest $Target
if ($Uninstall) {
  if (Test-Path $dest) { Remove-Item $dest -Recurse -Force; Write-Host "removed: $dest" }
  else { Write-Host "not installed: $dest" }
  exit 0
}

New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item (Join-Path $src "SKILL.md") $dest -Force
foreach ($d in @("scripts", "templates", "references")) {
  $p = Join-Path $src $d
  if (Test-Path $p) { Copy-Item $p $dest -Recurse -Force }
}
Write-Host "[1/3] installed to: $dest"

# Dependencies go into <skill>/_pylibs (scripts add it to sys.path); no global env changes.
if (-not $NoDeps) {
  $py = Find-Python
  if (-not $py) {
    Write-Warning "[2/3] Python not found. Install Python 3.10+ then run:"
    Write-Warning "      python -m pip install --target `"$dest\_pylibs`" pypdfium2 Pillow"
  } else {
    $lib = Join-Path $dest "_pylibs"
    New-Item -ItemType Directory -Force -Path $lib | Out-Null
    Write-Host "[2/3] installing deps into $lib"
    Write-Host "      python: $py"
    & $py -m pip install --no-cache-dir --quiet --upgrade --target $lib pypdfium2 Pillow
    if ($LASTEXITCODE -ne 0) {
      Write-Warning "      auto-install failed. run manually:"
      Write-Warning "      & `"$py`" -m pip install --target `"$lib`" pypdfium2 Pillow"
    } else {
      $libf = $lib -replace '\\', '/'
      & $py -c "import sys;sys.path.insert(0,'$libf');import pypdfium2,PIL;print('      deps ok, Pillow',PIL.__version__)"
    }
  }
} else {
  Write-Host "[2/3] skipped deps (-NoDeps)"
}

if ($Target -eq "core") {
  $agents = Join-Path $env:USERPROFILE ".dsh\AGENTS.md"
  $marker = "bilingual-dual-pdf"
  $ruleLines = @(
    '',
    '## Bilingual PDF requests: always use the `bilingual-dual-pdf` skill',
    '',
    'When the user provides a PDF and asks for a bilingual / side-by-side version, you MUST:',
    '1. load the `bilingual-dual-pdf` skill and follow its 5-step pipeline (extract -> crop_assets -> translate_chunks + subagent -> mdgen/md2pdf -> verify);',
    '2. default to the Markdown backend and deliver a .md source + .pdf result;',
    '3. never dump the extracted body text into the conversation, read at most 1-2 contact sheets, and delegate translation to subagents.',
    'Exception: scanned PDFs without a text layer need OCR first.',
    ''
  )
  $rule = $ruleLines -join "`r`n"
  if ((Test-Path $agents) -and (Select-String -Path $agents -Pattern $marker -SimpleMatch -Quiet)) {
    Write-Host "[3/3] AGENTS.md already contains the rule, skipped"
  } else {
    Add-Content -Path $agents -Value $rule -Encoding UTF8
    Write-Host "[3/3] appended trigger rule: $agents"
  }
} else {
  Write-Host "[3/3] done"
}

Write-Host ""
Write-Host "Next: restart your session (skill list shows $name), then tell the agent:"
Write-Host "  `"use $name to make a bilingual version of this PDF`""
