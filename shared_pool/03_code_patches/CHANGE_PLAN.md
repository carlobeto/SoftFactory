# Engineer Change Plan: Weather CLI Tool with Local Cache

## Contract Freezing (Congelamiento del Contrato)
En estricto cumplimiento con la gobernanza de la Software Factory (AGENTS.md) y el diseño aprobado en `shared_pool/02_system_design/SYSTEM_DESIGN.md`, se congelan las superficies y responsabilidades a modificar.

### Superficie de Archivos Autorizados (Touched-Surface List)
Únicamente se crearán/modificarán los siguientes archivos dentro de `environment/workspace/`:
1. `environment/workspace/weather_tool/__init__.py`
2. `environment/workspace/weather_tool/models.py`
3. `environment/workspace/weather_tool/cache.py`
4. `environment/workspace/weather_tool/client.py`
5. `environment/workspace/weather_tool/service.py`
6. `environment/workspace/weather_tool/cli.py`
7. `environment/workspace/main.py`
8. `environment/workspace/tests/__init__.py`
9. `environment/workspace/tests/test_models.py`
10. `environment/workspace/tests/test_cache.py`
11. `environment/workspace/tests/test_client.py`
12. `environment/workspace/tests/test_service.py`
13. `environment/workspace/tests/test_cli.py`

### Mapeo de Componentes y Funciones Planificadas
- `models.py`:
  - `GeoLocation(name, latitude, longitude, country)`
  - `WeatherData(city, country, temperature, unit, humidity, wind_speed, condition, weather_code, timestamp, from_cache, cache_age_seconds)`
- `cache.py`:
  - `WeatherCache(db_path, default_ttl)`
  - Métodos: `_init_db()`, `get(city, ttl)`, `set(data)`, `clear()`, `remove_expired(ttl)`, `close()`
- `client.py`:
  - `WeatherClient(timeout)`
  - Métodos: `_fetch_url(url, timeout)`, `get_coordinates(city)`, `fetch_weather(location, units)`, `_wmo_code_to_condition(code)`
- `service.py`:
  - `WeatherService(client, cache)`
  - Métodos: `get_weather(city, ttl, force_refresh, units)`, `clear_cache()`
- `cli.py`:
  - `build_parser()`
  - `format_text(data)`
  - `format_json(data)`
  - `main(argv)`
- `main.py`:
  - Invocación de `cli.main(sys.argv[1:])`

### Criterios de Aceptación y Pruebas
- Pruebas unitarias completas con 100% de aprobación para cada módulo en `environment/workspace/tests/`.
- Verificación estática con `python3 -m py_compile`.
- Validación de ejecuciones manuales del CLI y generación final de `model.patch`.
