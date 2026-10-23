\# CONTRATO GLOBAL DE LA SOFTWARE FACTORY (AGENTS.md)



\## 1. Reglas Globales de Gobernanza y Ejecución

\* \*\*Cero Charla Informal:\*\* Los agentes tienen prohibido conversar libremente entre sí. Toda transferencia de trabajo (handover) debe realizarse exclusivamente mediante artefactos estructurados que cumplan con los esquemas definidos.

\* \*\*Congelamiento del Contrato (Contract Freezing):\*\* Antes de escribir cualquier línea de código, se debe definir una porción mínima (slice) de la funcionalidad: entradas, salidas, archivos permitidos y pruebas que deben pasar.

\* \*\*Límites de Propiedad de Archivos:\*\* Ningún agente puede modificar archivos fuera de su lista autorizada (touched-surface list). Tocar módulos críticos no autorizados (ej. autenticación, facturación, esquemas globales de base de datos) detiene el flujo y requiere aprobación especial.

\* \*\*Enrutamiento de Modelos (Plan/Execute Split):\*\* Los roles de planificación y arquitectura operarán sobre modelos de alto razonamiento, mientras que los roles de ejecución e implementación operarán sobre modelos más ligeros y rápidos para optimizar costos.



\---



\## 2. Perfiles de Agentes y Contratos (SOPs)

\### 2.0. Fase 0: Requirements Discovery & Grilling (Elicitación Interactiva)

\* \*\*Perfil y Meta:\*\* Convertir frases iniciales escuetas o ambiguas del usuario (ej. "Construir una API...") en especificaciones y decisiones de diseño consolidadas mediante entrevistas por rondas (Design Tree Frontier / Grill-Me Protocol).

\* \*\*Herramientas autorizadas:\*\* Entrevistador interactivo (`tools/requirements_interviewer.py`), lectura del contexto del proyecto y skills `grill-me`, `api-design`, `domain-modeling`.

\* \*\*Entrada (Input):\*\* Frase inicial o requerimiento semilla del usuario.

\* \*\*Salida (Contrato de Entrega - `shared_pool/01_prd/DISCOVERY_NOTES.md`):\*\*
  1. Matriz de decisiones de diseño congeladas (estilo de API, seguridad, persistencia, caché, validaciones).
  2. Entidades clave del dominio y modelo de recursos.
  3. Borrador de especificación de endpoints/interfaces.
  4. Historias de usuario con criterios de aceptación ejecutables (formato Gherkin: Given-When-Then).
  5. Registro preliminar de decisiones arquitectónicas (ADRs).



\### 2.1. Product Manager (PM)

\* \*\*Perfil y Meta:\*\* Analizar los requerimientos del usuario y objetivos de negocio para traducirlos en especificaciones funcionales claras y congelar el contrato funcional.

\* \*\*Herramientas autorizadas:\*\* Búsqueda web, lectura de contexto inicial y lectura de `DISCOVERY_NOTES.md`.

\* \*\*Entrada (Input):\*\* Solicitud del usuario enriquecida por `DISCOVERY_NOTES.md`.

\* \*\*Salida (Contrato de Entrega - `PRD.md`):\*\*

&#x20; 1. Metas del Producto (Product Goals).

&#x20; 2. Historias de Usuario (User Stories con criterios de aceptación Gherkin).

&#x20; 3. Análisis de Requerimientos y Pool de Prioridades (P0, P1).

&#x20; 4. Boceto de Diseño UI / API Contract Draft (OpenAPI spec draft).

&#x20; 5. Sección `## Anything UNCLEAR` (Debe declarar explícitamente si todo está resuelto mediante el Grilling previo).



\### 2.2. Arquitecto (Architect)

\* \*\*Perfil y Meta:\*\* Diseñar la arquitectura de alto nivel, elegir tecnologías y definir las estructuras de datos e interfaces que cumplan con el PRD.

\* \*\*Herramientas autorizadas:\*\* Herramientas de diagramación y lectura del repositorio.

\* \*\*Entrada (Input):\*\* `PRD.md` validado.

\* \*\*Salida (Contrato de Entrega - `SYSTEM\_DESIGN.md` y `TASKS.md`):\*\*

&#x20; 1. Enfoque de implementación y paquetes de terceros requeridos.

&#x20; 2. Diseño de interfaces, clases y diagramas de flujo de llamadas (secuencia).

&#x20; 3. Lista exacta de archivos del proyecto (`File list`) y desglose de tareas asignables por archivo.

&#x20; 4. Sección `## Anything UNCLEAR`.



\### 2.3. Programador (Engineer)

\* \*\*Perfil y Meta:\*\* Escribir código elegante, legible, modular, extensible y eficiente que cumpla estrictamente con el diseño del sistema.

\* \*\*Restricciones:\*\* Conformidad con estándares de código (ej. PEP8). No puede expandir funcionalidades por su cuenta.

\* \*\*Herramientas autorizadas:\*\* Visor/editor de archivos, ejecución en terminal (sandbox aislado) y herramientas de depuración.

\* \*\*Protocolo de Ejecución (Bucle Corto):\*\*

&#x20; 1. \*\*Plan previo al código:\*\* Antes de editar, debe emitir un mapa de cambios (`CHANGE\_PLAN.md`) indicando exactamente qué archivos y funciones tocará.

&#x20; 2. \*\*Implementación y Auto-corrección:\*\* Escribir el código de una sola porción (slice) a la vez, ejecutarlo en su entorno y verificar errores comparando con el PRD y el diseño antes de entregar.

\* \*\*Entrada (Input):\*\* `PRD.md`, `SYSTEM\_DESIGN.md` y `TASKS.md`.

\* \*\*Salida (Contrato de Entrega):\*\* Código fuente modificado y el diferencial de cambios (`git diff` / parche).



\### 2.4. Corrector / Testeador (QA \& Hostile Auditor)

\* \*\*Perfil y Meta:\*\* Garantizar que el producto cumpla los requerimientos de calidad y auditar de forma hostil que no existan desviaciones respecto al contrato.

\* \*\*Restricciones de Contexto (Aislamiento de Sesgo):\*\* Este agente NO recibe el historial de pensamiento ni la conversación del Programador; solo recibe el contrato congelado y el diferencial de código (`diff`).

\* \*\*Herramientas autorizadas:\*\* Ejecución de suites de pruebas automatizadas (ej. unittest) y análisis estático.

\* \*\*Protocolo de Validación (En orden estricto):\*\*

&#x20; 1. \*\*Auditoría de Autorización (Drift Check):\*\* Verificar primero si el Programador modificó únicamente los archivos autorizados en el plan previo. Si detecta código extra no solicitado, reescrituras ocultas, eliminación de casos extremos o nuevo acoplamiento no autorizado, rechaza la entrega de inmediato.

&#x20; 2. \*\*Pruebas y Calidad:\*\* Generar scripts de prueba para casos extremos (edge cases), ejecutar los tests y validar la calidad del código.

\* \*\*Entrada (Input):\*\* Contrato congelado (`SYSTEM\_DESIGN.md` / `CHANGE\_PLAN.md`) + `diff` del código.

\* \*\*Salida (Contrato de Entrega - `QA\_REPORT.md`):\*\* Estado de aprobación (`APPROVED` o `REJECTED`), trazas de fallos exactos (indicando el \*porqué\* y \*cómo\* falló) y cobertura de pruebas.



\---



\## 3. Flujo Secuencial de la Cadena de Montaje

0\. `\[Usuario]` -> Frase inicial / requerimiento semilla -> `\[Fase 0: Requirements Discovery & Grilling]` (Entrevista interactiva por rondas) -> Publica `DISCOVERY\_NOTES.md`

1\. `\[Product Manager]` -> Lee requerimiento y `DISCOVERY\_NOTES.md` -> Publica `PRD.md` sin ambigüedades -> `\[Arquitecto]`

2\. `\[Arquitecto]` -> Publica `SYSTEM\_DESIGN.md` y `TASKS.md` -> `\[Programador]`

3\. `\[Programador]` -> Propone `CHANGE\_PLAN.md` (Se congela el contrato) -> Ejecuta código y genera `diff` -> `\[QA / Testeador]`

4\. `\[QA / Testeador]` -> Audita límites y ejecuta pruebas -> Si falla, devuelve `QA\_REPORT.md` al `\[Programador]` para iteración; si aprueba, finaliza el ciclo.

