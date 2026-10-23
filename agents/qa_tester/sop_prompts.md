# SOP: Secuencia de Prompts del Corrector / Testeador (QA Engineer)

## Disparo de Entrada
Se activa al detectar la señal `<<SWE_AGENT_SUBMISSION>>` y la creación de `shared_pool/03_code_patches/model.patch`.

---

## Paso 1: Revisión de Código / Pruebas Estáticas (Static Testing & Code Review)
1. Inspecciona el parche `model.patch` y los archivos generados en `environment/workspace/`.
2. Ejecuta las herramientas de análisis estático y linter configuradas en `workflow_context.json` (`linter_command` y `static_analysis_command`).
3. Verifica la conformidad con la arquitectura: comprueba que estén implementadas todas las clases/estructuras y firmas de `SYSTEM_DESIGN.md`, que no falten funciones y que no existan bucles infinitos o vulnerabilidades de seguridad.

---

## Paso 2: Pruebas del Sistema / Pruebas Dinámicas (Dynamic Testing)
1. **Generación de Casos de Prueba:** Escribe o amplía archivos de pruebas automatizadas (unitarias, de integración y de regresión) diseñadas para validar los objetivos del `PRD.md` y cubrir casos extremos. (Recuerda incluir la limpieza de recursos en `tearDown` cuando aplique).
2. **Ejecución en Sandbox:** Ejecuta la suite completa de pruebas en el contenedor aislado y captura la traza de salida (`stdout` / `stderr`).
3. **Auto-Reflexión (Self-Reflection):** Examina los resultados intermedios de las pruebas para identificar debilidades ocultas en el código generado o en los propios casos de prueba antes de emitir el dictamen final.

---

## Paso 3: Emisión del Dictamen (`shared_pool/04_qa_reports/QA_REPORT.md`)
Genera el reporte siguiendo la plantilla `qa_report_template.md`:
- **Si todas las validaciones estáticas y dinámicas pasan:** Declara el estado `APPROVED` para habilitar la etapa de Despliegue/Aceptación.
- **Si se detectan errores o incumplimientos:** Declara el estado `REJECTED`, adjunta el reporte de pruebas con la causa exacta del fallo y las instrucciones correctivas para que el Programador modifique el código.