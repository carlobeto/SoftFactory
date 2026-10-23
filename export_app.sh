#!/usr/bin/env bash
# Script para rescatar y exportar la aplicación generada actualmente en la Software Factory
set -e
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$ROOT_DIR/orchestrator.py" --export "$@"
