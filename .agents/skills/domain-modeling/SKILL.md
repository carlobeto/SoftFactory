---
name: domain-modeling
description: Disciplina para capturar el lenguaje ubicuo, modelos de dominio y registros de decisiones arquitectónicas (ADRs) durante la definición de sistemas.
version: 1.0.0
type: knowledge
applies_to_stages: [discovery_notes, prd, system_design]
---

# Skill: Domain Modeling & ADRs

Esta skill se activa durante la fase de análisis y diseño para evitar ambigüedades terminológicas y asentar por escrito las decisiones arquitectónicas clave.

## 1. Glosario y Lenguaje Ubicuo (Ubiquitous Language)
- Identificar y desambiguar términos sobrecargados. (Ejemplo: ¿Un "Cliente" es lo mismo que un "Usuario" o una "Cuenta"?).
- Cada término clave del negocio debe tener una definición inequívoca que se use idénticamente en:
  1. El PRD y las Historias de Usuario.
  2. El diseño de clases y modelos del Arquitecto.
  3. Los nombres de variables, tablas y rutas del Programador.
  4. Los casos de prueba del QA Tester.

## 2. Registro de Decisiones Arquitectónicas (ADR)
Cuando se tome una decisión estructural (ej. elegir SQLite vs Postgres, o JWT vs Sessions), debe documentarse con el formato:
- **Título:** ADR-[Número]: [Título de la Decisión]
- **Estado:** Propuesto / Aceptado / Reemplazado
- **Contexto:** ¿Qué problema o necesidad motiva esta decisión?
- **Decisión:** ¿Qué opción técnica o patrón se adopta?
- **Consecuencias:** ¿Qué beneficios aporta y qué compensaciones (trade-offs) implica?
