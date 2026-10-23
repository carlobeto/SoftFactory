#!/usr/bin/env bash
# Script para limpiar y reiniciar el ambiente de producción de la Software Factory
set -e
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$ROOT_DIR/orchestrator.py" --reset "$@"
