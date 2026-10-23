# Requirements Discovery & Grilling Report

## 1. Contexto Inicial
- **Requerimiento Semilla:** `Construir una aplicacion con frontend y backend separados para controlar los turnos de una taller mecánico`
- **Metodología Aplicada:** AI Hero Grill-Me (Frontier Design Tree Protocol)
- **Estado de Elicitación:** `COMPLETADO Y CONGELADO`

---

## 2. Matriz de Decisiones de Diseño Congeladas

| Dimensión | Decisión Adoptada | Razón Técnica / Implicancia |
| :--- | :--- | :--- |
| **Estilo Arquitectónico** | FastAPI asíncrono con esquemas Pydantic y documentación OpenAPI automática | Contrato estructurado predecible para el cliente |
| **Consumidores Clave** | Aplicaciones frontend (SPA Web) y clientes móviles | Define los requerimientos de latencia y CORS |
| **Seguridad & Auth** | Bearer Token (JWT) con expiración y soporte para Refresh Token | Aislamiento y control de acceso robusto |
| **Gestión de Errores** | RFC 7807 (Problem Details: 'type', 'title', 'status', 'detail', 'invalid_params') | Estándar predecible para simplificar la integración frontend |
| **Persistencia** | SQLite3 local con WAL activado (ligera, embebida, ideal para pruebas y microservicios autocontenidos) | Integridad transaccional y bajo acoplamiento |
| **Caché & Rendimiento** | Caché en memoria local con tiempo de expiración (TTL) y purga automática | Evita sobrecarga en operaciones de lectura repetitivas |
| **Validación de Datos** | Esquemas estrictos tipados (Pydantic / dataclasses) | Previene inyección y corrupción del modelo |
| **Estrategia Despliegue** | Contenedor Docker (python:3.11-slim) | Autocontenido y ejecutable en cualquier entorno |

---

## 3. Modelo de Dominio y Recursos Clave
Las siguientes entidades componen el núcleo de datos del sistema:
- **Clientes**: Entidad principal de negocio gestionada por la API.
- **Reservas**: Entidad principal de negocio gestionada por la API.
- **Pagos**: Entidad principal de negocio gestionada por la API.
- **Vehiculos**: Entidad principal de negocio gestionada por la API.
- **Trabajos**: Entidad principal de negocio gestionada por la API.
- **Materiales**: Entidad principal de negocio gestionada por la API.
- **Costos**: Entidad principal de negocio gestionada por la API.
- **Empleados**: Entidad principal de negocio gestionada por la API.

---

## 4. Borrador del Contrato de Endpoints (API Specification Draft)
- `GET /api/v1/clientes` - Listar y filtrar Clientes
- `POST /api/v1/clientes` - Crear nuevo registro de Clientes
- `GET /api/v1/clientes/{id}` - Obtener detalle por ID
- `PUT /api/v1/clientes/{id}` - Actualizar Clientes existente
- `DELETE /api/v1/clientes/{id}` - Eliminar Clientes
- `GET /api/v1/reservas` - Listar y filtrar Reservas
- `POST /api/v1/reservas` - Crear nuevo registro de Reservas
- `GET /api/v1/reservas/{id}` - Obtener detalle por ID
- `PUT /api/v1/reservas/{id}` - Actualizar Reservas existente
- `DELETE /api/v1/reservas/{id}` - Eliminar Reservas
- `GET /api/v1/pagos` - Listar y filtrar Pagos
- `POST /api/v1/pagos` - Crear nuevo registro de Pagos
- `GET /api/v1/pagos/{id}` - Obtener detalle por ID
- `PUT /api/v1/pagos/{id}` - Actualizar Pagos existente
- `DELETE /api/v1/pagos/{id}` - Eliminar Pagos
- `GET /api/v1/vehiculos` - Listar y filtrar Vehiculos
- `POST /api/v1/vehiculos` - Crear nuevo registro de Vehiculos
- `GET /api/v1/vehiculos/{id}` - Obtener detalle por ID
- `PUT /api/v1/vehiculos/{id}` - Actualizar Vehiculos existente
- `DELETE /api/v1/vehiculos/{id}` - Eliminar Vehiculos
- `GET /api/v1/trabajos` - Listar y filtrar Trabajos
- `POST /api/v1/trabajos` - Crear nuevo registro de Trabajos
- `GET /api/v1/trabajos/{id}` - Obtener detalle por ID
- `PUT /api/v1/trabajos/{id}` - Actualizar Trabajos existente
- `DELETE /api/v1/trabajos/{id}` - Eliminar Trabajos
- `GET /api/v1/materiales` - Listar y filtrar Materiales
- `POST /api/v1/materiales` - Crear nuevo registro de Materiales
- `GET /api/v1/materiales/{id}` - Obtener detalle por ID
- `PUT /api/v1/materiales/{id}` - Actualizar Materiales existente
- `DELETE /api/v1/materiales/{id}` - Eliminar Materiales
- `GET /api/v1/costos` - Listar y filtrar Costos
- `POST /api/v1/costos` - Crear nuevo registro de Costos
- `GET /api/v1/costos/{id}` - Obtener detalle por ID
- `PUT /api/v1/costos/{id}` - Actualizar Costos existente
- `DELETE /api/v1/costos/{id}` - Eliminar Costos
- `GET /api/v1/empleados` - Listar y filtrar Empleados
- `POST /api/v1/empleados` - Crear nuevo registro de Empleados
- `GET /api/v1/empleados/{id}` - Obtener detalle por ID
- `PUT /api/v1/empleados/{id}` - Actualizar Empleados existente
- `DELETE /api/v1/empleados/{id}` - Eliminar Empleados


---

## 5. Criterios de Aceptación Ejecutables (Historias de Usuario en Gherkin)

### Escenario 1: Creación exitosa de recurso
```gherkin
Característica: Gestión de Clientes
  Escenario: Crear un nuevo registro con datos válidos
    Dado un cliente autenticado con credenciales válidas (Bearer Token (JWT) con expiración y soporte para Refresh Token)
    Cuando envía una petición POST a "/api/v1/clientes" con payload válido
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
- **Decisión:** FastAPI asíncrono con esquemas Pydantic y documentación OpenAPI automática
- **Justificación:** Ofrece el mejor balance entre desacoplamiento, facilidad de pruebas automatizadas y soporte universal.

### ADR-002: Esquema de Persistencia
- **Decisión:** SQLite3 local con WAL activado (ligera, embebida, ideal para pruebas y microservicios autocontenidos)
- **Justificación:** Garantiza aislamiento en el sandbox y despliegue rápido sin requerir servicios externos pesados en la fase inicial.

### ADR-003: Manejo Estándar de Errores
- **Decisión:** RFC 7807 (Problem Details: 'type', 'title', 'status', 'detail', 'invalid_params')
- **Justificación:** Facilita que el QA Tester audite de forma hostil los casos extremos y códigos de estado.
