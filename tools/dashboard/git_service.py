"""
Servicio Git para el Dashboard de la Software Factory.
Permite inspeccionar ramas, tags, historial y extraer artefactos históricos
utilizando 'git show' sin necesidad de modificar el workspace de trabajo.
"""

import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


def run_git_command(args: list[str]) -> tuple[int, str, str]:
    """Ejecuta un comando git seguro en el repositorio raíz."""
    try:
        res = subprocess.run(
            ["git"] + args,
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            check=False,
        )
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def get_git_branches() -> list[dict]:
    """Obtiene la lista de ramas locales con sus metadatos y commits recientes."""
    code, out, _ = run_git_command(["branch", "--format=%(refname:short)|%(objectname:short)|%(authordate:relative)|%(subject)"])
    if code != 0 or not out:
        return []

    branches = []
    current_code, current_branch, _ = run_git_command(["branch", "--show-current"])
    active_branch = current_branch if current_code == 0 else "main"

    for line in out.splitlines():
        parts = line.split("|")
        if len(parts) >= 4:
            name, commit_hash, date_rel, subject = parts[0], parts[1], parts[2], parts[3]
            is_app = name.startswith("app/") or name.startswith("feature/")
            branches.append({
                "name": name,
                "commit": commit_hash,
                "date": date_rel,
                "subject": subject,
                "is_current": (name == active_branch),
                "is_app_branch": is_app,
                "type": "application" if is_app else "system"
            })
    return branches


def get_git_tags() -> list[dict]:
    """Obtiene la lista de tags (versiones y entregas de aplicaciones)."""
    code, out, _ = run_git_command(["tag", "-l", "--format=%(refname:short)|%(objectname:short)|%(creatordate:relative)|%(contents:subject)"])
    if code != 0 or not out:
        return []

    tags = []
    for line in out.splitlines():
        parts = line.split("|")
        if len(parts) >= 4:
            tags.append({
                "tag": parts[0],
                "commit": parts[1],
                "date": parts[2],
                "message": parts[3]
            })
    return tags


def get_file_content_from_branch(branch_or_tag: str, relative_path: str) -> str | None:
    """Extrae el contenido de cualquier archivo en una rama específica usando 'git show'."""
    clean_path = relative_path.lstrip("/")
    code, out, _ = run_git_command(["show", f"{branch_or_tag}:{clean_path}"])
    if code == 0:
        return out
    return None


def get_branch_artifacts(branch_name: str) -> dict:
    """Extrae todos los artefactos clave del ciclo de vida para una rama dada."""
    artifacts = {
        "discovery_notes": get_file_content_from_branch(branch_name, "shared_pool/01_prd/DISCOVERY_NOTES.md"),
        "prd": get_file_content_from_branch(branch_name, "shared_pool/01_prd/PRD.md"),
        "system_design": get_file_content_from_branch(branch_name, "shared_pool/02_system_design/SYSTEM_DESIGN.md"),
        "tasks": get_file_content_from_branch(branch_name, "shared_pool/02_system_design/TASKS.md"),
        "change_plan": get_file_content_from_branch(branch_name, "shared_pool/03_code_patches/CHANGE_PLAN.md"),
        "patch": get_file_content_from_branch(branch_name, "shared_pool/03_code_patches/model.patch"),
        "qa_report": get_file_content_from_branch(branch_name, "shared_pool/04_qa_reports/QA_REPORT.md"),
        "workflow_context": get_file_content_from_branch(branch_name, "config/workflow_context.json"),
    }
    return {k: v for k, v in artifacts.items() if v is not None}


def get_branch_diff(branch_name: str, base_branch: str = "main") -> str:
    """Genera el diferencial unificado entre una rama de aplicación y la rama base."""
    code, out, _ = run_git_command(["diff", f"{base_branch}...{branch_name}"])
    if code == 0:
        return out
    return ""


def restore_branch_into_workspace(branch_name: str) -> tuple[bool, str]:
    """
    Restaura los contenidos del proyecto guardado en branch_name hacia el workspace actual.
    Preserva la seguridad de la fábrica realizando respaldo previo.
    """
    try:
        from tools.factory_manager import export_application, reset_environment
        # 1. Backup de seguridad
        export_application(make_tar=True)
        # 2. Limpieza segura
        reset_environment(backup_first=False, force=True)

        # 3. Checkout de los directorios de artefactos y workspace de la rama seleccionada
        targets = ["environment/workspace", "shared_pool", "config/workflow_context.json"]
        for target in targets:
            code, _, err = run_git_command(["checkout", branch_name, "--", target])
            if code != 0:
                return False, f"Error restaurando {target}: {err}"

        return True, f"Proyecto de la rama '{branch_name}' cargado exitosamente en el Workspace."
    except Exception as e:
        return False, f"Excepción durante la restauración: {str(e)}"
