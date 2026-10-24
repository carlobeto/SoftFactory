"""
Módulo de Gestión de Repositorios Git Desacoplados por Proyecto.
Asegura que cada aplicación creada en projects/<Nombre_Proyecto> disponga de su propio
repositorio Git local e independiente (.git), con commits semánticos por etapa y tags de versiones.
"""

import subprocess
from pathlib import Path
from typing import Any, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
PROJECTS_DIR = ROOT_DIR / "projects"


def get_project_dir(project_name: Optional[str] = None) -> Path:
    """Retorna la ruta absoluta del proyecto especificado o del activo."""
    if not project_name:
        active_file = PROJECTS_DIR / ".active_project"
        if active_file.exists():
            name = active_file.read_text(encoding="utf-8").strip()
            if name:
                return PROJECTS_DIR / name
        existing = [p.name for p in PROJECTS_DIR.iterdir() if p.is_dir() and not p.name.startswith(".")]
        name = existing[0] if existing else "app"
    else:
        name = project_name.strip()
    return PROJECTS_DIR / name


def run_project_git(project_name: Optional[str], args: list[str]) -> tuple[int, str, str]:
    """Ejecuta un comando git seguro dentro del directorio exclusivo del proyecto."""
    p_dir = get_project_dir(project_name)
    if not p_dir.exists():
        return 1, "", f"Directorio del proyecto {p_dir} no existe."

    try:
        res = subprocess.run(
            ["git"] + args,
            cwd=p_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def init_project_git(project_name: Optional[str] = None) -> bool:
    """
    Inicializa un repositorio Git local dentro de projects/<project_name>/.git si no existe.
    Configura autor local, .gitignore del proyecto y realiza el commit inicial.
    """
    p_dir = get_project_dir(project_name)
    p_name = p_dir.name
    git_dir = p_dir / ".git"

    if git_dir.exists() and git_dir.is_dir():
        return True

    p_dir.mkdir(parents=True, exist_ok=True)
    code, _, err = run_project_git(p_name, ["init"])
    if code != 0:
        print(f"[Project Git] Error en git init para {p_name}: {err}")
        return False

    # Configuración de autor local del proyecto
    run_project_git(p_name, ["config", "user.name", "SoftFactory Engine"])
    run_project_git(p_name, ["config", "user.email", "softfactory@local"])

    # Crear .gitignore específico del proyecto
    gitignore_file = p_dir / ".gitignore"
    if not gitignore_file.exists():
        gitignore_content = """__pycache__/
*.py[cod]
*$py.class
*.db
.pytest_cache/
*.tar.gz
.venv/
"""
        gitignore_file.write_text(gitignore_content, encoding="utf-8")

    run_project_git(p_name, ["add", "-A"])
    run_project_git(p_name, ["commit", "-m", f"chore(init): initialize project structure for '{p_name}'"])
    print(f"[Project Git] Repositorio Git independiente inicializado en: {git_dir}")
    return True


def commit_project_stage(
    project_name: Optional[str],
    stage_key: str,
    message: str,
    tag: Optional[str] = None,
) -> tuple[bool, str]:
    """
    Registra un commit semántico en el repositorio Git del proyecto para la etapa completada.
    Opcionalmente añade un tag de versión (ej. v1.0.0 al aprobar QA).
    """
    p_name = get_project_dir(project_name).name
    init_project_git(p_name)

    # Añadir cambios de la etapa
    run_project_git(p_name, ["add", "-A"])

    # Verificar si hay cambios
    code, status, _ = run_project_git(p_name, ["status", "--porcelain"])
    if not status:
        return True, "No se detectaron cambios pendientes de confirmar en Git."

    # Confirmar commit
    code, out, err = run_project_git(p_name, ["commit", "-m", message])
    if code != 0:
        return False, f"Fallo al registrar commit: {err}"

    # Crear tag de versión si fue provisto
    if tag:
        clean_tag = tag.strip().replace(" ", "-")
        run_project_git(p_name, ["tag", "-f", "-a", clean_tag, "-m", f"Entrega formal Etapa {stage_key}: {message}"])

    return True, f"Commit '{message}' registrado exitosamente en {p_name}."


def get_project_git_commits(project_name: Optional[str] = None) -> list[dict[str, Any]]:
    """Obtiene los commits del proyecto activo con sus hashes, fechas y mensajes."""
    p_dir = get_project_dir(project_name)
    p_name = p_dir.name

    if not (p_dir / ".git").exists():
        init_project_git(p_name)

    code, out, _ = run_project_git(
        p_name,
        ["log", "-n", "30", "--format=%h|%s|%cr|%an|%D"],
    )
    if code != 0 or not out:
        return []

    commits = []
    for line in out.splitlines():
        parts = line.split("|")
        if len(parts) >= 4:
            commit_hash, subject, date_rel, author = parts[0], parts[1], parts[2], parts[3]
            ref_info = parts[4] if len(parts) > 4 else ""
            commits.append({
                "hash": commit_hash,
                "commit": commit_hash,
                "name": f"commit/{commit_hash}",
                "subject": subject,
                "date": date_rel,
                "author": author,
                "ref_info": ref_info,
                "is_current": len(commits) == 0,
                "is_app_branch": True,
                "type": "checkpoint",
            })
    return commits


def get_project_git_tags(project_name: Optional[str] = None) -> list[dict[str, Any]]:
    """Obtiene la lista de tags (versiones formalizadas) del proyecto activo."""
    p_dir = get_project_dir(project_name)
    p_name = p_dir.name

    if not (p_dir / ".git").exists():
        return []

    code, out, _ = run_project_git(
        p_name,
        ["tag", "-l", "--format=%(refname:short)|%(objectname:short)|%(creatordate:relative)|%(contents:subject)"],
    )
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
                "message": parts[3],
            })
    return tags


def get_file_content_from_commit(
    project_name: Optional[str],
    commit_or_tag: str,
    relative_path: str,
) -> Optional[str]:
    """Extrae el contenido de un archivo en un commit específico usando 'git show'."""
    p_dir = get_project_dir(project_name)
    clean_path = relative_path.lstrip("/")
    code, out, _ = run_project_git(p_dir.name, ["show", f"{commit_or_tag}:{clean_path}"])
    if code == 0:
        return out
    return None


def get_commit_artifacts(project_name: Optional[str], commit_or_tag: str) -> dict[str, str]:
    """Extrae todos los artefactos clave del ciclo de vida para un commit o tag dado."""
    p_name = get_project_dir(project_name).name
    artifacts = {
        "discovery_notes": get_file_content_from_commit(p_name, commit_or_tag, "artifacts/01_prd/DISCOVERY_NOTES.md"),
        "prd": get_file_content_from_commit(p_name, commit_or_tag, "artifacts/01_prd/PRD.md"),
        "system_design": get_file_content_from_commit(p_name, commit_or_tag, "artifacts/02_system_design/SYSTEM_DESIGN.md"),
        "tasks": get_file_content_from_commit(p_name, commit_or_tag, "artifacts/02_system_design/TASKS.md"),
        "change_plan": get_file_content_from_commit(p_name, commit_or_tag, "artifacts/03_code_patches/CHANGE_PLAN.md"),
        "patch": get_file_content_from_commit(p_name, commit_or_tag, "artifacts/03_code_patches/model.patch"),
        "qa_report": get_file_content_from_commit(p_name, commit_or_tag, "artifacts/04_qa_reports/QA_REPORT.md"),
        "workflow_context": get_file_content_from_commit(p_name, commit_or_tag, "workflow_context.json"),
    }
    return {k: v for k, v in artifacts.items() if v is not None}


def get_project_diff(project_name: Optional[str], commit_or_tag: str = "HEAD") -> str:
    """Genera el diferencial unificado de un commit o contra el estado anterior."""
    p_name = get_project_dir(project_name).name
    code, out, _ = run_project_git(p_name, ["show", "--stat", "-p", commit_or_tag])
    if code == 0:
        return out
    return ""


def restore_project_commit(project_name: Optional[str], commit_or_ref: str) -> tuple[bool, str]:
    """Restaura el estado de los archivos del proyecto al commit seleccionado."""
    p_name = get_project_dir(project_name).name
    clean_ref = commit_or_ref.replace("commit/", "").strip()
    code, out, err = run_project_git(p_name, ["checkout", clean_ref, "--", "."])
    if code != 0:
        return False, f"Fallo al restaurar commit {clean_ref}: {err}"
    return True, f"Proyecto '{p_name}' restaurado exitosamente al punto {clean_ref}."
