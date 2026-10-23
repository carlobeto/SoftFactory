"""Weather service orchestrating cache and client interactions."""

from typing import Optional
from .cache import WeatherCache
from .client import WeatherClient
from .models import WeatherData


class WeatherService:
    """Coordina las consultas al caché local y las peticiones a la API meteorológica."""

    def __init__(
        self,
        client: Optional[WeatherClient] = None,
        cache: Optional[WeatherCache] = None,
    ) -> None:
        """Inicializa el servicio inyectando cliente y caché (o creando instancias por defecto)."""
        self.client = client or WeatherClient()
        self.cache = cache or WeatherCache()

    def get_weather(
        self,
        city: str,
        ttl: int = 1800,
        force_refresh: bool = False,
        units: str = "metric",
    ) -> WeatherData:
        """Consulta el clima para una ciudad dada.

        Prioriza el caché si está vigente y no se forzó la actualización.
        Verifica también que las unidades coincidan con las solicitadas.
        """
        expected_unit = "°F" if units.lower() == "imperial" else "°C"

        if not force_refresh:
            cached_data = self.cache.get(city, ttl=ttl)
            if cached_data is not None and cached_data.unit == expected_unit:
                return cached_data

        # Fallo de caché, recarga forzada o cambio de unidades: consultar API
        location = self.client.get_coordinates(city)
        fresh_data = self.client.fetch_weather(location, units=units)

        # Actualizar caché local
        self.cache.set(fresh_data)
        return fresh_data

    def clear_cache(self) -> int:
        """Elimina todos los datos del caché local."""
        return self.cache.clear()

    def close(self) -> None:
        """Libera recursos y conexiones del caché."""
        self.cache.close()
