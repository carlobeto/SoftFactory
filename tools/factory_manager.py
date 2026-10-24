#!/usr/bin/env python3
"""
Factory Manager: Módulo para gestionar el ciclo de vida y aislamiento de proyectos en la Software Factory.
Asegura que cada aplicación se construya en su propia carpeta autocontenida dentro de projects/<Nombre_Proyecto>,
garantizando que el motor de SoftFactory y sus archivos preexistentes permanezcan 100% inmutables y limpios.
"""

import argparse
import datetime
import json
import os
import shutil
import sys
import tarfile
from pathlib import Path
from typing import Any, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
PROJECTS_DIR = ROOT_DIR / "projects"
EXPORTS_DIR = ROOT_DIR / "exports"
CONFIG_DIR = ROOT_DIR / "config"
TEMPLATE_FILE = CONFIG_DIR / "workflow_context.template.json"
ACTIVE_PROJECT_FILE = PROJECTS_DIR / ".active_project"

# Rutas globales de fallback / base
LEGACY_WORKSPACE_DIR = ROOT_DIR / "environment" / "workspace"
LEGACY_SHARED_POOL_DIR = ROOT_DIR / "shared_pool"
LEGACY_CONTEXT_FILE = CONFIG_DIR / "workflow_context.json"


def get_projects_dir() -> Path:
    """Retorna el directorio raíz de proyectos asegurando su existencia."""
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    return PROJECTS_DIR


def get_active_project_name() -> str:
    """Obtiene el nombre del proyecto actualmente activo."""
    get_projects_dir()
    if ACTIVE_PROJECT_FILE.exists():
        try:
            name = ACTIVE_PROJECT_FILE.read_text(encoding="utf-8").strip()
            if name and (PROJECTS_DIR / name).is_dir():
                return name
        except Exception:
            pass

    # Si no hay activo o no existe, buscar el primer proyecto en projects/
    existing = [p.name for p in PROJECTS_DIR.iterdir() if p.is_dir() and not p.name.startswith(".")]
    if existing:
        selected = existing[0]
        set_active_project(selected)
        return selected

    return "default_app"


def set_active_project(project_name: str) -> str:
    """Establece el proyecto activo en .active_project."""
    get_projects_dir()
    clean_name = project_name.strip()
    with open(ACTIVE_PROJECT_FILE, "w", encoding="utf-8") as f:
        f.write(clean_name)
    return clean_name


def get_project_dir(project_name: Optional[str] = None) -> Path:
    """Retorna la ruta absoluta del directorio del proyecto (activo si es None)."""
    name = project_name or get_active_project_name()
    return PROJECTS_DIR / name


def get_project_paths(project_name: Optional[str] = None) -> dict[str, Path]:
    """
    Retorna el diccionario con todas las rutas autocontenidas de un proyecto.
    Estructura:
      projects/<nombre>/
        artifacts/
          01_prd/
          02_system_design/
          03_code_patches/
          04_qa_reports/
        workspace/
        workflow_context.json
    """
    proj_dir = get_project_dir(project_name)
    return {
        "project_name": proj_dir.name,
        "root": proj_dir,
        "artifacts": proj_dir / "artifacts",
        "01_prd": proj_dir / "artifacts" / "01_prd",
        "02_system_design": proj_dir / "artifacts" / "02_system_design",
        "03_code_patches": proj_dir / "artifacts" / "03_code_patches",
        "04_qa_reports": proj_dir / "artifacts" / "04_qa_reports",
        "workspace": proj_dir / "workspace",
        "context": proj_dir / "workflow_context.json",
    }


def list_projects() -> list[dict[str, Any]]:
    """Descubre y retorna la lista de todos los proyectos creados con sus metadatos."""
    p_dir = get_projects_dir()
    active_name = get_active_project_name()
    projects = []

    for item in p_dir.iterdir():
        if not item.is_dir() or item.name.startswith("."):
            continue

        paths = get_project_paths(item.name)
        ctx_file = paths["context"]
        meta = {"project_name": item.name, "status": "INITIALIZED"}
        human_approvals = {}
        architecture = {}

        if ctx_file.exists():
            try:
                with open(ctx_file, "r", encoding="utf-8") as f:
                    data = json.load(f).get("WORKFLOW_CONTEXT", {})
                    meta = data.get("project_metadata", meta)
                    human_approvals = data.get("human_approvals", {})
                    architecture = data.get("project_architecture", {})
            except Exception:
                pass

        # Conteo de archivos de workspace
        ws_files_count = 0
        if paths["workspace"].exists():
            ws_files_count = sum(1 for f in paths["workspace"].glob("**/*") if f.is_file() and "__pycache__" not in str(f))

        # Conteo de artefactos presentes
        artifacts_status = {
            "discovery_notes": (paths["01_prd"] / "DISCOVERY_NOTES.md").exists(),
            "prd": (paths["01_prd"] / "PRD.md").exists(),
            "system_design": (paths["02_system_design"] / "SYSTEM_DESIGN.md").exists(),
            "tasks": (paths["02_system_design"] / "TASKS.md").exists(),
            "change_plan": (paths["03_code_patches"] / "CHANGE_PLAN.md").exists(),
            "patch": (paths["03_code_patches"] / "model.patch").exists(),
            "qa_report": (paths["04_qa_reports"] / "QA_REPORT.md").exists(),
        }
        completed_stages = sum(1 for v in artifacts_status.values() if v)

        stat = item.stat()
        mod_time = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

        projects.append({
            "name": item.name,
            "path": str(item),
            "is_active": (item.name == active_name),
            "status": meta.get("status", "INITIALIZED"),
            "modified_at": mod_time,
            "workspace_files_count": ws_files_count,
            "completed_stages": completed_stages,
            "artifacts_status": artifacts_status,
            "human_approvals": human_approvals,
            "architecture": architecture,
        })

    # Ordenar: primero el activo, luego por fecha de modificación descendente
    projects.sort(key=lambda x: (not x["is_active"], x["modified_at"]), reverse=False)
    return projects


def create_new_project(project_name: str, requirement: Optional[str] = None) -> dict[str, Any]:
    """
    Inicializa una nueva carpeta de proyecto completamente autocontenida en projects/<project_name>.
    No modifica ningún archivo preexistente en el repositorio raíz de SoftFactory.
    """
    clean_name = project_name.strip()
    paths = get_project_paths(clean_name)
    proj_root = paths["root"]

    # Crear directorios del proyecto
    for key in ["01_prd", "02_system_design", "03_code_patches", "04_qa_reports", "workspace"]:
        paths[key].mkdir(parents=True, exist_ok=True)

    # Inicializar workflow_context.json a partir de la plantilla sin alterar la plantilla
    context_data = {}
    if TEMPLATE_FILE.exists():
        try:
            with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
                context_data = json.load(f)
        except Exception:
            pass

    context_data.setdefault("WORKFLOW_CONTEXT", {})
    context_data["WORKFLOW_CONTEXT"]["project_metadata"] = {
        "project_name": clean_name,
        "status": "INITIALIZED",
        "created_at": datetime.datetime.now().isoformat(),
        "project_directory": str(proj_root),
    }
    context_data["WORKFLOW_CONTEXT"]["human_approvals"] = {
        "discovery_notes": False,
        "prd": False,
        "system_design": False,
        "change_plan": False,
        "code_modification": False,
        "qa_report": False,
    }
    context_data["WORKFLOW_CONTEXT"]["file_boundaries_template"] = {
        "allowed_to_touch": [f"projects/{clean_name}/workspace/*"],
        "strictly_forbidden": [
            "agents/*",
            "tools/*",
            "config/*",
            "orchestrator.py",
            "dashboard.sh",
            "AGENTS.md",
            "shared_pool/*",
            "environment/*",
        ],
    }

    with open(paths["context"], "w", encoding="utf-8") as f:
        json.dump(context_data, f, indent=4)

    # Registrar requerimiento semilla si fue provisto
    if requirement:
        req_file = paths["01_prd"] / "NEW_REQUIREMENT.txt"
        with open(req_file, "w", encoding="utf-8") as f:
            f.write(f"PROYECTO: {clean_name}\nREQUERIMIENTO INICIAL:\n{requirement}\n")

    # Inicializar repositorio Git desacoplado para el proyecto
    try:
        from tools.project_git import init_project_git
        init_project_git(clean_name)
    except Exception as e:
        print(f"[Factory Manager] Nota sobre Git en {clean_name}: {e}")

    # Establecer como proyecto activo
    set_active_project(clean_name)
    print(f"[Factory Manager] Nuevo proyecto '{clean_name}' inicializado de forma aislada en: {proj_root}")
    return paths


def delete_project(project_name: str) -> bool:
    """
    Elimina por completo la carpeta de un proyecto en projects/<project_name>.
    No toca absolutamente nada del motor de la Software Factory.
    """
    clean_name = project_name.strip()
    proj_dir = PROJECTS_DIR / clean_name
    if not proj_dir.exists() or not proj_dir.is_dir():
        return False

    shutil.rmtree(proj_dir)
    print(f"[Factory Manager] Proyecto '{clean_name}' eliminado exitosamente.")

    # Si era el proyecto activo, reasignar o limpiar
    current_active = get_active_project_name()
    if current_active == clean_name:
        existing = [p.name for p in PROJECTS_DIR.iterdir() if p.is_dir() and not p.name.startswith(".")]
        if existing:
            set_active_project(existing[0])
        else:
            if ACTIVE_PROJECT_FILE.exists():
                ACTIVE_PROJECT_FILE.unlink()

    return True


def get_current_project_metadata(project_name: Optional[str] = None) -> dict[str, Any]:
    """Obtiene los metadatos del proyecto especificado (o del proyecto activo)."""
    paths = get_project_paths(project_name)
    ctx_file = paths["context"]
    if ctx_file.exists():
        try:
            with open(ctx_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("WORKFLOW_CONTEXT", {}).get("project_metadata", {})
        except Exception:
            pass
    return {"project_name": paths["project_name"], "status": "INITIALIZED"}


def export_application(
    project_name: Optional[str] = None,
    target_dir: Optional[str] = None,
    make_tar: bool = True,
    include_artifacts: bool = True,
) -> tuple[Optional[Path], Optional[Path]]:
    """
    Exporta la aplicación de un proyecto aislado hacia exports/<project_name> o la ruta especificada.
    Empaqueta el código fuente del workspace y copia sus artefactos.
    """
    paths = get_project_paths(project_name)
    proj_name = paths["project_name"]

    if not target_dir:
        target_path = EXPORTS_DIR / proj_name
    else:
        target_path = Path(target_dir).resolve()

    print(f"\n[Export] Rescatando aplicación '{proj_name}'...")
    print(f"-> Destino: {target_path}")

    ws_dir = paths["workspace"]
    if not ws_dir.exists() or not any(ws_dir.iterdir()):
        print(f"[Export] Advertencia: El workspace de '{proj_name}' está vacío. Nada que exportar.")
        return None, None

    if target_path.exists():
        shutil.rmtree(target_path)
    target_path.mkdir(parents=True, exist_ok=True)

    # 1. Copiar código fuente
    for item in ws_dir.iterdir():
        if item.name == "__pycache__":
            continue
        dest = target_path / item.name
        if item.is_dir():
            shutil.copytree(item, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(item, dest)

    # 2. Copiar Dockerfile si no existe en el workspace
    if not (target_path / "Dockerfile").exists():
        env_dockerfile = ROOT_DIR / "environment" / "Dockerfile"
        if env_dockerfile.exists():
            shutil.copy2(env_dockerfile, target_path / "Dockerfile")

    # 3. Copiar artefactos
    if include_artifacts and paths["artifacts"].exists():
        docs_dir = target_path / "docs" / "softfactory_artifacts"
        docs_dir.mkdir(parents=True, exist_ok=True)

        artifact_sources = [
            (paths["01_prd"] / "DISCOVERY_NOTES.md", "00_DISCOVERY_NOTES.md"),
            (paths["01_prd"] / "PRD.md", "01_PRD.md"),
            (paths["02_system_design"] / "SYSTEM_DESIGN.md", "02_SYSTEM_DESIGN.md"),
            (paths["02_system_design"] / "TASKS.md", "02_TASKS.md"),
            (paths["03_code_patches"] / "CHANGE_PLAN.md", "03_CHANGE_PLAN.md"),
            (paths["03_code_patches"] / "model.patch", "03_model.patch"),
            (paths["04_qa_reports"] / "QA_REPORT.md", "04_QA_REPORT.md"),
        ]

        for src, name in artifact_sources:
            if src.exists():
                shutil.copy2(src, docs_dir / name)

    # 4. Asegurar README.md standalone
    readme_path = target_path / "README.md"
    if not readme_path.exists():
        readme_content = f"""# {proj_name.capitalize()} (Exportado desde SoftFactory)

Esta aplicación fue desarrollada de forma aislada en la Software Factory.

## Estructura
- Código fuente: Módulos y servicios
- Pruebas unitarias: `tests/`
- Dockerfile para ejecución en contenedores
- Documentación de arquitectura y QA: `docs/softfactory_artifacts/`

## Ejecución Local
```bash
python3 main.py --help
```

## Pruebas
```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```
"""
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)

    tar_path = None
    if make_tar:
        tar_path = target_path.parent / f"{proj_name}.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(target_path, arcname=proj_name)
        print(f"[Export] Paquete comprimido generado en: {tar_path}")

    return target_path, tar_path


def reset_environment(
    project_name: Optional[str] = None,
    backup_first: bool = True,
    force: bool = False,
):
    """
    Reinicia únicamente el proyecto activo o especificado.
    Limpia sus artefactos y workspace, y restaura su workflow_context.json.
    NUNCA toca los archivos preexistentes de SoftFactory.
    """
    paths = get_project_paths(project_name)
    proj_name = paths["project_name"]

    if backup_first and paths["workspace"].exists() and any(paths["workspace"].iterdir()):
        print(f"[Reset] Creando copia de seguridad de '{proj_name}' antes de reiniciar...")
        export_application(project_name=proj_name, make_tar=True)

    print(f"\n[Reset] Limpiando ambiente del proyecto '{proj_name}'...")

    # Limpiar workspace del proyecto
    if paths["workspace"].exists():
        for item in paths["workspace"].iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
    else:
        paths["workspace"].mkdir(parents=True, exist_ok=True)

    # Limpiar artefactos del proyecto
    for stage in ["01_prd", "02_system_design", "03_code_patches", "04_qa_reports"]:
        s_dir = paths[stage]
        if s_dir.exists():
            for item in s_dir.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
        else:
            s_dir.mkdir(parents=True, exist_ok=True)

    # Restaurar workflow_context.json del proyecto desde plantilla
    create_new_project(proj_name)
    print(f"[Reset] Proyecto '{proj_name}' reiniciado y listo para reanudar.")


def init_new_project(project_name: str, requirement: Optional[str] = None, backup_current: bool = False):
    """Wrapper para crear un nuevo proyecto respetando la API existente."""
    return create_new_project(project_name, requirement=requirement)


def print_status(project_name: Optional[str] = None):
    """Imprime el estado de los proyectos y del proyecto activo."""
    active_name = project_name or get_active_project_name()
    paths = get_project_paths(active_name)
    meta = get_current_project_metadata(active_name)

    print("=" * 65)
    print("   ESTADO ACTUAL DE LA SOFTWARE FACTORY (AISLAMIENTO DE PROYECTOS)")
    print("=" * 65)
    print(f"Proyecto activo:    {active_name}")
    print(f"Ruta de proyecto:   {paths['root']}")
    print(f"Estado QA/Fase:     {meta.get('status', 'N/A')}")

    discovery_exists = (paths["01_prd"] / "DISCOVERY_NOTES.md").exists()
    prd_exists = (paths["01_prd"] / "PRD.md").exists()
    design_exists = (paths["02_system_design"] / "SYSTEM_DESIGN.md").exists()
    tasks_exists = (paths["02_system_design"] / "TASKS.md").exists()
    patch_exists = (paths["03_code_patches"] / "model.patch").exists()
    qa_exists = (paths["04_qa_reports"] / "QA_REPORT.md").exists()

    print("\nArtefactos del Proyecto:")
    print(f"  [1] DISCOVERY_NOTES.md:  {'PRESENTE' if discovery_exists else 'VACÍO'}")
    print(f"  [2] PRD.md:              {'PRESENTE' if prd_exists else 'VACÍO'}")
    print(f"  [3] SYSTEM_DESIGN.md:    {'PRESENTE' if design_exists else 'VACÍO'}")
    print(f"  [3] TASKS.md:            {'PRESENTE' if tasks_exists else 'VACÍO'}")
    print(f"  [4] model.patch:         {'PRESENTE' if patch_exists else 'VACÍO'}")
    print(f"  [5] QA_REPORT.md:        {'PRESENTE' if qa_exists else 'VACÍO'}")

    ws_files = list(paths["workspace"].glob("**/*")) if paths["workspace"].exists() else []
    files_only = [f for f in ws_files if f.is_file() and "__pycache__" not in str(f)]
    print(f"\nArchivos en workspace: {len(files_only)}")
    for f in files_only[:6]:
        print(f"  - {f.relative_to(paths['workspace'])}")

    all_projs = list_projects()
    print(f"\nProyectos disponibles en projects/ ({len(all_projs)}):")
    for p in all_projs:
        act = " (ACTIVO)" if p["is_active"] else ""
        print(f"  * {p['name']}{act} - Estado: {p['status']} ({p['workspace_files_count']} archivos)")
    print("=" * 65)


def main():
    parser = argparse.ArgumentParser(
        description="Gestor de proyectos y ciclo de vida de la Software Factory."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--export", nargs="?", const="", help="Exporta la aplicación actual a exports/ o ruta indicada")
    group.add_argument("--reset", action="store_true", help="Reinicia el ambiente del proyecto activo")
    group.add_argument("--init", metavar="PROJECT_NAME", help="Crea un nuevo proyecto en projects/<PROJECT_NAME>")
    group.add_argument("--delete", metavar="PROJECT_NAME", help="Elimina la carpeta de un proyecto")
    group.add_argument("--list", action="store_true", help="Lista todos los proyectos en projects/")
    group.add_argument("--select", metavar="PROJECT_NAME", help="Establece el proyecto activo")
    group.add_argument("--status", action="store_true", help="Muestra el estado del proyecto activo")

    parser.add_argument("--project", help="Nombre del proyecto específico a operar (por defecto: activo)")
    parser.add_argument("--req", help="Requerimiento del usuario para el nuevo proyecto")
    parser.add_argument("--no-backup", action="store_true", help="No realiza backup previo al reset")

    args = parser.parse_args()

    if args.list:
        projects = list_projects()
        print(f"Proyectos en projects/ ({len(projects)}):")
        for p in projects:
            act = " [ACTIVO]" if p["is_active"] else ""
            print(f"  - {p['name']}{act}: Estado {p['status']}, Modificado: {p['modified_at']}")
    elif args.select:
        set_active_project(args.select)
        print(f"Proyecto activo establecido a: '{args.select}'")
    elif args.delete:
        delete_project(args.delete)
    elif args.export is not None:
        target = args.export if args.export != "" else None
        export_application(project_name=args.project, target_dir=target)
    elif args.reset:
        reset_environment(project_name=args.project, backup_first=not args.no_backup)
    elif args.init:
        create_new_project(args.init, requirement=args.req)
    elif args.status:
        print_status(args.project)
    else:
        print_status(args.project)


if __name__ == "__main__":
    main()
