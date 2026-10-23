#!/usr/bin/env bash
# Script para iniciar el Dashboard de la Software Factory en http://localhost:5000
set -e
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$ROOT_DIR/.venv/bin/python3" ]; then
    PYTHON_BIN="$ROOT_DIR/.venv/bin/python3"
else
    PYTHON_BIN="python3"
fi

exec "$PYTHON_BIN" "$ROOT_DIR/tools/dashboard/run.py" "$@"
