# Requirements Discovery & Grilling Report

## 1. Contexto Inicial
- **Requerimiento Semilla:** `Construir una API para gestionar tareas y proyectos`
- **Metodología Aplicada:** AI Hero Grill-Me (Frontier Design Tree Protocol)
- **Estado de Elicitación:** `COMPLETADO Y CONGELADO`

---

## 2. Matriz de Decisiones de Diseño Congeladas

| Dimensión | Decisión Adoptada | Razón Técnica / Implicancia |
| :--- | :--- | :--- |
| **Estilo Arquitectónico** | RESTful API sobre HTTP con payloads JSON y códigos de estado estándar | Contrato estructurado predecible para el cliente |
| **Consumidores Clave** | Aplicaciones frontend (SPA Web / React / Vue) y aplicaciones móviles | Define los requerimientos de latencia y CORS |
| **Seguridad & Auth** | Bearer Token (JWT) con expiración y soporte para Refresh Token | Aislamiento y control de acceso robusto |
| **Gestión de Errores** | RFC 7807 (Problem Details: 'type', 'title', 'status', 'detail', 'invalid_params') | Estándar predecible para simplificar la integración frontend |
| **Persistencia** | SQLite3 local con WAL activado (ligera, embebida, ideal para pruebas y microservicios autocontenidos) | Integridad transaccional y bajo acoplamiento |
| **Caché & Rendimiento** | Caché en memoria local con tiempo de expiración (TTL) y purga automática | Evita sobrecarga en operaciones de lectura repetitivas |
| **Validación de Datos** | Esquemas estrictos tipados (Pydantic / dataclasses) con rechazo automático 422 | Previene inyección y corrupción del modelo |
| **Estrategia Despliegue** | Contenedor Docker (python:3.11-slim) con entrypoint preconfigurado y healthcheck | Autocontenido y ejecutable en cualquier entorno |

---

## 3. Modelo de Dominio y Recursos Clave
Las siguientes entidades componen el núcleo de datos del sistema:
- **Tareas**: Entidad principal de negocio gestionada por la API.
- **Proyectos**: Entidad principal de negocio gestionada por la API.
- **Etiquetas**: Entidad principal de negocio gestionada por la API.

---

## 4. Borrador del Contrato de Endpoints (API Specification Draft)
- `GET /api/v1/tareas` - Listar y filtrar Tareas
- `POST /api/v1/tareas` - Crear nuevo registro de Tareas
- `GET /api/v1/tareas/{id}` - Obtener detalle por ID
- `PUT /api/v1/tareas/{id}` - Actualizar Tareas existente
- `DELETE /api/v1/tareas/{id}` - Eliminar Tareas
- `GET /api/v1/proyectos` - Listar y filtrar Proyectos
- `POST /api/v1/proyectos` - Crear nuevo registro de Proyectos
- `GET /api/v1/proyectos/{id}` - Obtener detalle por ID
- `PUT /api/v1/proyectos/{id}` - Actualizar Proyectos existente
- `DELETE /api/v1/proyectos/{id}` - Eliminar Proyectos
- `GET /api/v1/etiquetas` - Listar y filtrar Etiquetas
- `POST /api/v1/etiquetas` - Crear nuevo registro de Etiquetas
- `GET /api/v1/etiquetas/{id}` - Obtener detalle por ID
- `PUT /api/v1/etiquetas/{id}` - Actualizar Etiquetas existente
- `DELETE /api/v1/etiquetas/{id}` - Eliminar Etiquetas


---

## 5. Criterios de Aceptación Ejecutables (Historias de Usuario en Gherkin)

### Escenario 1: Creación exitosa de recurso
```gherkin
Característica: Gestión de Tareas
  Escenario: Crear un nuevo registro con datos válidos
    Dado un cliente autenticado con credenciales válidas (Bearer Token (JWT) con expiración y soporte para Refresh Token)
    Cuando envía una petición POST a "/api/v1/tareas" con payload válido
    Entonces la API retorna código 201 Created
    Y el cuerpo de la respuesta contiene el ID generado y los datos persistidos
```

### Escenario 2: Rechazo ante datos no válidos (Validación Estricta)
```gherkin
  Escenario: Rechazo de petición con datos malformados
    Dado un cliente que envía un POST con campos obligatorios vacíos
    Cuando la API procesa la solicitud
    Entonces retorna código 422 Unprocessable Entity
    Y el cuerpo responde bajo el estándar RFC 7807 (Problem Details: 'type', 'title', 'status', 'detail', 'invalid_params')
```

### Escenario 3: Acceso no autorizado
```gherkin
  Escenario: Intentar consumir endpoints protegidos sin credenciales
    Dado un cliente sin cabecera de autenticación
    Cuando solicita un endpoint protegido
    Entonces la API rechaza la solicitud con código 401 Unauthorized
```


---

## 6. Registros de Decisiones Arquitectónicas (ADRs Preliminares)

### ADR-001: Adopción del Estilo de API
- **Decisión:** RESTful API sobre HTTP con payloads JSON y códigos de estado estándar
- **Justificación:** Ofrece el mejor balance entre desacoplamiento, facilidad de pruebas automatizadas y soporte universal.

### ADR-002: Esquema de Persistencia
- **Decisión:** SQLite3 local con WAL activado (ligera, embebida, ideal para pruebas y microservicios autocontenidos)
- **Justificación:** Garantiza aislamiento en el sandbox y despliegue rápido sin requerir servicios externos pesados en la fase inicial.

### ADR-003: Manejo Estándar de Errores
- **Decisión:** RFC 7807 (Problem Details: 'type', 'title', 'status', 'detail', 'invalid_params')
- **Justificación:** Facilita que el QA Tester audite de forma hostil los casos extremos y códigos de estado.
