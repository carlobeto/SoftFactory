"""
FastAPI Backend para el Dashboard de la Software Factory.
Proporciona endpoints REST para el estado del pipeline, lectura de artefactos,
gestión y aislamiento de proyectos en projects/<nombre>, inspección de Git y ejecución de operaciones.
"""

import json
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from tools.dashboard.git_service import (
    commit_project_stage,
    get_branch_artifacts,
    get_branch_diff,
    get_git_branches,
    get_git_tags,
    init_project_git,
    restore_branch_into_workspace,
)
from tools.factory_manager import (
    create_new_project,
    delete_project,
    export_application,
    get_active_project_name,
    get_current_project_metadata,
    get_project_paths,
    init_new_project,
    list_projects,
    reset_environment,
    set_active_project,
)
from tools.dashboard.agent_runners import (
    generate_prd_artifact,
    generate_system_design_artifact,
    run_qa_audit_and_tests,
)
from tools.requirements_interviewer import generate_discovery_notes, run_grill_interview

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"
PROJECTS_DIR = ROOT_DIR / "projects"
CONFIG_DIR = ROOT_DIR / "config"
EXPORTS_DIR = ROOT_DIR / "exports"

app = FastAPI(
    title="SoftFactory Control Plane API",
    description="API de administración, gobernanza y aislamiento de proyectos para la Software Factory",
    version="2.0.0",
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


class SelectProjectRequest(BaseModel):
    project_name: str


class ExportRequest(BaseModel):
    project_name: Optional[str] = None
    target_dir: Optional[str] = None


class InterviewRequest(BaseModel):
    prompt: str
    answers: Optional[dict[str, str]] = None
    reset_first: bool = True
    project_name: Optional[str] = None


class MaintenanceRequest(BaseModel):
    project_name: Optional[str] = None
    request_type: str  # "bugfix" o "rfc"
    title: str
    description: str


# --- Endpoints de Gestión de Proyectos Aislados ---

@app.get("/api/projects")
def get_projects_endpoint() -> dict[str, Any]:
    """Retorna la lista de todos los proyectos creados y el proyecto actualmente activo."""
    active_name = get_active_project_name()
    projs = list_projects()
    return {
        "active_project": active_name,
        "projects": projs,
        "count": len(projs),
    }


@app.post("/api/projects/select")
def select_project_endpoint(req: SelectProjectRequest) -> dict[str, Any]:
    """Cambia el proyecto activo sin modificar ningún archivo de la fábrica."""
    proj_dir = PROJECTS_DIR / req.project_name
    if not proj_dir.exists():
        raise HTTPException(status_code=404, detail=f"El proyecto '{req.project_name}' no existe en projects/.")

    active_name = set_active_project(req.project_name)
    return {
        "success": True,
        "active_project": active_name,
        "message": f"Proyecto '{active_name}' seleccionado como activo.",
    }


@app.post("/api/projects/create")
def create_project_endpoint(req: InitProjectRequest) -> dict[str, Any]:
    """Crea una carpeta de proyecto completamente aislada en projects/<project_name>."""
    try:
        paths = create_new_project(req.project_name, requirement=req.requirement)
        return {
            "success": True,
            "project_name": req.project_name,
            "directory": str(paths["root"]),
            "message": f"Proyecto '{req.project_name}' creado exitosamente en projects/{req.project_name}.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/projects/{project_name}")
def delete_project_endpoint(project_name: str) -> dict[str, Any]:
    """Elimina por completo la carpeta de un proyecto en projects/<project_name>."""
    success = delete_project(project_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"No se pudo eliminar el proyecto '{project_name}'.")

    new_active = get_active_project_name()
    return {
        "success": True,
        "deleted_project": project_name,
        "active_project": new_active,
        "message": f"Proyecto '{project_name}' eliminado. SoftFactory no se modificó.",
    }


# --- Endpoints de Estado y Artefactos del Proyecto Activo ---

@app.get("/api/status")
def get_factory_status(project: Optional[str] = None) -> dict[str, Any]:
    """Retorna el estado global del proyecto activo (o el especificado) y sus archivos."""
    paths = get_project_paths(project)
    pname = paths["project_name"]
    meta = get_current_project_metadata(pname)
    context_file = paths["context"]
    full_context = {}
    if context_file.exists():
        try:
            with open(context_file, "r", encoding="utf-8") as f:
                full_context = json.load(f).get("WORKFLOW_CONTEXT", {})
        except Exception:
            pass

    # Verificación de artefactos en projects/<pname>/artifacts/
    artifacts_status = {
        "discovery_notes": (paths["01_prd"] / "DISCOVERY_NOTES.md").exists(),
        "delta_requirement": (paths["01_prd"] / "DELTA_REQUIREMENT.txt").exists(),
        "prd": (paths["01_prd"] / "PRD.md").exists(),
        "system_design": (paths["02_system_design"] / "SYSTEM_DESIGN.md").exists(),
        "tasks": (paths["02_system_design"] / "TASKS.md").exists(),
        "change_plan": (paths["03_code_patches"] / "CHANGE_PLAN.md").exists(),
        "patch": (paths["03_code_patches"] / "model.patch").exists(),
        "qa_report": (paths["04_qa_reports"] / "QA_REPORT.md").exists(),
    }

    # Archivos del workspace del proyecto activo
    workspace_files = []
    ws_dir = paths["workspace"]
    if ws_dir.exists():
        for path in ws_dir.glob("**/*"):
            if path.is_file() and "__pycache__" not in str(path):
                workspace_files.append(str(path.relative_to(ws_dir)))

    # Exports existentes
    exports = []
    if EXPORTS_DIR.exists():
        exports = [e.name for e in EXPORTS_DIR.iterdir()]

    human_approvals = full_context.get("human_approvals", {
        "discovery_notes": False,
        "prd": False,
        "system_design": False,
        "change_plan": False,
        "code_modification": False,
        "qa_report": False,
    })

    return {
        "active_project": pname,
        "project_directory": str(paths["root"]),
        "project_metadata": meta,
        "context": full_context,
        "artifacts_status": artifacts_status,
        "human_approvals": human_approvals,
        "workspace_files": workspace_files,
        "projects": list_projects(),
        "exports": exports,
    }


@app.get("/api/artifacts/{artifact_key}")
def get_active_artifact(artifact_key: str, project: Optional[str] = None):
    """Devuelve el contenido en texto del artefacto solicitado en el proyecto activo."""
    paths = get_project_paths(project)
    mapping = {
        "discovery_notes": paths["01_prd"] / "DISCOVERY_NOTES.md",
        "delta_requirement": paths["01_prd"] / "DELTA_REQUIREMENT.txt",
        "prd": paths["01_prd"] / "PRD.md",
        "system_design": paths["02_system_design"] / "SYSTEM_DESIGN.md",
        "tasks": paths["02_system_design"] / "TASKS.md",
        "change_plan": paths["03_code_patches"] / "CHANGE_PLAN.md",
        "patch": paths["03_code_patches"] / "model.patch",
        "qa_report": paths["04_qa_reports"] / "QA_REPORT.md",
        "requirement": paths["01_prd"] / "NEW_REQUIREMENT.txt",
    }
    file_path = mapping.get(artifact_key)
    if not file_path or not file_path.exists():
        return {
            "artifact_key": artifact_key,
            "project": paths["project_name"],
            "exists": False,
            "content": "",
            "message": f"Artefacto '{artifact_key}' aún no ha sido generado para el proyecto '{paths['project_name']}'."
        }

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    return {"artifact_key": artifact_key, "project": paths["project_name"], "exists": True, "content": content}


# --- Endpoints de Inspección de Git (Checkpoints, Commits y Tags del Proyecto) ---

@app.get("/api/git/overview")
def get_git_overview(project: Optional[str] = None):
    """Retorna los checkpoints y tags del proyecto activo en projects/<nombre>/.git."""
    pname = project or get_active_project_name()
    branches = get_git_branches(pname)
    tags = get_git_tags(pname)
    return {"project": pname, "branches": branches, "tags": tags}


@app.get("/api/git/branch/{branch_name:path}/artifacts")
def get_branch_artifacts_endpoint(branch_name: str, project: Optional[str] = None):
    """Extrae sin checkout los artefactos generados en un commit del proyecto."""
    pname = project or get_active_project_name()
    artifacts = get_branch_artifacts(branch_name, project_name=pname)
    return {"branch": branch_name, "project": pname, "artifacts": artifacts or {}}


@app.get("/api/git/branch/{branch_name:path}/diff")
def get_branch_diff_endpoint(branch_name: str, project: Optional[str] = None):
    """Retorna el diff unificado del commit o checkpoint seleccionado."""
    pname = project or get_active_project_name()
    diff = get_branch_diff(branch_name, project_name=pname)
    return {"branch": branch_name, "project": pname, "diff": diff}


@app.post("/api/git/branch/{branch_name:path}/restore")
def restore_branch_endpoint(branch_name: str, project: Optional[str] = None):
    """Restaura los artefactos y workspace del commit seleccionado hacia el proyecto."""
    pname = project or get_active_project_name()
    success, msg, proj_name = restore_branch_into_workspace(branch_name, project_name=pname)
    if not success:
        raise HTTPException(status_code=500, detail=msg)
    return {"success": True, "message": msg, "project_name": proj_name}


# --- Endpoints de Acciones Operativas de la Fábrica sobre el Proyecto Activo ---

@app.post("/api/actions/init")
def init_project_endpoint(req: InitProjectRequest):
    """Inicializa la Software Factory para un nuevo proyecto en projects/<project_name>."""
    try:
        paths = create_new_project(req.project_name, requirement=req.requirement)
        return {"success": True, "message": f"Proyecto '{req.project_name}' inicializado en {paths['root']}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/actions/reset")
def reset_factory_endpoint(project: Optional[str] = None):
    """Limpia el ambiente del proyecto activo creando un respaldo automático previo."""
    try:
        paths = get_project_paths(project)
        pname = paths["project_name"]
        reset_environment(project_name=pname, backup_first=True, force=True)
        return {"success": True, "message": f"Proyecto '{pname}' reiniciado y respaldado con éxito. SoftFactory permanece limpia."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/actions/export")
def export_application_endpoint(req: ExportRequest):
    """Exporta y empaqueta la aplicación del proyecto activo hacia exports/."""
    try:
        pname = req.project_name or get_active_project_name()
        target, tar = export_application(project_name=pname, target_dir=req.target_dir, make_tar=True)
        if not target:
            raise HTTPException(status_code=400, detail=f"El workspace del proyecto '{pname}' está vacío. Nada que exportar.")
        return {
            "success": True,
            "project_name": pname,
            "target_dir": str(target),
            "tar_path": str(tar) if tar else None,
            "message": f"Aplicación '{pname}' exportada exitosamente.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/actions/interview")
def run_interview_endpoint(req: InterviewRequest):
    """Ejecuta la elicitación de requerimientos Grill-Me dentro de la carpeta del proyecto."""
    try:
        proj_name = req.project_name or get_active_project_name()
        paths = get_project_paths(proj_name)

        if not paths["root"].exists() or req.reset_first:
            paths = create_new_project(proj_name, requirement=req.prompt)

        output_file = paths["01_prd"] / "DISCOVERY_NOTES.md"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        if req.answers:
            generate_discovery_notes(req.prompt, req.answers, output_file)
            commit_project_stage(proj_name, "discovery_notes", f"feat(discovery): freeze requirements for '{proj_name}'")

            ctx_file = paths["context"]
            if ctx_file.exists():
                try:
                    with open(ctx_file, "r", encoding="utf-8") as f:
                        ctx_data = json.load(f)
                    ctx_data["WORKFLOW_CONTEXT"]["project_metadata"]["status"] = "DISCOVERY_COMPLETED"
                    with open(ctx_file, "w", encoding="utf-8") as f:
                        json.dump(ctx_data, f, indent=4)
                except Exception:
                    pass

            return {
                "success": True,
                "project_name": proj_name,
                "message": f"Discovery completado y congelado para '{proj_name}'.",
                "file": str(output_file),
            }
        else:
            disc_file, answers = run_grill_interview(req.prompt, interactive=False, project_name=proj_name)
            commit_project_stage(proj_name, "discovery_notes", f"feat(discovery): freeze requirements for '{proj_name}'")

            ctx_file = paths["context"]
            if ctx_file.exists():
                try:
                    with open(ctx_file, "r", encoding="utf-8") as f:
                        ctx_data = json.load(f)
                    ctx_data["WORKFLOW_CONTEXT"]["project_metadata"]["status"] = "DISCOVERY_COMPLETED"
                    with open(ctx_file, "w", encoding="utf-8") as f:
                        json.dump(ctx_data, f, indent=4)
                except Exception:
                    pass

            return {
                "success": True,
                "project_name": proj_name,
                "answers": answers,
                "file": str(disc_file),
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/actions/generate/prd")
def generate_prd_endpoint(project: Optional[str] = None):
    """Etapa 2: Genera el Documento de Requerimientos de Producto (PRD.md) para el proyecto activo."""
    try:
        pname = project or get_active_project_name()
        prd_file = generate_prd_artifact(project_name=pname)
        commit_project_stage(pname, "prd", f"feat(prd): generate PRD and acceptance criteria for '{pname}'")
        return {
            "success": True,
            "project_name": pname,
            "message": f"PRD.md generado con éxito por el Product Manager para '{pname}'.",
            "file": str(prd_file),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/actions/generate/system_design")
def generate_system_design_endpoint(project: Optional[str] = None):
    """Etapa 3: Genera la Arquitectura del Sistema (SYSTEM_DESIGN.md y TASKS.md) para el proyecto activo."""
    try:
        pname = project or get_active_project_name()
        design_file, tasks_file = generate_system_design_artifact(project_name=pname)
        commit_project_stage(pname, "system_design", f"feat(design): system design and tasks roadmap for '{pname}'")
        return {
            "success": True,
            "project_name": pname,
            "message": f"Arquitectura y tareas generadas con éxito por el Arquitecto para '{pname}'.",
            "design_file": str(design_file),
            "tasks_file": str(tasks_file),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/actions/run_qa")
def run_qa_endpoint(project: Optional[str] = None):
    """Etapa 5: Ejecuta la auditoría hostil de límites y la suite de tests sobre el proyecto activo."""
    try:
        pname = project or get_active_project_name()
        approved, qa_file = run_qa_audit_and_tests(project_name=pname)
        tag = "v1.0.0" if approved else None
        commit_project_stage(
            pname,
            "qa_report",
            f"chore(qa): {'approved' if approved else 'rejected'} audit and dynamic tests for '{pname}'",
            tag=tag,
        )
        status_label = "APROBADO" if approved else "RECHAZADO"
        return {
            "success": approved,
            "project_name": pname,
            "message": f"Auditoría de QA completada para '{pname}'. Dictamen: {status_label}",
            "file": str(qa_file),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/actions/maintenance")
def submit_maintenance_endpoint(req: MaintenanceRequest):
    """
    Inicia el lazo de mantenimiento o corrección sobre la aplicación activa.
    Preserva el workspace del proyecto y genera un artefacto semilla en DELTA_REQUIREMENT.txt.
    """
    try:
        pname = req.project_name or get_active_project_name()
        paths = get_project_paths(pname)
        req_file = paths["01_prd"] / "DELTA_REQUIREMENT.txt"
        req_file.parent.mkdir(parents=True, exist_ok=True)
        type_str = "Corrección de Defecto / Bugfix" if req.request_type == "bugfix" else "Nuevo Requerimiento / RFC Evolutivo"

        content = f"""# REQUERIMIENTO DE MANTENIMIENTO ({req.request_type.upper()})

**Proyecto:** {pname}
**Título:** {req.title}
**Tipo:** {type_str}

## Descripción Detallada:
{req.description}

## Directiva de la Cadena de Montaje:
1. Preservar intacto el código existente en `projects/{pname}/workspace/`.
2. Etapa 2 (Product Manager): Formular historias Gherkin incrementales en `DELTA_PRD.md`.
3. Etapa 3 (Arquitecto): Estudiar impacto y delimitar archivos autorizados en `TASKS.md`.
4. Etapa 4 (Programador): Implementar parche incremental y actualizar `model.patch`.
5. Etapa 5 (QA & Hostile Auditor): Ejecutar suite de regresión y pruebas de la nueva funcionalidad.
"""
        with open(req_file, "w", encoding="utf-8") as f:
            f.write(content)

        # Actualizar workflow_context.json del proyecto
        context_file = paths["context"]
        if context_file.exists():
            with open(context_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            data.setdefault("WORKFLOW_CONTEXT", {})
            data["WORKFLOW_CONTEXT"].setdefault("project_metadata", {})
            data["WORKFLOW_CONTEXT"]["project_metadata"]["status"] = f"MAINTENANCE_{req.request_type.upper()}"
            data["WORKFLOW_CONTEXT"].setdefault("human_approvals", {})
            data["WORKFLOW_CONTEXT"]["human_approvals"]["code_modification"] = False
            with open(context_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)

        commit_project_stage(
            pname,
            "maintenance",
            f"chore(maintenance): register {req.request_type} - {req.title} for '{pname}'",
        )

        return {
            "success": True,
            "project_name": pname,
            "message": f"Solicitud de {type_str} registrada en {req_file.name}. Se requerirá aprobación humana antes de modificar fuentes.",
            "file": str(req_file),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Endpoints de Aprobación Humana (Human-in-the-Loop Gatekeeper) ---

@app.post("/api/actions/approve/{stage_key}")
def approve_stage_endpoint(stage_key: str, project: Optional[str] = None):
    """Registra la aprobación humana explícita para una etapa del ciclo de vida del proyecto activo."""
    valid_stages = ["discovery_notes", "prd", "system_design", "change_plan", "code_modification", "qa_report"]
    if stage_key not in valid_stages:
        raise HTTPException(status_code=400, detail=f"Clave de etapa no válida para aprobación: '{stage_key}'")

    paths = get_project_paths(project)
    context_file = paths["context"]
    ctx = {}
    if context_file.exists():
        with open(context_file, "r", encoding="utf-8") as f:
            ctx = json.load(f)
    ctx.setdefault("WORKFLOW_CONTEXT", {})
    ctx["WORKFLOW_CONTEXT"].setdefault("human_approvals", {})
    ctx["WORKFLOW_CONTEXT"]["human_approvals"][stage_key] = True

    with open(context_file, "w", encoding="utf-8") as f:
        json.dump(ctx, f, indent=4)

    label_map = {
        "discovery_notes": "Etapa 1: Discovery & Grilling",
        "prd": "Etapa 2: Product Manager (PRD)",
        "system_design": "Etapa 3: Arquitecto (System Design)",
        "change_plan": "Etapa 4: Plan de Cambios",
        "code_modification": "Compuerta de Modificación de Fuentes",
        "qa_report": "Etapa 5: QA Hostile Auditor",
    }
    label = label_map.get(stage_key, stage_key)
    return {
        "success": True,
        "project_name": paths["project_name"],
        "message": f"'{label}' aprobada formalmente por el usuario humano.",
        "stage_key": stage_key,
        "human_approvals": ctx["WORKFLOW_CONTEXT"]["human_approvals"],
    }


@app.post("/api/actions/revoke/{stage_key}")
def revoke_approval_endpoint(stage_key: str, project: Optional[str] = None):
    """Revoca la aprobación de una etapa solicitando ajustes al agente para el proyecto activo."""
    paths = get_project_paths(project)
    context_file = paths["context"]
    ctx = {}
    if context_file.exists():
        with open(context_file, "r", encoding="utf-8") as f:
            ctx = json.load(f)
    ctx.setdefault("WORKFLOW_CONTEXT", {})
    ctx["WORKFLOW_CONTEXT"].setdefault("human_approvals", {})
    ctx["WORKFLOW_CONTEXT"]["human_approvals"][stage_key] = False

    with open(context_file, "w", encoding="utf-8") as f:
        json.dump(ctx, f, indent=4)

    return {
        "success": True,
        "project_name": paths["project_name"],
        "message": f"Aprobación revocada para '{stage_key}'. Se solicitarán ajustes.",
        "stage_key": stage_key,
        "human_approvals": ctx["WORKFLOW_CONTEXT"]["human_approvals"],
    }


@app.get("/api/actions/preflight_code_check")
def preflight_code_check_endpoint(project: Optional[str] = None):
    """Retorna el informe previo de impacto para la autorización humana de modificación de fuentes."""
    paths = get_project_paths(project)
    pname = paths["project_name"]
    context_file = paths["context"]
    ctx = {}
    if context_file.exists():
        with open(context_file, "r", encoding="utf-8") as f:
            ctx = json.load(f).get("WORKFLOW_CONTEXT", {})

    boundaries = ctx.get("file_boundaries_template", {})
    approvals = ctx.get("human_approvals", {})
    meta = ctx.get("project_metadata", {})

    delta_file = paths["01_prd"] / "DELTA_REQUIREMENT.txt"
    delta_text = ""
    if delta_file.exists():
        with open(delta_file, "r", encoding="utf-8") as f:
            delta_text = f.read()

    change_plan_file = paths["03_code_patches"] / "CHANGE_PLAN.md"
    plan_text = ""
    if change_plan_file.exists():
        with open(change_plan_file, "r", encoding="utf-8") as f:
            plan_text = f.read()

    return {
        "project_name": pname,
        "project_directory": str(paths["root"]),
        "status": meta.get("status", "INITIALIZED"),
        "allowed_to_touch": boundaries.get("allowed_to_touch", [f"projects/{pname}/workspace/*"]),
        "strictly_forbidden": boundaries.get("strictly_forbidden", []),
        "forbidden_directories": boundaries.get("strictly_forbidden", []),
        "is_code_approved": approvals.get("code_modification", False),
        "delta_requirement": delta_text,
        "change_plan": plan_text,
    }


# Servir Frontend Estático
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(STATIC_DIR / "index.html")
