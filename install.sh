#!/usr/bin/env bash
# 安装 bilingual-dual-pdf 技能（macOS / Linux）
#   ./install.sh                    用户级 DSH: ~/.dsh/skills/，并自动装依赖
#   ./install.sh --target project   项目级: ./.dsh/skills/
#   ./install.sh --target claude    ~/.claude/skills/
#   ./install.sh --target core      用户级 + 写入 ~/.dsh/AGENTS.md 触发规则
#   ./install.sh --no-deps          跳过依赖安装
#   ./install.sh --uninstall
set -euo pipefail

NAME="bilingual-dual-pdf"
TARGET="user"
UNINSTALL=0
NO_DEPS=0
for arg in "$@"; do
  case "$arg" in
    --target) shift ;;
    --target=*) TARGET="${arg#*=}" ;;
    project|user|claude|core) TARGET="$arg" ;;
    --no-deps) NO_DEPS=1 ;;
    --uninstall) UNINSTALL=1 ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
  esac
done

SRC="$(cd "$(dirname "$0")" && pwd)"
case "$TARGET" in
  user|core) DEST="$HOME/.dsh/skills/$NAME" ;;
  project)   DEST="$(pwd)/.dsh/skills/$NAME" ;;
  claude)    DEST="$HOME/.claude/skills/$NAME" ;;
  *) echo "unknown target: $TARGET" >&2; exit 2 ;;
esac

if [ "$UNINSTALL" = "1" ]; then
  rm -rf "$DEST"; echo "removed: $DEST"; exit 0
fi

mkdir -p "$DEST"
cp "$SRC/SKILL.md" "$DEST/"
for d in scripts templates references; do
  [ -d "$SRC/$d" ] && cp -R "$SRC/$d" "$DEST/"
done
echo "[1/3] installed: $DEST"

if [ "$NO_DEPS" = "0" ]; then
  PY=""
  for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1; then PY="$(command -v "$c")"; break; fi
  done
  if [ -z "$PY" ]; then
    echo "[2/3] python not found. run: python3 -m pip install --target \"$DEST/_pylibs\" pypdfium2 Pillow" >&2
  else
    echo "[2/3] installing deps into $DEST/_pylibs (using $PY)"
    mkdir -p "$DEST/_pylibs"
    if "$PY" -m pip install --no-cache-dir --quiet --upgrade --target "$DEST/_pylibs" pypdfium2 Pillow; then
      "$PY" -c "import sys;sys.path.insert(0,'$DEST/_pylibs');import pypdfium2,PIL;print('      deps ok, Pillow',PIL.__version__)"
    else
      echo "      auto-install failed. run:" >&2
      echo "      $PY -m pip install --target \"$DEST/_pylibs\" pypdfium2 Pillow" >&2
    fi
  fi
else
  echo "[2/3] skipped deps (--no-deps)"
fi

if [ "$TARGET" = "core" ]; then
  AGENTS="$HOME/.dsh/AGENTS.md"
  mkdir -p "$(dirname "$AGENTS")"
  if ! grep -q "bilingual-dual-pdf" "$AGENTS" 2>/dev/null; then
    cat >> "$AGENTS" <<'RULE'

## 中英对照 / 双语 PDF —— 一律走 `bilingual-dual-pdf` skill

当用户提供**一个 PDF** 并要求「中英对照 / 双语对照 / 左边英文右边中文 / 逐段对照」时，必须：
1. 先加载 `bilingual-dual-pdf` 技能，按其五步流水线执行（extract → crop_assets → translate_chunks + subagent → mdgen/md2pdf → verify）；
2. 默认 Markdown 后端，交付 `<主题>_中英对照.md` + `<主题>_中英对照.pdf`；
3. 不把正文 dump 进对话，读图最多 1~2 张 contact sheet，翻译交给 subagent 并行。
例外：扫描件（无文本层）需先 OCR。
RULE
    echo "[3/3] rule appended: $AGENTS"
  else
    echo "[3/3] AGENTS.md already contains the rule"
  fi
else
  echo "[3/3] done"
fi

echo ""
echo "next: restart your session, then ask the agent:"
echo "  \"use $NAME to make a bilingual version of this PDF\""
