"""Local persistent cache implementation backed by SQLite."""

import json
import sqlite3
import time
from typing import Optional
from .models import WeatherData


class WeatherCache:
    """Administra el almacenamiento en caché local de consultas meteorológicas con TTL."""

    def __init__(self, db_path: str = "weather_cache.db", default_ttl: int = 1800) -> None:
        """Inicializa la base de datos de caché en la ruta indicada o en memoria."""
        self.db_path = db_path
        self.default_ttl = default_ttl
        self.conn = sqlite3.connect(self.db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Crea la tabla de almacenamiento de caché si aún no existe."""
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS weather_cache (
                    city_key TEXT PRIMARY KEY,
                    city_name TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )

    @staticmethod
    def _normalize_key(city: str) -> str:
        """Normaliza el nombre de la ciudad eliminando espacios y convirtiendo a minúsculas."""
        return city.strip().lower()

    def get(self, city: str, ttl: Optional[int] = None) -> Optional[WeatherData]:
        """Obtiene datos de la ciudad desde el caché si no han excedido el TTL.

        Retorna None si la ciudad no está en caché o si el registro expiró.
        """
        effective_ttl = self.default_ttl if ttl is None else ttl
        key = self._normalize_key(city)
        now = time.time()

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT data_json, updated_at FROM weather_cache WHERE city_key = ?",
            (key,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        data_json, updated_at = row
        age_seconds = now - updated_at

        # Comprobar expiración según TTL
        if age_seconds > effective_ttl:
            return None

        try:
            raw_dict = json.loads(data_json)
            data = WeatherData.from_dict(raw_dict)
            data.from_cache = True
            data.cache_age_seconds = round(age_seconds, 1)
            return data
        except (json.JSONDecodeError, KeyError):
            return None

    def set(self, data: WeatherData) -> None:
        """Guarda o actualiza la información meteorológica en el caché local."""
        key = self._normalize_key(data.city)
        now = time.time()
        # Copia para serializar sin flags de caché previos
        payload = data.to_dict()
        payload["from_cache"] = False
        payload["cache_age_seconds"] = 0.0

        with self.conn:
            self.conn.execute(
                """
                INSERT INTO weather_cache (city_key, city_name, data_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(city_key) DO UPDATE SET
                    city_name = excluded.city_name,
                    data_json = excluded.data_json,
                    updated_at = excluded.updated_at
                """,
                (key, data.city, json.dumps(payload), now),
            )

    def clear(self) -> int:
        """Limpia todos los registros del caché y retorna la cantidad de registros eliminados."""
        with self.conn:
            cursor = self.conn.execute("DELETE FROM weather_cache")
            return cursor.rowcount

    def remove_expired(self, ttl: Optional[int] = None) -> int:
        """Elimina registros que hayan superado el TTL especificado."""
        effective_ttl = self.default_ttl if ttl is None else ttl
        threshold = time.time() - effective_ttl
        with self.conn:
            cursor = self.conn.execute(
                "DELETE FROM weather_cache WHERE updated_at < ?",
                (threshold,),
            )
            return cursor.rowcount

    def close(self) -> None:
        """Cierra la conexión con la base de datos."""
        if self.conn:
            self.conn.close()
