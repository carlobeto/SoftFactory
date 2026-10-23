#!/usr/bin/env python3
"""Orchestrator de la Software Factory según las reglas de AGENTS.md."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Directorios de la fábrica de software
ROOT_DIR = Path(__file__).resolve().parent
SHARED_POOL = ROOT_DIR / "shared_pool"
CONFIG_DIR = ROOT_DIR / "config"
WORKSPACE_DIR = ROOT_DIR / "environment" / "workspace"

# Importación de herramientas de gestión de la fábrica
try:
    from tools.factory_manager import (
        export_application,
        reset_environment,
        init_new_project,
        print_status,
    )
    from tools.requirements_interviewer import run_grill_interview
except ImportError:
    sys.path.append(str(ROOT_DIR))
    from tools.factory_manager import (
        export_application,
        reset_environment,
        init_new_project,
        print_status,
    )
    from tools.requirements_interviewer import run_grill_interview


def check_environment():
    """Verifica la existencia de la estructura base y el archivo de contexto global."""
    context_file = CONFIG_DIR / "workflow_context.json"
    if not context_file.exists():
        raise FileNotFoundError(
            "Falta el archivo config/workflow_context.json. Inicializa el contexto antes de arrancar."
        )
    print("[Orchestrator] Entorno verificado correctamente.")


def run_discovery(user_requirement: str, interactive: bool = True):
    """Fase 0: Requirements Discovery & Grilling según la metodología de AI Hero."""
    print("\n=== [FASE 0] Requirements Discovery & Grilling (Frontier Protocol) ===")
    discovery_path, _ = run_grill_interview(user_requirement, interactive=interactive)
    print(f"-> Elicitación completada y decisiones congeladas en: {discovery_path}")
    return discovery_path


def run_product_manager(user_requirement: str):
    """Fase 1: El Product Manager analiza el requerimiento y genera/valida el PRD.md."""
    print("\n=== [FASE 1] Product Manager: Analizando requerimientos y generando PRD ===")
    prd_path = SHARED_POOL / "01_prd" / "PRD.md"
    discovery_path = SHARED_POOL / "01_prd" / "DISCOVERY_NOTES.md"

    print(f"-> Requerimiento: {user_requirement}")
    if discovery_path.exists():
        print(f"-> Incorporando especificación previa de Discovery: {discovery_path}")
    print(f"-> Procesando con SOP de Product Manager...")

    if not prd_path.exists():
        raise FileNotFoundError(f"No se encontró el artefacto esperado en: {prd_path}")

    print(f"-> PRD verificado exitosamente en: {prd_path}")
    return prd_path


def run_architect():
    """Fase 2: El Arquitecto diseña la solución técnica, interfaces y tareas."""
    print("\n=== [FASE 2] Arquitecto: Generando System Design y Desglose de Tareas ===")
    design_path = SHARED_POOL / "02_system_design" / "SYSTEM_DESIGN.md"
    tasks_path = SHARED_POOL / "02_system_design" / "TASKS.md"

    if not design_path.exists() or not tasks_path.exists():
        raise FileNotFoundError("Faltan los artefactos SYSTEM_DESIGN.md o TASKS.md en 02_system_design.")

    print(f"-> Especificación técnica validada en: {design_path}")
    print(f"-> Tareas asignadas validadas en: {tasks_path}")
    return design_path, tasks_path


def run_engineer():
    """Fase 3: El Programador implementa la solución y genera model.patch."""
    print("\n=== [FASE 3] Programador: Verificando implementación y parche de código ===")
    change_plan_path = SHARED_POOL / "03_code_patches" / "CHANGE_PLAN.md"
    patch_path = SHARED_POOL / "03_code_patches" / "model.patch"

    if not change_plan_path.exists():
        raise FileNotFoundError(f"Falta el plan de cambios en: {change_plan_path}")
    if not patch_path.exists():
        raise FileNotFoundError(f"Falta el parche de código en: {patch_path}")

    print(f"-> Plan previo verificado en: {change_plan_path}")
    print(f"-> Parche generado (SWE Submission): {patch_path}")
    return patch_path


def run_qa_tester():
    """Fase 4: QA & Hostile Auditor ejecuta análisis estático y suite de pruebas."""
    print("\n=== [FASE 4] QA & Hostile Auditor: Ejecutando verificación y CI Checks ===")
    context_file = CONFIG_DIR / "workflow_context.json"
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
        print(f"-> Ejecutando Suite de Pruebas Dinámicas: {test_cmd}")
        res = subprocess.run(test_cmd, shell=True, cwd=ROOT_DIR)
        if res.returncode != 0:
            raise RuntimeError(f"Fallo en ejecución de pruebas: {res.returncode}")

    qa_report_path = SHARED_POOL / "04_qa_reports" / "QA_REPORT.md"
    if not qa_report_path.exists():
        raise FileNotFoundError(f"Falta el reporte de QA en: {qa_report_path}")

    print(f"-> QA Report validado con éxito en: {qa_report_path}")
    print("\n*** Software Factory: CICLO COMPLETADO Y APROBADO EXITOSAMENTE ***")


def get_pending_requirement():
    """Obtiene el requerimiento pendiente si fue registrado previamente con --init."""
    req_file = SHARED_POOL / "01_prd" / "NEW_REQUIREMENT.txt"
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
    return "Crear una herramienta para consultar el clima por ciudad con cache local y test unitarios"


def run_pipeline(user_requirement: str):
    """Ejecuta el ciclo de vida completo de 4 fases según AGENTS.md."""
    check_environment()
    run_product_manager(user_requirement)
    run_architect()
    run_engineer()
    run_qa_tester()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Software Factory Orchestrator (Gobierno y Ciclo de Vida según AGENTS.md)"
    )
    parser.add_argument("--export", nargs="?", const="", help="Rescata/exporta la aplicación actual a exports/ o ruta indicada")
    parser.add_argument("--reset", action="store_true", help="Limpia y reinicia el ambiente de la fábrica")
    parser.add_argument("--init", metavar="PROJECT_NAME", help="Inicializa el entorno para una nueva aplicación")
    parser.add_argument("--interview", "--grill", nargs="?", const="", metavar="PROMPT",
                        help="Ejecuta la sesión interactiva de Grill-Me (Fase 0) para desgranar un requerimiento")
    parser.add_argument("--non-interactive", action="store_true",
                        help="Ejecuta la entrevista utilizando recomendaciones automáticas (Smart Defaults)")
    parser.add_argument("--ui", action="store_true", help="Inicia el Dashboard Web interactivo en http://localhost:5000")
    parser.add_argument("--status", action="store_true", help="Muestra el estado actual de la fábrica")
    parser.add_argument("--req", help="Requerimiento del usuario para ejecutar o inicializar")
    parser.add_argument("--no-backup", action="store_true", help="No realiza backup automático antes de resetear")

    args = parser.parse_args()

    if args.ui:
        venv_py = ROOT_DIR / ".venv" / "bin" / "python3"
        py_bin = str(venv_py) if venv_py.exists() else sys.executable
        subprocess.run([py_bin, str(ROOT_DIR / "tools" / "dashboard" / "run.py")])
    elif args.export is not None:
        target = args.export if args.export != "" else None
        export_application(target_dir=target)
    elif args.reset:
        reset_environment(backup_first=not args.no_backup)
    elif args.init:
        init_new_project(args.init, requirement=args.req, backup_current=not args.no_backup)
        if args.interview is not None:
            prompt = args.interview if args.interview != "" else (args.req or f"Construir el sistema {args.init}")
            run_discovery(prompt, interactive=not args.non_interactive)
    elif args.interview is not None:
        prompt = args.interview if args.interview != "" else (args.req or get_pending_requirement())
        run_discovery(prompt, interactive=not args.non_interactive)
    elif args.status:
        print_status()
    else:
        req = args.req or get_pending_requirement()
        run_pipeline(req)