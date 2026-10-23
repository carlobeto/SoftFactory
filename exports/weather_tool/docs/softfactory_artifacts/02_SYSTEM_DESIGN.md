# System Design: Weather CLI with Local Cache

## Implementation Approach
Para satisfacer los requerimientos del PRD de forma modular, extensible y de cero dependencias externas conflictivas, se utilizará Python 3 estándar con una arquitectura en capas:
- **Capa de Dominio y Modelos (`models.py`):** Define `GeoLocation` y `WeatherData` con tipado estricto mediante `@dataclass`, serialización a diccionario/JSON y compatibilidad con diferentes unidades (Celsius, Fahrenheit).
- **Capa de Persistencia / Caché (`cache.py`):** `WeatherCache` encapsula almacenamiento en base de datos local SQLite (`weather_cache.db`), administrando timestamps en UTC, expiración por TTL (Time-To-Live), invalidación y purga manual.
- **Capa de Integración / Red (`client.py`):** `WeatherClient` consume APIs abiertas y gratuitas (Open-Meteo Geocoding API para resolver latitud/longitud y Open-Meteo Forecast API para obtener temperatura, humedad, viento y código meteorológico WMO). Incluye transporte desacoplado para inyección de mocks en tests sin requerir internet.
- **Capa de Servicio / Orquestación (`service.py`):** `WeatherService` coordina la lógica de negocio: consulta el caché; si existe y está vigente (cache hit), retorna los datos marcados con origen `CACHE`; si expiró o no existe o se forzó recarga (`--refresh`), consulta `WeatherClient`, actualiza el caché y retorna con origen `API`.
- **Capa de Presentación / CLI (`cli.py` & `main.py`):** Parser de argumentos con `argparse`, formateo legible en consola con indicadores de caché/TTL y soporte para salida JSON estructurada.

## Project / Package / Module Name
`weather_tool`

## Data Structures and Interface Definitions
```mermaid
classDiagram
    class GeoLocation {
        +str name
        +float latitude
        +float longitude
        +str country
        +to_dict() dict
    }

    class WeatherData {
        +str city
        +str country
        +float temperature
        +str unit
        +int humidity
        +float wind_speed
        +str condition
        +int weather_code
        +str timestamp
        +bool from_cache
        +float cache_age_seconds
        +to_dict() dict
    }

    class WeatherCache {
        +str db_path
        +int default_ttl
        +_init_db() void
        +get(str city, int ttl) WeatherData
        +set(WeatherData data) void
        +clear() int
        +remove_expired(int ttl) int
        +close() void
    }

    class WeatherClient {
        +int timeout
        +get_coordinates(str city) GeoLocation
        +fetch_weather(GeoLocation location, str units) WeatherData
        +_wmo_code_to_condition(int code) str
    }

    class WeatherService {
        +WeatherClient client
        +WeatherCache cache
        +get_weather(str city, int ttl, bool force_refresh, str units) WeatherData
        +clear_cache() int
    }

    class WeatherCLI {
        +WeatherService service
        +run(list argv) int
        +format_text(WeatherData data) str
        +format_json(WeatherData data) str
    }

    WeatherService --> WeatherClient : usa
    WeatherService --> WeatherCache : usa
    WeatherService --> WeatherData : retorna
    WeatherCache --> WeatherData : almacena/recupera
    WeatherClient --> GeoLocation : resuelve
    WeatherClient --> WeatherData : construye
    WeatherCLI --> WeatherService : delega
```

## Program Call Flow
```mermaid
sequenceDiagram
    autonumber
    actor User as Usuario CLI
    participant CLI as WeatherCLI (cli.py)
    participant Svc as WeatherService (service.py)
    participant Cache as WeatherCache (cache.py)
    participant Client as WeatherClient (client.py)
    participant API as Open-Meteo API

    User->>CLI: main(["--city", "Madrid", "--ttl", "1800"])
    CLI->>Svc: get_weather("Madrid", ttl=1800, force_refresh=False)
    
    alt force_refresh is False
        Svc->>Cache: get("Madrid", ttl=1800)
        Cache-->>Svc: WeatherData (Cache Hit) o None (Cache Miss)
    end

    alt Cache Hit
        Svc-->>CLI: WeatherData (from_cache=True)
    else Cache Miss o force_refresh is True
        Svc->>Client: get_coordinates("Madrid")
        Client->>API: GET /geocoding-api/v1/search?name=Madrid
        API-->>Client: GeoLocation(Madrid, ES, lat, lon)
        Client->>API: GET /v1/forecast?latitude=..&longitude=..
        API-->>Client: Raw Weather JSON
        Client-->>Svc: WeatherData(from_cache=False)
        Svc->>Cache: set(WeatherData)
        Svc-->>CLI: WeatherData(from_cache=False)
    end

    CLI->>User: Formateo en pantalla (Texto / JSON)
```

## File List
Lista cerrada y autorizada de archivos para la implementación del proyecto:
```python
[
    "environment/workspace/weather_tool/__init__.py",
    "environment/workspace/weather_tool/models.py",
    "environment/workspace/weather_tool/cache.py",
    "environment/workspace/weather_tool/client.py",
    "environment/workspace/weather_tool/service.py",
    "environment/workspace/weather_tool/cli.py",
    "environment/workspace/main.py",
    "environment/workspace/tests/__init__.py",
    "environment/workspace/tests/test_models.py",
    "environment/workspace/tests/test_cache.py",
    "environment/workspace/tests/test_client.py",
    "environment/workspace/tests/test_service.py",
    "environment/workspace/tests/test_cli.py"
]
```

## Anything UNCLEAR
There are no unclear points. El diseño proporciona una separación clara entre modelo, transporte, persistencia y CLI, listo para la fase de desglose de tareas y posterior codificación.
