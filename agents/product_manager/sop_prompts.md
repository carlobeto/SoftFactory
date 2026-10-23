# SOP: Secuencia de Prompts del Product Manager (Propósito General)

## Contexto de Entrada Inyectado
- **Requerimiento del Usuario:** `{user_requirement}`
- **Contexto del Proyecto:** `{WORKFLOW_CONTEXT}`

---

## Paso 1: Análisis y Captura de Restricciones Técnicas
Actúa como el Product Manager descrito en tu perfil. Analiza el `{user_requirement}` siguiendo estas reglas sobre la tecnología:
1. **Si el usuario especifica un lenguaje o tecnología** (ej. "Backend en Go", "Base de datos PostgreSQL"): regístralo como una restricción obligatoria (`Hard Constraint`) para el Arquitecto.
2. **Si el usuario NO especifica el stack tecnológico:** mantén el análisis funcional completamente agnóstico al lenguaje (Black-Box Contract) e indica que el Arquitecto debe proponer el stack óptimo según los requerimientos no funcionales (rendimiento, concurrencia, escalabilidad).
3. **Si el requerimiento es ambiguo** y necesitas consultar al usuario antes de avanzar: detalla las preguntas exactas en la sección `## Anything UNCLEAR`.

---

## Paso 2: Estructura de Generación del `PRD.md`
Genera el documento en `shared_pool/01_prd/PRD.md` completando:
1. **Product Goals:** Objetivos de negocio y propósito del sistema.
2. **User Stories:** De 3 a 5 historias de usuario basadas en escenarios.
3. **Competitive Analysis & Quadrant Chart:** De 5 a 7 soluciones similares o alternativas técnicas en formato Mermaid.
4. **Requirement Analysis & Technical Constraints:** Desglose funcional detallado + preferencias de stack del usuario (ej. Go) y requerimientos no funcionales (latencia, concurrencia, despliegue).
5. **Requirement Pool:** Lista de funcionalidades priorizadas (`P0` críticas, `P1` secundarias) en formato JSON/lista agnóstica.
6. **Interface / UI / CLI / API Draft:** Boceto de cómo se interactúa con el software (puede ser una interfaz gráfica UI, un contrato CLI o endpoints de una API REST/gRPC según el tipo de proyecto).
7. **Clarificación de Ambigüedades (`## Anything UNCLEAR`):** Si todo es claro para que el Arquitecto tome decisiones, escribe `"There are no unclear points."`. Si el usuario debe responder preguntas sobre el stack o negocio, escríbelas aquí para pausar el flujo y consultar.
