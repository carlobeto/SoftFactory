"""Tests for WeatherService coordinating cache and client."""

import unittest
from unittest.mock import MagicMock
from weather_tool.models import GeoLocation, WeatherData
from weather_tool.service import WeatherService


class TestWeatherService(unittest.TestCase):
    """Pruebas unitarias para la lógica del servicio meteorológico."""

    def setUp(self):
        self.mock_client = MagicMock()
        self.mock_cache = MagicMock()
        self.service = WeatherService(client=self.mock_client, cache=self.mock_cache)

        self.sample_cached = WeatherData(
            city="Madrid",
            country="España",
            temperature=18.0,
            unit="°C",
            humidity=55,
            wind_speed=10.0,
            condition="Despejado",
            weather_code=0,
            timestamp="2026-10-22T10:00",
            from_cache=True,
            cache_age_seconds=300.0,
        )

        self.sample_fresh = WeatherData(
            city="Madrid",
            country="España",
            temperature=20.0,
            unit="°C",
            humidity=50,
            wind_speed=12.0,
            condition="Soleado",
            weather_code=0,
            timestamp="2026-10-22T12:00",
            from_cache=False,
            cache_age_seconds=0.0,
        )

    def test_get_weather_cache_hit(self):
        self.mock_cache.get.return_value = self.sample_cached

        result = self.service.get_weather("Madrid", ttl=1800, force_refresh=False, units="metric")

        self.assertEqual(result, self.sample_cached)
        self.assertTrue(result.from_cache)
        self.mock_cache.get.assert_called_once_with("Madrid", ttl=1800)
        # El cliente de red no debió haber sido consultado
        self.mock_client.get_coordinates.assert_not_called()
        self.mock_client.fetch_weather.assert_not_called()
        self.mock_cache.set.assert_not_called()

    def test_get_weather_cache_miss(self):
        self.mock_cache.get.return_value = None
        mock_loc = GeoLocation(name="Madrid", latitude=40.4, longitude=-3.7, country="España")
        self.mock_client.get_coordinates.return_value = mock_loc
        self.mock_client.fetch_weather.return_value = self.sample_fresh

        result = self.service.get_weather("Madrid", ttl=1800, force_refresh=False, units="metric")

        self.assertEqual(result, self.sample_fresh)
        self.mock_client.get_coordinates.assert_called_once_with("Madrid")
        self.mock_client.fetch_weather.assert_called_once_with(mock_loc, units="metric")
        self.mock_cache.set.assert_called_once_with(self.sample_fresh)

    def test_get_weather_force_refresh(self):
        self.mock_cache.get.return_value = self.sample_cached
        mock_loc = GeoLocation(name="Madrid", latitude=40.4, longitude=-3.7, country="España")
        self.mock_client.get_coordinates.return_value = mock_loc
        self.mock_client.fetch_weather.return_value = self.sample_fresh

        # Con force_refresh=True, ignora el dato en caché y consulta API
        result = self.service.get_weather("Madrid", ttl=1800, force_refresh=True, units="metric")

        self.assertEqual(result, self.sample_fresh)
        self.mock_client.get_coordinates.assert_called_once_with("Madrid")
        self.mock_client.fetch_weather.assert_called_once_with(mock_loc, units="metric")
        self.mock_cache.set.assert_called_once_with(self.sample_fresh)

    def test_get_weather_unit_mismatch_refetches(self):
        # Caché contiene °C pero el usuario solicita imperial (°F)
        self.mock_cache.get.return_value = self.sample_cached
        mock_loc = GeoLocation(name="Madrid", latitude=40.4, longitude=-3.7, country="España")
        self.mock_client.get_coordinates.return_value = mock_loc
        imperial_fresh = WeatherData(
            city="Madrid",
            country="España",
            temperature=68.0,
            unit="°F",
            humidity=50,
            wind_speed=7.5,
            condition="Soleado",
            weather_code=0,
            timestamp="2026-10-22T12:00",
        )
        self.mock_client.fetch_weather.return_value = imperial_fresh

        result = self.service.get_weather("Madrid", ttl=1800, force_refresh=False, units="imperial")

        self.assertEqual(result.unit, "°F")
        self.mock_client.fetch_weather.assert_called_once_with(mock_loc, units="imperial")
        self.mock_cache.set.assert_called_once_with(imperial_fresh)

    def test_clear_cache(self):
        self.mock_cache.clear.return_value = 5
        count = self.service.clear_cache()
        self.assertEqual(count, 5)
        self.mock_cache.clear.assert_called_once()

    def test_close(self):
        self.service.close()
        self.mock_cache.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
