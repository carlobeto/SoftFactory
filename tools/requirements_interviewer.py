#!/usr/bin/env python3
"""
Requirements Interviewer (Grill-Me Engine para la Software Factory)
Implementa el protocolo de entrevista por rondas (Design Tree Frontier)
para transformar frases escuetas de requerimientos en especificaciones de sistema
estructuradas antes de generar el PRD.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from tools.factory_manager import get_project_paths, get_active_project_name
except ImportError:
    get_project_paths = None
    get_active_project_name = lambda: "app"


def ask_round_question(q_id, title, description, options, recommended, interactive=True):
    """
    Formula una pregunta con recomendaciones inteligentes (Smart Defaults).
    En modo interactivo, el usuario puede presionar ENTER para aceptar el default o escribir su respuesta.
    """
    print(f"\n❓ [Q{q_id}] - {title}")
    print(f"   {description}")
    print("   Opciones disponibles:")
    for opt_key, opt_desc in options.items():
        print(f"     [{opt_key}] {opt_desc}")
    print(f"   ➡️  Recomendación: [{recommended}] {options.get(recommended, '')}")

    if not interactive or not sys.stdin.isatty():
        print(f"   ✓ [Selección Automática/Default]: {recommended}")
        return recommended, options.get(recommended, recommended)

    try:
        user_input = input(f"   Elige opción o escribe respuesta personalizada (ENTER para '{recommended}'): ").strip()
    except (EOFError, KeyboardInterrupt):
        print(f"\n   ✓ [Selección por omisión]: {recommended}")
        return recommended, options.get(recommended, recommended)

    if not user_input:
        selected_code = recommended
        selected_text = options.get(recommended, recommended)
    elif user_input in options:
        selected_code = user_input
        selected_text = options[user_input]
    else:
        selected_code = "custom"
        selected_text = user_input

    print(f"   ✓ [Aceptado]: {selected_text}")
    return selected_code, selected_text


# ---------------------------------------------------------------------------
# Árbol de preguntas: se lee de los skills activos de la Etapa 1 (modo datos)
# ---------------------------------------------------------------------------

# Claves núcleo que el resto de la cadena (PM, Arquitecto, parse_discovery_notes) espera siempre.
CORE_KEYS = [
    "api_style", "ui_layout", "ui_theme", "consumers", "entities", "auth_scheme", "error_format",
    "persistence", "caching", "validation", "deployment",
]


def load_question_tree(project_name: str = None) -> list[dict]:
    """
    Retorna las rondas de preguntas: primero las de 'grill-me' (global) y luego las que
    AGREGUEN los skills de proyecto aprobados para la etapa 'discovery_notes'.
    Cada ronda queda anotada con 'source' (nombre del skill que la aporta).
    """
    rounds: list[dict] = []
    try:
        from tools.skill_loader import GLOBAL_SKILLS_DIR, collect_stage_data
        contributions = collect_stage_data("discovery_notes", "questions.json", project_name)
        if not any(sk.name == "grill-me" for sk, _ in contributions):
            base = GLOBAL_SKILLS_DIR / "grill-me" / "questions.json"
            if base.exists():
                contributions.insert(0, (type("S", (), {"name": "grill-me"})(), json.loads(base.read_text(encoding="utf-8"))))
        contributions.sort(key=lambda c: c[0].name != "grill-me")
        seen_keys: set[str] = set()
        for sk, data in contributions:
            for rnd in data.get("rounds", []):
                qs = [q for q in rnd.get("questions", []) if q.get("key") and q["key"] not in seen_keys]
                if not qs:
                    continue
                seen_keys.update(q["key"] for q in qs)
                rounds.append({"title": rnd.get("title", f"Ronda ({sk.name})"), "source": sk.name, "questions": qs})
    except Exception as e:
        print(f"[Interviewer] No se pudo cargar el árbol de preguntas desde los skills: {e}")
    if not rounds:
        raise RuntimeError(
            "No se encontró el árbol de preguntas. Verifique .agents/skills/grill-me/questions.json"
        )
    return rounds


def _match_rule(rules: list[dict], prompt: str):
    low = prompt.lower()
    for r in rules or []:
        if any(w.lower() in low for w in r.get("prompt_contains_any", [])):
            return r.get("value")
    return None


def resolve_default(question: dict, prompt: str) -> tuple[str, str]:
    """Retorna (código, texto) recomendado para una pregunta dado el requerimiento semilla."""
    if question.get("type") == "free_text":
        text = _match_rule(question.get("default_if"), prompt) or question.get("default", "")
        return "custom", text
    options = question.get("options", {})
    code = _match_rule(question.get("recommend_if"), prompt) or question.get("recommended") or next(iter(options), "")
    return code, options.get(code, code)


def default_answers(prompt: str, project_name: str = None) -> dict[str, str]:
    """Respuestas por defecto (Smart Defaults) para todo el árbol activo."""
    answers = {}
    for rnd in load_question_tree(project_name):
        for q in rnd["questions"]:
            answers[q["key"]] = resolve_default(q, prompt)[1]
    return answers


def complete_answers_with_defaults(prompt: str, answers: dict, project_name: str = None) -> dict[str, str]:
    """Completa las claves faltantes (ej. preguntas agregadas por skills de proyecto) con sus defaults."""
    merged = default_answers(prompt, project_name)
    merged.update({k: v for k, v in (answers or {}).items() if v})
    return merged


def get_matrix_labels(project_name: str = None) -> dict[str, str]:
    labels = {}
    try:
        for rnd in load_question_tree(project_name):
            for q in rnd["questions"]:
                labels[q["key"]] = q.get("matrix_label") or q.get("title", q["key"])
    except Exception:
        pass
    return labels


def run_grill_interview(initial_prompt: str, interactive: bool = True, project_name: str = None):
    """
    Ejecuta las rondas del árbol de diseño basadas en la filosofía 'grill-me'.
    El árbol se lee de los skills activos (grill-me + skills de proyecto aprobados).
    Guarda los artefactos de forma aislada en projects/<project_name>/artifacts/01_prd/.
    """
    pname = project_name or (get_active_project_name() if get_active_project_name else "app")
    paths = get_project_paths(pname) if get_project_paths else {"01_prd": Path(f"projects/{pname}/artifacts/01_prd")}
    prd_pool = paths["01_prd"]
    prd_pool.mkdir(parents=True, exist_ok=True)

    active_skills = []
    try:
        from tools.skill_loader import get_stage_skills
        active_skills = get_stage_skills("discovery_notes", pname)
    except Exception:
        pass
    skills_info = ", ".join(f"{s.name}@{s.version} ({s.scope})" for s in active_skills) if active_skills else "grill-me@1.1.0 (global)"

    print("=" * 70)
    print("  SOFTWARE FACTORY: SESIÓN DE REQUIREMENTS GRILLING & DISCOVERY (ETAPA 1)")
    print("  Metodología Grill-Me de AI Hero — Gobernanza de Skills AGENTS.md §5")
    print(f"  Skills Activos: [{skills_info}]")
    print("=" * 70)
    print(f"Requerimiento Semilla: \"{initial_prompt}\"")
    print(f"Proyecto Destino:       \"{pname}\"")
    print("Iniciando rondas de preguntas para desgranar el árbol de decisiones...\n")

    answers = {}
    q_id = 0
    for rnd in load_question_tree(project_name):
        skill_name = rnd.get("source", "grill-me")
        print(f"\n--- [{rnd['title']}] [Skill: {skill_name}] ---")
        for q in rnd["questions"]:
            q_id += 1
            code, text = resolve_default(q, initial_prompt)
            if q.get("type") == "free_text":
                print(f"\n❓ [Q{q_id}] - {q.get('title', q['key'])}")
                print(f"   {q.get('description', '')}")
                print(f"   ➡️  Recomendación: {text}")
                value = text
                if interactive and sys.stdin.isatty():
                    try:
                        user_input = input(f"   Respuesta (ENTER para '{text}'): ").strip()
                        value = user_input or text
                    except (EOFError, KeyboardInterrupt):
                        value = text
                answers[q["key"]] = value
                print(f"   ✓ [Aceptado]: {value}")
            else:
                _, answers[q["key"]] = ask_round_question(
                    q_id=q_id,
                    title=q.get("title", q["key"]),
                    description=q.get("description", ""),
                    options=q.get("options", {}),
                    recommended=code,
                    interactive=interactive,
                )

    answers = complete_answers_with_defaults(initial_prompt, answers, project_name)

    # -------------------------------------------------------------
    # COMPILACIÓN DEL ARTEFACTO: DISCOVERY_NOTES.md
    # -------------------------------------------------------------
    discovery_file = prd_pool / "DISCOVERY_NOTES.md"
    generate_discovery_notes(initial_prompt, answers, discovery_file, project_name=project_name)

    # Actualizar también NEW_REQUIREMENT.txt
    req_file = prd_pool / "NEW_REQUIREMENT.txt"
    with open(req_file, "w", encoding="utf-8") as f:
        f.write(f"PROYECTO: {initial_prompt}\n")
        f.write("REQUERIMIENTO DESCUBIERTO (GRILL-ME):\n")
        f.write(f"- Arquitectura: {answers['api_style']}\n")
        f.write(f"- Entidades: {answers['entities']}\n")
        f.write(f"- Autenticación: {answers['auth_scheme']}\n")
        f.write(f"- Persistencia: {answers['persistence']}\n")
        f.write(f"- Errores: {answers['error_format']}\n")

    print("\n" + "=" * 70)
    print("  [GRILL-ME COMPLETADO] ARTEFACTOS GENERADOS CON ÉXITO")
    print("=" * 70)
    print(f"-> Artefacto de Discovery generado en: {discovery_file}")
    if active_skills:
        print(f"-> Skills y restricciones aplicadas:   {', '.join(f'{s.name}@{s.version}' for s in active_skills)}")
    print("-> Las decisiones han sido congeladas. El Product Manager puede generar el PRD sin suposiciones.")
    print("=" * 70 + "\n")

    return discovery_file, answers


def generate_discovery_notes(initial_prompt: str, answers: dict, output_path: Path, project_name: str = None):
    """Genera el documento DISCOVERY_NOTES.md en formato Markdown enriquecido."""
    try:
        answers = complete_answers_with_defaults(initial_prompt, answers, project_name)
    except Exception:
        pass
    entities_list = [e.strip() for e in answers["entities"].split(",") if e.strip()]

    # Decisiones adicionales aportadas por skills de proyecto (preguntas fuera del núcleo)
    labels = get_matrix_labels(project_name)
    extra_rows = "".join(
        f"| **{labels.get(k, k)}** | {v} | Restricción agregada por skill del proyecto |\n"
        for k, v in answers.items() if k not in CORE_KEYS
    )

    endpoints_md = ""
    for ent in entities_list:
        slug = ent.lower().replace(" ", "-")
        endpoints_md += f"- `GET /api/v1/{slug}` - Listar y filtrar {ent}\n"
        endpoints_md += f"- `POST /api/v1/{slug}` - Crear nuevo registro de {ent}\n"
        endpoints_md += f"- `GET /api/v1/{slug}/{{id}}` - Obtener detalle por ID\n"
        endpoints_md += f"- `PUT /api/v1/{slug}/{{id}}` - Actualizar {ent} existente\n"
        endpoints_md += f"- `DELETE /api/v1/{slug}/{{id}}` - Eliminar {ent}\n"

    gherkin_scenarios = f"""
### Escenario 1: Creación exitosa de recurso
```gherkin
Característica: Gestión de {entities_list[0] if entities_list else 'Recursos'}
  Escenario: Crear un nuevo registro con datos válidos
    Dado un cliente autenticado con credenciales válidas ({answers['auth_scheme']})
    Cuando envía una petición POST a "/api/v1/{entities_list[0].lower() if entities_list else 'items'}" con payload válido
    Entonces la API retorna código 201 Created
    Y el cuerpo de la respuesta contiene el ID generado y los datos persistidos
```

### Escenario 2: Rechazo ante datos no válidos (Validación Estricta)
```gherkin
  Escenario: Rechazo de petición con datos malformados
    Dado un cliente que envía un POST con campos obligatorios vacíos
    Cuando la API procesa la solicitud
    Entonces retorna código 422 Unprocessable Entity
    Y el cuerpo responde bajo el estándar {answers['error_format']}
```

### Escenario 3: Acceso no autorizado
```gherkin
  Escenario: Intentar consumir endpoints protegidos sin credenciales
    Dado un cliente sin cabecera de autenticación
    Cuando solicita un endpoint protegido
    Entonces la API rechaza la solicitud con código 401 Unauthorized
```
"""

    content = f"""# Requirements Discovery & Grilling Report

## 1. Contexto Inicial
- **Requerimiento Semilla:** `{initial_prompt}`
- **Metodología Aplicada:** AI Hero Grill-Me (Frontier Design Tree Protocol)
- **Estado de Elicitación:** `COMPLETADO Y CONGELADO`

---

## 2. Matriz de Decisiones de Diseño Congeladas

| Dimensión | Decisión Adoptada | Razón Técnica / Implicancia |
| :--- | :--- | :--- |
| **Estilo Arquitectónico** | {answers['api_style']} | Contrato estructurado predecible para el cliente |
| **Pantalla Inicial & UI** | {answers.get('ui_layout', 'Dashboard Web Interactivo con componentes dinámicos')} | Disposición visual y componentes de la pantalla inicial |
| **Tema Visual & Estilo** | {answers.get('ui_theme', 'Modern Dark Mode')} | Sistema de diseño, estética y tipografía moderna |
| **Consumidores Clave** | {answers['consumers']} | Define los requerimientos de latencia y CORS |
| **Seguridad & Auth** | {answers['auth_scheme']} | Aislamiento y control de acceso robusto |
| **Gestión de Errores** | {answers['error_format']} | Estándar predecible para simplificar la integración frontend |
| **Persistencia** | {answers['persistence']} | Integridad transaccional y bajo acoplamiento |
| **Caché & Rendimiento** | {answers['caching']} | Evita sobrecarga en operaciones de lectura repetitivas |
| **Validación de Datos** | {answers['validation']} | Previene inyección y corrupción del modelo |
| **Estrategia Despliegue** | {answers['deployment']} | Autocontenido y ejecutable en cualquier entorno |
{extra_rows}
---

## 3. Modelo de Dominio y Recursos Clave
Las siguientes entidades componen el núcleo de datos del sistema:
{chr(10).join(f"- **{e}**: Entidad principal de negocio gestionada por la API." for e in entities_list)}

---

## 4. Borrador del Contrato de Endpoints (API Specification Draft)
{endpoints_md}

---

## 5. Criterios de Aceptación Ejecutables (Historias de Usuario en Gherkin)
{gherkin_scenarios}

---

## 6. Registros de Decisiones Arquitectónicas (ADRs Preliminares)

### ADR-001: Adopción del Estilo de API
- **Decisión:** {answers['api_style']}
- **Justificación:** Ofrece el mejor balance entre desacoplamiento, facilidad de pruebas automatizadas y soporte universal.

### ADR-002: Esquema de Persistencia
- **Decisión:** {answers['persistence']}
- **Justificación:** Garantiza aislamiento en el sandbox y despliegue rápido sin requerir servicios externos pesados en la fase inicial.

### ADR-003: Manejo Estándar de Errores
- **Decisión:** {answers['error_format']}
- **Justificación:** Facilita que el QA Tester audite de forma hostil los casos extremos y códigos de estado.
"""

    try:
        from tools.skill_loader import record_provenance, render_skills_section
        content += render_skills_section("discovery_notes", project_name)
    except Exception:
        record_provenance = None

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    if record_provenance and get_project_paths:
        try:
            record_provenance("discovery_notes", project_name, [Path(output_path)])
        except Exception:
            pass


def parse_discovery_notes(content: str) -> dict[str, str]:
    """Extrae las decisiones y respuestas estructuradas de un documento DISCOVERY_NOTES.md."""
    parsed = {
        "prompt": "",
        "api_style": "",
        "ui_layout": "",
        "ui_theme": "",
        "consumers": "",
        "auth_scheme": "",
        "error_format": "",
        "persistence": "",
        "caching": "",
        "validation": "",
        "deployment": "",
        "entities": "",
    }
    if not content:
        return parsed

    for line in content.splitlines():
        if "Requerimiento Semilla:" in line:
            parsed["prompt"] = line.split("`")[1] if "`" in line else line.split(":", 1)[1].strip()
        elif "| **Estilo Arquitectónico** |" in line:
            parts = line.split("|")
            if len(parts) >= 3:
                parsed["api_style"] = parts[2].strip()
        elif "| **Pantalla Inicial & UI** |" in line:
            parts = line.split("|")
            if len(parts) >= 3:
                parsed["ui_layout"] = parts[2].strip()
        elif "| **Tema Visual & Estilo** |" in line:
            parts = line.split("|")
            if len(parts) >= 3:
                parsed["ui_theme"] = parts[2].strip()
        elif "| **Consumidores Clave** |" in line:
            parts = line.split("|")
            if len(parts) >= 3:
                parsed["consumers"] = parts[2].strip()
        elif "| **Seguridad & Auth** |" in line:
            parts = line.split("|")
            if len(parts) >= 3:
                parsed["auth_scheme"] = parts[2].strip()
        elif "| **Gestión de Errores** |" in line:
            parts = line.split("|")
            if len(parts) >= 3:
                parsed["error_format"] = parts[2].strip()
        elif "| **Persistencia** |" in line:
            parts = line.split("|")
            if len(parts) >= 3:
                parsed["persistence"] = parts[2].strip()
        elif "| **Caché & Rendimiento** |" in line:
            parts = line.split("|")
            if len(parts) >= 3:
                parsed["caching"] = parts[2].strip()
        elif "| **Validación de Datos** |" in line:
            parts = line.split("|")
            if len(parts) >= 3:
                parsed["validation"] = parts[2].strip()
        elif "| **Estrategia Despliegue** |" in line:
            parts = line.split("|")
            if len(parts) >= 3:
                parsed["deployment"] = parts[2].strip()

    ents = []
    in_entities = False
    for line in content.splitlines():
        if "## 3. Modelo de Dominio" in line:
            in_entities = True
            continue
        if in_entities:
            if line.startswith("---") or line.startswith("## "):
                break
            m = re.match(r"^\s*-\s*\*\*([^*]+)\*\*", line)
            if m:
                ents.append(m.group(1).strip())
    if ents:
        parsed["entities"] = ", ".join(ents)

    return parsed


def main():
    parser = argparse.ArgumentParser(
        description="Requirements Interviewer (Grill-Me Protocol para Software Factory)"
    )
    parser.add_argument("prompt", nargs="?", default="Construir una API REST para gestionar inventario de productos",
                        help="Frase de requerimiento inicial del usuario")
    parser.add_argument("--non-interactive", action="store_true",
                        help="Ejecuta en modo no interactivo utilizando los Smart Defaults recomendados")
    args = parser.parse_args()

    run_grill_interview(args.prompt, interactive=not args.non_interactive)


if __name__ == "__main__":
    main()
