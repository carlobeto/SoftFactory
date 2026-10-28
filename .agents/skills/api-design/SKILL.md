---
name: api-design
description: Principios y estándares para el diseño de contratos de APIs (REST, OpenAPI, gRPC) y estructuración de especificaciones de interfaz en la Software Factory.
version: 1.0.0
type: knowledge
applies_to_stages: [discovery_notes, system_design]
---

# Skill: API Design (Contract-First)

Esta skill establece las directrices para definir contratos de APIs limpios, consistentes y robustos en la fase de requerimientos y diseño de sistema.

## Convenciones de Endpoints (RESTful)
1. **Nombres de Recursos:**
   - Usar sustantivos en plural y en minúsculas en kebab-case: `/api/v1/user-profiles`, `/api/v1/orders/{id}/items`.
   - Evitar verbos en las rutas (`GET /orders`, NO `GET /getOrders`).
2. **Métodos HTTP Estándar:**
   - `GET`: Idempotente y seguro. Retorna `200 OK` (o `404 Not Found`).
   - `POST`: No idempotente. Creación de recursos. Retorna `201 Created` con cabecera `Location` y el recurso creado.
   - `PUT`: Reemplazo completo de recurso. Retorna `200 OK` o `204 No Content`.
   - `PATCH`: Modificación parcial. Retorna `200 OK`.
   - `DELETE`: Eliminación. Retorna `204 No Content` o `200 OK`.

## Formato Estándar de Errores (RFC 7807 Problem Details)
Todas las respuestas de error (`4xx` y `5xx`) deben usar una estructura predecible:
```json
{
  "type": "https://api.tuempresa.com/errors/invalid-input",
  "title": "Unprocessable Entity",
  "status": 422,
  "detail": "El campo 'email' no tiene un formato válido.",
  "instance": "/api/v1/users",
  "invalid_params": [
    {"name": "email", "reason": "Debe contener '@'"}
  ]
}
```

## Paginación, Ordenamiento y Filtrado
- **Paginación estándar por Query Params:** `?page=1&limit=20` o cursor `?cursor=eyJpZ...`.
- **Estructura de respuesta paginada:**
```json
{
  "data": [...],
  "pagination": {
    "total_records": 150,
    "current_page": 1,
    "total_pages": 8,
    "limit": 20
  }
}
```

## Versionado y Seguridad
- Versionado por prefijo de URL: `/api/v1/...`
- Cabecera de autenticación: `Authorization: Bearer <token>` o `X-API-Key: <key>`
- Especificación preliminar OpenAPI 3.0+ en formato YAML cuando se definan más de 3 endpoints.
