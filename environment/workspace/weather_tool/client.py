"""HTTP client for Open-Meteo Geocoding and Weather Forecast APIs."""

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict
from .models import GeoLocation, WeatherData


class WeatherClient:
    """Cliente HTTP para geocodificación y consulta de pronóstico meteorológico."""

    GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

    WMO_CONDITIONS: Dict[int, str] = {
        0: "Cielo despejado",
        1: "Mayormente despejado",
        2: "Parcialmente nublado",
        3: "Nublado",
        45: "Niebla",
        48: "Niebla con escarcha",
        51: "Llovizna ligera",
        53: "Llovizna moderada",
        55: "Llovizna densa",
        61: "Lluvia ligera",
        63: "Lluvia moderada",
        65: "Lluvia fuerte",
        71: "Nevada ligera",
        73: "Nevada moderada",
        75: "Nevada fuerte",
        77: "Granos de nieve",
        80: "Chubascos leves",
        81: "Chubascos moderados",
        82: "Chubascos violentos",
        85: "Chubascos de nieve leves",
        86: "Chubascos de nieve fuertes",
        95: "Tormenta eléctrica",
        96: "Tormenta con granizo leve",
        99: "Tormenta con granizo fuerte",
    }

    def __init__(self, timeout: int = 10) -> None:
        """Inicializa el cliente con un tiempo de espera por defecto."""
        self.timeout = timeout

    def _fetch_url(self, url: str) -> Dict[str, Any]:
        """Realiza una petición HTTP GET y parsea la respuesta JSON."""
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "WeatherToolCLI/1.0 (SoftFactory-Tool)"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                payload = response.read().decode("utf-8")
                return json.loads(payload)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Error HTTP del servicio meteorológico: {e.code} {e.reason}") from e
        except urllib.error.URLError as e:
            raise ConnectionError(f"No se pudo conectar con el servicio meteorológico: {e.reason}") from e

    def _wmo_code_to_condition(self, code: int) -> str:
        """Traduce códigos meteorológicos WMO a texto descriptivo en español."""
        return self.WMO_CONDITIONS.get(code, f"Condición meteorológica ({code})")

    def get_coordinates(self, city: str) -> GeoLocation:
        """Resuelve el nombre de una ciudad a sus coordenadas geográficas."""
        cleaned_city = city.strip()
        if not cleaned_city:
            raise ValueError("El nombre de la ciudad no puede estar vacío.")

        query = urllib.parse.urlencode({
            "name": cleaned_city,
            "count": 1,
            "language": "es",
            "format": "json",
        })
        url = f"{self.GEOCODING_URL}?{query}"
        data = self._fetch_url(url)

        results = data.get("results")
        if not results:
            raise ValueError(f"No se encontró la ciudad '{cleaned_city}'.")

        top = results[0]
        return GeoLocation(
            name=top.get("name", cleaned_city),
            latitude=float(top["latitude"]),
            longitude=float(top["longitude"]),
            country=top.get("country", ""),
        )

    def fetch_weather(self, location: GeoLocation, units: str = "metric") -> WeatherData:
        """Obtiene el clima actual para una ubicación geográfica dada."""
        params = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "timezone": "auto",
        }
        if units.lower() == "imperial":
            params["temperature_unit"] = "fahrenheit"
            params["wind_speed_unit"] = "mph"
            unit_label = "°F"
        else:
            unit_label = "°C"

        query = urllib.parse.urlencode(params)
        url = f"{self.FORECAST_URL}?{query}"
        data = self._fetch_url(url)

        current = data.get("current")
        if not current:
            raise RuntimeError("Respuesta meteorológica inválida: falta el bloque 'current'.")

        wmo_code = int(current.get("weather_code", -1))
        condition = self._wmo_code_to_condition(wmo_code)

        return WeatherData(
            city=location.name,
            country=location.country,
            temperature=float(current.get("temperature_2m", 0.0)),
            unit=unit_label,
            humidity=int(current.get("relative_humidity_2m", 0)),
            wind_speed=float(current.get("wind_speed_10m", 0.0)),
            condition=condition,
            weather_code=wmo_code,
            timestamp=str(current.get("time", "")),
            from_cache=False,
            cache_age_seconds=0.0,
        )
