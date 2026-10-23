"""Tests for domain models (GeoLocation and WeatherData)."""

import unittest
from weather_tool.models import GeoLocation, WeatherData


class TestModels(unittest.TestCase):
    """Pruebas unitarias para los modelos de datos."""

    def test_geolocation_to_dict_and_from_dict(self):
        geo = GeoLocation(name="Madrid", latitude=40.4168, longitude=-3.7038, country="España")
        d = geo.to_dict()
        self.assertEqual(d["name"], "Madrid")
        self.assertEqual(d["latitude"], 40.4168)
        self.assertEqual(d["longitude"], -3.7038)
        self.assertEqual(d["country"], "España")

        restored = GeoLocation.from_dict(d)
        self.assertEqual(restored.name, geo.name)
        self.assertEqual(restored.latitude, geo.latitude)
        self.assertEqual(restored.longitude, geo.longitude)
        self.assertEqual(restored.country, geo.country)

    def test_geolocation_from_dict_defaults(self):
        geo = GeoLocation.from_dict({"name": "TestCity"})
        self.assertEqual(geo.name, "TestCity")
        self.assertEqual(geo.latitude, 0.0)
        self.assertEqual(geo.longitude, 0.0)
        self.assertEqual(geo.country, "")

    def test_weather_data_to_dict_and_from_dict(self):
        weather = WeatherData(
            city="Buenos Aires",
            country="Argentina",
            temperature=22.5,
            unit="°C",
            humidity=60,
            wind_speed=15.0,
            condition="Parcialmente nublado",
            weather_code=2,
            timestamp="2026-10-22T14:00",
            from_cache=True,
            cache_age_seconds=120.5,
        )
        d = weather.to_dict()
        self.assertEqual(d["city"], "Buenos Aires")
        self.assertEqual(d["temperature"], 22.5)
        self.assertEqual(d["unit"], "°C")
        self.assertTrue(d["from_cache"])
        self.assertEqual(d["cache_age_seconds"], 120.5)

        restored = WeatherData.from_dict(d)
        self.assertEqual(restored.city, "Buenos Aires")
        self.assertEqual(restored.temperature, 22.5)
        self.assertEqual(restored.unit, "°C")
        self.assertEqual(restored.humidity, 60)
        self.assertEqual(restored.condition, "Parcialmente nublado")
        self.assertTrue(restored.from_cache)
        self.assertEqual(restored.cache_age_seconds, 120.5)

    def test_weather_data_from_dict_defaults(self):
        weather = WeatherData.from_dict({"city": "Lima"})
        self.assertEqual(weather.city, "Lima")
        self.assertEqual(weather.temperature, 0.0)
        self.assertEqual(weather.unit, "°C")
        self.assertEqual(weather.condition, "Desconocido")
        self.assertFalse(weather.from_cache)


if __name__ == "__main__":
    unittest.main()
