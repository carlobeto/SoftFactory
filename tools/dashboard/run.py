#!/usr/bin/env python3
"""
Lanzador del Dashboard de la Software Factory con Uvicorn y FastAPI en el puerto 5000.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# Asegurar que ROOT_DIR esté en sys.path
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    import uvicorn
except ImportError:
    # Intentar ejecutar con el intérprete del entorno virtual local
    venv_python = ROOT_DIR / ".venv" / "bin" / "python3"
    if venv_python.exists():
        import os
        os.execv(str(venv_python), [str(venv_python)] + sys.argv)
    else:
        print("[Error] No se encontró 'uvicorn'. Asegúrate de instalarlo con: pip install uvicorn fastapi")
        sys.exit(1)


def main():
    host = "0.0.0.0"
    port = 5000
    print("=" * 70)
    print("  🚀 SOFTFACTORY CONTROL PLANE DASHBOARD")
    print(f"  Servidor activo en: http://localhost:{port}")
    print("  Presiona CTRL+C para detener el servidor.")
    print("=" * 70)
    uvicorn.run("tools.dashboard.api:app", host=host, port=port, reload=False, log_level="info")


if __name__ == "__main__":
    main()
