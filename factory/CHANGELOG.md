# CHANGELOG del Motor SoftFactory

Cada cambio del motor (skills globales, reglas de `AGENTS.md`, plantillas o código de `tools/`) se registra aquí como resultado de un **Factory RFC** aprobado por el usuario. Ver `AGENTS.md` §5.

## 0.8.0 — 2026-10-26
- **Skill Loader** (`tools/skill_loader.py`): los skills pasan a ser consumidos en tiempo de ejecución (modo prompt y modo datos).
- Manifiesto `skills:` en cada `agents/*/profile.yaml` y nuevo perfil `agents/requirements_discovery/`.
- `grill-me` v1.1.0: el árbol de preguntas de la Etapa 1 se externaliza en `questions.json`.
- Overlays de skills por proyecto (`projects/<p>/.agents/skills/`) con regla de **solo agregar restricciones**.
- Invalidación en cascada: aprobar/revocar un skill de proyecto pasa a *Pendiente* la primera etapa afectada y las posteriores (artefactos archivados en `artifacts/_superseded/`).
- Trazabilidad: `engine_version`, `skills_snapshot` y `artifact_provenance` en `workflow_context.json`; sello de procedencia en los artefactos `.md`.
- Registro de lecciones (`factory/FACTORY_LESSONS.md`) en modo `development` y promoción de skills proyecto → global.
- Suite de regresión del motor en `factory_tests/`.

## 0.7.0 — 2026-10-26
- Etapa 6 (Entorno de Pruebas Local) y menú lateral de 7 etapas en el Dashboard.
