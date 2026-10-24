#!/usr/bin/env python3
"""Orchestrator de la Software Factory según las reglas de AGENTS.md con soporte para aislamiento de proyectos."""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Directorios de la fábrica de software
ROOT_DIR = Path(__file__).resolve().parent

# Importación de herramientas de gestión de la fábrica
try:
    from tools.factory_manager import (
        create_new_project,
        delete_project,
        export_application,
        get_active_project_name,
        get_project_paths,
        list_projects,
        print_status,
        reset_environment,
        set_active_project,
    )
    from tools.project_git import commit_project_stage
    from tools.requirements_interviewer import run_grill_interview
except ImportError:
    sys.path.append(str(ROOT_DIR))
    from tools.factory_manager import (
        create_new_project,
        delete_project,
        export_application,
        get_active_project_name,
        get_project_paths,
        list_projects,
        print_status,
        reset_environment,
        set_active_project,
    )
    from tools.project_git import commit_project_stage
    from tools.requirements_interviewer import run_grill_interview


def check_environment(project_name: Optional[str] = None):
    """Verifica la existencia del proyecto y su contexto."""
    paths = get_project_paths(project_name)
    context_file = paths["context"]
    if not context_file.exists():
        print(f"[Orchestrator] Inicializando contexto para el proyecto '{paths['project_name']}'...")
        create_new_project(paths["project_name"])
    print(f"[Orchestrator] Entorno verificado para el proyecto: '{paths['project_name']}' ({paths['root']})")


def run_discovery(user_requirement: str, interactive: bool = True, project_name: Optional[str] = None):
    """Fase 0: Requirements Discovery & Grilling según la metodología de AI Hero."""
    pname = project_name or get_active_project_name()
    print(f"\n=== [FASE 0] Discovery & Grilling para Proyecto: '{pname}' ===")
    discovery_path, _ = run_grill_interview(user_requirement, interactive=interactive, project_name=pname)
    print(f"-> Elicitación completada y decisiones congeladas en: {discovery_path}")
    commit_project_stage(pname, "discovery_notes", f"feat(discovery): freeze requirements for '{pname}'")
    return discovery_path


def run_product_manager(user_requirement: str, project_name: Optional[str] = None):
    """Fase 1: El Product Manager analiza el requerimiento y genera/valida el PRD.md."""
    paths = get_project_paths(project_name)
    pname = paths["project_name"]
    print(f"\n=== [FASE 1] Product Manager: Analizando requerimientos para '{pname}' ===")
    prd_path = paths["01_prd"] / "PRD.md"
    discovery_path = paths["01_prd"] / "DISCOVERY_NOTES.md"

    print(f"-> Requerimiento: {user_requirement}")
    if discovery_path.exists():
        print(f"-> Incorporando especificación previa de Discovery: {discovery_path}")

    if not prd_path.exists():
        raise FileNotFoundError(f"No se encontró el PRD en: {prd_path}. Genera la fase 1 primero.")

    print(f"-> PRD verificado exitosamente en: {prd_path}")
    return prd_path


def run_architect(project_name: Optional[str] = None):
    """Fase 2: El Arquitecto diseña la solución técnica, interfaces y tareas."""
    paths = get_project_paths(project_name)
    pname = paths["project_name"]
    print(f"\n=== [FASE 2] Arquitecto: System Design y Tareas para '{pname}' ===")
    design_path = paths["02_system_design"] / "SYSTEM_DESIGN.md"
    tasks_path = paths["02_system_design"] / "TASKS.md"

    if not design_path.exists() or not tasks_path.exists():
        raise FileNotFoundError(f"Faltan artefactos en {paths['02_system_design']}.")

    print(f"-> Especificación técnica validada en: {design_path}")
    print(f"-> Tareas asignadas validadas en: {tasks_path}")
    return design_path, tasks_path


def run_engineer(project_name: Optional[str] = None):
    """Fase 3: El Programador implementa la solución y genera model.patch."""
    paths = get_project_paths(project_name)
    pname = paths["project_name"]
    print(f"\n=== [FASE 3] Programador: Verificando implementación para '{pname}' ===")
    change_plan_path = paths["03_code_patches"] / "CHANGE_PLAN.md"
    patch_path = paths["03_code_patches"] / "model.patch"

    if not change_plan_path.exists():
        raise FileNotFoundError(f"Falta el plan de cambios en: {change_plan_path}")
    if not patch_path.exists():
        raise FileNotFoundError(f"Falta el parche de código en: {patch_path}")

    print(f"-> Plan previo verificado en: {change_plan_path}")
    print(f"-> Parche generado: {patch_path}")
    return patch_path


def run_qa_tester(project_name: Optional[str] = None):
    """Fase 4: QA & Hostile Auditor ejecuta análisis estático y suite de pruebas."""
    paths = get_project_paths(project_name)
    pname = paths["project_name"]
    print(f"\n=== [FASE 4] QA & Hostile Auditor: Ejecutando verificación para '{pname}' ===")
    context_file = paths["context"]
    with open(context_file, "r", encoding="utf-8") as f:
        ctx = json.load(f)["WORKFLOW_CONTEXT"]

    ci_checks = ctx.get("mandatory_ci_checks", {})
    linter_cmd = ci_checks.get("linter_command")
    test_cmd = ci_checks.get("unit_test_command")

    if linter_cmd:
        print(f"-> Ejecutando Linter/Análisis Estático: {linter_cmd}")
        res = subprocess.run(linter_cmd, shell=True, cwd=ROOT_DIR)
        if res.returncode != 0:
            raise RuntimeError(f"Fallo en comprobación estática: {res.returncode}")

    if test_cmd:
        print(f"-> Ejecutando Suite de Pruebas: {test_cmd}")
        res = subprocess.run(test_cmd, shell=True, cwd=ROOT_DIR)
        if res.returncode != 0:
            raise RuntimeError(f"Fallo en ejecución de pruebas: {res.returncode}")

    qa_report_path = paths["04_qa_reports"] / "QA_REPORT.md"
    if not qa_report_path.exists():
        raise FileNotFoundError(f"Falta el reporte de QA en: {qa_report_path}")

    print(f"-> QA Report validado con éxito en: {qa_report_path}")
    print(f"\n*** Software Factory: CICLO COMPLETADO EXITOSAMENTE PARA '{pname}' ***")


def get_pending_requirement(project_name: Optional[str] = None):
    """Obtiene el requerimiento registrado para el proyecto."""
    paths = get_project_paths(project_name)
    req_file = paths["01_prd"] / "NEW_REQUIREMENT.txt"
    if req_file.exists():
        try:
            with open(req_file, "r", encoding="utf-8") as f:
                content = f.read()
                for line in content.splitlines():
                    if not line.startswith("PROYECTO:") and not line.startswith("REQUERIMIENTO INICIAL:"):
                        if line.strip():
                            return line.strip()
        except Exception:
            pass
    return "Crear una herramienta interactiva con cache local y test unitarios"


def run_pipeline(user_requirement: str, project_name: Optional[str] = None):
    """Ejecuta el ciclo de vida completo de 4 fases para el proyecto especificado."""
    pname = project_name or get_active_project_name()
    check_environment(pname)
    run_product_manager(user_requirement, project_name=pname)
    run_architect(project_name=pname)
    run_engineer(project_name=pname)
    run_qa_tester(project_name=pname)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Software Factory Orchestrator con Aislamiento de Proyectos en projects/"
    )
    parser.add_argument("--project", help="Nombre del proyecto específico (por defecto: activo)")
    parser.add_argument("--export", nargs="?", const="", help="Rescata/exporta la aplicación a exports/")
    parser.add_argument("--reset", action="store_true", help="Reinicia el ambiente del proyecto activo")
    parser.add_argument("--init", metavar="PROJECT_NAME", help="Inicializa una carpeta aislada para un nuevo proyecto")
    parser.add_argument("--delete", metavar="PROJECT_NAME", help="Elimina la carpeta de un proyecto")
    parser.add_argument("--interview", "--grill", nargs="?", const="", metavar="PROMPT",
                        help="Ejecuta sesión interactiva de Grill-Me (Fase 0) para desgranar requerimientos")
    parser.add_argument("--non-interactive", action="store_true",
                        help="Ejecuta la entrevista utilizando Smart Defaults")
    parser.add_argument("--ui", action="store_true", help="Inicia el Dashboard Web interactivo en http://localhost:5000")
    parser.add_argument("--status", action="store_true", help="Muestra el estado actual del proyecto")
    parser.add_argument("--req", help="Requerimiento del usuario para ejecutar o inicializar")
    parser.add_argument("--no-backup", action="store_true", help="No realiza backup automático antes de resetear")

    args = parser.parse_args()

    if args.ui:
        venv_py = ROOT_DIR / ".venv" / "bin" / "python3"
        py_bin = str(venv_py) if venv_py.exists() else sys.executable
        subprocess.run([py_bin, str(ROOT_DIR / "tools" / "dashboard" / "run.py")])
    elif args.delete:
        delete_project(args.delete)
    elif args.export is not None:
        target = args.export if args.export != "" else None
        export_application(project_name=args.project, target_dir=target)
    elif args.reset:
        reset_environment(project_name=args.project, backup_first=not args.no_backup)
    elif args.init:
        create_new_project(args.init, requirement=args.req)
        if args.interview is not None:
            prompt = args.interview if args.interview != "" else (args.req or f"Construir el sistema {args.init}")
            run_discovery(prompt, interactive=not args.non_interactive, project_name=args.init)
    elif args.interview is not None:
        pname = args.project or get_active_project_name()
        prompt = args.interview if args.interview != "" else (args.req or get_pending_requirement(pname))
        run_discovery(prompt, interactive=not args.non_interactive, project_name=pname)
    elif args.status:
        print_status(args.project)
    else:
        pname = args.project or get_active_project_name()
        req = args.req or get_pending_requirement(pname)
        run_pipeline(req, project_name=pname)