#!/usr/bin/env bash
# Maika installer — bootstrap a venv and scaffold/update Maika into a target project.
#
# Usage: ./install.sh /path/to/your/project
set -euo pipefail

Maika_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$Maika_ROOT/.venv"

TARGET="${1:-}"
if [ -z "$TARGET" ]; then
  echo "Usage: ./install.sh /path/to/your/project"
  exit 1
fi
if [ ! -d "$TARGET" ]; then
  echo "❌ Target directory does not exist: $TARGET"
  exit 1
fi
TARGET="$(cd "$TARGET" && pwd)"
shift || true
EXTRA_INIT_ARGS=("$@")   # forwarded verbatim to `cli.maika init`

# Require python3 >= 3.9 (matches pyproject.toml requires-python).
if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ python3 not found. Please install Python 3.9 or newer."
  exit 1
fi
PY_VER="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
if [ "$(printf '%s\n' "3.9" "$PY_VER" | sort -V | head -1)" != "3.9" ]; then
  echo "❌ Python >= 3.9 required (found $PY_VER)."
  exit 1
fi

# Create the venv on first run and install dependencies.
if [ ! -d "$VENV" ]; then
  echo "→ Creating virtualenv at $VENV"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --quiet --upgrade pip
  "$VENV/bin/pip" install --quiet "jinja2>=3.1" "pyyaml>=6.0"
fi

PY="$VENV/bin/python"

# Install the maika CLI as an editable package and expose it on PATH.
# pyproject.toml declares the console script: maika = cli.maika:main
"$VENV/bin/pip" install --quiet -e "$Maika_ROOT"
mkdir -p "$HOME/.local/bin"
ln -sf "$VENV/bin/maika" "$HOME/.local/bin/maika"
echo "→ Installed 'maika' → $HOME/.local/bin/maika"
echo "  (ensure ~/.local/bin is on your PATH: export PATH=\"\$HOME/.local/bin:\$PATH\")"

# Route to update if Maika already installed, else init.
if [ -f "$TARGET/.agents/resolved-config.yaml" ] || \
   [ -f "$TARGET/.claude/resolved-config.yaml" ] || \
   [ -f "$TARGET/.maika/resolved-config.yaml" ]; then
  echo "→ Existing Maika install detected — updating."
  ( cd "$Maika_ROOT" && "$PY" -m cli.maika update --target "$TARGET" )
else
  echo "→ Fresh install."
  ( cd "$Maika_ROOT" && "$PY" -m cli.maika init --target "$TARGET" ${EXTRA_INIT_ARGS[@]+"${EXTRA_INIT_ARGS[@]}"} )
fi
