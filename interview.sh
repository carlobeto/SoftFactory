#!/usr/bin/env bash
# Script para ejecutar la sesión interactiva de Grill-Me (Fase 0: Requirements Discovery)
set -e
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$ROOT_DIR/orchestrator.py" --interview "$@"
