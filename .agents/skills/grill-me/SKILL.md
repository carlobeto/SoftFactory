---
name: grill-me
description: Entrevista exhaustiva, interactiva y estructurada por rondas de diseño para refinar requerimientos iniciales de software y APIs antes de generar el PRD.
version: 1.1.0
type: knowledge
applies_to_stages: [discovery_notes]
---

# Skill: Grill-Me para Software Factory (Requirements Discovery)

Usa esta skill cuando el usuario proporcione una idea inicial escueta (ej. "Construir una API...", "Hacer un microservicio...") y sea necesario desgranar todas las decisiones arquitectónicas, modelos de datos, casos de uso y restricciones antes de redactar el `PRD.md`.

## Filosofía Operativa
1. **Inversión de Carga:** El usuario no debe escribir un prompt perfecto; tú debes entrevistarlo implacablemente para modelar su pensamiento.
2. **Árbol de Diseño (Design Tree):** Las decisiones se organizan en jerarquía. No preguntes sobre persistencia o bases de datos relacionales si aún no se definió si los datos requieren transaccionalidad ACID o documentos.
3. **Avance por Rondas de la Frontera (Frontier Rounds):** Agrupa en cada ronda únicamente aquellas preguntas cuyos prerrequisitos ya estén decididos.
4. **Recomendaciones Inteligentes (Smart Defaults):** Cada pregunta DEBE incluir una respuesta recomendada (`➡️`), permitiendo al usuario aceptar con un simple "acepto las recomendaciones" o ajustar selectivamente.
5. **Autonomía en Hechos vs Juicios de Valor:** Investiga el repositorio y documentación técnica por tu cuenta; sólo pregunta al usuario sobre preferencias de negocio, restricciones de dominio o prioridades.
6. **Cierre y Materialización:** La sesión no concluye en el chat; debe culminar generando el artefacto estructurado `shared_pool/01_prd/DISCOVERY_NOTES.md`.

---

## Formato Estricto de Cada Ronda

Formula de 2 a 4 preguntas por ronda con el siguiente formato:

```markdown
❓ **Q[Número] - [Título de la Decisión]**: [Explicación contextual y opciones concisas (a, b, c)]
➡️ **Recomendación:** [Opción recomendada] — [Justificación técnica breve]
```

---

## Dimensiones Clave a Explorar en Proyectos de Software y APIs

### Ronda 1: Propósito, Actores y Alcance Central
- **Objetivo del sistema:** ¿Qué problema central resuelve la API/aplicación y quiénes la consumen (frontend web, apps móviles, scripts batch, terceros)?
- **Estilo de Arquitectura:** RESTful JSON, GraphQL, gRPC o CLI.
- **Entidades primarias (Dominio):** ¿Cuáles son los 2 a 4 recursos o entidades centrales de la aplicación?

### Ronda 2: Autenticación, Seguridad y Contrato de la API
- **Seguridad:** ¿Pública, API Keys, Bearer Token (JWT), OAuth2?
- **Control de Acceso:** ¿Todos los usuarios tienen los mismos permisos o se requiere RBAC (ej. Admin vs User)?
- **Manejo de Errores y Validaciones:** ¿Se requiere formato estándar de error (ej. RFC 7807 Problem Details)?

### Ronda 3: Persistencia, Volumen y Rendimiento
- **Persistencia:** ¿Base de datos en memoria, SQLite local, PostgreSQL, o almacenamiento de archivos?
- **Estrategia de Caché:** ¿En memoria (TTL), Redis, o no requerida para el MVP?
- **Paginación y Filtrado:** ¿Cursor-based, Offset-limit, o colecciones de tamaño reducido?

### Ronda 4: Historias de Usuario y Casos Extremos (Edge Cases)
- **Criterios de Aceptación:** Definir los 3 escenarios principales en formato Given-When-Then.
- **Restricciones de Despliegue:** ¿Contenedor Docker standalone, paquete ejecutable, o script liviano?

---

## Generación de Artefacto Final: `DISCOVERY_NOTES.md`

Al completar las rondas de preguntas, consolida las decisiones en `shared_pool/01_prd/DISCOVERY_NOTES.md`:
1. **Resumen Ejecutivo del Requerimiento.**
2. **Decisiones Clave Congeladas (Matriz de Respuestas).**
3. **Entidades del Dominio y Atributos Principales.**
4. **Contrato Preliminar de Endpoints / Interfaces.**
5. **Historias de Usuario con Criterios de Aceptación (Gherkin).**
6. **Restricciones No Funcionales (Seguridad, Despliegue, Rendimiento).**
