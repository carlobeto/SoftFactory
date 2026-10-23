"""Command Line Interface for weather_tool."""

import argparse
import json
import sys
from typing import List, Optional
from .cache import WeatherCache
from .client import WeatherClient
from .models import WeatherData
from .service import WeatherService


def build_parser() -> argparse.ArgumentParser:
    """Construye y configura el parser de argumentos de la CLI."""
    parser = argparse.ArgumentParser(
        prog="weather-cli",
        description="Consulta del clima por ciudad con soporte de caché local persistente.",
    )
    parser.add_argument(
        "-c",
        "--city",
        type=str,
        help="Nombre de la ciudad a consultar (ej. 'Madrid', 'Buenos Aires', 'Tokyo').",
    )
    parser.add_argument(
        "--ttl",
        type=int,
        default=1800,
        help="Tiempo de vida del caché en segundos (por defecto: 1800s / 30min).",
    )
    parser.add_argument(
        "-r",
        "--refresh",
        action="store_true",
        help="Fuerza la consulta a la red ignorando el caché existente.",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Limpia completamente el almacenamiento local de caché.",
    )
    parser.add_argument(
        "-u",
        "--units",
        choices=["metric", "imperial"],
        default="metric",
        help="Sistema de unidades: 'metric' (°C, km/h) o 'imperial' (°F, mph).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Imprime la salida en formato JSON estructurado.",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="weather_cache.db",
        help="Ruta al archivo SQLite de caché local.",
    )
    return parser


def format_text(data: WeatherData) -> str:
    """Formatea la información meteorológica en una representación legible para consola."""
    wind_unit = "mph" if data.unit == "°F" else "km/h"
    if data.from_cache:
        origin = f"Caché local (antigüedad: {data.cache_age_seconds}s)"
    else:
        origin = "API en tiempo real (guardado en caché)"

    lines = [
        "==================================================",
        f" Clima en {data.city}" + (f", {data.country}" if data.country else ""),
        "==================================================",
        f"  • Condición:     {data.condition}",
        f"  • Temperatura:   {data.temperature} {data.unit}",
        f"  • Humedad:       {data.humidity}%",
        f"  • Viento:        {data.wind_speed} {wind_unit}",
        f"  • Origen datos:  {origin}",
        f"  • Actualización: {data.timestamp}",
        "==================================================",
    ]
    return "\n".join(lines)


def format_json(data: WeatherData) -> str:
    """Formatea la información meteorológica como JSON."""
    return json.dumps(data.to_dict(), indent=2, ensure_ascii=False)


def main(
    argv: Optional[List[str]] = None,
    service: Optional[WeatherService] = None,
) -> int:
    """Punto de entrada de la CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    svc = service
    if svc is None:
        cache = WeatherCache(db_path=args.db_path, default_ttl=args.ttl)
        client = WeatherClient()
        svc = WeatherService(client=client, cache=cache)

    try:
        if args.clear_cache:
            deleted = svc.clear_cache()
            if args.json:
                print(json.dumps({"status": "ok", "cleared_records": deleted}))
            else:
                print(f"[Caché] Se han limpiado {deleted} registros del almacenamiento local.")
            return 0

        if not args.city:
            sys.stderr.write("Error: Debe especificar una ciudad con --city (-c) o la opción --clear-cache.\n")
            parser.print_usage(sys.stderr)
            return 1

        weather_data = svc.get_weather(
            city=args.city,
            ttl=args.ttl,
            force_refresh=args.refresh,
            units=args.units,
        )

        if args.json:
            print(format_json(weather_data))
        else:
            print(format_text(weather_data))
        return 0

    except (ValueError, ConnectionError, RuntimeError) as e:
        if args.json:
            sys.stderr.write(json.dumps({"error": str(e)}) + "\n")
        else:
            sys.stderr.write(f"Error al consultar el clima: {e}\n")
        return 1
    finally:
        svc.close()
