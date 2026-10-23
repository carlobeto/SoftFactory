"""Tests for WeatherClient using mocked HTTP responses."""

import unittest
from unittest.mock import MagicMock, patch
import urllib.error
from weather_tool.client import WeatherClient
from weather_tool.models import GeoLocation


class TestWeatherClient(unittest.TestCase):
    """Pruebas unitarias para el cliente HTTP de Open-Meteo."""

    def setUp(self):
        self.client = WeatherClient(timeout=5)

    def test_wmo_code_to_condition(self):
        self.assertEqual(self.client._wmo_code_to_condition(0), "Cielo despejado")
        self.assertEqual(self.client._wmo_code_to_condition(61), "Lluvia ligera")
        self.assertEqual(self.client._wmo_code_to_condition(95), "Tormenta eléctrica")
        self.assertIn("9999", self.client._wmo_code_to_condition(9999))

    def test_get_coordinates_empty_input(self):
        with self.assertRaises(ValueError):
            self.client.get_coordinates("   ")

    @patch.object(WeatherClient, "_fetch_url")
    def test_get_coordinates_success(self, mock_fetch):
        mock_fetch.return_value = {
            "results": [
                {
                    "name": "Montevideo",
                    "latitude": -34.9011,
                    "longitude": -56.1645,
                    "country": "Uruguay",
                }
            ]
        }
        loc = self.client.get_coordinates("Montevideo")
        self.assertIsInstance(loc, GeoLocation)
        self.assertEqual(loc.name, "Montevideo")
        self.assertEqual(loc.latitude, -34.9011)
        self.assertEqual(loc.longitude, -56.1645)
        self.assertEqual(loc.country, "Uruguay")

    @patch.object(WeatherClient, "_fetch_url")
    def test_get_coordinates_not_found(self, mock_fetch):
        mock_fetch.return_value = {"results": []}
        with self.assertRaises(ValueError) as ctx:
            self.client.get_coordinates("CiudadFantasma123")
        self.assertIn("No se encontró la ciudad", str(ctx.exception))

    @patch.object(WeatherClient, "_fetch_url")
    def test_fetch_weather_metric_success(self, mock_fetch):
        mock_fetch.return_value = {
            "current": {
                "temperature_2m": 21.4,
                "relative_humidity_2m": 65,
                "weather_code": 0,
                "wind_speed_10m": 12.3,
                "time": "2026-10-22T16:00",
            }
        }
        loc = GeoLocation(name="Montevideo", latitude=-34.9, longitude=-56.1, country="Uruguay")
        data = self.client.fetch_weather(loc, units="metric")

        self.assertEqual(data.city, "Montevideo")
        self.assertEqual(data.temperature, 21.4)
        self.assertEqual(data.unit, "°C")
        self.assertEqual(data.humidity, 65)
        self.assertEqual(data.wind_speed, 12.3)
        self.assertEqual(data.condition, "Cielo despejado")
        self.assertFalse(data.from_cache)

    @patch.object(WeatherClient, "_fetch_url")
    def test_fetch_weather_imperial_success(self, mock_fetch):
        mock_fetch.return_value = {
            "current": {
                "temperature_2m": 72.5,
                "relative_humidity_2m": 50,
                "weather_code": 2,
                "wind_speed_10m": 8.0,
                "time": "2026-10-22T16:00",
            }
        }
        loc = GeoLocation(name="New York", latitude=40.7, longitude=-74.0, country="USA")
        data = self.client.fetch_weather(loc, units="imperial")

        self.assertEqual(data.unit, "°F")
        self.assertEqual(data.temperature, 72.5)
        self.assertEqual(data.condition, "Parcialmente nublado")

    @patch.object(WeatherClient, "_fetch_url")
    def test_fetch_weather_invalid_response(self, mock_fetch):
        mock_fetch.return_value = {"invalid_structure": {}}
        loc = GeoLocation(name="Test", latitude=0, longitude=0)
        with self.assertRaises(RuntimeError) as ctx:
            self.client.fetch_weather(loc)
        self.assertIn("falta el bloque 'current'", str(ctx.exception))

    @patch("urllib.request.urlopen")
    def test_fetch_url_connection_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Network unreachable")
        with self.assertRaises(ConnectionError):
            self.client._fetch_url("http://dummy-url")

    @patch("urllib.request.urlopen")
    def test_fetch_url_http_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "http://dummy-url", 500, "Server Error", {}, None
        )
        with self.assertRaises(RuntimeError):
            self.client._fetch_url("http://dummy-url")


if __name__ == "__main__":
    unittest.main()
