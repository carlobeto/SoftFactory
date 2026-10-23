"""Data models for weather_tool."""

from dataclasses import dataclass, asdict
from typing import Any, Dict


@dataclass
class GeoLocation:
    """Representa la ubicación geográfica de una ciudad."""

    name: str
    latitude: float
    longitude: float
    country: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convierte la ubicación a un diccionario serializable."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GeoLocation":
        """Instancia GeoLocation desde un diccionario."""
        return cls(
            name=str(data.get("name", "")),
            latitude=float(data.get("latitude", 0.0)),
            longitude=float(data.get("longitude", 0.0)),
            country=str(data.get("country", "")),
        )


@dataclass
class WeatherData:
    """Información meteorológica consolidada."""

    city: str
    country: str
    temperature: float
    unit: str
    humidity: int
    wind_speed: float
    condition: str
    weather_code: int
    timestamp: str
    from_cache: bool = False
    cache_age_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convierte los datos meteorológicos a un diccionario serializable."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WeatherData":
        """Crea una instancia de WeatherData a partir de un diccionario serializado."""
        return cls(
            city=str(data.get("city", "")),
            country=str(data.get("country", "")),
            temperature=float(data.get("temperature", 0.0)),
            unit=str(data.get("unit", "°C")),
            humidity=int(data.get("humidity", 0)),
            wind_speed=float(data.get("wind_speed", 0.0)),
            condition=str(data.get("condition", "Desconocido")),
            weather_code=int(data.get("weather_code", -1)),
            timestamp=str(data.get("timestamp", "")),
            from_cache=bool(data.get("from_cache", False)),
            cache_age_seconds=float(data.get("cache_age_seconds", 0.0)),
        )
