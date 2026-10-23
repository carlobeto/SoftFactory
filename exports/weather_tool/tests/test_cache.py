"""Tests for WeatherCache with SQLite persistence and TTL management."""

import json
import time
import unittest
from weather_tool.cache import WeatherCache
from weather_tool.models import WeatherData


class TestWeatherCache(unittest.TestCase):
    """Pruebas unitarias para el almacenamiento en caché local SQLite."""

    def setUp(self):
        """Inicializa una base de datos de prueba en memoria."""
        self.cache = WeatherCache(db_path=":memory:", default_ttl=60)
        self.sample_data = WeatherData(
            city="Santiago",
            country="Chile",
            temperature=19.0,
            unit="°C",
            humidity=50,
            wind_speed=10.0,
            condition="Despejado",
            weather_code=0,
            timestamp="2026-10-22T12:00",
        )

    def tearDown(self):
        """Cierra la conexión al finalizar cada prueba."""
        self.cache.close()

    def test_set_and_get_cache_hit(self):
        self.cache.set(self.sample_data)
        result = self.cache.get("Santiago")
        self.assertIsNotNone(result)
        self.assertEqual(result.city, "Santiago")
        self.assertEqual(result.temperature, 19.0)
        self.assertTrue(result.from_cache)
        self.assertGreaterEqual(result.cache_age_seconds, 0.0)

    def test_case_insensitive_key_normalization(self):
        self.cache.set(self.sample_data)
        # Búsqueda con espacios y diferentes mayúsculas/minúsculas
        result = self.cache.get("  sAnTiAgO  ")
        self.assertIsNotNone(result)
        self.assertEqual(result.city, "Santiago")

    def test_get_non_existent_city(self):
        result = self.cache.get("CiudadInexistente")
        self.assertIsNone(result)

    def test_expired_ttl(self):
        self.cache.set(self.sample_data)
        # Simulamos TTL de 0 segundos para forzar expiración inmediata
        result = self.cache.get("Santiago", ttl=0)
        self.assertIsNone(result)

    def test_update_existing_entry(self):
        self.cache.set(self.sample_data)
        updated = WeatherData(
            city="Santiago",
            country="Chile",
            temperature=25.0,
            unit="°C",
            humidity=40,
            wind_speed=8.0,
            condition="Caluroso",
            weather_code=0,
            timestamp="2026-10-22T15:00",
        )
        self.cache.set(updated)
        result = self.cache.get("Santiago")
        self.assertIsNotNone(result)
        self.assertEqual(result.temperature, 25.0)
        self.assertEqual(result.condition, "Caluroso")

    def test_clear_cache(self):
        self.cache.set(self.sample_data)
        cleared_count = self.cache.clear()
        self.assertEqual(cleared_count, 1)
        self.assertIsNone(self.cache.get("Santiago"))

    def test_remove_expired(self):
        # Insertar entrada con timestamp en el pasado
        old_time = time.time() - 3600
        key = WeatherCache._normalize_key("Bogota")
        payload = json.dumps(self.sample_data.to_dict())
        with self.cache.conn:
            self.cache.conn.execute(
                "INSERT INTO weather_cache VALUES (?, ?, ?, ?)",
                (key, "Bogota", payload, old_time),
            )

        # Entrada reciente
        self.cache.set(self.sample_data)

        # Borrar con TTL de 300 segundos
        removed = self.cache.remove_expired(ttl=300)
        self.assertEqual(removed, 1)
        self.assertIsNone(self.cache.get("Bogota"))
        self.assertIsNotNone(self.cache.get("Santiago"))

    def test_corrupt_data_handling(self):
        key = WeatherCache._normalize_key("CorruptCity")
        with self.cache.conn:
            self.cache.conn.execute(
                "INSERT INTO weather_cache VALUES (?, ?, ?, ?)",
                (key, "CorruptCity", "{json invalido", time.time()),
            )
        result = self.cache.get("CorruptCity")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
