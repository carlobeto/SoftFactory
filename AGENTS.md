\# CONTRATO GLOBAL DE LA SOFTWARE FACTORY (AGENTS.md)



\## 1. Reglas Globales de Gobernanza y Ejecución

\* \*\*Cero Charla Informal:\*\* Los agentes tienen prohibido conversar libremente entre sí. Toda transferencia de trabajo (handover) debe realizarse exclusivamente mediante artefactos estructurados que cumplan con los esquemas definidos.

\* \*\*Congelamiento del Contrato (Contract Freezing):\*\* Antes de escribir cualquier línea de código, se debe definir una porción mínima (slice) de la funcionalidad: entradas, salidas, archivos permitidos y pruebas que deben pasar.

\* \*\*Límites de Propiedad de Archivos:\*\* Ningún agente puede modificar archivos fuera de su lista autorizada (touched-surface list). Tocar módulos críticos no autorizados (ej. autenticación, facturación, esquemas globales de base de datos) detiene el flujo y requiere aprobación especial.

\* \*\*Enrutamiento de Modelos (Plan/Execute Split):\*\* Los roles de planificación y arquitectura operarán sobre modelos de alto razonamiento, mientras que los roles de ejecución e implementación operarán sobre modelos más ligeros y rápidos para optimizar costos.

\* \*\*Separación Estricta de Instancias (Motor SoftFactory vs. Producto Generado):\*\* La Software Factory es una plataforma/motor inmutable. Toda aplicación o producto de software desarrollado por las etapas de la fábrica se genera de forma 100% aislada en su propia carpeta autocontenida: `projects/<Nombre_Proyecto>/` (con sus subcarpetas `artifacts/`, `workspace/` y su propio `workflow_context.json`). El motor de SoftFactory, sus agentes, herramientas, scripts y configuración preexistente tienen prohibido ser modificados o ensuciados al interactuar desde la UI o CLI. Las carpetas de proyecto pueden ser conservadas, exportadas o eliminadas independientemente sin afectar la Software Factory.

\* \*\*Compuertas de Aprobación Humana Obligatoria (Human-in-the-Loop Gatekeeper):\*\* Cada etapa de la fábrica produce entregables sujetos a la revisión y aprobación explícita del usuario humano antes de habilitar la fase siguiente.
  \*\*Restricción Crítica sobre Fuentes de Código:\*\* El Programador tiene TERMINANTEMENTE PROHIBIDO crear, editar o parchar archivos en `projects/<Nombre_Proyecto>/workspace/` (o cualquier directorio de código) sin que el usuario humano haya revisado y aprobado formalmente el plan de cambios (`CHANGE_PLAN.md`), el diseño técnico y la lista de archivos autorizados.
  En solicitudes de mantenimiento, corrección de defectos (bugfixes) o nuevas funcionalidades (RFCs), la fábrica debe informar de manera obligatoria el alcance e impacto de la modificación al usuario y requerir su consentimiento antes de ejecutar cualquier cambio en los fuentes.



\---



\## 2. Perfiles de Agentes y Contratos (SOPs)

\### 2.1. Etapa 1: Requirements Discovery & Grilling (Elicitación Interactiva)

\* \*\*Perfil y Meta:\*\* Convertir frases iniciales escuetas o ambiguas del usuario (ej. "Construir una API...") en especificaciones y decisiones de diseño consolidadas mediante entrevistas por rondas (Design Tree Frontier / Grill-Me Protocol).

\* \*\*Herramientas autorizadas:\*\* Entrevistador interactivo (`tools/requirements_interviewer.py`), lectura del contexto del proyecto y skills `grill-me`, `api-design`, `domain-modeling`.

\* \*\*Entrada (Input):\*\* Frase inicial o requerimiento semilla del usuario.

\* \*\*Salida (Contrato de Entrega - `shared_pool/01_prd/DISCOVERY_NOTES.md`):\*\*
  1. Matriz de decisiones de diseño congeladas (estilo de API, seguridad, persistencia, caché, validaciones).
  2. Entidades clave del dominio y modelo de recursos.
  3. Borrador de especificación de endpoints/interfaces.
  4. Historias de usuario con criterios de aceptación ejecutables (formato Gherkin: Given-When-Then).
  5. Registro preliminar de decisiones arquitectónicas (ADRs).



\### 2.2. Etapa 2: Product Manager (PM)

\* \*\*Perfil y Meta:\*\* Analizar los requerimientos del usuario y objetivos de negocio para traducirlos en especificaciones funcionales claras y congelar el contrato funcional.

\* \*\*Herramientas autorizadas:\*\* Búsqueda web, lectura de contexto inicial y lectura de `DISCOVERY_NOTES.md`.

\* \*\*Entrada (Input):\*\* Solicitud del usuario enriquecida por `DISCOVERY_NOTES.md`.

\* \*\*Salida (Contrato de Entrega - `PRD.md`):\*\*

&#x20; 1. Metas del Producto (Product Goals).

&#x20; 2. Historias de Usuario (User Stories con criterios de aceptación Gherkin).

&#x20; 3. Análisis de Requerimientos y Pool de Prioridades (P0, P1).

&#x20; 4. Boceto de Diseño UI / API Contract Draft (OpenAPI spec draft).

&#x20; 5. Sección `## Anything UNCLEAR` (Debe declarar explícitamente si todo está resuelto mediante el Grilling previo).



\### 2.3. Etapa 3: Arquitecto (Architect)

\* \*\*Perfil y Meta:\*\* Diseñar la arquitectura de alto nivel, elegir tecnologías y definir las estructuras de datos e interfaces que cumplan con el PRD.

\* \*\*Herramientas autorizadas:\*\* Herramientas de diagramación y lectura del repositorio.

\* \*\*Entrada (Input):\*\* `PRD.md` validado.

\* \*\*Salida (Contrato de Entrega - `SYSTEM_DESIGN.md` y `TASKS.md`):\*\*

&#x20; 1. Enfoque de implementación y paquetes de terceros requeridos.

&#x20; 2. Diseño de interfaces, clases y diagramas de flujo de llamadas (secuencia).

&#x20; 3. Lista exacta de archivos del proyecto (`File list`) y desglose de tareas asignables por archivo.

&#x20; 4. Sección `## Anything UNCLEAR`.



\### 2.4. Etapa 4: Programador (Engineer)

\* \*\*Perfil y Meta:\*\* Escribir código elegante, legible, modular, extensible y eficiente que cumpla estrictamente con el diseño del sistema.

\* \*\*Restricciones:\*\* Conformidad con estándares de código (ej. PEP8). No puede expandir funcionalidades por su cuenta.

\* \*\*Herramientas autorizadas:\*\* Visor/editor de archivos, ejecución en terminal (sandbox aislado) y herramientas de depuración.

\* \*\*Protocolo de Ejecución (Bucle Corto):\*\*

&#x20; 1. \*\*Plan previo al código:\*\* Antes de editar, debe emitir un mapa de cambios (`CHANGE_PLAN.md`) indicando exactamente qué archivos y funciones tocará.

&#x20; 2. \*\*Implementación y Auto-corrección:\*\* Escribir el código de una sola porción (slice) a la vez, ejecutarlo en su entorno y verificar errores comparando con el PRD y el diseño antes de entregar.

\* \*\*Entrada (Input):\*\* `PRD.md`, `SYSTEM_DESIGN.md` y `TASKS.md`.

\* \*\*Salida (Contrato de Entrega):\*\* Código fuente modificado y el diferencial de cambios (`git diff` / parche `model.patch`).



\### 2.5. Etapa 5: Corrector / Testeador (QA & Hostile Auditor)

\* \*\*Perfil y Meta:\*\* Garantizar que el producto cumpla los requerimientos de calidad y auditar de forma hostil que no existan desviaciones respecto al contrato.

\* \*\*Restricciones de Contexto (Aislamiento de Sesgo):\*\* Este agente NO recibe el historial de pensamiento ni la conversación del Programador; solo recibe el contrato congelado y el diferencial de código (`diff`).

\* \*\*Herramientas autorizadas:\*\* Ejecución de suites de pruebas automatizadas (ej. unittest) y análisis estático.

\* \*\*Protocolo de Validación (En orden estricto):\*\*

&#x20; 1. \*\*Auditoría de Autorización (Drift Check):\*\* Verificar primero si el Programador modificó únicamente los archivos autorizados en el plan previo. Si detecta código extra no solicitado, reescrituras ocultas, eliminación de casos extremos o nuevo acoplamiento no autorizado, rechaza la entrega de inmediato.

&#x20; 2. \*\*Pruebas y Calidad:\*\* Generar scripts de prueba para casos extremos (edge cases), ejecutar los tests y validar la calidad del código.

\* \*\*Entrada (Input):\*\* Contrato congelado (`SYSTEM_DESIGN.md` / `CHANGE_PLAN.md`) + `diff` del código.

\* \*\*Salida (Contrato de Entrega - `QA_REPORT.md`):\*\* Estado de aprobación (`APPROVED` o `REJECTED`), trazas de fallos exactos (indicando el \*porqué\* y \*cómo\* falló) y cobertura de pruebas.



\---



\## 3. Flujo Secuencial de la Cadena de Montaje con Compuertas de Aprobación Humana (1 a 5)

1\. `[Usuario]` -> Frase inicial / requerimiento semilla -> `[Etapa 1: Discovery & Grilling]` -> Publica `DISCOVERY_NOTES.md` -> 🛡️ **[Compuerta 1: Revisión y Aprobación Humana del Discovery]**

2\. 🛡️ *Aprobado por Usuario* -> `[Product Manager]` -> Publica `PRD.md` -> 🛡️ **[Compuerta 2: Revisión y Aprobación Humana del PRD]**

3\. 🛡️ *Aprobado por Usuario* -> `[Arquitecto]` -> Publica `SYSTEM_DESIGN.md` y `TASKS.md` -> 🛡️ **[Compuerta 3: Revisión y Aprobación Humana de la Arquitectura]**

4\. 🛡️ *Aprobado por Usuario* -> `[Programador]` -> Emite `CHANGE_PLAN.md` -> 🚨 **[Compuerta Crítica 4: AUTORIZACIÓN HUMANA PREVIA A MODIFICAR FUENTES]**
   - El sistema informa al usuario los archivos autorizados y el plan de cambios exacto.
   - Solo tras la aprobación explícita humana, el Programador escribe código en `environment/workspace/` y genera `model.patch`.

5\. `[QA / Testeador]` -> Audita límites y ejecuta pruebas -> Emite `QA_REPORT.md` -> 🛡️ **[Compuerta 5: Aprobación Humana Final para Despliegue/Exportación]**
   - Si falla, devuelve `QA_REPORT.md` al `[Programador]` para corrección bajo supervisión humana.



\---



\## 4. Lazo de Mantenimiento y Corrección Continua (Feedback Loops)

Para evitar reiniciar proyectos desde cero ante defectos o ampliaciones funcionales, la Software Factory opera bajo dos lazos de retroalimentación con control humano estricto:

\* \*\*Regla de Oro de Fuentes:\*\* Toda corrección de bug o nueva funcionalidad requiere autorización humana previa antes de tocar cualquier archivo de código existente en `environment/workspace/`.

\### 4.1. Lazo Corto de Corrección (Bugfix / Rechazo de QA en Etapa 5)
\* \*\*Disparador:\*\* `QA_REPORT.md` emite estado `REJECTED` debido a fallos de pruebas o detección de deriva no autorizada (Drift).
\* \*\*Regla de Preservación:\*\* El espacio `environment/workspace/` se conserva intacto (no se borra).
\* \*\*Acción y Compuerta:\*\*
  1. El Programador lee las trazas del fallo y emite `CHANGE_PLAN.md` con la corrección puntual propuesta.
  2. 🚨 **Compuerta Humana:** El usuario revisa el plan de corrección y autoriza la modificación de fuentes.
  3. El Programador aplica el parche estrictamente en los archivos aprobados, regenera `model.patch` y reenvía a Etapa 5 (QA).

\### 4.2. Lazo de Mantenimiento Evolutivo (RFC / Nuevos Requerimientos sobre Proyectos Activos)
\* \*\*Disparador:\*\* Solicitud del usuario de una nueva funcionalidad, cambio en reglas de negocio o corrección post-aprobación en una app existente.
\* \*\*Artefacto Semilla:\*\* `shared_pool/01_prd/DELTA_REQUIREMENT.txt`.
\* \*\*Flujo Incremental con Aprobación:\*\*
  1. \*\*Product Manager (Etapa 2 - Delta):\*\* Analiza el código actual y genera un `DELTA_PRD.md` con historias Gherkin incrementales.
  2. \*\*Arquitecto (Etapa 3 - Delta):\*\* Evalúa impacto en base de datos, módulos y endpoints. Actualiza `TASKS.md` y delimita la superficie permitida en `workflow_context.json`.
  3. 🚨 **Compuerta Humana de Pre-Modificación:** El usuario revisa el informe de impacto (`DELTA_PRD.md`, tareas y archivos afectados) y aprueba la modificación de código.
  4. \*\*Programador (Etapa 4 - Incremental):\*\* Implementa la modificación en el workspace existente y genera el parche acumulativo.
  5. \*\*QA & Hostile Auditor (Etapa 5 - Regresión):\*\* Ejecuta:
     a) **Pruebas de Regresión:** Verifica que las funcionalidades previas sigan pasando al 100%.
     b) **Nuevas Pruebas:** Evalúa los nuevos criterios de aceptación del `DELTA_PRD.md`.
     c) Si aprueba, emite `QA_REPORT.md (APPROVED)` y habilita la confirmación humana para el nuevo tag de versión en Git (ej: `v1.1`).

