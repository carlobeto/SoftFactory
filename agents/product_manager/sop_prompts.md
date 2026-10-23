# SOP: Secuencia de Prompts del Product Manager (Propósito General)

## Contexto de Entrada Inyectado
- **Requerimiento del Usuario:** `{user_requirement}`
- **Contexto del Proyecto:** `{WORKFLOW_CONTEXT}`
- **Notas de Discovery / Grilling (Fase 0):** `shared_pool/01_prd/DISCOVERY_NOTES.md` (si existe)

---

## Paso 1: Análisis y Captura de Restricciones Técnicas
Actúa como el Product Manager descrito en tu perfil. Analiza el `{user_requirement}` y, si está presente, el archivo `DISCOVERY_NOTES.md`:
1. **Si existe `DISCOVERY_NOTES.md`:** Considera todas las decisiones arquitectónicas, entidades, autenticación y criterios Gherkin como decisiones congeladas por el usuario. Trasládalas directamente al PRD sin inventar alternativas que contradigan dicho documento.
2. **Si el usuario especifica un lenguaje o tecnología** (ej. "Backend en Go", "Base de datos PostgreSQL"): regístralo como una restricción obligatoria (`Hard Constraint`) para el Arquitecto.
3. **Si el usuario NO especifica el stack tecnológico:** mantén el análisis funcional completamente agnóstico al lenguaje (Black-Box Contract) e indica que el Arquitecto debe proponer el stack óptimo según los requerimientos no funcionales (rendimiento, concurrencia, escalabilidad).
4. **Si el requerimiento es ambiguo y NO hay `DISCOVERY_NOTES.md`:** activa o recomienda la ejecución de la skill `grill-me` y detalla las preguntas exactas en la sección `## Anything UNCLEAR`. Si existe `DISCOVERY_NOTES.md`, declara resuelta la sección.

---

## Paso 2: Estructura de Generación del `PRD.md`
Genera el documento en `shared_pool/01_prd/PRD.md` completando:
1. **Product Goals:** Objetivos de negocio y propósito del sistema.
2. **User Stories:** De 3 a 5 historias de usuario basadas en escenarios, cada una con sus **Criterios de Aceptación en formato Gherkin** (`Dado... Cuando... Entonces...`).
3. **Competitive Analysis & Quadrant Chart:** De 3 a 5 soluciones similares o alternativas técnicas en formato Mermaid.
4. **Requirement Analysis & Technical Constraints:** Desglose funcional detallado + restricciones técnicas acordadas en Discovery (Auth, Persistencia, Validaciones).
5. **Requirement Pool:** Lista de funcionalidades priorizadas (`P0` críticas, `P1` secundarias) en formato JSON/lista agnóstica.
6. **Interface / UI / CLI / API Draft:** Boceto detallado del contrato de endpoints de la API (rutas, métodos HTTP, códigos de retorno y esquema de error RFC 7807) o interfaces correspondientes.
7. **Clarificación de Ambigüedades (`## Anything UNCLEAR`):** Si `DISCOVERY_NOTES.md` resolvió las dudas, escribe: `"All requirements and architectural boundaries have been clarified and frozen via Phase 0 Grilling."`. De lo contrario, lista las preguntas pendientes.
