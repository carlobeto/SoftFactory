"""Tests for the Command Line Interface (CLI)."""

import io
import json
import unittest
from unittest.mock import MagicMock, patch
from weather_tool.cli import build_parser, format_json, format_text, main
from weather_tool.models import WeatherData


class TestCLI(unittest.TestCase):
    """Pruebas unitarias para el módulo CLI y formateadores."""

    def setUp(self):
        self.sample_data = WeatherData(
            city="Valencia",
            country="España",
            temperature=24.0,
            unit="°C",
            humidity=55,
            wind_speed=14.0,
            condition="Despejado",
            weather_code=0,
            timestamp="2026-10-22T14:30",
            from_cache=False,
            cache_age_seconds=0.0,
        )

    def test_build_parser_defaults(self):
        parser = build_parser()
        args = parser.parse_args(["-c", "Sevilla"])
        self.assertEqual(args.city, "Sevilla")
        self.assertEqual(args.ttl, 1800)
        self.assertEqual(args.units, "metric")
        self.assertFalse(args.refresh)
        self.assertFalse(args.clear_cache)
        self.assertFalse(args.json)

    def test_format_text_output(self):
        out = format_text(self.sample_data)
        self.assertIn("Valencia", out)
        self.assertIn("24.0 °C", out)
        self.assertIn("Despejado", out)
        self.assertIn("API en tiempo real", out)

    def test_format_text_cached_output(self):
        cached_data = WeatherData(
            city="Valencia",
            country="España",
            temperature=24.0,
            unit="°C",
            humidity=55,
            wind_speed=14.0,
            condition="Despejado",
            weather_code=0,
            timestamp="2026-10-22T14:30",
            from_cache=True,
            cache_age_seconds=45.0,
        )
        out = format_text(cached_data)
        self.assertIn("Caché local (antigüedad: 45.0s)", out)

    def test_format_json_output(self):
        out = format_json(self.sample_data)
        parsed = json.loads(out)
        self.assertEqual(parsed["city"], "Valencia")
        self.assertEqual(parsed["temperature"], 24.0)

    @patch("sys.stderr", new_callable=io.StringIO)
    def test_main_missing_city_argument(self, mock_stderr):
        mock_svc = MagicMock()
        exit_code = main([], service=mock_svc)
        self.assertEqual(exit_code, 1)
        self.assertIn("Debe especificar una ciudad", mock_stderr.getvalue())

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_main_success_text(self, mock_stdout):
        mock_svc = MagicMock()
        mock_svc.get_weather.return_value = self.sample_data

        exit_code = main(["--city", "Valencia"], service=mock_svc)
        self.assertEqual(exit_code, 0)
        output = mock_stdout.getvalue()
        self.assertIn("Valencia", output)
        self.assertIn("24.0 °C", output)
        mock_svc.close.assert_called_once()

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_main_success_json(self, mock_stdout):
        mock_svc = MagicMock()
        mock_svc.get_weather.return_value = self.sample_data

        exit_code = main(["--city", "Valencia", "--json"], service=mock_svc)
        self.assertEqual(exit_code, 0)
        parsed = json.loads(mock_stdout.getvalue())
        self.assertEqual(parsed["city"], "Valencia")
        self.assertEqual(parsed["temperature"], 24.0)
        mock_svc.close.assert_called_once()

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_main_clear_cache_text(self, mock_stdout):
        mock_svc = MagicMock()
        mock_svc.clear_cache.return_value = 3

        exit_code = main(["--clear-cache"], service=mock_svc)
        self.assertEqual(exit_code, 0)
        self.assertIn("3 registros", mock_stdout.getvalue())
        mock_svc.close.assert_called_once()

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_main_clear_cache_json(self, mock_stdout):
        mock_svc = MagicMock()
        mock_svc.clear_cache.return_value = 2

        exit_code = main(["--clear-cache", "--json"], service=mock_svc)
        self.assertEqual(exit_code, 0)
        parsed = json.loads(mock_stdout.getvalue())
        self.assertEqual(parsed["status"], "ok")
        self.assertEqual(parsed["cleared_records"], 2)
        mock_svc.close.assert_called_once()

    @patch("sys.stderr", new_callable=io.StringIO)
    def test_main_error_handling(self, mock_stderr):
        mock_svc = MagicMock()
        mock_svc.get_weather.side_effect = ValueError("Ciudad desconocida")

        exit_code = main(["--city", "Invalida"], service=mock_svc)
        self.assertEqual(exit_code, 1)
        self.assertIn("Ciudad desconocida", mock_stderr.getvalue())
        mock_svc.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
