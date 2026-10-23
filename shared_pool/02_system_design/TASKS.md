# Tasks and Implementation Breakdown: Weather Tool

## Required Third-Party Packages / Dependencies
- **Lenguaje:** Python 3.11+
- **Dependencias Externas:** Ninguna (0 dependencias de terceros). El proyecto utiliza exclusivamente módulos estándar:
  - `dataclasses`: Definición limpia de modelos de dominio.
  - `sqlite3`: Persistencia local del caché con soporte transaccional y timestamps.
  - `urllib.request` / `urllib.error` / `urllib.parse`: Cliente HTTP para geocodificación y obtención de pronóstico meteorológico.
  - `json`: Serialización y parseo de respuestas y datos de caché.
  - `argparse`: Interfaz CLI con soporte para banderas y validación de tipos.
  - `unittest`: Suite de pruebas unitarias automatizadas con `unittest.mock`.

## Task List
1. `environment/workspace/weather_tool/__init__.py`: Inicialización del paquete y exposición de símbolos públicos.
2. `environment/workspace/weather_tool/models.py`: Estructuras de datos (`GeoLocation`, `WeatherData`).
3. `environment/workspace/weather_tool/cache.py`: Manejador de persistencia SQLite para el caché y gestión de TTL.
4. `environment/workspace/weather_tool/client.py`: Cliente de red para APIs de Open-Meteo (Geocoding y Forecast).
5. `environment/workspace/weather_tool/service.py`: Capa de orquestación que implementa la lógica de caché vs API.
6. `environment/workspace/weather_tool/cli.py`: Controlador de la línea de comandos (CLI) y formateador de salida.
7. `environment/workspace/main.py`: Punto de entrada ejecutable.
8. `environment/workspace/tests/__init__.py`: Paquete de pruebas.
9. `environment/workspace/tests/test_models.py`: Pruebas de modelos y serialización.
10. `environment/workspace/tests/test_cache.py`: Pruebas del almacenamiento local en SQLite y expiración de TTL.
11. `environment/workspace/tests/test_client.py`: Pruebas de cliente HTTP con simulación (mocking) de respuestas de red y errores.
12. `environment/workspace/tests/test_service.py`: Pruebas de la lógica de servicio (coordinación cache hit / miss / refresh).
13. `environment/workspace/tests/test_cli.py`: Pruebas integradas de comandos CLI y formateadores de salida.

## Logic Analysis (Análisis Lógico por Archivo)

### 1. `environment/workspace/weather_tool/models.py`
- **Responsabilidad:** Modelos de datos inmutables y tipados.
- **Detalle de implementación:**
  - `GeoLocation`: Campos `name`, `latitude`, `longitude`, `country`. Método `to_dict()`.
  - `WeatherData`: Campos `city`, `country`, `temperature`, `unit` (Celsius/Fahrenheit), `humidity`, `wind_speed`, `condition`, `weather_code`, `timestamp`, `from_cache`, `cache_age_seconds`. Métodos `to_dict()`.

### 2. `environment/workspace/weather_tool/cache.py`
- **Responsabilidad:** Almacenamiento local indexado por nombre de ciudad normalizado.
- **Detalle de implementación:**
  - Tabla `weather_cache (city_key PRIMARY KEY, city_name TEXT, data_json TEXT, updated_at REAL)`.
  - Método `get(city: str, ttl: int) -> Optional[WeatherData]`: Comprueba si existe y si `(time.time() - updated_at) <= ttl`. Si es válido, parsea `WeatherData` marcando `from_cache=True` y calcula `cache_age_seconds`. Si expiró, retorna `None`.
  - Método `set(data: WeatherData) -> None`: Inserta o reemplaza el registro serializado con el `timestamp` actual.
  - Método `clear() -> int`: Elimina todos los registros de la tabla de caché y retorna la cantidad de filas borradas.
  - Método `remove_expired(ttl: int) -> int`: Purga registros cuyo tiempo exceda el TTL.

### 3. `environment/workspace/weather_tool/client.py`
- **Responsabilidad:** Comunicación con servicios externos sin dependencias externas.
- **Detalle de implementación:**
  - Función o método `_fetch_url(url: str, timeout: int) -> dict`: Utiliza `urllib.request.urlopen` con cabecera `User-Agent`. Permite inyectar o mockear fácilmente.
  - Método `get_coordinates(city: str) -> GeoLocation`: Consulta `https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=es&format=json`. Si no hay resultados, lanza `ValueError("Ciudad no encontrada")`.
  - Método `fetch_weather(location: GeoLocation, units: str = "metric") -> WeatherData`: Consulta `https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m`. Si `units == "imperial"`, agrega parámetro `temperature_unit=fahrenheit`.
  - Método `_wmo_code_to_condition(code: int) -> str`: Traduce códigos meteorológicos WMO (0=Despejado, 1-3=Parcialmente nublado, 61-65=Lluvia, etc.) a descripciones en lenguaje natural.

### 4. `environment/workspace/weather_tool/service.py`
- **Responsabilidad:** Flujo de decisión entre caché y llamada a la API.
- **Detalle de implementación:**
  - Inicializador recibe `client: WeatherClient` y `cache: WeatherCache`.
  - `get_weather(city: str, ttl: int = 1800, force_refresh: bool = False, units: str = "metric") -> WeatherData`:
    1. Si `force_refresh` es `False`, consulta `cache.get(city, ttl)`.
    2. Si hay acierto de caché (hit), devuelve el objeto de datos inmediatamente.
    3. Si es fallo (miss) o `force_refresh` es `True`, obtiene coordenadas vía `client.get_coordinates(city)`.
    4. Consulta clima vía `client.fetch_weather(coords, units=units)`.
    5. Guarda el resultado en `cache.set(data)`.
    6. Retorna los datos con `from_cache=False`.
  - `clear_cache() -> int`: Invoca `cache.clear()`.

### 5. `environment/workspace/weather_tool/cli.py`
- **Responsabilidad:** Argument parsing, manejo de excepciones de usuario y renderizado de consola.
- **Detalle de implementación:**
  - Argumentos: `--city` (str), `--ttl` (int, default 1800), `--refresh` (flag booleano), `--clear-cache` (flag booleano), `--units` (choices: metric, imperial, default metric), `--json` (flag booleano), `--db-path` (opcional).
  - Manejo de salidas: `format_text(WeatherData)` y `format_json(WeatherData)`.
  - Retorna código de salida 0 en éxito, 1 en error controlado.

### 6. `environment/workspace/main.py`
- **Responsabilidad:** Archivo ejecutable de entrada `if __name__ == "__main__": sys.exit(main())`.

### 7. Pruebas Unitarias (`tests/`)
- Cobertura exhaustiva:
  - `test_models.py`: Serialización, instanciación y formato de datos.
  - `test_cache.py`: Operaciones SQLite en memoria (`:memory:`), persistencia, TTL vigente, TTL expirado, reemplazo y borrado.
  - `test_client.py`: Mocks con `unittest.mock.patch` de llamadas HTTP para geocodificación exitosa, ciudad inexistente, códigos WMO y timeouts.
  - `test_service.py`: Mocks de client y cache para verificar que no llame a la red cuando hay cache hit, que llame a la red cuando hay cache miss o refresh forzado, y que guarde en cache.
  - `test_cli.py`: Invocación del CLI con diferentes argumentos, banderas `--json`, `--clear-cache` y errores de entrada.

## Shared Knowledge
- **Normalización de claves:** Para evitar duplicados en el caché (ej. "madrid", "Madrid", "  MADRID "), las claves en la base de datos se normalizan con `.strip().lower()`.
- **Manejo de Tiempos:** Se utiliza `time.time()` en segundos UTC para cálculos de TTL limpios y exactos.
- **Aislamiento en pruebas:** Los tests de caché usan `:memory:` o archivos temporales aislados, garantizando pruebas reproducibles e independientes de disco.
