# Weather_tool (Exportado desde SoftFactory)

Esta aplicación fue desarrollada, auditada y aprobada por la cadena de montaje de la Software Factory.

## Estructura
- Código fuente: Directorio principal y módulos
- Pruebas unitarias: `tests/`
- Dockerfile para ejecución en contenedores
- Documentación de arquitectura y QA: `docs/softfactory_artifacts/`

## Ejecución Local
```bash
python3 main.py --help
```

## Ejecución de Pruebas
```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## Ejecución con Docker
```bash
docker build -t weather_tool:latest .
docker run --rm weather_tool:latest
```
