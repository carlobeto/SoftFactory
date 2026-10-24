# System Design Specification: Sistema

## 1. Implementation Approach & Tech Stack
- **Patrón Arquitectónico:** Service-Repository Layered Pattern con separación estricta de responsabilidades.
- **Lenguaje Principal:** Python 3.11+
- **Persistencia:** SQLite3 con transaccionalidad ACID.
- **Testing:** unittest (Python Standard Library) para ejecución instantánea sin dependencias externas obligatorias.

---

## 2. Diagrama de Clases y Estructuras (Data Structures)

```mermaid
classDiagram
    class ModelRecord {
        +str id
        +str name
        +dict attributes
        +str created_at
        +to_dict() dict
        +from_dict(data) ModelRecord
    }

    class StorageRepository {
        +str db_path
        +get(id) ModelRecord
        +list_all(filters) list
        +save(record) bool
        +delete(id) bool
    }

    class AppService {
        +StorageRepository repository
        +create_item(payload) ModelRecord
        +get_item(id) ModelRecord
        +list_items() list
    }

    class PresentationHandler {
        +AppService service
        +handle_request(request) Response
    }

    AppService --> StorageRepository
    PresentationHandler --> AppService
    StorageRepository ..> ModelRecord
```

---

## 3. Diagrama de Flujo de Llamadas (Sequence Diagram)

```mermaid
sequenceDiagram
    autonumber
    actor Client as Cliente / Usuario
    participant Handler as Presentation Handler
    participant Service as Application Service
    participant Repo as Storage Repository
    participant DB as Base de Datos (SQLite3)

    Client->>Handler: Enviar petición (Payload JSON)
    Handler->>Handler: Validar esquema de entrada
    alt Datos inválidos
        Handler-->>Client: 422 Unprocessable Entity
    else Datos válidos
        Handler->>Service: create_item(payload)
        Service->>Repo: save(record)
        Repo->>DB: Inserción SQL / Commit
        DB-->>Repo: Confirmación
        Repo-->>Service: Registro guardado con ID
        Service-->>Handler: Objeto de negocio procesado
        Handler-->>Client: 201 Created (JSON Response)
    end
```

---

## 4. File List (Superficie Autorizada de Archivos)
1. `environment/workspace/app/__init__.py`
2. `environment/workspace/app/models.py`
3. `environment/workspace/app/storage.py`
4. `environment/workspace/app/service.py`
5. `environment/workspace/app/api.py`
6. `environment/workspace/main.py`
7. `environment/workspace/tests/__init__.py`
8. `environment/workspace/tests/test_models.py`
9. `environment/workspace/tests/test_storage.py`
10. `environment/workspace/tests/test_service.py`

---

## 5. Anything UNCLEAR
The architectural boundaries, interfaces, and file boundaries are fully frozen and ready for code implementation.
