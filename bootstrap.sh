#!/usr/bin/env bash
# 一行式安装（macOS / Linux）
#
#   curl -fsSL https://raw.githubusercontent.com/liux84651-afk/bilingual-dual-pdf/main/bootstrap.sh | bash
#
# 参数：
#   ... | bash -s -- --project      # 装到当前项目 ./.dsh/skills
#   ... | bash -s -- --no-deps      # 不自动装依赖
#   ... | bash -s -- --ref dev      # 指定分支/标签
set -euo pipefail

REPO="liux84651-afk/bilingual-dual-pdf"
REF="main"
TARGET="user"
DEPS=""

while [ $# -gt 0 ]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --ref) REF="$2"; shift 2 ;;
    --project) TARGET="project"; shift ;;
    --no-deps) DEPS="--no-deps"; shift ;;
    *) shift ;;
  esac
done

echo "bilingual-dual-pdf bootstrap"
echo "  repo: $REPO@$REF"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
URL="https://github.com/$REPO/archive/refs/heads/$REF.tar.gz"

echo "[1/3] downloading $URL"
if command -v curl >/dev/null 2>&1; then
  curl -fsSL "$URL" | tar -xz -C "$TMP"
else
  wget -qO- "$URL" | tar -xz -C "$TMP"
fi

SRC="$(find "$TMP" -maxdepth 1 -mindepth 1 -type d | head -n 1)"
[ -n "$SRC" ] || { echo "extract failed: $TMP" >&2; exit 1; }
[ -f "$SRC/install.sh" ] || { echo "install.sh missing in package" >&2; exit 1; }

echo "[2/3] running installer (target=$TARGET)"
# shellcheck disable=SC2086
bash "$SRC/install.sh" --target "$TARGET" $DEPS

echo "[3/3] done"
echo
echo "restart your session, then drop a PDF and say: make it bilingual (中英对照)"
