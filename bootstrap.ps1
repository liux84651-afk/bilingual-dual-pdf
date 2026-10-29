# One-line installer for bilingual-dual-pdf (Windows PowerShell)
#
#   irm https://raw.githubusercontent.com/liux84651-afk/bilingual-dual-pdf/main/bootstrap.ps1 | iex
#
# With parameters:
#   $s = irm https://raw.githubusercontent.com/liux84651-afk/bilingual-dual-pdf/main/bootstrap.ps1
#   & ([scriptblock]::Create($s)) -Project      # install into ./.dsh/skills
#   & ([scriptblock]::Create($s)) -NoDeps       # skip dependency install
#   & ([scriptblock]::Create($s)) -Ref dev      # use another branch/tag
#
# NOTE: ASCII-only, no BOM (required for `irm | iex` on Windows PowerShell 5.1).
param(
  [string]$Repo = "liux84651-afk/bilingual-dual-pdf",
  [string]$Ref = "main",
  [switch]$Project,
  [switch]$NoDeps
)

$ErrorActionPreference = "Stop"
Write-Host "bilingual-dual-pdf bootstrap"
Write-Host "  repo: $Repo@$Ref"

$stamp = [guid]::NewGuid().ToString("N").Substring(0, 8)
$zip = Join-Path $env:TEMP "bdp-$stamp.zip"
$tmp = Join-Path $env:TEMP "bdp-$stamp"
$url = "https://github.com/$Repo/archive/refs/heads/$Ref.zip"

Write-Host "[1/3] downloading $url"
Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing
Expand-Archive -Path $zip -DestinationPath $tmp -Force

$src = Get-ChildItem $tmp -Directory | Select-Object -First 1
if (-not $src) { throw "extract failed: $tmp" }
$installer = Join-Path $src.FullName "install.ps1"
if (-not (Test-Path $installer)) { throw "install.ps1 not found in package" }

$target = if ($Project) { "project" } else { "user" }
Write-Host "[2/3] running installer (target=$target)"
$argList = @("-Target", $target, "-Source", $src.FullName)
if ($NoDeps) { $argList += "-NoDeps" }
# Run via scriptblock so ExecutionPolicy does not block the downloaded .ps1
$code = Get-Content -LiteralPath $installer -Raw
& ([scriptblock]::Create($code)) @argList

Write-Host "[3/3] cleaning temp files"
Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $zip -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Done. Restart your session; the skill list will show bilingual-dual-pdf."
Write-Host "Then drop a PDF and say: make it bilingual."
