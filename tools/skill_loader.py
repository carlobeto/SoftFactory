#!/usr/bin/env python3
"""
Skill Loader de la Software Factory.

Conecta los skills (conocimiento y restricciones) con las etapas que los consumen.

Fuentes de skills (en orden de carga):
  1. Globales del motor:   .agents/skills/<nombre>/SKILL.md
  2. Overlay del proyecto: projects/<p>/.agents/skills/<nombre>/SKILL.md

Reglas de gobernanza (AGENTS.md §5):
  * Un skill de proyecto SOLO puede AGREGAR restricciones o conocimiento.
    No puede reemplazar un skill global (mismo nombre) ni relajar compuertas humanas.
  * Un skill de proyecto solo está ACTIVO cuando su estado es 'approved' en el
    workflow_context.json del proyecto.
  * Aprobar o revocar un skill de proyecto invalida (pasa a Pendiente) la primera etapa
    afectada y todas las posteriores, archivando sus artefactos.

Modos de consumo (ambos soportados):
  * Prompt (LLM): build_prompt_context(stage) concatena los cuerpos de los skills.
  * Datos (runners deterministas): load_skill_data(nombre, archivo) devuelve JSON
    estructurado (ej. grill-me/questions.json).
"""

from __future__ import annotations

import datetime
import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
GLOBAL_SKILLS_DIR = ROOT_DIR / ".agents" / "skills"
AGENTS_DIR = ROOT_DIR / "agents"
FACTORY_DIR = ROOT_DIR / "factory"
FACTORY_INFO_FILE = FACTORY_DIR / "factory.json"

# Orden canónico de las etapas (claves de human_approvals)
STAGES_ORDER = [
    "discovery_notes",
    "prd",
    "system_design",
    "code_modification",
    "qa_report",
    "local_runner",
    "deploy",
]

# Etapa -> carpeta de perfil en agents/
STAGE_PROFILES = {
    "discovery_notes": "requirements_discovery",
    "prd": "product_manager",
    "system_design": "architect",
    "code_modification": "engineer",
    "qa_report": "qa_tester",
}

# Etapa -> (clave de carpeta en get_project_paths, [archivos del artefacto])
STAGE_ARTIFACTS = {
    "discovery_notes": ("01_prd", ["DISCOVERY_NOTES.md"]),
    "prd": ("01_prd", ["PRD.md", "DELTA_PRD.md"]),
    "system_design": ("02_system_design", ["SYSTEM_DESIGN.md", "TASKS.md"]),
    "code_modification": ("03_code_patches", ["CHANGE_PLAN.md", "model.patch"]),
    "qa_report": ("04_qa_reports", ["QA_REPORT.md"]),
    "local_runner": ("05_local_runner", ["LOCAL_TESTING_SPEC.md"]),
    "deploy": ("06_deploy", ["DEPLOY_SPEC.md"]),
}

# Alias aceptados en applies_to_stages
STAGE_ALIASES = {
    "discovery": "discovery_notes",
    "requisitos": "discovery_notes",
    "pm": "prd",
    "product_manager": "prd",
    "architect": "system_design",
    "arquitecto": "system_design",
    "engineer": "code_modification",
    "programador": "code_modification",
    "patch": "code_modification",
    "change_plan": "code_modification",
    "qa": "qa_report",
    "auditor": "qa_report",
    "test_local": "local_runner",
}

SKILL_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{1,48}[a-z0-9]$")

# Patrones que indican un intento de RELAJAR la gobernanza (prohibido para skills de proyecto)
RELAXATION_PATTERNS = [
    r"sin\s+aprobaci[oó]n",
    r"omitir\s+(la\s+)?(compuerta|aprobaci[oó]n)",
    r"saltear\s+(la\s+)?(compuerta|aprobaci[oó]n)",
    r"desactivar\s+(la\s+)?(compuerta|aprobaci[oó]n|auditor[ií]a|qa)",
    r"no\s+requiere\s+aprobaci[oó]n",
    r"skip\s+(the\s+)?(gate|approval|qa)",
    r"bypass\s+(the\s+)?(gate|approval|qa)",
    r"disable\s+(the\s+)?(gate|approval|qa)",
    r"without\s+(human\s+)?approval",
    r"human_approvals\s*[:=]",
    r"modificar\s+(el\s+)?motor",
    r"(editar|modificar)\s+(agents|tools|config)/",
]


class SkillValidationError(ValueError):
    """Error de validación de un skill de proyecto."""


@dataclass
class Skill:
    name: str
    description: str
    version: str
    scope: str  # "global" | "project"
    path: Path
    body: str
    applies_to_stages: list[str] = field(default_factory=list)
    skill_type: str = "knowledge"  # "knowledge" | "restriction"
    status: str = "approved"  # globales siempre approved; proyecto: proposed|approved|revoked
    data_files: list[str] = field(default_factory=list)

    @property
    def is_active(self) -> bool:
        return self.status == "approved"

    @property
    def is_global(self) -> bool:
        return self.scope == "global"

    @property
    def is_project(self) -> bool:
        return self.scope == "project"

    def to_dict(self, include_body: bool = False) -> dict[str, Any]:
        d = {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "scope": self.scope,
            "path": str(self.path),
            "applies_to_stages": self.applies_to_stages,
            "type": self.skill_type,
            "status": self.status,
            "is_active": self.is_active,
            "data_files": self.data_files,
        }
        if include_body:
            d["body"] = self.body
        return d


# ---------------------------------------------------------------------------
# Información del motor (versión y modo)
# ---------------------------------------------------------------------------

def get_factory_info() -> dict[str, Any]:
    """Retorna engine_version y mode ('development' | 'production')."""
    info = {"engine_version": "0.0.0", "mode": "development"}
    if FACTORY_INFO_FILE.exists():
        try:
            info.update(json.loads(FACTORY_INFO_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass
    return info


def get_engine_version() -> str:
    return str(get_factory_info().get("engine_version", "0.0.0"))


def is_development_mode() -> bool:
    return get_factory_info().get("mode", "development") == "development"


# ---------------------------------------------------------------------------
# Parsing de SKILL.md (frontmatter mínimo, sin dependencia de PyYAML)
# ---------------------------------------------------------------------------

def _parse_inline_list(value: str) -> list[str]:
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    return [v.strip().strip("\"'") for v in value.split(",") if v.strip()]


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Extrae el frontmatter '---' de un SKILL.md. Soporta 'clave: valor' y listas inline o con guiones."""
    text = text.replace("\r\n", "\n")
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    raw = text[3:end].strip("\n")
    body = text[end + 4:].lstrip("\n")

    meta: dict[str, Any] = {}
    current_list_key: Optional[str] = None
    for line in raw.split("\n"):
        if not line.strip() or line.strip().startswith("#"):
            continue
        stripped = line.strip()
        if stripped.startswith("- ") and current_list_key:
            meta.setdefault(current_list_key, []).append(stripped[2:].strip().strip("\"'"))
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if value == "":
                current_list_key = key
                meta[key] = []
            elif value.startswith("["):
                meta[key] = _parse_inline_list(value)
                current_list_key = None
            else:
                meta[key] = value.strip("\"'")
                current_list_key = None
    return meta, body


def normalize_stage(stage: str) -> Optional[str]:
    s = stage.strip().lower()
    s = STAGE_ALIASES.get(s, s)
    return s if s in STAGES_ORDER else None


def _read_skill_dir(skill_dir: Path, scope: str) -> Optional[Skill]:
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        return None
    text = skill_file.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    stages_raw = meta.get("applies_to_stages", [])
    if isinstance(stages_raw, str):
        stages_raw = _parse_inline_list(stages_raw)
    stages = [s for s in (normalize_stage(x) for x in stages_raw) if s]
    data_files = sorted(p.name for p in skill_dir.iterdir() if p.is_file() and p.suffix == ".json")
    return Skill(
        name=str(meta.get("name", skill_dir.name)),
        description=str(meta.get("description", "")),
        version=str(meta.get("version", "1.0.0")),
        scope=scope,
        path=skill_dir,
        body=body,
        applies_to_stages=stages,
        skill_type=str(meta.get("type", "knowledge")),
        data_files=data_files,
    )


# ---------------------------------------------------------------------------
# Contexto del proyecto (estado de skills de proyecto)
# ---------------------------------------------------------------------------

def _project_paths(project_name: Optional[str]) -> dict[str, Any]:
    from tools.factory_manager import get_project_paths
    return get_project_paths(project_name)


def get_project_skills_dir(project_name: Optional[str] = None) -> Path:
    return _project_paths(project_name)["root"] / ".agents" / "skills"


def _load_context(project_name: Optional[str]) -> tuple[Path, dict[str, Any]]:
    ctx_file = _project_paths(project_name)["context"]
    data: dict[str, Any] = {}
    if ctx_file.exists():
        try:
            data = json.loads(ctx_file.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data.setdefault("WORKFLOW_CONTEXT", {})
    return ctx_file, data


def _save_context(ctx_file: Path, data: dict[str, Any]) -> None:
    ctx_file.parent.mkdir(parents=True, exist_ok=True)
    ctx_file.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")


def get_project_skill_registry(project_name: Optional[str] = None) -> dict[str, dict[str, Any]]:
    _, data = _load_context(project_name)
    return data["WORKFLOW_CONTEXT"].get("project_skills", {})


# ---------------------------------------------------------------------------
# Descubrimiento y resolución
# ---------------------------------------------------------------------------

def discover_global_skills() -> dict[str, Skill]:
    skills: dict[str, Skill] = {}
    if GLOBAL_SKILLS_DIR.exists():
        for d in sorted(GLOBAL_SKILLS_DIR.iterdir()):
            if d.is_dir():
                sk = _read_skill_dir(d, "global")
                if sk:
                    skills[sk.name] = sk
    return skills


def discover_project_skills(project_name: Optional[str] = None) -> dict[str, Skill]:
    skills: dict[str, Skill] = {}
    try:
        base = get_project_skills_dir(project_name)
    except Exception:
        return skills
    if not base.exists():
        return skills
    registry = get_project_skill_registry(project_name)
    for d in sorted(base.iterdir()):
        if d.is_dir():
            sk = _read_skill_dir(d, "project")
            if sk:
                sk.status = registry.get(sk.name, {}).get("status", "proposed")
                skills[sk.name] = sk
    return skills


def discover_skills(project_name: Optional[str] = None, include_inactive: bool = True) -> list[Skill]:
    """Retorna globales + de proyecto. Un skill de proyecto con nombre global se ignora (no puede reemplazarlo)."""
    globals_ = discover_global_skills()
    result = list(globals_.values())
    for name, sk in discover_project_skills(project_name).items():
        if name in globals_:
            continue  # prohibido reemplazar un global: solo se permite agregar
        if include_inactive or sk.is_active:
            result.append(sk)
    return result


def get_profile_skill_manifest(stage: str) -> dict[str, list[str]]:
    """Lee el bloque 'skills:' (required/optional) del profile.yaml de la etapa."""
    manifest = {"required": [], "optional": []}
    profile_dir = STAGE_PROFILES.get(stage)
    if not profile_dir:
        return manifest
    profile = AGENTS_DIR / profile_dir / "profile.yaml"
    if not profile.exists():
        return manifest
    in_skills = False
    skills_indent = 0
    for line in profile.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n"):
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if stripped.startswith("skills:"):
            in_skills = True
            skills_indent = indent
            continue
        if in_skills:
            if indent <= skills_indent:
                break
            key, _, value = stripped.partition(":")
            if key in manifest:
                manifest[key] = _parse_inline_list(value)
    return manifest


def get_stage_skills(stage: str, project_name: Optional[str] = None) -> list[Skill]:
    """
    Skills ACTIVOS para una etapa = manifiesto del profile.yaml (required + optional)
    ∪ skills cuyo frontmatter declare la etapa en applies_to_stages.
    Orden: requeridos, opcionales, luego globales y de proyecto por nombre.
    """
    stage = normalize_stage(stage) or stage
    manifest = get_profile_skill_manifest(stage)
    all_skills = {s.name: s for s in discover_skills(project_name, include_inactive=False)}

    ordered: list[Skill] = []
    seen: set[str] = set()
    for name in manifest["required"] + manifest["optional"]:
        if name in all_skills and name not in seen:
            ordered.append(all_skills[name])
            seen.add(name)
    for sk in sorted(all_skills.values(), key=lambda s: (s.scope != "global", s.name)):
        if sk.name not in seen and stage in sk.applies_to_stages:
            ordered.append(sk)
            seen.add(sk.name)
    return ordered


def get_missing_required_skills(stage: str) -> list[str]:
    globals_ = discover_global_skills()
    return [n for n in get_profile_skill_manifest(stage)["required"] if n not in globals_]


# ---------------------------------------------------------------------------
# Consumo: modo PROMPT (LLM) y modo DATOS (deterministas)
# ---------------------------------------------------------------------------

def build_prompt_context(stage: str, project_name: Optional[str] = None) -> str:
    """Concatena los skills activos de la etapa en un bloque listo para inyectar en un prompt de LLM."""
    parts = [f"# SKILLS ACTIVOS PARA LA ETAPA '{stage}'\n"]
    for sk in get_stage_skills(stage, project_name):
        parts.append(
            f"\n<skill name=\"{sk.name}\" version=\"{sk.version}\" scope=\"{sk.scope}\" type=\"{sk.skill_type}\">\n"
            f"{sk.body.strip()}\n</skill>\n"
        )
    return "".join(parts)


def load_skill_data(skill_name: str, filename: str, project_name: Optional[str] = None) -> Optional[Any]:
    """Devuelve el JSON estructurado de un skill activo (global o de proyecto aprobado)."""
    for sk in discover_skills(project_name, include_inactive=False):
        if sk.name == skill_name:
            f = sk.path / filename
            if f.exists():
                try:
                    return json.loads(f.read_text(encoding="utf-8"))
                except Exception:
                    return None
    return None


def collect_stage_data(stage: str, filename: str, project_name: Optional[str] = None) -> list[tuple[Skill, Any]]:
    """Retorna [(skill, json)] para todos los skills activos de la etapa que aporten 'filename'."""
    out = []
    for sk in get_stage_skills(stage, project_name):
        f = sk.path / filename
        if f.exists():
            try:
                out.append((sk, json.loads(f.read_text(encoding="utf-8"))))
            except Exception:
                continue
    return out


def extract_restrictions(skill: Skill) -> list[str]:
    """Extrae las viñetas bajo un encabezado '## Reglas' o '## Restricciones' del cuerpo del skill."""
    lines = skill.body.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    capturing = False
    for line in lines:
        if re.match(r"^#{2,3}\s+(Reglas|Restricciones|Rules|Constraints)\b", line, re.I):
            capturing = True
            continue
        if capturing and re.match(r"^#{1,3}\s+", line):
            break
        if capturing:
            m = re.match(r"^\s*(?:[-*]|\d+\.)\s+(.*)", line)
            if m:
                out.append(m.group(1).strip())
    return out


def render_skills_section(stage: str, project_name: Optional[str] = None) -> str:
    """
    Sección Markdown para anexar a los artefactos deterministas: lista los skills aplicados
    y sus restricciones, de modo que fluyan a las etapas siguientes.
    """
    skills = get_stage_skills(stage, project_name)
    if not skills:
        return ""
    md = ["\n---\n", "## Skills y Restricciones Aplicadas\n"]
    md.append("| Skill | Versión | Alcance | Tipo |\n| :--- | :--- | :--- | :--- |\n")
    for sk in skills:
        md.append(f"| `{sk.name}` | {sk.version} | {sk.scope} | {sk.skill_type} |\n")
    restrictions = [(sk, r) for sk in skills for r in extract_restrictions(sk)]
    if restrictions:
        md.append("\n### Restricciones obligatorias\n")
        for sk, r in restrictions:
            md.append(f"- **[{sk.name}]** {r}\n")
    return "".join(md)


# ---------------------------------------------------------------------------
# Trazabilidad (sello de procedencia)
# ---------------------------------------------------------------------------

def skills_snapshot(project_name: Optional[str] = None) -> dict[str, dict[str, str]]:
    return {
        sk.name: {"version": sk.version, "scope": sk.scope}
        for sk in discover_skills(project_name, include_inactive=False)
    }


def provenance_header(stage: str, project_name: Optional[str] = None) -> str:
    used = ", ".join(f"{s.name}@{s.version}({s.scope})" for s in get_stage_skills(stage, project_name)) or "ninguno"
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    return f"<!-- softfactory: engine={get_engine_version()} stage={stage} skills=[{used}] generated_at={ts} -->\n"


def record_provenance(stage: str, project_name: Optional[str] = None, files: Optional[list[Path]] = None) -> dict[str, Any]:
    """
    Sella los artefactos .md generados con un comentario de procedencia y registra en el
    workflow_context.json del proyecto el motor y los skills usados por la etapa.
    """
    header = provenance_header(stage, project_name)
    for f in files or []:
        f = Path(f)
        if f.suffix != ".md" or not f.exists():
            continue
        content = f.read_text(encoding="utf-8")
        content = re.sub(r"^<!-- softfactory: .*?-->\n", "", content)
        f.write_text(header + content, encoding="utf-8")

    entry = {
        "engine_version": get_engine_version(),
        "skills": {s.name: f"{s.version}({s.scope})" for s in get_stage_skills(stage, project_name)},
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    try:
        ctx_file, data = _load_context(project_name)
        wc = data["WORKFLOW_CONTEXT"]
        wc.setdefault("artifact_provenance", {})[stage] = entry
        wc["skills_snapshot"] = skills_snapshot(project_name)
        wc.setdefault("project_metadata", {}).setdefault("engine_version", get_engine_version())
        _save_context(ctx_file, data)
    except Exception:
        pass
    return entry


# ---------------------------------------------------------------------------
# Skills de proyecto: validación, propuesta, aprobación, revocación
# ---------------------------------------------------------------------------

def validate_project_skill(name: str, body: str, applies_to_stages: list[str]) -> list[str]:
    """Valida la regla 'solo agregar restricciones'. Retorna las etapas normalizadas."""
    if not SKILL_NAME_RE.match(name):
        raise SkillValidationError(
            "Nombre de skill inválido: usa minúsculas, números y guiones (3-50 caracteres)."
        )
    if name in discover_global_skills():
        raise SkillValidationError(
            f"Ya existe un skill global '{name}'. Un skill de proyecto no puede reemplazarlo; "
            "elige otro nombre para AGREGAR restricciones."
        )
    stages = [s for s in (normalize_stage(x) for x in applies_to_stages) if s]
    if not stages:
        raise SkillValidationError(f"Debe indicar al menos una etapa válida: {', '.join(STAGES_ORDER)}")
    for pat in RELAXATION_PATTERNS:
        if re.search(pat, body, re.I):
            raise SkillValidationError(
                "El skill intenta relajar la gobernanza (compuertas, aprobaciones o el motor). "
                "Los skills de proyecto solo pueden AGREGAR restricciones."
            )
    return stages


def propose_project_skill(
    project_name: Optional[str],
    name: str,
    description: str,
    applies_to_stages: list[str],
    body: Optional[str] = None,
    skill_type: str = "restriction",
    version: str = "1.0.0",
    data: Optional[dict[str, Any]] = None,
    *,
    instructions_md: Optional[str] = None,
    type_name: Optional[str] = None,
    structured_data: Optional[dict[str, Any]] = None,
) -> Skill:
    """Crea/actualiza un skill de proyecto en estado 'proposed' (no activo hasta aprobarse)."""
    actual_body = instructions_md if instructions_md is not None else (body or "")
    actual_type = type_name if type_name is not None else skill_type
    actual_data = structured_data if structured_data is not None else data

    name = name.strip().lower()
    stages = validate_project_skill(name, actual_body, applies_to_stages)
    if actual_type not in ("knowledge", "restriction"):
        actual_type = "restriction"

    skill_dir = get_project_skills_dir(project_name) / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    safe_desc = description.replace("\n", " ").strip()
    content = (
        "---\n"
        f"name: {name}\n"
        f"description: {safe_desc}\n"
        f"version: {version}\n"
        f"type: {actual_type}\n"
        f"applies_to_stages: [{', '.join(stages)}]\n"
        "---\n\n"
        f"{actual_body.strip()}\n"
    )
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    if actual_data:
        for fname, payload in actual_data.items():
            if fname.endswith(".json") and "/" not in fname:
                (skill_dir / fname).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    ctx_file, ctx = _load_context(project_name)
    reg = ctx["WORKFLOW_CONTEXT"].setdefault("project_skills", {})
    prev = reg.get(name, {})
    reg[name] = {
        "status": "proposed",
        "version": version,
        "applies_to_stages": stages,
        "proposed_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "was_approved_before": prev.get("status") == "approved" or prev.get("was_approved_before", False),
    }
    _save_context(ctx_file, ctx)

    sk = _read_skill_dir(skill_dir, "project")
    assert sk is not None
    sk.status = "proposed"
    return sk


def first_affected_stage(stages: list[str]) -> Optional[str]:
    idx = [STAGES_ORDER.index(s) for s in stages if s in STAGES_ORDER]
    return STAGES_ORDER[min(idx)] if idx else None


def invalidate_from_stage(project_name: Optional[str], stage: str, reason: str) -> dict[str, Any]:
    """
    Pasa a 'Pendiente' la etapa indicada y todas las posteriores:
      * archiva sus artefactos en artifacts/_superseded/<timestamp>/
      * pone en False sus aprobaciones humanas
    El workspace NO se borra (regla de preservación del lazo de mantenimiento).
    """
    paths = _project_paths(project_name)
    if stage not in STAGES_ORDER:
        return {"invalidated_stages": [], "archived_files": []}
    start = STAGES_ORDER.index(stage)
    affected = STAGES_ORDER[start:]

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = paths["artifacts"] / "_superseded" / ts
    archived: list[str] = []
    for st in affected:
        folder_key, files = STAGE_ARTIFACTS.get(st, (None, []))
        if not folder_key:
            continue
        folder = paths.get(folder_key) or (paths["artifacts"] / folder_key)
        for fname in files:
            src = Path(folder) / fname
            if src.exists():
                dest = archive_dir / folder_key / fname
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dest))
                archived.append(f"{folder_key}/{fname}")

    # Archivar también workspace/local_runner.py si local_runner fue invalidado
    if "local_runner" in affected and "workspace" in paths:
        runner_file = paths["workspace"] / "local_runner.py"
        if runner_file.exists():
            dest_runner = archive_dir / "workspace" / "local_runner.py"
            dest_runner.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(runner_file), str(dest_runner))
            archived.append("workspace/local_runner.py")

    if archived:
        (archive_dir / "REASON.md").write_text(
            f"# Artefactos reemplazados\n\n- Fecha: {ts}\n- Motivo: {reason}\n- Etapas invalidadas: {', '.join(affected)}\n",
            encoding="utf-8",
        )

    ctx_file, ctx = _load_context(project_name)
    wc = ctx["WORKFLOW_CONTEXT"]
    approvals = wc.setdefault("human_approvals", {})
    for st in affected:
        approvals[st] = False
    if "code_modification" in affected:
        approvals["change_plan"] = False
    wc.setdefault("invalidation_log", []).append({
        "at": ts,
        "from_stage": stage,
        "reason": reason,
        "archived": archived,
    })
    prov = wc.get("artifact_provenance", {})
    for st in affected:
        prov.pop(st, None)
    _save_context(ctx_file, ctx)
    return {"invalidated_stages": affected, "archived_files": archived, "archive_dir": str(archive_dir) if archived else None}


def _set_project_skill_status(project_name: Optional[str], name: str, status: str) -> tuple[Skill, dict[str, Any]]:
    skills = discover_project_skills(project_name)
    if name not in skills:
        raise SkillValidationError(f"No existe el skill de proyecto '{name}'.")
    sk = skills[name]
    # Revalidar contra la regla de solo agregar (por si se editó a mano)
    validate_project_skill(name, sk.body, sk.applies_to_stages)

    ctx_file, ctx = _load_context(project_name)
    reg = ctx["WORKFLOW_CONTEXT"].setdefault("project_skills", {})
    entry = reg.setdefault(name, {})
    entry["status"] = status
    entry["version"] = sk.version
    entry["applies_to_stages"] = sk.applies_to_stages
    entry[f"{status}_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    if status == "approved":
        entry["was_approved_before"] = True
    _save_context(ctx_file, ctx)
    sk.status = status
    return sk, entry


def approve_project_skill(project_name: Optional[str], name: str) -> dict[str, Any]:
    """Aprueba un skill de proyecto e invalida desde la primera etapa afectada en adelante."""
    sk, _ = _set_project_skill_status(project_name, name, "approved")
    stage = first_affected_stage(sk.applies_to_stages)
    inv = invalidate_from_stage(project_name, stage, f"Skill de proyecto '{name}' v{sk.version} aprobado") if stage else {}
    return {"success": True, "skill": sk.to_dict(), "first_affected_stage": stage, **inv}


def revoke_project_skill(project_name: Optional[str], name: str) -> dict[str, Any]:
    """Revoca un skill de proyecto aprobado; como cambian las salidas, también invalida."""
    prev_status = get_project_skill_registry(project_name).get(name, {}).get("status")
    sk, _ = _set_project_skill_status(project_name, name, "revoked")
    stage = first_affected_stage(sk.applies_to_stages)
    inv: dict[str, Any] = {}
    if prev_status == "approved" and stage:
        inv = invalidate_from_stage(project_name, stage, f"Skill de proyecto '{name}' revocado")
    return {"success": True, "skill": sk.to_dict(), "first_affected_stage": stage, **inv}


def delete_project_skill(project_name: Optional[str], name: str) -> dict[str, Any]:
    reg = get_project_skill_registry(project_name)
    was_active = reg.get(name, {}).get("status") == "approved"
    result: dict[str, Any] = {"success": True, "deleted": name}
    if was_active:
        result.update(revoke_project_skill(project_name, name))
    skill_dir = get_project_skills_dir(project_name) / name
    if skill_dir.exists():
        shutil.rmtree(skill_dir)
    ctx_file, ctx = _load_context(project_name)
    ctx["WORKFLOW_CONTEXT"].setdefault("project_skills", {}).pop(name, None)
    _save_context(ctx_file, ctx)
    return result


# ---------------------------------------------------------------------------
# Promoción proyecto -> global (Factory RFC)
# ---------------------------------------------------------------------------

PROPOSALS_DIR = FACTORY_DIR / "skill_proposals"


def propose_promotion(project_name: Optional[str], name: str) -> dict[str, Any]:
    """Copia un skill de proyecto APROBADO a factory/skill_proposals/ para revisión como Factory RFC."""
    skills = discover_project_skills(project_name)
    if name not in skills or skills[name].status != "approved":
        raise SkillValidationError("Solo se pueden promover skills de proyecto en estado 'approved'.")
    if name in discover_global_skills():
        raise SkillValidationError(f"Ya existe un skill global '{name}'.")
    dest = PROPOSALS_DIR / name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(skills[name].path, dest)
    meta = {
        "source_project": _project_paths(project_name)["project_name"],
        "proposed_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "status": "pending_review",
    }
    (dest / "PROMOTION.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"proposal": name, "path": str(dest), **meta}


def list_promotion_proposals() -> list[dict[str, Any]]:
    out = []
    if PROPOSALS_DIR.exists():
        for d in sorted(PROPOSALS_DIR.iterdir()):
            if d.is_dir():
                meta = {}
                if (d / "PROMOTION.json").exists():
                    meta = json.loads((d / "PROMOTION.json").read_text(encoding="utf-8"))
                sk = _read_skill_dir(d, "proposal")
                out.append({"name": d.name, **meta, **({"description": sk.description, "version": sk.version} if sk else {})})
    return out


def _bump_patch(version: str) -> str:
    parts = (version.split(".") + ["0", "0", "0"])[:3]
    try:
        parts[2] = str(int(parts[2]) + 1)
    except ValueError:
        parts[2] = "1"
    return ".".join(parts)


def approve_promotion(name: str) -> dict[str, Any]:
    """
    Factory RFC aprobado: instala el skill como global, sube la versión patch del motor
    y registra la entrada en factory/CHANGELOG.md.
    """
    src = PROPOSALS_DIR / name
    if not src.exists():
        raise SkillValidationError(f"No existe la propuesta de promoción '{name}'.")
    if name in discover_global_skills():
        raise SkillValidationError(f"Ya existe un skill global '{name}'.")
    meta = {}
    if (src / "PROMOTION.json").exists():
        meta = json.loads((src / "PROMOTION.json").read_text(encoding="utf-8"))
    dest = GLOBAL_SKILLS_DIR / name
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("PROMOTION.json"))
    shutil.rmtree(src)

    info = get_factory_info()
    old = str(info.get("engine_version", "0.0.0"))
    info["engine_version"] = _bump_patch(old)
    FACTORY_DIR.mkdir(parents=True, exist_ok=True)
    FACTORY_INFO_FILE.write_text(json.dumps(info, indent=4, ensure_ascii=False), encoding="utf-8")

    changelog = FACTORY_DIR / "CHANGELOG.md"
    entry = (
        f"\n## {info['engine_version']} — {datetime.date.today().isoformat()}\n"
        f"- **Skill promovido a global:** `{name}` (origen: proyecto `{meta.get('source_project', '?')}`).\n"
    )
    existing = changelog.read_text(encoding="utf-8") if changelog.exists() else "# CHANGELOG del Motor SoftFactory\n"
    changelog.write_text(existing.rstrip("\n") + "\n" + entry, encoding="utf-8")
    return {"promoted": name, "engine_version": info["engine_version"], "previous_engine_version": old}


# ---------------------------------------------------------------------------
# Registro de lecciones (modo desarrollo)
# ---------------------------------------------------------------------------

LESSONS_FILE = FACTORY_DIR / "FACTORY_LESSONS.md"
LESSON_TARGETS = {"skill", "rule", "engine", "template"}


def register_lesson(project: str, stage: str, symptom: str, root_cause: str = "", target: str = "engine", proposal: str = "") -> dict[str, Any]:
    """Agrega una lección al registro del motor. Solo disponible en modo 'development'."""
    if not is_development_mode():
        raise SkillValidationError("El registro de lecciones solo está disponible en modo 'development'.")
    if target not in LESSON_TARGETS:
        target = "engine"
    FACTORY_DIR.mkdir(parents=True, exist_ok=True)
    existing = LESSONS_FILE.read_text(encoding="utf-8") if LESSONS_FILE.exists() else ""
    count = len(re.findall(r"^### L-\d+", existing, re.M))
    lesson_id = f"L-{count + 1:03d}"
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    block = (
        f"\n### {lesson_id} — {ts}\n"
        f"- **Proyecto de origen:** {project}\n"
        f"- **Etapa:** {stage}\n"
        f"- **Motor:** {get_engine_version()}\n"
        f"- **Síntoma:** {symptom.strip()}\n"
        f"- **Causa raíz:** {root_cause.strip() or '_(por analizar)_'}\n"
        f"- **Destino:** {target}\n"
        f"- **Propuesta:** {proposal.strip() or '_(por definir)_'}\n"
        f"- **Estado:** abierta\n"
    )
    if not existing:
        existing = (
            "# Registro de Lecciones del Motor SoftFactory\n\n"
            "Cada lección surge de una prueba con un proyecto y se resuelve mediante un Factory RFC "
            "(skill, regla, plantilla o código del motor) con aprobación humana. Ver AGENTS.md §5.\n"
        )
    LESSONS_FILE.write_text(existing.rstrip("\n") + "\n" + block, encoding="utf-8")
    return {"id": lesson_id, "file": str(LESSONS_FILE), "status": "registered", "success": True}



def list_lessons() -> list[dict[str, str]]:
    if not LESSONS_FILE.exists():
        return []
    text = LESSONS_FILE.read_text(encoding="utf-8")
    out = []
    for m in re.finditer(r"^### (L-\d+) — (\S+)\n((?:- .*\n?)+)", text, re.M):
        fields = dict(re.findall(r"- \*\*(.+?):\*\* (.*)", m.group(3)))
        out.append({"id": m.group(1), "at": m.group(2), **fields})
    return out
