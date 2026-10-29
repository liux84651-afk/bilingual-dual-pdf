# 一行式安装（Windows PowerShell）
#
#   irm https://raw.githubusercontent.com/liux84651-afk/bilingual-dual-pdf/main/bootstrap.ps1 | iex
#
# 也可加参数：
#   $s = irm .../bootstrap.ps1; & ([scriptblock]::Create($s)) -Project      # 装到当前项目 ./.dsh/skills
#   ... -NoDeps                                                             # 不自动装依赖
#   ... -Ref dev                                                            # 指定分支/标签
param(
  [string]$Repo = "liux84651-afk/bilingual-dual-pdf",
  [string]$Ref = "main",
  [switch]$Project,
  [switch]$NoDeps
)

$ErrorActionPreference = "Stop"
Write-Host "bilingual-dual-pdf bootstrap"
Write-Host "  repo: $Repo@$Ref"

$zip = Join-Path $env:TEMP "bdp-$([guid]::NewGuid().ToString('N').Substring(0,8)).zip"
$tmp = Join-Path $env:TEMP "bdp-$([guid]::NewGuid().ToString('N').Substring(0,8))"
$url = "https://github.com/$Repo/archive/refs/heads/$Ref.zip"

Write-Host "[1/3] 下载 $url"
Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing
Expand-Archive -Path $zip -DestinationPath $tmp -Force

$src = Get-ChildItem $tmp -Directory | Select-Object -First 1
if (-not $src) { throw "解压失败：$tmp" }
$installer = Join-Path $src.FullName "install.ps1"
if (-not (Test-Path $installer)) { throw "包里没有 install.ps1：$($src.FullName)" }

$target = if ($Project) { "project" } else { "user" }
Write-Host "[2/3] 运行安装脚本 (target=$target)"
$args = @("-Target", $target)
if ($NoDeps) { $args += "-NoDeps" }
& $installer @args

Write-Host "[3/3] 清理临时文件"
Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $zip -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "安装完成。重启会话后，技能列表里会出现 bilingual-dual-pdf。"
Write-Host "然后直接丢一个 PDF 给它，说：「把这个 PDF 做成中英对照」。"
