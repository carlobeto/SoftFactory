"""
FastAPI Backend para el Dashboard de la Software Factory.
Proporciona endpoints REST para el estado del pipeline, lectura de artefactos,
gestión y aislamiento de proyectos en projects/<nombre>, inspección de Git y ejecución de operaciones.
"""

import json
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Diccionario de procesos de prueba en ejecución: project_name -> dict
APP_PROCESSES: dict[str, dict[str, Any]] = {}


def find_free_port(start_port: int = 8000, max_port: int = 8999) -> int:
    """Encuentra un puerto libre en el rango evitando el puerto 5000 del dashboard."""
    for p in range(start_port, max_port):
        if p == 5000:
            continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    raise RuntimeError("No se encontró ningún puerto libre en el rango 8000-8999")


def is_app_running(project_name: str) -> Optional[dict[str, Any]]:
    """Verifica si el servidor de prueba de un proyecto está activo y respondiendo."""
    info = APP_PROCESSES.get(project_name)
    if not info:
        return None
    proc = info.get("proc")
    if proc is not None and proc.poll() is None:
        port = info.get("port")
        if port:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.3)
                    if s.connect_ex(("127.0.0.1", port)) == 0:
                        return {
                            "running": True,
                            "project_name": project_name,
                            "port": port,
                            "url": info.get("url", f"http://localhost:{port}"),
                            "pid": proc.pid,
                        }
            except Exception:
                pass
        return {
            "running": True,
            "project_name": project_name,
            "port": port,
            "url": info.get("url", f"http://localhost:{port}"),
            "pid": proc.pid,
        }
    APP_PROCESSES.pop(project_name, None)
    return None

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
    get_workflow_context,
    init_new_project,
    list_projects,
    reset_environment,
    set_active_project,
)
from tools.dashboard.agent_runners import (
    generate_code_implementation,
    generate_local_runner_artifact,
    generate_prd_artifact,
    generate_system_design_artifact,
    run_qa_audit_and_tests,
)
from tools.requirements_interviewer import (
    generate_discovery_notes,
    parse_discovery_notes,
    run_grill_interview,
)
from tools.skill_loader import (
    approve_project_skill,
    approve_promotion,
    delete_project_skill,
    discover_skills,
    get_factory_info,
    list_lessons,
    list_promotion_proposals,
    propose_project_skill,
    propose_promotion,
    register_lesson,
    revoke_project_skill,
)

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


class ProposeSkillRequest(BaseModel):
    name: str
    description: str
    applies_to_stages: list[str]
    instructions_md: str
    type: str = "project_skill"
    structured_data: Optional[dict[str, Any]] = None
    project_name: Optional[str] = None


class RegisterLessonRequest(BaseModel):
    stage: str = "general"
    symptom: str
    root_cause: str = ""
    target: str = "engine"
    proposal: str = ""
    project_name: Optional[str] = None



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
        "local_runner": (paths["05_local_runner"] / "LOCAL_TESTING_SPEC.md").exists(),
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
        "local_runner": False,
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
        "running_app": is_app_running(pname),
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
        "local_runner": paths["05_local_runner"] / "LOCAL_TESTING_SPEC.md",
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

    resp = {"artifact_key": artifact_key, "project": paths["project_name"], "exists": True, "content": content}
    if artifact_key == "discovery_notes":
        try:
            resp["parsed_answers"] = parse_discovery_notes(content)
        except Exception:
            resp["parsed_answers"] = None
    return resp


@app.get("/api/projects/{project_name:path}/discovery-answers")
def get_project_discovery_answers(project_name: str):
    """Retorna las respuestas estructuradas ya extraídas de DISCOVERY_NOTES.md para pre-cargar el asistente Grill-Me."""
    paths = get_project_paths(project_name)
    discovery_file = paths["01_prd"] / "DISCOVERY_NOTES.md"
    if not discovery_file.exists():
        return {"exists": False, "answers": None, "project": paths["project_name"]}
    with open(discovery_file, "r", encoding="utf-8") as f:
        content = f.read()
    return {"exists": True, "answers": parse_discovery_notes(content), "project": paths["project_name"]}


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


def get_project_approvals(context_file: Path) -> dict[str, bool]:
    """Lee el diccionario de aprobaciones humanas del archivo workflow_context.json."""
    if not context_file.exists():
        return {}
    try:
        with open(context_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("WORKFLOW_CONTEXT", {}).get("human_approvals", {})
    except Exception:
        return {}


def validate_stage_execution(stage_key: str, project_paths: dict[str, Any], is_new_project: bool = False):
    """
    Valida las reglas estrictas de gobernanza para la generación de etapas:
    Regla A: NO se puede generar el documento correspondiente si está APROBADO (debe revocarse primero).
    Regla B: NO se puede generar si no existe el documento del paso anterior o no está APROBADO.
    """
    if is_new_project and stage_key == "discovery_notes":
        return

    approvals = get_project_approvals(project_paths["context"])

    # 1. Regla A: Si la etapa actual ya está aprobada, se bloquea la regeneración hasta que se revoque.
    if approvals.get(stage_key, False):
        stage_names = {
            "discovery_notes": "Etapa 1 (Discovery & Grilling)",
            "prd": "Etapa 2 (Product Manager - PRD)",
            "system_design": "Etapa 3 (Arquitecto - System Design)",
            "code_modification": "Etapa 4 (Programador - Código)",
            "qa_report": "Etapa 5 (QA Hostile Auditor)",
            "local_runner": "Etapa 6 (Runner Local - Testing PC)",
        }
        # Caso especial para code_modification: si el workspace está vacío o no existe parche, es la primera ejecución autorizada
        if stage_key == "code_modification":
            ws = project_paths["workspace"]
            has_files = ws.exists() and any(ws.iterdir())
            patch_file = project_paths["03_code_patches"] / "model.patch"
            if not has_files or not patch_file.exists():
                pass  # Permitir la primera generación de código
            else:
                name = stage_names.get(stage_key, stage_key)
                raise HTTPException(
                    status_code=400,
                    detail=f"No se puede regenerar '{name}': El código ya se encuentra implementado y APROBADO formalmente. "
                           f"Para regenerar este código, primero debes revocar la aprobación existente."
                )
        else:
            name = stage_names.get(stage_key, stage_key)
            raise HTTPException(
                status_code=400,
                detail=f"No se puede regenerar '{name}': La etapa ya se encuentra APROBADA formalmente. "
                       f"Para regenerar este documento, primero debes revocar la aprobación existente."
            )

    # 2. Regla B: Predecesores obligatorios (deben existir y estar en estado 3: Aprobado).
    predecessors = {
        "discovery_notes": None,
        "prd": {
            "key": "discovery_notes",
            "file": project_paths["01_prd"] / "DISCOVERY_NOTES.md",
            "name": "Etapa 1 (Discovery & Grilling)",
            "doc": "DISCOVERY_NOTES.md",
        },
        "system_design": {
            "key": "prd",
            "file": project_paths["01_prd"] / "PRD.md",
            "name": "Etapa 2 (Product Manager)",
            "doc": "PRD.md",
        },
        "code_modification": {
            "key": "system_design",
            "file": project_paths["02_system_design"] / "SYSTEM_DESIGN.md",
            "name": "Etapa 3 (Arquitecto)",
            "doc": "SYSTEM_DESIGN.md",
        },
        "qa_report": {
            "key": "code_modification",
            "file": project_paths["03_code_patches"] / "model.patch",
            "name": "Etapa 4 (Programador - Código)",
            "doc": "código / model.patch",
        },
        "local_runner": {
            "key": "qa_report",
            "file": project_paths["04_qa_reports"] / "QA_REPORT.md",
            "name": "Etapa 5 (QA & Hostile Auditor)",
            "doc": "QA_REPORT.md",
        },
    }

    pred = predecessors.get(stage_key)
    if pred:
        # Verificar existencia del documento anterior
        if pred["file"] and not pred["file"].exists():
            if stage_key == "qa_report":
                ws = project_paths["workspace"]
                has_files = ws.exists() and any(ws.iterdir())
                if not has_files and not pred["file"].exists():
                    raise HTTPException(
                        status_code=400,
                        detail=f"No se puede proceder con la etapa: No existe el documento de la etapa anterior ({pred['doc']})."
                    )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"No se puede proceder con la etapa: No existe el documento de la etapa anterior ({pred['doc']})."
                )

        # Verificar aprobación del paso anterior (Estado 3: Aprobado)
        if not approvals.get(pred["key"], False):
            raise HTTPException(
                status_code=400,
                detail=f"Bloqueado: La {pred['name']} aún no ha sido APROBADA formalmente por el usuario humano. "
                       f"Hasta que no esté en estado 'Aprobado', no se puede ejecutar ninguna etapa posterior."
            )


@app.post("/api/actions/interview")
def run_interview_endpoint(req: InterviewRequest):
    """Ejecuta la elicitación de requerimientos Grill-Me dentro de la carpeta del proyecto."""
    try:
        proj_name = req.project_name or get_active_project_name()
        paths = get_project_paths(proj_name)
        set_active_project(paths["project_name"])

        if not paths["root"].exists() or req.reset_first:
            paths = create_new_project(proj_name, requirement=req.prompt)
        else:
            # Si el usuario ejecuta la toma de datos sobre un proyecto existente,
            # esto constituye una generación/regeneración de la Etapa 1.
            # Según la Regla de Revocación o Regeneración en AGENTS.md, si ya estaba aprobada,
            # se revoca e invalida en cascada todas las etapas posteriores.
            approvals = get_project_approvals(paths["context"])
            if approvals.get("discovery_notes", False):
                from tools.skill_loader import invalidate_from_stage
                invalidate_from_stage(proj_name, "prd", "Regeneración de Discovery (Etapa 1)")
                ctx_file = paths["context"]
                if ctx_file.exists():
                    try:
                        with open(ctx_file, "r", encoding="utf-8") as f:
                            ctx_data = json.load(f)
                        ctx_data["WORKFLOW_CONTEXT"].setdefault("human_approvals", {})["discovery_notes"] = False
                        with open(ctx_file, "w", encoding="utf-8") as f:
                            json.dump(ctx_data, f, indent=4)
                    except Exception:
                        pass
            else:
                validate_stage_execution("discovery_notes", paths, is_new_project=False)

        output_file = paths["01_prd"] / "DISCOVERY_NOTES.md"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        if req.answers:
            generate_discovery_notes(req.prompt, req.answers, output_file, project_name=proj_name)
            commit_project_stage(proj_name, "discovery_notes", f"feat(discovery): freeze requirements for '{proj_name}'")

            from tools.skill_loader import invalidate_from_stage
            invalidate_from_stage(proj_name, "prd", "Regeneración de Discovery (Etapa 1)")

            ctx_file = paths["context"]
            if ctx_file.exists():
                try:
                    with open(ctx_file, "r", encoding="utf-8") as f:
                        ctx_data = json.load(f)
                    ctx_data["WORKFLOW_CONTEXT"]["project_metadata"]["status"] = "DISCOVERY_COMPLETED"
                    ctx_data["WORKFLOW_CONTEXT"].setdefault("human_approvals", {})["discovery_notes"] = False
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

            from tools.skill_loader import invalidate_from_stage
            invalidate_from_stage(proj_name, "prd", "Regeneración de Discovery (Etapa 1)")

            ctx_file = paths["context"]
            if ctx_file.exists():
                try:
                    with open(ctx_file, "r", encoding="utf-8") as f:
                        ctx_data = json.load(f)
                    ctx_data["WORKFLOW_CONTEXT"]["project_metadata"]["status"] = "DISCOVERY_COMPLETED"
                    ctx_data["WORKFLOW_CONTEXT"].setdefault("human_approvals", {})["discovery_notes"] = False
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/grill/questions")
def get_grill_questions(project: Optional[str] = None):
    """Devuelve las rondas del árbol de preguntas (Design Tree Frontier) y los skills activos para la Etapa 1."""
    pname = project or get_active_project_name()
    try:
        from tools.requirements_interviewer import load_question_tree
        from tools.skill_loader import get_stage_skills
        stage_skills = get_stage_skills("discovery_notes", pname)
        skills_summary = [
            {
                "name": s.name,
                "version": s.version,
                "scope": s.scope,
                "type": s.skill_type,
                "description": s.description,
            }
            for s in stage_skills
        ]
        rounds = load_question_tree(pname)
        return {
            "project_name": pname,
            "stage": "discovery_notes",
            "skills": skills_summary,
            "rounds": rounds,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cargando preguntas de Grill-Me: {e}")


@app.get("/api/stages/{stage_name}/skills")
def get_stage_skills_endpoint(stage_name: str, project: Optional[str] = None):
    """Retorna los skills activos y requeridos para una etapa específica del ciclo de vida."""
    pname = project or get_active_project_name()
    try:
        from tools.skill_loader import get_stage_skills, get_profile_skill_manifest
        stage_skills = get_stage_skills(stage_name, pname)
        manifest = get_profile_skill_manifest(stage_name)
        return {
            "stage": stage_name,
            "project_name": pname,
            "required": manifest.get("required", []),
            "optional": manifest.get("optional", []),
            "active_skills": [
                {
                    "name": s.name,
                    "version": s.version,
                    "scope": s.scope,
                    "type": s.skill_type,
                    "description": s.description,
                }
                for s in stage_skills
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/actions/generate/prd")
def generate_prd_endpoint(project: Optional[str] = None):
    """Etapa 2: Genera el Documento de Requerimientos de Producto (PRD.md) para el proyecto activo."""
    try:
        pname = project or get_active_project_name()
        paths = get_project_paths(pname)
        validate_stage_execution("prd", paths)

        # Invalida las etapas posteriores para que deban ser regeneradas con el nuevo PRD
        from tools.skill_loader import invalidate_from_stage
        invalidate_from_stage(pname, "system_design", "Regeneración del PRD (Etapa 2)")

        prd_file = generate_prd_artifact(project_name=pname)
        commit_project_stage(pname, "prd", f"feat(prd): generate PRD and acceptance criteria for '{pname}'")
        return {
            "success": True,
            "project_name": pname,
            "message": f"PRD.md generado con éxito por el Product Manager para '{pname}'.",
            "file": str(prd_file),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/actions/generate/system_design")
def generate_system_design_endpoint(project: Optional[str] = None):
    """Etapa 3: Genera la Arquitectura del Sistema (SYSTEM_DESIGN.md y TASKS.md) para el proyecto activo."""
    try:
        pname = project or get_active_project_name()
        paths = get_project_paths(pname)
        validate_stage_execution("system_design", paths)

        # Invalida las etapas posteriores para que deban ser regeneradas con el nuevo diseño
        from tools.skill_loader import invalidate_from_stage
        invalidate_from_stage(pname, "code_modification", "Regeneración de Arquitectura y Tareas (Etapa 3)")

        design_file, tasks_file = generate_system_design_artifact(project_name=pname)
        commit_project_stage(pname, "system_design", f"feat(design): system design and tasks roadmap for '{pname}'")
        return {
            "success": True,
            "project_name": pname,
            "message": f"Arquitectura y tareas generadas con éxito por el Arquitecto para '{pname}'.",
            "design_file": str(design_file),
            "tasks_file": str(tasks_file),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/actions/generate/code")
def generate_code_endpoint(project: Optional[str] = None):
    """Etapa 4: El Programador implementa el código en workspace y emite CHANGE_PLAN.md y model.patch."""
    try:
        pname = project or get_active_project_name()
        paths = get_project_paths(pname)
        validate_stage_execution("code_modification", paths)

        # Invalida las etapas posteriores de QA y Runner local ante nuevo código
        from tools.skill_loader import invalidate_from_stage
        invalidate_from_stage(pname, "qa_report", "Nueva implementación de código en workspace (Etapa 4)")

        change_plan_path, patch_path, generated_files = generate_code_implementation(project_name=pname)
        commit_project_stage(pname, "code_modification", f"feat(code): implement source code, change plan and tests for '{pname}'")

        return {
            "success": True,
            "project_name": pname,
            "message": f"Código fuente implementado con éxito por el Programador para '{pname}' ({len(generated_files)} archivos creados en workspace).",
            "files": generated_files,
            "change_plan": str(change_plan_path),
            "patch": str(patch_path),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/actions/run_qa")
def run_qa_endpoint(project: Optional[str] = None):
    """Etapa 5: Ejecuta la auditoría hostil de límites y la suite de tests sobre el proyecto activo."""
    try:
        pname = project or get_active_project_name()
        paths = get_project_paths(pname)
        validate_stage_execution("qa_report", paths)

        # Invalida las etapas posteriores al correr nueva auditoría de QA
        from tools.skill_loader import invalidate_from_stage
        invalidate_from_stage(pname, "local_runner", "Nueva auditoría de QA ejecutada (Etapa 5)")

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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/actions/generate/local_runner")
def generate_local_runner_endpoint(project: Optional[str] = None):
    """Etapa 6: Entorno de Pruebas Local para la PC de Desarrollo."""
    try:
        pname = project or get_active_project_name()
        paths = get_project_paths(pname)
        validate_stage_execution("local_runner", paths)

        # Invalida la etapa de deploy cloud ante nuevo runner local
        from tools.skill_loader import invalidate_from_stage
        invalidate_from_stage(pname, "deploy", "Regeneración de Entorno Local (Etapa 6)")

        spec_path, runner_path = generate_local_runner_artifact(project_name=pname)
        commit_project_stage(
            pname,
            "local_runner",
            f"feat(local-runner): setup local test environment and runner for '{pname}'"
        )

        return {
            "success": True,
            "project_name": pname,
            "message": f"Entorno de pruebas local generado con éxito para '{pname}'. Servidor de prueba y sandbox listos en workspace/local_runner.py.",
            "spec_file": str(spec_path),
            "runner_file": str(runner_path),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Endpoints de Ejecución y Prueba en Vivo de la Aplicación en Workspace ---

@app.post("/api/actions/app/start")
def start_app_endpoint(project: Optional[str] = None):
    """
    Inicia el servidor de prueba local del proyecto en segundo plano y abre la URL
    en el navegador predeterminado (o retorna la URL para carga en el frontend).
    Utiliza preferentemente workspace/local_runner.py (Etapa 6) o workspace/main.py.
    """
    try:
        pname = project or get_active_project_name()
        paths = get_project_paths(pname)
        set_active_project(paths["project_name"])
        ws_dir = paths["workspace"]

        # Compuerta Humana Crítica: Requiere que la Etapa 6 (local_runner) esté formalmente APROBADA
        approvals = get_project_approvals(paths["context"])
        if not approvals.get("local_runner", False):
            raise HTTPException(
                status_code=400,
                detail=f"No se puede iniciar el servidor de prueba para '{pname}': "
                       f"La Etapa 6 (Entorno de Pruebas Local) debe estar formalmente APROBADA por el usuario antes de probar la aplicación."
            )

        # Determinar punto de entrada: preferir local_runner.py (Etapa 6), con fallback a main.py
        runner_file = ws_dir / "local_runner.py"
        if not runner_file.exists():
            runner_file = ws_dir / "main.py"

        if not ws_dir.exists() or not runner_file.exists():
            raise HTTPException(
                status_code=400,
                detail=f"No se puede iniciar el servidor de prueba: No existe 'local_runner.py' ni 'main.py' en projects/{pname}/workspace/. "
                       f"Asegúrate de generar la Etapa 6 (Runner Local) primero."
            )

        # Si ya se encuentra activo y respondiendo, reutilizarlo y abrir el navegador
        running_info = is_app_running(pname)
        if running_info:
            url = running_info["url"]
            return {
                "success": True,
                "project_name": pname,
                "port": running_info["port"],
                "url": url,
                "pid": running_info["pid"],
                "already_running": True,
                "message": f"La aplicación '{pname}' ya se encuentra activa en {url} y fue abierta en tu navegador."
            }

        # Encontrar puerto libre (evitando el 5000 del dashboard)
        port = find_free_port(start_port=8000, max_port=8999)
        url = f"http://localhost:{port}"

        # Levantar el backend de prueba con el intérprete de Python activo
        python_bin = sys.executable
        proc = subprocess.Popen(
            [python_bin, str(runner_file.resolve()), "--port", str(port)],
            cwd=str(ws_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )

        APP_PROCESSES[pname] = {
            "proc": proc,
            "pid": proc.pid,
            "port": port,
            "url": url,
            "project_name": pname,
        }

        # Esperar hasta 2.5s a que el servidor enlace el puerto
        started = False
        for _ in range(25):
            time.sleep(0.1)
            if proc.poll() is not None:
                # Proceso terminó inesperadamente
                _, err = proc.communicate(timeout=1)
                err_text = err.decode("utf-8", errors="replace") if err else "Proceso finalizado prematuramente."
                APP_PROCESSES.pop(pname, None)
                raise HTTPException(
                    status_code=500,
                    detail=f"Fallo al levantar el servidor de '{pname}': {err_text}"
                )
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.15)
                    if s.connect_ex(("127.0.0.1", port)) == 0:
                        started = True
                        break
            except Exception:
                pass

        # Abrir en el navegador predeterminado: delegado al frontend (window.open) para evitar ventanas duplicadas

        return {
            "success": True,
            "project_name": pname,
            "port": port,
            "url": url,
            "pid": proc.pid,
            "already_running": False,
            "message": f"Servidor de prueba para '{pname}' levantado con éxito en {url} y cargado en el navegador."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/actions/app/status")
def get_app_status_endpoint(project: Optional[str] = None):
    """Retorna si el servidor de prueba del proyecto está activo y su puerto/URL."""
    pname = project or get_active_project_name()
    running_info = is_app_running(pname)
    if running_info:
        return {
            "running": True,
            "project_name": pname,
            "port": running_info["port"],
            "url": running_info["url"],
            "pid": running_info["pid"],
        }
    return {
        "running": False,
        "project_name": pname,
        "port": None,
        "url": None,
        "pid": None,
    }


def terminate_app_process(pname: str) -> bool:
    """Detiene el proceso en segundo plano de la aplicación de prueba si está activo."""
    info = APP_PROCESSES.pop(pname, None)
    if info:
        proc = info.get("proc")
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        return True
    return False


@app.post("/api/actions/app/stop")
def stop_app_endpoint(project: Optional[str] = None):
    """Detiene el servidor de prueba del proyecto si está en ejecución."""
    pname = project or get_active_project_name()
    stopped = terminate_app_process(pname)
    if stopped:
        return {"success": True, "message": f"Servidor de prueba de '{pname}' detenido."}
    return {"success": True, "message": f"No había ningún servidor activo para '{pname}'."}


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
    valid_stages = ["discovery_notes", "prd", "system_design", "change_plan", "code_modification", "qa_report", "local_runner", "deploy"]
    if stage_key not in valid_stages:
        raise HTTPException(status_code=400, detail=f"Clave de etapa no válida para aprobación: '{stage_key}'")

    paths = get_project_paths(project)
    set_active_project(paths["project_name"])
    approvals = get_project_approvals(paths["context"])

    # Regla: hasta que la etapa anterior no esté en estado 3 (Aprobado), no se puede aprobar una etapa posterior
    predecessors = {
        "prd": ("discovery_notes", "Etapa 1 (Discovery & Grilling)"),
        "system_design": ("prd", "Etapa 2 (Product Manager - PRD)"),
        "change_plan": ("system_design", "Etapa 3 (Arquitecto - System Design)"),
        "code_modification": ("system_design", "Etapa 3 (Arquitecto - System Design)"),
        "qa_report": ("code_modification", "Etapa 4 (Programador - Código)"),
        "local_runner": ("qa_report", "Etapa 5 (QA & Hostile Auditor)"),
        "deploy": ("local_runner", "Etapa 6 (Entorno de Pruebas Local)"),
    }
    pred = predecessors.get(stage_key)
    if pred and not approvals.get(pred[0], False):
        raise HTTPException(
            status_code=400,
            detail=f"No se puede aprobar esta etapa: La {pred[1]} debe estar Aprobada primero (Estado 3)."
        )

    context_file = paths["context"]
    ctx = {}
    if context_file.exists():
        with open(context_file, "r", encoding="utf-8") as f:
            ctx = json.load(f)
    ctx.setdefault("WORKFLOW_CONTEXT", {})
    ctx["WORKFLOW_CONTEXT"].setdefault("human_approvals", {})
    ctx["WORKFLOW_CONTEXT"]["human_approvals"][stage_key] = True
    if stage_key == "code_modification":
        ctx["WORKFLOW_CONTEXT"]["human_approvals"]["change_plan"] = True
    elif stage_key == "change_plan":
        ctx["WORKFLOW_CONTEXT"]["human_approvals"]["code_modification"] = True

    with open(context_file, "w", encoding="utf-8") as f:
        json.dump(ctx, f, indent=4)

    label_map = {
        "discovery_notes": "Etapa 1: Discovery & Grilling",
        "prd": "Etapa 2: Product Manager (PRD)",
        "system_design": "Etapa 3: Arquitecto (System Design)",
        "change_plan": "Etapa 4: Plan de Cambios",
        "code_modification": "Compuerta de Modificación de Fuentes",
        "qa_report": "Etapa 5: QA Hostile Auditor",
        "local_runner": "Etapa 6: Entorno de Pruebas Local (PC de Desarrollo)",
        "deploy": "Etapa 7: Deploy",
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
    """
    Revoca la aprobación de una etapa.
    Por gobernanza de la Software Factory:
      - La etapa revocada pasa a 'Por Aprobar' (aprobación = False, artefacto conservado).
      - TODAS las etapas posteriores deben ser regeneradas, por lo tanto pasan al estado 'Pendiente'
        (sus artefactos son archivados en artifacts/_superseded/<timestamp>/ y sus aprobaciones = False).
    """
    pname = project or get_active_project_name()
    paths = get_project_paths(pname)
    set_active_project(paths["project_name"])
    context_file = paths["context"]

    label_map = {
        "discovery_notes": "Etapa 1: Discovery & Grilling",
        "prd": "Etapa 2: Product Manager (PRD)",
        "system_design": "Etapa 3: Arquitecto (System Design)",
        "change_plan": "Etapa 4: Plan de Cambios",
        "code_modification": "Compuerta de Modificación de Fuentes",
        "qa_report": "Etapa 5: QA Hostile Auditor",
        "local_runner": "Etapa 6: Entorno de Pruebas Local (PC de Desarrollo)",
        "deploy": "Etapa 7: Deploy",
    }
    label = label_map.get(stage_key, stage_key)

    stages_order = ["discovery_notes", "prd", "system_design", "code_modification", "qa_report", "local_runner", "deploy"]
    norm_key = "code_modification" if stage_key == "change_plan" else stage_key

    archived_info = {}
    if norm_key in stages_order:
        start_idx = stages_order.index(norm_key)

        # 1. Todas las etapas posteriores deben ser regeneradas y pasar al estado 'Pendiente'
        if start_idx + 1 < len(stages_order):
            first_subsequent = stages_order[start_idx + 1]
            from tools.skill_loader import invalidate_from_stage
            archived_info = invalidate_from_stage(
                pname,
                first_subsequent,
                f"Revocación de aprobación en etapa previa: '{label}' ({stage_key})"
            )

        # 2. La etapa actual pierde su aprobación humana (vuelve a Estado 2: 'Por Aprobar')
        ctx = {}
        if context_file.exists():
            with open(context_file, "r", encoding="utf-8") as f:
                ctx = json.load(f)
        ctx.setdefault("WORKFLOW_CONTEXT", {})
        approvals = ctx["WORKFLOW_CONTEXT"].setdefault("human_approvals", {})
        approvals[norm_key] = False
        if stage_key == "change_plan" or norm_key == "code_modification":
            approvals["change_plan"] = False
            approvals["code_modification"] = False
            # Si se revoca change_plan específicamente, archivar model.patch si existe
            if stage_key == "change_plan":
                patch_file = paths["03_code_patches"] / "model.patch"
                if patch_file.exists():
                    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    arch_patch = paths["artifacts"] / "_superseded" / ts / "03_code_patches" / "model.patch"
                    arch_patch.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(patch_file), str(arch_patch))

        with open(context_file, "w", encoding="utf-8") as f:
            json.dump(ctx, f, indent=4)
    else:
        ctx = {}
        if context_file.exists():
            with open(context_file, "r", encoding="utf-8") as f:
                ctx = json.load(f)
        ctx.setdefault("WORKFLOW_CONTEXT", {})
        ctx["WORKFLOW_CONTEXT"].setdefault("human_approvals", {})[stage_key] = False
        with open(context_file, "w", encoding="utf-8") as f:
            json.dump(ctx, f, indent=4)

    # Detener servidor de prueba si estaba activo (al revocar etapas, la app no debe seguir en ejecución)
    terminate_app_process(pname)

    # Cargar contexto final actualizado
    with open(context_file, "r", encoding="utf-8") as f:
        final_ctx = json.load(f)

    inval_msg = ""
    if archived_info.get("invalidated_stages"):
        inval_stages_str = ", ".join(archived_info["invalidated_stages"])
        inval_msg = f" Las etapas posteriores ({inval_stages_str}) han pasado al estado 'Pendiente' y deberán ser regeneradas."

    return {
        "success": True,
        "project_name": pname,
        "message": f"Aprobación revocada para '{label}'.{inval_msg}",
        "stage_key": stage_key,
        "invalidated_stages": archived_info.get("invalidated_stages", []),
        "archived_files": archived_info.get("archived_files", []),
        "human_approvals": final_ctx["WORKFLOW_CONTEXT"]["human_approvals"],
    }


# --- Endpoints de Skills y Evolución del Motor ---

@app.get("/api/skills")
def list_skills_endpoint(project: Optional[str] = None):
    """Lista los skills globales y de proyecto, su estado y el manifiesto del motor."""
    pname = project or get_active_project_name()
    skills = discover_skills(project_name=pname, include_inactive=True)
    global_list = [s.to_dict(include_body=True) for s in skills if s.is_global]
    project_list = [s.to_dict(include_body=True) for s in skills if not s.is_global]
    info = get_factory_info()
    return {
        "project_name": pname,
        "engine": info,
        "global_skills": global_list,
        "project_skills": project_list,
        "total_active": len([s for s in skills if s.is_active()]),
    }


@app.post("/api/skills/project/propose")
def propose_skill_endpoint(req: ProposeSkillRequest, project: Optional[str] = None):
    """Propone un nuevo skill exclusivo para el proyecto en estado 'proposed'."""
    pname = req.project_name or project or get_active_project_name()
    try:
        skill = propose_project_skill(
            project_name=pname,
            name=req.name,
            description=req.description,
            applies_to_stages=req.applies_to_stages,
            instructions_md=req.instructions_md,
            type_name=req.type,
            structured_data=req.structured_data,
        )
        return {
            "success": True,
            "message": f"Skill de proyecto '{skill.name}' propuesto exitosamente en estado 'proposed'.",
            "skill": skill.to_dict(include_body=True),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/skills/project/{name}/approve")
def approve_skill_endpoint(name: str, project: Optional[str] = None):
    """Aprueba un skill de proyecto, activándolo e invalidando en cascada las etapas afectadas."""
    pname = project or get_active_project_name()
    try:
        res = approve_project_skill(project_name=pname, name=name)
        return res
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/skills/project/{name}/revoke")
def revoke_skill_endpoint(name: str, project: Optional[str] = None):
    """Revoca un skill de proyecto e invalida en cascada las etapas afectadas."""
    pname = project or get_active_project_name()
    try:
        res = revoke_project_skill(project_name=pname, name=name)
        return res
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/skills/project/{name}")
def delete_skill_endpoint(name: str, project: Optional[str] = None):
    """Elimina la carpeta y registro de un skill de proyecto."""
    pname = project or get_active_project_name()
    try:
        res = delete_project_skill(project_name=pname, name=name)
        return res
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/skills/project/{name}/promote")
def promote_skill_endpoint(name: str, project: Optional[str] = None):
    """Propone promover un skill maduro de proyecto a la Software Factory global."""
    pname = project or get_active_project_name()
    try:
        res = propose_promotion(project_name=pname, name=name)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/skills/promotions")
def get_promotions_endpoint():
    """Lista las propuestas de promoción de skills a nivel global."""
    return {
        "promotions": list_promotion_proposals()
    }


@app.post("/api/skills/promotions/{name}/approve")
def approve_promotion_endpoint(name: str):
    """Aprueba la promoción de un skill a global, versionando el motor con un bump de patch."""
    try:
        res = approve_promotion(name=name)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/factory/lessons")
def list_lessons_endpoint():
    """Retorna las lecciones aprendidas registradas durante el desarrollo de la Software Factory."""
    return {
        "lessons": list_lessons(),
        "engine": get_factory_info(),
    }


@app.post("/api/factory/lessons")
def register_lesson_endpoint(req: RegisterLessonRequest, project: Optional[str] = None):
    """Registra una lección aprendida en factory/FACTORY_LESSONS.md."""
    pname = req.project_name or project or get_active_project_name()
    try:
        res = register_lesson(
            project=pname,
            stage=req.stage,
            symptom=req.symptom,
            root_cause=req.root_cause,
            target=req.target,
            proposal=req.proposal,
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/factory/info")
def factory_info_endpoint():
    """Información del motor de la Software Factory (versión, modo de ejecución)."""
    return get_factory_info()



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
