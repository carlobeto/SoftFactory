"""
FastAPI Backend para el Dashboard de la Software Factory.
Proporciona endpoints REST para el estado del pipeline, lectura de artefactos,
inspección de ramas de Git y ejecución de operaciones (Grill-Me, Export, Reset, Restore).
"""

import json
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from tools.dashboard.git_service import (
    get_branch_artifacts,
    get_branch_diff,
    get_git_branches,
    get_git_tags,
    restore_branch_into_workspace,
)
from tools.factory_manager import (
    export_application,
    get_current_project_metadata,
    init_new_project,
    reset_environment,
)
from tools.requirements_interviewer import generate_discovery_notes, run_grill_interview

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"
SHARED_POOL = ROOT_DIR / "shared_pool"
WORKSPACE_DIR = ROOT_DIR / "environment" / "workspace"
CONFIG_DIR = ROOT_DIR / "config"
EXPORTS_DIR = ROOT_DIR / "exports"

app = FastAPI(
    title="SoftFactory Control Plane API",
    description="API de administración y monitoreo para la Software Factory",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Modelos Pydantic ---
class InitProjectRequest(BaseModel):
    project_name: str
    requirement: Optional[str] = None


class ExportRequest(BaseModel):
    target_dir: Optional[str] = None


class InterviewRequest(BaseModel):
    prompt: str
    answers: Optional[dict[str, str]] = None


# --- Endpoints de Estado y Artefactos Activos ---

@app.get("/api/status")
def get_factory_status() -> dict[str, Any]:
    """Retorna el estado global de la Software Factory y el workspace activo."""
    meta = get_current_project_metadata()
    context_file = CONFIG_DIR / "workflow_context.json"
    full_context = {}
    if context_file.exists():
        try:
            with open(context_file, "r", encoding="utf-8") as f:
                full_context = json.load(f).get("WORKFLOW_CONTEXT", {})
        except Exception:
            pass

    # Verificación de artefactos
    artifacts_status = {
        "discovery_notes": (SHARED_POOL / "01_prd" / "DISCOVERY_NOTES.md").exists(),
        "prd": (SHARED_POOL / "01_prd" / "PRD.md").exists(),
        "system_design": (SHARED_POOL / "02_system_design" / "SYSTEM_DESIGN.md").exists(),
        "tasks": (SHARED_POOL / "02_system_design" / "TASKS.md").exists(),
        "change_plan": (SHARED_POOL / "03_code_patches" / "CHANGE_PLAN.md").exists(),
        "patch": (SHARED_POOL / "03_code_patches" / "model.patch").exists(),
        "qa_report": (SHARED_POOL / "04_qa_reports" / "QA_REPORT.md").exists(),
    }

    # Archivos del workspace activo
    workspace_files = []
    if WORKSPACE_DIR.exists():
        for path in WORKSPACE_DIR.glob("**/*"):
            if path.is_file() and "__pycache__" not in str(path):
                workspace_files.append(str(path.relative_to(WORKSPACE_DIR)))

    # Exports existentes
    exports = []
    if EXPORTS_DIR.exists():
        exports = [e.name for e in EXPORTS_DIR.iterdir()]

    return {
        "project_metadata": meta,
        "context": full_context,
        "artifacts_status": artifacts_status,
        "workspace_files": workspace_files,
        "exports": exports,
    }


@app.get("/api/artifacts/{artifact_key}")
def get_active_artifact(artifact_key: str):
    """Devuelve el contenido en texto del artefacto solicitado en el workspace activo."""
    mapping = {
        "discovery_notes": SHARED_POOL / "01_prd" / "DISCOVERY_NOTES.md",
        "prd": SHARED_POOL / "01_prd" / "PRD.md",
        "system_design": SHARED_POOL / "02_system_design" / "SYSTEM_DESIGN.md",
        "tasks": SHARED_POOL / "02_system_design" / "TASKS.md",
        "change_plan": SHARED_POOL / "03_code_patches" / "CHANGE_PLAN.md",
        "patch": SHARED_POOL / "03_code_patches" / "model.patch",
        "qa_report": SHARED_POOL / "04_qa_reports" / "QA_REPORT.md",
        "requirement": SHARED_POOL / "01_prd" / "NEW_REQUIREMENT.txt",
    }
    file_path = mapping.get(artifact_key)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Artefacto '{artifact_key}' no encontrado o no generado.")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    return {"artifact_key": artifact_key, "content": content}


# --- Endpoints de Inspección de Git (Ramas y Tags) ---

@app.get("/api/git/overview")
def get_git_overview():
    """Retorna todas las ramas, tags y proyectos históricos reflejados en Git."""
    branches = get_git_branches()
    tags = get_git_tags()
    return {"branches": branches, "tags": tags}


@app.get("/api/git/branch/{branch_name:path}/artifacts")
def get_branch_artifacts_endpoint(branch_name: str):
    """Extrae sin checkout los artefactos generados en una rama histórica de Git."""
    artifacts = get_branch_artifacts(branch_name)
    if not artifacts:
        raise HTTPException(status_code=404, detail=f"No se encontraron artefactos en la rama '{branch_name}'.")
    return {"branch": branch_name, "artifacts": artifacts}


@app.get("/api/git/branch/{branch_name:path}/diff")
def get_branch_diff_endpoint(branch_name: str):
    """Retorna el diff unificado de la rama respecto a la base main."""
    diff = get_branch_diff(branch_name, base_branch="main")
    return {"branch": branch_name, "diff": diff}


@app.post("/api/git/branch/{branch_name:path}/restore")
def restore_branch_endpoint(branch_name: str):
    """Restaura los artefactos y workspace de la rama seleccionada al espacio activo."""
    success, msg = restore_branch_into_workspace(branch_name)
    if not success:
        raise HTTPException(status_code=500, detail=msg)
    return {"success": True, "message": msg}


# --- Endpoints de Acciones Operativas de la Fábrica ---

@app.post("/api/actions/init")
def init_project_endpoint(req: InitProjectRequest):
    """Inicializa la Software Factory para un nuevo proyecto."""
    try:
        init_new_project(req.project_name, requirement=req.requirement, backup_current=True)
        return {"success": True, "message": f"Proyecto '{req.project_name}' inicializado correctamente."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/actions/reset")
def reset_factory_endpoint():
    """Limpia el ambiente de la fábrica creando un respaldo automático previo."""
    try:
        reset_environment(backup_first=True, force=True)
        return {"success": True, "message": "Ambiente de la fábrica reiniciado y respaldado con éxito."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/actions/export")
def export_application_endpoint(req: ExportRequest):
    """Exporta y empaqueta la aplicación generada en exports/."""
    try:
        target, tar = export_application(target_dir=req.target_dir, make_tar=True)
        if not target:
            raise HTTPException(status_code=400, detail="El workspace actual está vacío. Nada que exportar.")
        return {
            "success": True,
            "target_dir": str(target),
            "tar_path": str(tar) if tar else None,
            "message": "Aplicación exportada exitosamente.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/actions/interview")
def run_interview_endpoint(req: InterviewRequest):
    """Ejecuta la elicitación de requerimientos Grill-Me."""
    try:
        if req.answers:
            output_file = SHARED_POOL / "01_prd" / "DISCOVERY_NOTES.md"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            generate_discovery_notes(req.prompt, req.answers, output_file)
            return {"success": True, "message": "Discovery completado y congelado.", "file": str(output_file)}
        else:
            disc_file, answers = run_grill_interview(req.prompt, interactive=False)
            return {"success": True, "answers": answers, "file": str(disc_file)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Servir Frontend Estático
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(STATIC_DIR / "index.html")
