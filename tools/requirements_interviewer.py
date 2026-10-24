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


def run_grill_interview(initial_prompt: str, interactive: bool = True, project_name: str = None):
    """
    Ejecuta las rondas del árbol de diseño basadas en la filosofía 'grill-me'.
    Guarda los artefactos de forma aislada en projects/<project_name>/artifacts/01_prd/.
    """
    paths = get_project_paths(project_name) if get_project_paths else {"01_prd": Path("projects/app/artifacts/01_prd")}
    prd_pool = paths["01_prd"]
    prd_pool.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("  SOFTWARE FACTORY: SESIÓN DE REQUIREMENTS GRILLING & DISCOVERY")
    print("  Basado en la metodología Grill-Me de AI Hero")
    print("=" * 70)
    print(f"Requerimiento Semilla: \"{initial_prompt}\"")
    print("Iniciando rondas de preguntas para desgranar el árbol de decisiones...\n")

    answers = {}

    # -------------------------------------------------------------
    # RONDA 1: Propósito, Arquitectura y Entidades Centrales
    # -------------------------------------------------------------
    print("--- [RONDA 1: Propósito del Sistema, Interfaz y Entidades] ---")

    # Q1: Estilo arquitectónico de API
    _, answers["api_style"] = ask_round_question(
        q_id=1,
        title="Estilo Arquitectónico y Protocolo",
        description="¿Qué estilo de API y formato de transferencia se requiere?",
        options={
            "rest_json": "RESTful API sobre HTTP con payloads JSON y códigos de estado estándar",
            "fastapi": "FastAPI (Python) asíncrono con esquemas Pydantic y documentación OpenAPI/Swagger automática",
            "grpc": "gRPC con Protobuf para alta performance y baja latencia",
            "cli_api": "Herramienta CLI interactiva con comandos enriquecidos",
        },
        recommended="fastapi" if "fastapi" in initial_prompt.lower() else "rest_json",
        interactive=interactive,
    )

    # Q2: Consumidores previstos
    _, answers["consumers"] = ask_round_question(
        q_id=2,
        title="Consumidores y Clientes del Sistema",
        description="¿Quiénes interactuarán directamente con esta API?",
        options={
            "spa_mobile": "Aplicaciones frontend (SPA Web / React / Vue) y aplicaciones móviles",
            "microservices": "Otros microservicios y sistemas backend (comunicación inter-servicio)",
            "third_party": "Desarrolladores y clientes externos a través de una API pública con rate-limiting",
            "internal_cli": "Operadores de sistemas mediante scripts y terminales CLI",
        },
        recommended="spa_mobile",
        interactive=interactive,
    )

    # Q3: Entidades del dominio
    print("\n❓ [Q3] - Entidades y Recursos Principales del Dominio")
    print("   Define los 2 a 4 recursos clave que gestionará la API (ej: Productos, Clientes, Pedidos).")
    default_entities = "Items, Categorias, Movimientos"
    if "clima" in initial_prompt.lower():
        default_entities = "Ciudades, Pronósticos, Alertas"
    elif "tarea" in initial_prompt.lower() or "todo" in initial_prompt.lower():
        default_entities = "Tareas, Proyectos, Etiquetas"
    elif "usuario" in initial_prompt.lower() or "auth" in initial_prompt.lower():
        default_entities = "Usuarios, Roles, Sesiones"
    elif "inventario" in initial_prompt.lower() or "stock" in initial_prompt.lower():
        default_entities = "Productos, Almacenes, Lotes, Stock"

    print(f"   ➡️  Recomendación: {default_entities}")
    if interactive and sys.stdin.isatty():
        try:
            ent_input = input(f"   Ingresa las entidades separadas por coma (ENTER para '{default_entities}'): ").strip()
            answers["entities"] = ent_input if ent_input else default_entities
        except (EOFError, KeyboardInterrupt):
            answers["entities"] = default_entities
    else:
        answers["entities"] = default_entities
    print(f"   ✓ [Entidades fijadas]: {answers['entities']}")

    # -------------------------------------------------------------
    # RONDA 2: Seguridad, Autenticación y Autorización
    # -------------------------------------------------------------
    print("\n--- [RONDA 2: Seguridad, Autenticación y Esquema de Errores] ---")

    # Q4: Autenticación
    _, answers["auth_scheme"] = ask_round_question(
        q_id=4,
        title="Esquema de Autenticación y Seguridad",
        description="¿Qué mecanismo de protección de endpoints se implementará?",
        options={
            "jwt_bearer": "Bearer Token (JWT) con expiración y soporte para Refresh Token",
            "api_key": "Cabecera 'X-API-Key' estática o administrable para cada cliente",
            "session_cookies": "Cookies de sesión HTTP-Only (Seguras contra XSS/CSRF)",
            "public_no_auth": "Acceso libre/público sin autenticación (sólo para endpoints informativos o MVP)",
        },
        recommended="jwt_bearer",
        interactive=interactive,
    )

    # Q5: Formato de Errores
    _, answers["error_format"] = ask_round_question(
        q_id=5,
        title="Estructura de Respuestas de Error",
        description="¿Cómo responderá la API ante excepciones y fallos de validación (4xx / 5xx)?",
        options={
            "rfc7807": "RFC 7807 (Problem Details: 'type', 'title', 'status', 'detail', 'invalid_params')",
            "standard_json": "JSON uniforme simple: {'success': false, 'error': {'code': '...', 'message': '...'}}",
            "http_status_only": "Códigos de estado HTTP básicos con texto plano",
        },
        recommended="rfc7807",
        interactive=interactive,
    )

    # -------------------------------------------------------------
    # RONDA 3: Persistencia, Volumen y Rendimiento
    # -------------------------------------------------------------
    print("\n--- [RONDA 3: Persistencia de Datos y Rendimiento] ---")

    # Q6: Base de datos / Persistencia
    _, answers["persistence"] = ask_round_question(
        q_id=6,
        title="Motor de Base de Datos y Persistencia",
        description="¿Dónde residirán los datos del sistema?",
        options={
            "sqlite": "SQLite3 local con WAL activado (ligera, embebida, ideal para pruebas y microservicios autocontenidos)",
            "postgresql": "PostgreSQL relacional con soporte para transacciones complejas y extensiones",
            "in_memory": "Almacenamiento en memoria volátil (Dicts/Memory-DB) con opción de volcado JSON",
            "mongodb": "Base de datos de documentos NoSQL para esquemas altamente variables",
        },
        recommended="sqlite",
        interactive=interactive,
    )

    # Q7: Estrategia de Caché
    _, answers["caching"] = ask_round_question(
        q_id=7,
        title="Estrategia de Caché y Optimización de Consultas",
        description="¿Se requiere acelerar las lecturas con mecanismos de caché?",
        options={
            "ttl_memory": "Caché en memoria local con tiempo de expiración (TTL) y purga automática",
            "redis": "Caché distribuida externa Redis con soporte pub/sub",
            "no_cache": "Sin capa de caché (consultas directas a persistencia para el MVP)",
        },
        recommended="ttl_memory",
        interactive=interactive,
    )

    # -------------------------------------------------------------
    # RONDA 4: Historias de Usuario, Validación y Despliegue
    # -------------------------------------------------------------
    print("\n--- [RONDA 4: Criterios de Aceptación, Validación y Despliegue] ---")

    # Q8: Validación de esquemas
    _, answers["validation"] = ask_round_question(
        q_id=8,
        title="Validación de Entradas y Tipado Estricto",
        description="¿Cómo se verificarán los payloads enviados por los clientes?",
        options={
            "strict_schemas": "Esquemas estrictos tipados (Pydantic / dataclasses) con rechazo automático 422",
            "manual_validation": "Validación manual ligera de campos obligatorios en cada controlador",
            "permissive": "Aceptación flexible con conversión de tipos automática",
        },
        recommended="strict_schemas",
        interactive=interactive,
    )

    # Q9: Despliegue
    _, answers["deployment"] = ask_round_question(
        q_id=9,
        title="Estrategia de Empaquetado y Despliegue",
        description="¿Cómo se empaquetará la solución para producción?",
        options={
            "docker_slim": "Contenedor Docker (python:3.11-slim) con entrypoint preconfigurado y healthcheck",
            "standalone_cli": "Script Python ejecutable o paquete instalable con pyproject.toml",
            "compose": "Entorno multi-servicio con Docker Compose",
        },
        recommended="docker_slim",
        interactive=interactive,
    )

    # -------------------------------------------------------------
    # COMPILACIÓN DEL ARTEFACTO: DISCOVERY_NOTES.md
    # -------------------------------------------------------------
    discovery_file = prd_pool / "DISCOVERY_NOTES.md"
    generate_discovery_notes(initial_prompt, answers, discovery_file)

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
    print("-> Las decisiones han sido congeladas. El Product Manager puede generar el PRD sin suposiciones.")
    print("=" * 70 + "\n")

    return discovery_file, answers


def generate_discovery_notes(initial_prompt: str, answers: dict, output_path: Path):
    """Genera el documento DISCOVERY_NOTES.md en formato Markdown enriquecido."""
    entities_list = [e.strip() for e in answers["entities"].split(",") if e.strip()]

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
| **Consumidores Clave** | {answers['consumers']} | Define los requerimientos de latencia y CORS |
| **Seguridad & Auth** | {answers['auth_scheme']} | Aislamiento y control de acceso robusto |
| **Gestión de Errores** | {answers['error_format']} | Estándar predecible para simplificar la integración frontend |
| **Persistencia** | {answers['persistence']} | Integridad transaccional y bajo acoplamiento |
| **Caché & Rendimiento** | {answers['caching']} | Evita sobrecarga en operaciones de lectura repetitivas |
| **Validación de Datos** | {answers['validation']} | Previene inyección y corrupción del modelo |
| **Estrategia Despliegue** | {answers['deployment']} | Autocontenido y ejecutable en cualquier entorno |

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

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)


def parse_discovery_notes(content: str) -> dict[str, str]:
    """Extrae las decisiones y respuestas estructuradas de un documento DISCOVERY_NOTES.md."""
    parsed = {
        "prompt": "",
        "api_style": "",
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
