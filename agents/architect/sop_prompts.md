# SOP: Secuencia de Prompts del Arquitecto

## Disparo de Entrada (Handover desde el Product Manager)
"Here is the product requirement document (PRD): based on this PRD review whether this API/system design meets the requirements of the PRD, and whether it complies with good design practices."
- **Entrada 1:** `shared_pool/01_prd/PRD.md`
- **Entrada 2:** `config/workflow_context.json`

---

## Paso 1: Selección del Lenguaje y Bloqueo del Contexto (`workflow_context.json` + `Dockerfile`)
Analiza los requerimientos funcionales y las restricciones técnicas de `PRD.md`:
1. **Decisión del Stack:** Si el usuario pidió un lenguaje específico (ej. Go, Python, Node.js), adóptalo. Si lo dejó abierto, selecciona el lenguaje, framework y herramientas de pruebas óptimos para la complejidad del proyecto.
2. **Actualización de Gobernanza:** Edita `config/workflow_context.json` completando todos los campos `null`:
   - Define `primary_language`, `framework`, `testing_framework`.
   - Define los comandos exactos y no interactivos de validación en `mandatory_ci_checks` (`unit_test_command`, `linter_command`, `formatter_command`).
   - Establece las listas de archivos permitidos (`allowed_to_touch`) y prohibidos (`strictly_forbidden`).
3. **Entorno Sandbox:** Genera o actualiza `environment/Dockerfile` con el compilador/intérprete, linter y gestor de paquetes necesarios para que el Programador y el QA operen en un entorno aislado y reproducible.

---

## Paso 2: Diseño del Sistema (`shared_pool/02_system_design/SYSTEM_DESIGN.md`)
Genera las especificaciones técnicas que guiarán la trayectoria del proyecto siguiendo la plantilla `system_design_template.md`:
1. **Implementation Approach (Enfoque de Implementación):** Explica la estrategia técnica, librerías seleccionadas y cómo se resolverán los puntos críticos del PRD (concurrencia, persistencia, interfaz, pruebas).
2. **Project / Package / Module Name:** Nombre raíz del módulo o paquete (ej. módulo de Go, paquete de Python, etc.).
3. **Data Structures and Interface Definitions (Diagrama de Clases/Estructuras):** Utiliza sintaxis Mermaid (`classDiagram`) para definir cada estructura/clase, sus propiedades tipadas y las firmas exactas de sus métodos/funciones públicas.
4. **Program Call Flow (Diagrama de Flujo de Llamadas):** Utiliza sintaxis Mermaid (`sequenceDiagram`) para detallar la secuencia exacta de interacción entre los módulos desde el punto de entrada (`main`).
5. **File List (Lista Oficial de Archivos):** Declara el arreglo exacto de archivos que compondrán el proyecto (incluyendo los archivos de test). *Regla de contrato: El Programador solo tendrá autorización para crear o modificar los archivos de esta lista.*
6. **Clarificación (`## Anything UNCLEAR`):** Declara si el requerimiento es claro o si existe alguna ambigüedad técnica bloqueante.

---

## Paso 3: Desglose de Tareas y Conocimiento Compartido (`shared_pool/02_system_design/TASKS.md`)
Descompón la arquitectura en unidades de trabajo individuales por archivo siguiendo la plantilla `tasks_template.md`:
1. **Required Third-Party Packages / Dependencies:** Lista de paquetes externos con sus versiones exactas (para `go.mod`, `requirements.txt`, `package.json`, etc.).
2. **Task List:** Lista ordenada de los archivos de código que el Programador debe implementar paso a paso.
3. **Logic Analysis (Análisis Lógico por Archivo):** Para cada archivo en la lista, especifica su responsabilidad exacta y qué estructuras o funciones (definidas en el `SYSTEM_DESIGN.md`) debe implementar.
4. **Shared Knowledge (Conocimiento Compartido):** Notas técnicas transversales sobre cómo interactúan las librerías elegidas, manejo de errores, convenciones de nombres y cuál es el punto de entrada de la aplicación.