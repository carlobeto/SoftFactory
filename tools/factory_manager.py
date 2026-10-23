#!/usr/bin/env python3
"""
Factory Manager: Módulo para gestionar el ciclo de vida de aplicaciones en la Software Factory.
Permite rescatar/exportar aplicaciones y reiniciar/inicializar el entorno para nuevas aplicaciones.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_DIR = ROOT_DIR / "environment" / "workspace"
SHARED_POOL_DIR = ROOT_DIR / "shared_pool"
CONFIG_DIR = ROOT_DIR / "config"
EXPORTS_DIR = ROOT_DIR / "exports"
CONTEXT_FILE = CONFIG_DIR / "workflow_context.json"
TEMPLATE_FILE = CONFIG_DIR / "workflow_context.template.json"


def get_current_project_metadata():
    """Obtiene el nombre y estado del proyecto actual desde el contexto."""
    if CONTEXT_FILE.exists():
        try:
            with open(CONTEXT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("WORKFLOW_CONTEXT", {}).get("project_metadata", {})
        except Exception:
            pass
    return {"project_name": "app", "status": "UNKNOWN"}


def export_application(target_dir=None, make_tar=True, include_artifacts=True):
    """
    Rescata y exporta la aplicación generada en el workspace actual.
    Crea un paquete standalone listo para producción con su código, tests y artefactos.
    """
    metadata = get_current_project_metadata()
    project_name = metadata.get("project_name", "app")

    if not target_dir:
        target_path = EXPORTS_DIR / project_name
    else:
        target_path = Path(target_dir).resolve()

    print(f"\n[Export] Rescatando aplicación '{project_name}'...")
    print(f"-> Destino: {target_path}")

    # Verificar si hay contenido en el workspace
    workspace_items = [item for item in WORKSPACE_DIR.iterdir() if item.name != "__pycache__"]
    if not workspace_items:
        print("[Export] Advertencia: El workspace está vacío. No hay archivos de aplicación que exportar.")
        return None, None

    # Crear directorio destino
    if target_path.exists():
        shutil.rmtree(target_path)
    target_path.mkdir(parents=True, exist_ok=True)

    # 1. Copiar código y contenido del workspace
    for item in WORKSPACE_DIR.iterdir():
        if item.name == "__pycache__":
            continue
        dest = target_path / item.name
        if item.is_dir():
            shutil.copytree(item, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(item, dest)

    # 2. Copiar Dockerfile del entorno si no existe en el workspace
    if not (target_path / "Dockerfile").exists():
        env_dockerfile = ROOT_DIR / "environment" / "Dockerfile"
        if env_dockerfile.exists():
            shutil.copy2(env_dockerfile, target_path / "Dockerfile")

    # 3. Incluir artefactos y documentación generada
    if include_artifacts:
        docs_dir = target_path / "docs" / "softfactory_artifacts"
        docs_dir.mkdir(parents=True, exist_ok=True)

        artifact_sources = [
            (SHARED_POOL_DIR / "01_prd" / "DISCOVERY_NOTES.md", "00_DISCOVERY_NOTES.md"),
            (SHARED_POOL_DIR / "01_prd" / "PRD.md", "01_PRD.md"),
            (SHARED_POOL_DIR / "02_system_design" / "SYSTEM_DESIGN.md", "02_SYSTEM_DESIGN.md"),
            (SHARED_POOL_DIR / "02_system_design" / "TASKS.md", "02_TASKS.md"),
            (SHARED_POOL_DIR / "03_code_patches" / "CHANGE_PLAN.md", "03_CHANGE_PLAN.md"),
            (SHARED_POOL_DIR / "03_code_patches" / "model.patch", "03_model.patch"),
            (SHARED_POOL_DIR / "04_qa_reports" / "QA_REPORT.md", "04_QA_REPORT.md"),
        ]

        for src, name in artifact_sources:
            if src.exists():
                shutil.copy2(src, docs_dir / name)

    # 4. Asegurar README standalone
    readme_path = target_path / "README.md"
    if not readme_path.exists():
        readme_content = f"""# {project_name.capitalize()} (Exportado desde SoftFactory)

Esta aplicación fue desarrollada, auditada y aprobada por la cadena de montaje de la Software Factory.

## Estructura
- Código fuente: Directorio principal y módulos
- Pruebas unitarias: `tests/`
- Dockerfile para ejecución en contenedores
- Documentación de arquitectura y QA: `docs/softfactory_artifacts/`

## Ejecución Local
```bash
python3 main.py --help
```

## Ejecución de Pruebas
```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## Ejecución con Docker
```bash
docker build -t {project_name}:latest .
docker run --rm {project_name}:latest
```
"""
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)

    print(f"[Export] Aplicación exportada exitosamente a: {target_path}")

    # 5. Generar archivo comprimido (.tar.gz)
    tar_path = None
    if make_tar:
        tar_path = target_path.parent / f"{project_name}.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(target_path, arcname=project_name)
        print(f"[Export] Paquete comprimido generado en: {tar_path}")

    return target_path, tar_path


def reset_environment(backup_first=True, force=False):
    """
    Limpia y reinicia el ambiente de producción de la fábrica.
    Restaura shared_pool, workspace y workflow_context a su estado base inicial.
    """
    metadata = get_current_project_metadata()
    current_name = metadata.get("project_name", "app")

    workspace_has_content = any(WORKSPACE_DIR.iterdir()) if WORKSPACE_DIR.exists() else False

    if workspace_has_content and backup_first:
        print(f"[Reset] Creando copia de seguridad automática de '{current_name}' antes de reiniciar...")
        export_application(make_tar=True)

    print("\n[Reset] Limpiando ambiente de la Software Factory...")

    # 1. Limpiar Workspace
    if WORKSPACE_DIR.exists():
        for item in WORKSPACE_DIR.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        print("-> [OK] environment/workspace/ limpiado.")
    else:
        WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

    # 2. Limpiar Shared Pool
    stages = ["01_prd", "02_system_design", "03_code_patches", "04_qa_reports"]
    for stage in stages:
        stage_dir = SHARED_POOL_DIR / stage
        if stage_dir.exists():
            for item in stage_dir.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
        else:
            stage_dir.mkdir(parents=True, exist_ok=True)
    print("-> [OK] shared_pool/ (01_prd, 02_system_design, 03_code_patches, 04_qa_reports) limpiado.")

    # 3. Limpiar archivos temporales y bases de datos en la raíz
    for db_file in ROOT_DIR.glob("*.db"):
        try:
            db_file.unlink()
            print(f"-> [OK] Archivo de base de datos eliminado: {db_file.name}")
        except Exception:
            pass

    # 4. Restaurar workflow_context.json desde template
    if TEMPLATE_FILE.exists():
        shutil.copy2(TEMPLATE_FILE, CONTEXT_FILE)
        print("-> [OK] config/workflow_context.json restaurado al estado base.")
    else:
        print("-> [Advertencia] No se encontró workflow_context.template.json")

    print("[Reset] Ambiente inicializado y listo para crear una nueva aplicación.\n")


def init_new_project(project_name, requirement=None, backup_current=True):
    """Inicializa el ambiente de producción para un nuevo proyecto con nombre y requerimiento."""
    reset_environment(backup_first=backup_current, force=True)

    # Actualizar metadata en workflow_context.json
    if CONTEXT_FILE.exists():
        with open(CONTEXT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        data.setdefault("WORKFLOW_CONTEXT", {})
        data["WORKFLOW_CONTEXT"].setdefault("project_metadata", {})
        data["WORKFLOW_CONTEXT"]["project_metadata"]["project_name"] = project_name
        data["WORKFLOW_CONTEXT"]["project_metadata"]["status"] = "INITIALIZED"

        with open(CONTEXT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"[Init] Proyecto configurado como: '{project_name}'.")

    # Guardar requerimiento inicial si fue provisto
    if requirement:
        req_file = SHARED_POOL_DIR / "01_prd" / "NEW_REQUIREMENT.txt"
        with open(req_file, "w", encoding="utf-8") as f:
            f.write(f"PROYECTO: {project_name}\nREQUERIMIENTO INICIAL:\n{requirement}\n")
        print(f"[Init] Requerimiento registrado para el Product Manager en: {req_file}")


def print_status():
    """Imprime el estado actual del flujo y componentes de la fábrica."""
    metadata = get_current_project_metadata()
    print("=" * 60)
    print("   ESTADO ACTUAL DE LA SOFTWARE FACTORY")
    print("=" * 60)
    print(f"Proyecto actual: {metadata.get('project_name', 'N/A')}")
    print(f"Estado QA/Fábrica: {metadata.get('status', 'N/A')}")

    discovery_exists = (SHARED_POOL_DIR / "01_prd" / "DISCOVERY_NOTES.md").exists()
    prd_exists = (SHARED_POOL_DIR / "01_prd" / "PRD.md").exists()
    design_exists = (SHARED_POOL_DIR / "02_system_design" / "SYSTEM_DESIGN.md").exists()
    tasks_exists = (SHARED_POOL_DIR / "02_system_design" / "TASKS.md").exists()
    patch_exists = (SHARED_POOL_DIR / "03_code_patches" / "model.patch").exists()
    qa_exists = (SHARED_POOL_DIR / "04_qa_reports" / "QA_REPORT.md").exists()

    print("\nArtefactos del Shared Pool:")
    print(f"  [0] DISCOVERY_NOTES.md:  {'PRESENTE' if discovery_exists else 'VACÍO'}")
    print(f"  [1] PRD.md:              {'PRESENTE' if prd_exists else 'VACÍO'}")
    print(f"  [2] SYSTEM_DESIGN.md:    {'PRESENTE' if design_exists else 'VACÍO'}")
    print(f"  [2] TASKS.md:            {'PRESENTE' if tasks_exists else 'VACÍO'}")
    print(f"  [3] model.patch:         {'PRESENTE' if patch_exists else 'VACÍO'}")
    print(f"  [4] QA_REPORT.md:        {'PRESENTE' if qa_exists else 'VACÍO'}")

    workspace_files = list(WORKSPACE_DIR.glob("**/*")) if WORKSPACE_DIR.exists() else []
    files_only = [f for f in workspace_files if f.is_file() and "__pycache__" not in str(f)]
    print(f"\nArchivos en environment/workspace: {len(files_only)}")
    for f in files_only[:8]:
        print(f"  - {f.relative_to(WORKSPACE_DIR)}")
    if len(files_only) > 8:
        print(f"  ... y {len(files_only) - 8} más.")

    # Exports existentes
    if EXPORTS_DIR.exists():
        exports = [e.name for e in EXPORTS_DIR.iterdir()]
        print(f"\nAplicaciones exportadas en exports/: {', '.join(exports) if exports else 'Ninguna'}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Gestor de ciclo de vida de la Software Factory (Rescate, Reset, Inicialización y Estado)."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--export", nargs="?", const="", help="Exporta y rescata la aplicación actual a una ruta o a exports/")
    group.add_argument("--reset", action="store_true", help="Limpia y reinicia el ambiente de producción")
    group.add_argument("--init", metavar="PROJECT_NAME", help="Inicializa el entorno para un nuevo proyecto")
    group.add_argument("--status", action="store_true", help="Muestra el estado de la fábrica")

    parser.add_argument("--req", help="Requerimiento del usuario para el nuevo proyecto (usado con --init)")
    parser.add_argument("--no-backup", action="store_true", help="No realiza copia de seguridad previa al reset")

    args = parser.parse_args()

    if args.export is not None:
        target = args.export if args.export != "" else None
        export_application(target_dir=target)
    elif args.reset:
        reset_environment(backup_first=not args.no_backup)
    elif args.init:
        init_new_project(args.init, requirement=args.req, backup_current=not args.no_backup)
    elif args.status:
        print_status()
    else:
        print_status()
        print("\nUso:")
        print("  python3 tools/factory_manager.py --export           # Rescata la app actual")
        print("  python3 tools/factory_manager.py --reset            # Reinicia el ambiente")
        print("  python3 tools/factory_manager.py --init <nombre>    # Prepara un nuevo proyecto")
        print("  python3 tools/factory_manager.py --status           # Muestra el estado")


if __name__ == "__main__":
    main()
