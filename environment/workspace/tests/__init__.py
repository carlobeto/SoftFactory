"""Test package for weather_tool."""

import sys
from pathlib import Path

# Garantizar que el directorio raíz de workspace esté en sys.path
WORKSPACE_DIR = Path(__file__).resolve().parent.parent
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))
