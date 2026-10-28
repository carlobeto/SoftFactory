"""
Workshop Management Application Workspace Generator.
Especializado en generar aplicaciones fullstack para talleres mecánicos con backend completo
y frontend con dos partes independientes:
1. Portal de identificación y reserva para clientes.
2. Panel administrativo con menú lateral para gestión total del taller.
"""
from pathlib import Path
from typing import Any


def _build_workshop_workspace(ws_dir: Path, pname: str, seed: str, entities: list[str], disc: dict) -> list[str]:
    """Genera la implementación de código especializada para administración de turnos y talleres mecánicos."""
    app_dir = ws_dir / "app"
    tests_dir = ws_dir / "tests"
    app_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(parents=True, exist_ok=True)

    # 1. app/__init__.py
    (app_dir / "__init__.py").write_text('"""Workshop Management Application Package."""\n__version__ = "1.0.0"\n', encoding="utf-8")

    # 2. app/models.py
    models_code = '''"""
Modelos de Dominio y Entidades de Negocio para Administración de Turnos en Taller Mecánico.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional
import uuid


@dataclass
class ClienteRecord:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    nombre: str = ""
    dni: str = ""
    telefono: str = ""
    email: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClienteRecord":
        return cls(
            id=data.get("id") or str(uuid.uuid4())[:8],
            nombre=data.get("nombre", ""),
            dni=data.get("dni", ""),
            telefono=data.get("telefono", ""),
            email=data.get("email", ""),
            created_at=data.get("created_at") or datetime.now(timezone.utc).isoformat(),
        )


@dataclass
class VehiculoRecord:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    cliente_id: str = ""
    patente: str = ""
    marca: str = ""
    modelo: str = ""
    anio: int = 2020
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self):
        if self.patente:
            self.patente = self.patente.upper().strip()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VehiculoRecord":
        return cls(
            id=data.get("id") or str(uuid.uuid4())[:8],
            cliente_id=data.get("cliente_id", ""),
            patente=data.get("patente", "").upper().strip(),
            marca=data.get("marca", ""),
            modelo=data.get("modelo", ""),
            anio=int(data.get("anio", 2020)),
            created_at=data.get("created_at") or datetime.now(timezone.utc).isoformat(),
        )


@dataclass
class ServicioRecord:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    nombre: str = ""
    categoria: str = "General"
    precio: float = 0.0
    duracion_min: int = 60
    descripcion: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ServicioRecord":
        return cls(
            id=data.get("id") or str(uuid.uuid4())[:8],
            nombre=data.get("nombre", ""),
            categoria=data.get("categoria", "General"),
            precio=float(data.get("precio", 0.0)),
            duracion_min=int(data.get("duracion_min", 60)),
            descripcion=data.get("descripcion", ""),
        )


@dataclass
class TurnoRecord:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    cliente_id: str = ""
    cliente_nombre: str = ""
    vehiculo_id: str = ""
    vehiculo_patente: str = ""
    vehiculo_desc: str = ""
    servicio_id: str = ""
    servicio_nombre: str = ""
    fecha: str = ""
    hora: str = ""
    estado: str = "pendiente"  # pendiente, confirmado, en_taller, completado, cancelado
    notas: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TurnoRecord":
        return cls(
            id=data.get("id") or str(uuid.uuid4())[:8],
            cliente_id=data.get("cliente_id", ""),
            cliente_nombre=data.get("cliente_nombre", ""),
            vehiculo_id=data.get("vehiculo_id", ""),
            vehiculo_patente=data.get("vehiculo_patente", ""),
            vehiculo_desc=data.get("vehiculo_desc", ""),
            servicio_id=data.get("servicio_id", ""),
            servicio_nombre=data.get("servicio_nombre", ""),
            fecha=data.get("fecha", ""),
            hora=data.get("hora", ""),
            estado=data.get("estado", "pendiente"),
            notas=data.get("notas", ""),
            created_at=data.get("created_at") or datetime.now(timezone.utc).isoformat(),
        )


@dataclass
class ModelRecord:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    entity_type: str = "item"
    name: str = ""
    status: str = "activo"
    attributes: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelRecord":
        return cls(
            id=data.get("id") or str(uuid.uuid4())[:8],
            entity_type=data.get("entity_type", "item"),
            name=data.get("name", ""),
            status=data.get("status", "activo"),
            attributes=data.get("attributes", {}),
            created_at=data.get("created_at") or datetime.now(timezone.utc).isoformat(),
        )
'''
    (app_dir / "models.py").write_text(models_code, encoding="utf-8")

    # 3. app/storage.py
    storage_code = '''"""
Capa de Persistencia SQLite3 para Administración de Taller Mecánico.
"""
import sqlite3
import json
from pathlib import Path
from typing import Optional, Any
from app.models import ClienteRecord, VehiculoRecord, ServicioRecord, TurnoRecord, ModelRecord


class StorageRepository:
    def __init__(self, db_path: Optional[str] = None):
        self.is_memory = (db_path is None or db_path == ":memory:")
        if self.is_memory:
            self.db_path = ":memory:"
            self._conn = sqlite3.connect(":memory:", check_same_thread=False)
        else:
            self.db_path = str(Path(db_path).resolve())
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        return self._conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                dni TEXT UNIQUE NOT NULL,
                telefono TEXT NOT NULL,
                email TEXT,
                created_at TEXT NOT NULL
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS vehiculos (
                id TEXT PRIMARY KEY,
                cliente_id TEXT NOT NULL,
                patente TEXT UNIQUE NOT NULL,
                marca TEXT NOT NULL,
                modelo TEXT NOT NULL,
                anio INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (cliente_id) REFERENCES clientes(id)
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS servicios (
                id TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                categoria TEXT NOT NULL,
                precio REAL NOT NULL,
                duracion_min INTEGER NOT NULL,
                descripcion TEXT
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS turnos (
                id TEXT PRIMARY KEY,
                cliente_id TEXT NOT NULL,
                cliente_nombre TEXT NOT NULL,
                vehiculo_id TEXT NOT NULL,
                vehiculo_patente TEXT NOT NULL,
                vehiculo_desc TEXT NOT NULL,
                servicio_id TEXT NOT NULL,
                servicio_nombre TEXT NOT NULL,
                fecha TEXT NOT NULL,
                hora TEXT NOT NULL,
                estado TEXT NOT NULL,
                notas TEXT,
                created_at TEXT NOT NULL
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS records (
                id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                attributes TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """)
            conn.commit()

            cursor.execute("SELECT COUNT(*) FROM clientes;")
            if cursor.fetchone()[0] == 0:
                self._seed_data(cursor)
                conn.commit()

    def _seed_data(self, cursor: sqlite3.Cursor):
        clientes = [
            ("cli-1", "Carlos Gómez", "30123456", "+54 11 4455-6677", "carlos.gomez@gmail.com", "2026-10-20T10:00:00"),
            ("cli-2", "Ana Martínez", "28987654", "+54 11 5566-7788", "ana.martinez@outlook.com", "2026-10-21T11:30:00"),
            ("cli-3", "Roberto Díaz", "33456789", "+54 11 6677-8899", "roberto.diaz@yahoo.com", "2026-10-22T09:15:00"),
        ]
        cursor.executemany("INSERT OR IGNORE INTO clientes (id, nombre, dni, telefono, email, created_at) VALUES (?, ?, ?, ?, ?, ?);", clientes)

        vehiculos = [
            ("veh-1", "cli-1", "AB 123 CD", "Ford", "Focus SE 2.0", 2019, "2026-10-20T10:05:00"),
            ("veh-2", "cli-2", "AC 456 EF", "Toyota", "Hilux 4x4", 2021, "2026-10-21T11:35:00"),
            ("veh-3", "cli-3", "AD 789 GH", "Volkswagen", "Golf TSI", 2020, "2026-10-22T09:20:00"),
            ("veh-4", "cli-1", "AE 321 IJ", "Peugeot", "208 Allure", 2022, "2026-10-23T14:00:00"),
        ]
        cursor.executemany("INSERT OR IGNORE INTO vehiculos (id, cliente_id, patente, marca, modelo, anio, created_at) VALUES (?, ?, ?, ?, ?, ?, ?);", vehiculos)

        servicios = [
            ("srv-1", "Mantenimiento Periódico 10.000 km", "Service General", 45000.0, 90, "Cambio de aceite sintético, filtros de aceite, aire y habitáculo, y revisión de 25 puntos clave."),
            ("srv-2", "Frenos Delanteros y Traseros", "Frenos", 38000.0, 60, "Sustitución de pastillas de freno, revisión de discos y purga de líquido DOT4."),
            ("srv-3", "Diagnóstico Computarizado OBD-II", "Diagnóstico", 18000.0, 45, "Escaneo computarizado de ECU, inyección, sensores, ABS y diagnóstico de fallas."),
            ("srv-4", "Alineación 3D y Balanceo", "Tren Delantero", 22000.0, 40, "Alineación láser 3D en ambos ejes y balanceo dinámico de las 4 ruedas."),
            ("srv-5", "Cambio de Kit Distribución y Bomba", "Motor", 95000.0, 180, "Reemplazo de correa/cadena de distribución, tensores y bomba de agua."),
        ]
        cursor.executemany("INSERT OR IGNORE INTO servicios (id, nombre, categoria, precio, duracion_min, descripcion) VALUES (?, ?, ?, ?, ?, ?);", servicios)

        turnos = [
            ("tur-101", "cli-1", "Carlos Gómez", "veh-1", "AB 123 CD", "Ford Focus SE 2.0 (2019)", "srv-1", "Mantenimiento Periódico 10.000 km", "2026-10-28", "09:00", "en_taller", "Revisión adicional de chirrido al girar volante.", "2026-10-26T10:00:00"),
            ("tur-102", "cli-2", "Ana Martínez", "veh-2", "AC 456 EF", "Toyota Hilux 4x4 (2021)", "srv-2", "Frenos Delanteros y Traseros", "2026-10-28", "11:30", "pendiente", "Pedal de freno con recorrido largo.", "2026-10-27T08:30:00"),
            ("tur-103", "cli-3", "Roberto Díaz", "veh-3", "AD 789 GH", "Volkswagen Golf TSI (2020)", "srv-4", "Alineación 3D y Balanceo", "2026-10-27", "15:00", "completado", "Servicio completado, listo para entrega.", "2026-10-25T14:15:00"),
            ("tur-104", "cli-1", "Carlos Gómez", "veh-4", "AE 321 IJ", "Peugeot 208 Allure (2022)", "srv-3", "Diagnóstico Computarizado OBD-II", "2026-10-29", "10:00", "confirmado", "Testigo de Check Engine encendido.", "2026-10-27T12:00:00"),
        ]
        cursor.executemany("INSERT OR IGNORE INTO turnos (id, cliente_id, cliente_nombre, vehiculo_id, vehiculo_patente, vehiculo_desc, servicio_id, servicio_nombre, fecha, hora, estado, notas, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", turnos)

    def buscar_cliente(self, query: str) -> Optional[ClienteRecord]:
        q = query.strip()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, nombre, dni, telefono, email, created_at FROM clientes WHERE dni = ? OR telefono = ? OR LOWER(nombre) LIKE ? LIMIT 1;", (q, q, f"%{q.lower()}%"))
            row = cursor.fetchone()
            if row:
                return ClienteRecord(id=row["id"], nombre=row["nombre"], dni=row["dni"], telefono=row["telefono"], email=row["email"] or "", created_at=row["created_at"])
            return None

    def get_cliente(self, cliente_id: str) -> Optional[ClienteRecord]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, nombre, dni, telefono, email, created_at FROM clientes WHERE id = ?;", (cliente_id,))
            row = cursor.fetchone()
            if row:
                return ClienteRecord(id=row["id"], nombre=row["nombre"], dni=row["dni"], telefono=row["telefono"], email=row["email"] or "", created_at=row["created_at"])
            return None

    def list_clientes(self) -> list[ClienteRecord]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, nombre, dni, telefono, email, created_at FROM clientes ORDER BY nombre ASC;")
            return [ClienteRecord(id=r["id"], nombre=r["nombre"], dni=r["dni"], telefono=r["telefono"], email=r["email"] or "", created_at=r["created_at"]) for r in cursor.fetchall()]

    def save_cliente(self, c: ClienteRecord) -> ClienteRecord:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO clientes (id, nombre, dni, telefono, email, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                nombre=excluded.nombre,
                dni=excluded.dni,
                telefono=excluded.telefono,
                email=excluded.email;
            """, (c.id, c.nombre, c.dni, c.telefono, c.email, c.created_at))
            conn.commit()
            return c

    def list_vehiculos(self, cliente_id: Optional[str] = None) -> list[VehiculoRecord]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if cliente_id:
                cursor.execute("SELECT id, cliente_id, patente, marca, modelo, anio, created_at FROM vehiculos WHERE cliente_id = ? ORDER BY created_at DESC;", (cliente_id,))
            else:
                cursor.execute("SELECT id, cliente_id, patente, marca, modelo, anio, created_at FROM vehiculos ORDER BY created_at DESC;")
            return [VehiculoRecord(id=r["id"], cliente_id=r["cliente_id"], patente=r["patente"], marca=r["marca"], modelo=r["modelo"], anio=r["anio"], created_at=r["created_at"]) for r in cursor.fetchall()]

    def get_vehiculo(self, vehiculo_id: str) -> Optional[VehiculoRecord]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, cliente_id, patente, marca, modelo, anio, created_at FROM vehiculos WHERE id = ?;", (vehiculo_id,))
            row = cursor.fetchone()
            if row:
                return VehiculoRecord(id=row["id"], cliente_id=row["cliente_id"], patente=row["patente"], marca=row["marca"], modelo=row["modelo"], anio=row["anio"], created_at=row["created_at"])
            return None

    def save_vehiculo(self, v: VehiculoRecord) -> VehiculoRecord:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO vehiculos (id, cliente_id, patente, marca, modelo, anio, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                cliente_id=excluded.cliente_id,
                patente=excluded.patente,
                marca=excluded.marca,
                modelo=excluded.modelo,
                anio=excluded.anio;
            """, (v.id, v.cliente_id, v.patente.upper().strip(), v.marca, v.modelo, v.anio, v.created_at))
            conn.commit()
            return v

    def list_servicios(self) -> list[ServicioRecord]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, nombre, categoria, precio, duracion_min, descripcion FROM servicios ORDER BY precio ASC;")
            return [ServicioRecord(id=r["id"], nombre=r["nombre"], categoria=r["categoria"], precio=r["precio"], duracion_min=r["duracion_min"], descripcion=r["descripcion"] or "") for r in cursor.fetchall()]

    def get_servicio(self, servicio_id: str) -> Optional[ServicioRecord]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, nombre, categoria, precio, duracion_min, descripcion FROM servicios WHERE id = ?;", (servicio_id,))
            row = cursor.fetchone()
            if row:
                return ServicioRecord(id=row["id"], nombre=row["nombre"], categoria=row["categoria"], precio=row["precio"], duracion_min=row["duracion_min"], descripcion=row["descripcion"] or "")
            return None

    def list_turnos(self, estado: Optional[str] = None, cliente_id: Optional[str] = None) -> list[TurnoRecord]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT id, cliente_id, cliente_nombre, vehiculo_id, vehiculo_patente, vehiculo_desc, servicio_id, servicio_nombre, fecha, hora, estado, notas, created_at FROM turnos"
            params = []
            conditions = []
            if estado and estado != "todos":
                conditions.append("estado = ?")
                params.append(estado)
            if cliente_id:
                conditions.append("cliente_id = ?")
                params.append(cliente_id)
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY fecha DESC, hora DESC;"
            cursor.execute(query, params)
            return [TurnoRecord(
                id=r["id"],
                cliente_id=r["cliente_id"],
                cliente_nombre=r["cliente_nombre"],
                vehiculo_id=r["vehiculo_id"],
                vehiculo_patente=r["vehiculo_patente"],
                vehiculo_desc=r["vehiculo_desc"],
                servicio_id=r["servicio_id"],
                servicio_nombre=r["servicio_nombre"],
                fecha=r["fecha"],
                hora=r["hora"],
                estado=r["estado"],
                notas=r["notas"] or "",
                created_at=r["created_at"]
            ) for r in cursor.fetchall()]

    def get_turno(self, turno_id: str) -> Optional[TurnoRecord]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, cliente_id, cliente_nombre, vehiculo_id, vehiculo_patente, vehiculo_desc, servicio_id, servicio_nombre, fecha, hora, estado, notas, created_at FROM turnos WHERE id = ?;", (turno_id,))
            r = cursor.fetchone()
            if r:
                return TurnoRecord(
                    id=r["id"],
                    cliente_id=r["cliente_id"],
                    cliente_nombre=r["cliente_nombre"],
                    vehiculo_id=r["vehiculo_id"],
                    vehiculo_patente=r["vehiculo_patente"],
                    vehiculo_desc=r["vehiculo_desc"],
                    servicio_id=r["servicio_id"],
                    servicio_nombre=r["servicio_nombre"],
                    fecha=r["fecha"],
                    hora=r["hora"],
                    estado=r["estado"],
                    notas=r["notas"] or "",
                    created_at=r["created_at"]
                )
            return None

    def save_turno(self, t: TurnoRecord) -> TurnoRecord:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO turnos (id, cliente_id, cliente_nombre, vehiculo_id, vehiculo_patente, vehiculo_desc, servicio_id, servicio_nombre, fecha, hora, estado, notas, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                estado=excluded.estado,
                fecha=excluded.fecha,
                hora=excluded.hora,
                notas=excluded.notas;
            """, (t.id, t.cliente_id, t.cliente_nombre, t.vehiculo_id, t.vehiculo_patente, t.vehiculo_desc, t.servicio_id, t.servicio_nombre, t.fecha, t.hora, t.estado, t.notas, t.created_at))
            conn.commit()
            return t

    def update_turno_estado(self, turno_id: str, nuevo_estado: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE turnos SET estado = ? WHERE id = ?;", (nuevo_estado, turno_id))
            conn.commit()
            return cursor.rowcount > 0

    def delete_turno(self, turno_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM turnos WHERE id = ?;", (turno_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_metricas(self) -> dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM turnos;")
            total_turnos = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM turnos WHERE estado = 'en_taller';")
            en_taller = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM turnos WHERE estado = 'pendiente';")
            pendientes = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM turnos WHERE estado = 'completado';")
            completados = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM clientes;")
            total_clientes = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM vehiculos;")
            total_vehiculos = cursor.fetchone()[0]
            return {
                "turnos_total": total_turnos,
                "turnos_en_taller": en_taller,
                "turnos_pendientes": pendientes,
                "turnos_completados": completados,
                "clientes_total": total_clientes,
                "vehiculos_total": total_vehiculos,
            }

    def save(self, record: ModelRecord) -> ModelRecord:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO records (id, entity_type, name, status, attributes, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                status=excluded.status,
                attributes=excluded.attributes;
            """, (record.id, record.entity_type, record.name, record.status, json.dumps(record.attributes), record.created_at))
            conn.commit()
            return record

    def get(self, record_id: str) -> Optional[ModelRecord]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, entity_type, name, status, attributes, created_at FROM records WHERE id = ?;", (record_id,))
            r = cursor.fetchone()
            if r:
                return ModelRecord(id=r["id"], entity_type=r["entity_type"], name=r["name"], status=r["status"], attributes=json.loads(r["attributes"]), created_at=r["created_at"])
            return None

    def list_all(self, entity_type: Optional[str] = None) -> list[ModelRecord]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if entity_type:
                cursor.execute("SELECT id, entity_type, name, status, attributes, created_at FROM records WHERE entity_type = ?;", (entity_type,))
            else:
                cursor.execute("SELECT id, entity_type, name, status, attributes, created_at FROM records;")
            return [ModelRecord(id=r["id"], entity_type=r["entity_type"], name=r["name"], status=r["status"], attributes=json.loads(r["attributes"]), created_at=r["created_at"]) for r in cursor.fetchall()]
'''
    (app_dir / "storage.py").write_text(storage_code, encoding="utf-8")

    # 4. app/service.py
    service_code = '''"""
Capa de Servicio: Lógica de negocio de taller y manejo de errores RFC 7807.
"""
from typing import Optional, Any
from app.models import ClienteRecord, VehiculoRecord, ServicioRecord, TurnoRecord, ModelRecord
from app.storage import StorageRepository


class ServiceError(Exception):
    def __init__(self, title: str, detail: str, status_code: int = 400):
        self.title = title
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)

    def to_problem_details(self) -> dict[str, Any]:
        return {
            "type": "about:blank",
            "title": self.title,
            "status": self.status_code,
            "detail": self.detail,
        }


class AppService:
    ESTADOS_VALIDOS = {"pendiente", "confirmado", "en_taller", "completado", "cancelado"}

    def __init__(self, repository: StorageRepository):
        self.repo = repository

    def buscar_cliente(self, query: str) -> dict[str, Any]:
        if not query or not query.strip():
            raise ServiceError("Validation Error", "El DNI o teléfono de búsqueda no puede estar vacío.", 400)
        cliente = self.repo.buscar_cliente(query.strip())
        if not cliente:
            raise ServiceError("Not Found", f"No se encontró ningún cliente con DNI o contacto '{query.strip()}'.", 404)
        vehiculos = self.repo.list_vehiculos(cliente.id)
        turnos = self.repo.list_turnos(cliente_id=cliente.id)
        return {
            "cliente": cliente.to_dict(),
            "vehiculos": [v.to_dict() for v in vehiculos],
            "turnos": [t.to_dict() for t in turnos],
        }

    def crear_cliente(self, nombre: str, dni: str, telefono: str, email: str = "") -> ClienteRecord:
        if not nombre or not nombre.strip():
            raise ServiceError("Validation Error", "El nombre del cliente es obligatorio.", 400)
        if not dni or not dni.strip():
            raise ServiceError("Validation Error", "El DNI del cliente es obligatorio.", 400)
        if not telefono or not telefono.strip():
            raise ServiceError("Validation Error", "El teléfono de contacto es obligatorio.", 400)
        existente = self.repo.buscar_cliente(dni.strip())
        if existente:
            raise ServiceError("Conflict", f"Ya existe un cliente registrado con el DNI '{dni.strip()}'.", 409)
        c = ClienteRecord(nombre=nombre.strip(), dni=dni.strip(), telefono=telefono.strip(), email=email.strip())
        return self.repo.save_cliente(c)

    def listar_clientes(self) -> list[ClienteRecord]:
        return self.repo.list_clientes()

    def obtener_cliente(self, cliente_id: str) -> ClienteRecord:
        c = self.repo.get_cliente(cliente_id)
        if not c:
            raise ServiceError("Not Found", f"Cliente con ID '{cliente_id}' no encontrado.", 404)
        return c

    def crear_vehiculo(self, cliente_id: str, patente: str, marca: str, modelo: str, anio: int) -> VehiculoRecord:
        self.obtener_cliente(cliente_id)
        if not patente or not patente.strip():
            raise ServiceError("Validation Error", "La patente del vehículo es obligatoria.", 400)
        if not marca or not marca.strip() or not modelo or not modelo.strip():
            raise ServiceError("Validation Error", "Marca y modelo son obligatorios.", 400)
        v = VehiculoRecord(cliente_id=cliente_id, patente=patente.upper().strip(), marca=marca.strip(), modelo=modelo.strip(), anio=int(anio))
        return self.repo.save_vehiculo(v)

    def listar_vehiculos(self, cliente_id: Optional[str] = None) -> list[VehiculoRecord]:
        return self.repo.list_vehiculos(cliente_id)

    def listar_servicios(self) -> list[ServicioRecord]:
        return self.repo.list_servicios()

    def crear_turno(self, cliente_id: str, vehiculo_id: str, servicio_id: str, fecha: str, hora: str, notas: str = "") -> TurnoRecord:
        cliente = self.obtener_cliente(cliente_id)
        vehiculo = self.repo.get_vehiculo(vehiculo_id)
        if not vehiculo:
            raise ServiceError("Not Found", f"Vehículo con ID '{vehiculo_id}' no encontrado.", 404)
        servicio = self.repo.get_servicio(servicio_id)
        if not servicio:
            raise ServiceError("Not Found", f"Servicio con ID '{servicio_id}' no encontrado.", 404)
        if not fecha or not fecha.strip():
            raise ServiceError("Validation Error", "La fecha del turno es requerida.", 400)
        if not hora or not hora.strip():
            raise ServiceError("Validation Error", "La hora del turno es requerida.", 400)

        t = TurnoRecord(
            cliente_id=cliente.id,
            cliente_nombre=cliente.nombre,
            vehiculo_id=vehiculo.id,
            vehiculo_patente=vehiculo.patente,
            vehiculo_desc=f"{vehiculo.marca} {vehiculo.modelo} ({vehiculo.anio})",
            servicio_id=servicio.id,
            servicio_nombre=servicio.nombre,
            fecha=fecha.strip(),
            hora=hora.strip(),
            estado="pendiente",
            notas=notas.strip(),
        )
        return self.repo.save_turno(t)

    def actualizar_estado_turno(self, turno_id: str, nuevo_estado: str) -> TurnoRecord:
        t = self.repo.get_turno(turno_id)
        if not t:
            raise ServiceError("Not Found", f"Turno con ID '{turno_id}' no encontrado.", 404)
        st = nuevo_estado.strip().lower()
        if st not in self.ESTADOS_VALIDOS:
            raise ServiceError("Validation Error", f"Estado '{nuevo_estado}' inválido. Estados permitidos: {', '.join(sorted(self.ESTADOS_VALIDOS))}", 422)
        self.repo.update_turno_estado(turno_id, st)
        t.estado = st
        return t

    def listar_turnos(self, estado: Optional[str] = None, cliente_id: Optional[str] = None) -> list[TurnoRecord]:
        return self.repo.list_turnos(estado, cliente_id)

    def obtener_metricas(self) -> dict[str, Any]:
        return self.repo.get_metricas()

    def create(self, entity_type: str, name: str, attributes: Optional[dict] = None) -> ModelRecord:
        if not name or not name.strip():
            raise ServiceError("Validation Error", "El nombre de la entidad es obligatorio.", 400)
        rec = ModelRecord(entity_type=entity_type.strip().lower(), name=name.strip(), attributes=attributes or {})
        return self.repo.save(rec)

    def get_by_id(self, record_id: str) -> ModelRecord:
        r = self.repo.get(record_id)
        if not r:
            raise ServiceError("Not Found", f"Registro '{record_id}' no encontrado.", 404)
        return r

    def list_records(self, entity_type: Optional[str] = None) -> list[ModelRecord]:
        return self.repo.list_all(entity_type)

    def delete_record(self, record_id: str) -> bool:
        self.get_by_id(record_id)
        return self.repo.delete_turno(record_id)
'''
    (app_dir / "service.py").write_text(service_code, encoding="utf-8")

    # 5. app/api.py
    api_code = '''"""
Controlador / Handler de API RESTful para Taller Mecánico con RFC 7807 Problem Details.
"""
import urllib.parse
from typing import Any, Optional
from app.service import AppService, ServiceError


class ApiHandler:
    def __init__(self, service: AppService):
        self.service = service

    def handle_request(self, method: str, full_path: str, payload: Optional[dict] = None) -> tuple[int, dict[str, Any]]:
        try:
            parsed = urllib.parse.urlparse(full_path)
            path = parsed.path.rstrip("/")
            query_params = urllib.parse.parse_qs(parsed.query)

            if path == "/health" and method == "GET":
                m = self.service.obtener_metricas()
                return 200, {
                    "status": "UP",
                    "database": "SQLite3 (Connected)",
                    "metricas": m,
                }

            parts = [p for p in path.split("/") if p]
            if len(parts) >= 2 and parts[0] == "api" and parts[1] == "v1":
                resource = parts[2] if len(parts) >= 3 else ""
                res_id = parts[3] if len(parts) >= 4 else None
                sub_action = parts[4] if len(parts) >= 5 else None

                if resource == "buscar-cliente" and method == "GET":
                    q = query_params.get("query", [""])[0] or query_params.get("q", [""])[0]
                    res = self.service.buscar_cliente(q)
                    return 200, {"success": True, "data": res}

                elif resource == "clientes":
                    if method == "GET":
                        if res_id:
                            if sub_action == "vehiculos":
                                vehs = self.service.listar_vehiculos(res_id)
                                return 200, {"success": True, "data": [v.to_dict() for v in vehs]}
                            cli = self.service.obtener_cliente(res_id)
                            return 200, {"success": True, "data": cli.to_dict()}
                        else:
                            clis = self.service.listar_clientes()
                            return 200, {"success": True, "data": [c.to_dict() for c in clis]}
                    elif method == "POST":
                        data = payload or {}
                        cli = self.service.crear_cliente(
                            nombre=data.get("nombre", ""),
                            dni=data.get("dni", ""),
                            telefono=data.get("telefono", ""),
                            email=data.get("email", ""),
                        )
                        return 201, {"success": True, "data": cli.to_dict()}

                elif resource == "vehiculos":
                    if method == "GET":
                        cli_id = query_params.get("cliente_id", [None])[0]
                        vehs = self.service.listar_vehiculos(cli_id)
                        return 200, {"success": True, "data": [v.to_dict() for v in vehs]}
                    elif method == "POST":
                        data = payload or {}
                        v = self.service.crear_vehiculo(
                            cliente_id=data.get("cliente_id", ""),
                            patente=data.get("patente", ""),
                            marca=data.get("marca", ""),
                            modelo=data.get("modelo", ""),
                            anio=int(data.get("anio", 2020)),
                        )
                        return 201, {"success": True, "data": v.to_dict()}

                elif resource == "servicios":
                    if method == "GET":
                        srvs = self.service.listar_servicios()
                        return 200, {"success": True, "data": [s.to_dict() for s in srvs]}

                elif resource == "turnos":
                    if method == "GET":
                        if res_id:
                            t = self.service.repo.get_turno(res_id)
                            if not t:
                                raise ServiceError("Not Found", f"Turno '{res_id}' no encontrado.", 404)
                            return 200, {"success": True, "data": t.to_dict()}
                        else:
                            st = query_params.get("estado", [None])[0]
                            cid = query_params.get("cliente_id", [None])[0]
                            turnos = self.service.listar_turnos(st, cid)
                            return 200, {"success": True, "data": [t.to_dict() for t in turnos]}
                    elif method == "POST":
                        data = payload or {}
                        t = self.service.crear_turno(
                            cliente_id=data.get("cliente_id", ""),
                            vehiculo_id=data.get("vehiculo_id", ""),
                            servicio_id=data.get("servicio_id", ""),
                            fecha=data.get("fecha", ""),
                            hora=data.get("hora", ""),
                            notas=data.get("notas", ""),
                        )
                        return 201, {"success": True, "data": t.to_dict()}
                    elif method in ("PUT", "PATCH") and res_id:
                        data = payload or {}
                        st = data.get("estado", "")
                        t = self.service.actualizar_estado_turno(res_id, st)
                        return 200, {"success": True, "data": t.to_dict()}
                    elif method == "DELETE" and res_id:
                        ok = self.service.repo.delete_turno(res_id)
                        if not ok:
                            raise ServiceError("Not Found", f"Turno '{res_id}' no encontrado.", 404)
                        return 200, {"success": True, "message": f"Turno '{res_id}' eliminado."}

                elif resource == "metricas" and method == "GET":
                    m = self.service.obtener_metricas()
                    return 200, {"success": True, "data": m}

                elif resource == "sistema":
                    if method == "GET":
                        items = self.service.list_records()
                        return 200, {"success": True, "data": [i.to_dict() for i in items]}
                    elif method == "POST":
                        data = payload or {}
                        item = self.service.create("general", data.get("name", "Item"), data.get("attributes", {}))
                        return 201, {"success": True, "data": item.to_dict()}

            raise ServiceError("Not Found", f"Endpoint '{method} {full_path}' no encontrado.", 404)

        except ServiceError as se:
            return se.status_code, se.to_problem_details()
        except Exception as e:
            err = ServiceError("Internal Server Error", str(e), 500)
            return 500, err.to_problem_details()
'''
    (app_dir / "api.py").write_text(api_code, encoding="utf-8")

    # 6. tests/
    (tests_dir / "__init__.py").write_text('"""Workshop Test Suite."""\n', encoding="utf-8")

    (tests_dir / "test_models.py").write_text('''"""Tests unitarios para modelos de dominio de Taller Mecánico."""
import unittest
from app.models import ClienteRecord, VehiculoRecord, ServicioRecord, TurnoRecord, ModelRecord


class TestWorkshopModels(unittest.TestCase):
    def test_cliente_record(self):
        c = ClienteRecord(nombre="Juan Pérez", dni="32111222", telefono="+54 11 1122-3344", email="juan@example.com")
        self.assertEqual(c.nombre, "Juan Pérez")
        d = c.to_dict()
        self.assertEqual(d["dni"], "32111222")
        clone = ClienteRecord.from_dict(d)
        self.assertEqual(clone.id, c.id)

    def test_vehiculo_record(self):
        v = VehiculoRecord(cliente_id="c1", patente="ab 123 cd", marca="Ford", modelo="Ka", anio=2018)
        self.assertEqual(v.patente, "AB 123 CD")
        d = v.to_dict()
        clone = VehiculoRecord.from_dict(d)
        self.assertEqual(clone.modelo, "Ka")

    def test_servicio_record(self):
        s = ServicioRecord(nombre="Frenos", precio=35000.0, duracion_min=45)
        self.assertEqual(s.precio, 35000.0)
        d = s.to_dict()
        self.assertEqual(d["duracion_min"], 45)

    def test_turno_record(self):
        t = TurnoRecord(cliente_id="c1", vehiculo_id="v1", fecha="2026-10-30", hora="10:00", estado="pendiente")
        self.assertEqual(t.estado, "pendiente")
        d = t.to_dict()
        self.assertEqual(d["fecha"], "2026-10-30")

    def test_model_record(self):
        m = ModelRecord(name="Repuesto", status="activo")
        self.assertEqual(m.name, "Repuesto")


if __name__ == "__main__":
    unittest.main()
''', encoding="utf-8")

    (tests_dir / "test_storage.py").write_text('''"""Tests unitarios para capa de persistencia SQLite3 de Taller."""
import unittest
from app.storage import StorageRepository
from app.models import ClienteRecord, VehiculoRecord, TurnoRecord, ModelRecord


class TestWorkshopStorage(unittest.TestCase):
    def setUp(self):
        self.repo = StorageRepository(":memory:")

    def test_seeding_and_retrieval(self):
        clientes = self.repo.list_clientes()
        self.assertGreaterEqual(len(clientes), 3)
        vehiculos = self.repo.list_vehiculos()
        self.assertGreaterEqual(len(vehiculos), 4)
        servicios = self.repo.list_servicios()
        self.assertGreaterEqual(len(servicios), 5)
        turnos = self.repo.list_turnos()
        self.assertGreaterEqual(len(turnos), 4)

    def test_buscar_cliente(self):
        cli = self.repo.buscar_cliente("30123456")
        self.assertIsNotNone(cli)
        self.assertEqual(cli.nombre, "Carlos Gómez")

    def test_turnos_status_update(self):
        turnos = self.repo.list_turnos()
        t0 = turnos[0]
        self.repo.update_turno_estado(t0.id, "completado")
        updated = self.repo.get_turno(t0.id)
        self.assertEqual(updated.estado, "completado")

    def test_metricas(self):
        m = self.repo.get_metricas()
        self.assertIn("turnos_total", m)
        self.assertIn("turnos_en_taller", m)
        self.assertGreaterEqual(m["clientes_total"], 3)


if __name__ == "__main__":
    unittest.main()
''', encoding="utf-8")

    (tests_dir / "test_service.py").write_text('''"""Tests unitarios para lógica de negocio de Taller y RFC 7807."""
import unittest
from app.storage import StorageRepository
from app.service import AppService, ServiceError


class TestWorkshopService(unittest.TestCase):
    def setUp(self):
        self.repo = StorageRepository(":memory:")
        self.service = AppService(self.repo)

    def test_buscar_cliente_ok(self):
        res = self.service.buscar_cliente("30123456")
        self.assertEqual(res["cliente"]["nombre"], "Carlos Gómez")
        self.assertGreaterEqual(len(res["vehiculos"]), 1)
        self.assertGreaterEqual(len(res["turnos"]), 1)

    def test_buscar_cliente_not_found(self):
        with self.assertRaises(ServiceError) as cm:
            self.service.buscar_cliente("99999999")
        self.assertEqual(cm.exception.status_code, 404)

    def test_crear_turno_and_state_transition(self):
        clientes = self.service.listar_clientes()
        c = clientes[0]
        vehs = self.service.listar_vehiculos(c.id)
        srvs = self.service.listar_servicios()
        t = self.service.crear_turno(c.id, vehs[0].id, srvs[0].id, "2026-11-01", "14:00", "Revisión general")
        self.assertEqual(t.estado, "pendiente")

        updated = self.service.actualizar_estado_turno(t.id, "en_taller")
        self.assertEqual(updated.estado, "en_taller")

    def test_invalid_state_transition(self):
        turnos = self.service.listar_turnos()
        with self.assertRaises(ServiceError) as cm:
            self.service.actualizar_estado_turno(turnos[0].id, "estado_inexistente")
        self.assertEqual(cm.exception.status_code, 422)

    def test_metricas(self):
        m = self.service.obtener_metricas()
        self.assertGreaterEqual(m["turnos_total"], 4)


if __name__ == "__main__":
    unittest.main()
''', encoding="utf-8")

    # 7. main.py with full HTML SPA template
    main_code = f'''\"\"\"
Punto de Entrada Principal y Servidor HTTP de Administración de Taller Mecánico para {pname}.
\"\"\"
import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Optional

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.models import ClienteRecord, VehiculoRecord, ServicioRecord, TurnoRecord, ModelRecord
from app.storage import StorageRepository
from app.service import AppService
from app.api import ApiHandler

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>🔧 AutoFix - __APP_NAME__</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #090e17;
      --sidebar-bg: #0d1527;
      --card-bg: rgba(19, 29, 51, 0.75);
      --card-border: rgba(255, 255, 255, 0.08);
      --primary: #38bdf8;
      --primary-glow: rgba(56, 189, 248, 0.25);
      --indigo: #6366f1;
      --emerald: #10b981;
      --amber: #f59e0b;
      --rose: #f43f5e;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --radius: 14px;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Outfit', sans-serif;
      background: radial-gradient(circle at 50% 0%, #172554 0%, #0d1527 35%, #090e17 100%);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.9rem 1.8rem;
      background: rgba(13, 21, 39, 0.85);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--card-border);
      position: sticky;
      top: 0;
      z-index: 50;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }}
    .brand-icon {{
      font-size: 1.8rem;
    }}
    .brand-title {{
      font-size: 1.25rem;
      font-weight: 700;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    .brand-badge {{
      background: rgba(56, 189, 248, 0.15);
      color: var(--primary);
      border: 1px solid rgba(56, 189, 248, 0.3);
      padding: 0.15rem 0.5rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
    }}
    .mode-switch {{
      display: flex;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--card-border);
      padding: 4px;
      border-radius: 9999px;
      gap: 4px;
    }}
    .mode-btn {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 0.45rem 1.1rem;
      border-radius: 9999px;
      font-family: 'Outfit', sans-serif;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s ease;
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }}
    .mode-btn:hover {{ color: #fff; }}
    .mode-btn.active {{
      background: var(--primary);
      color: #090e17;
      box-shadow: 0 0 12px var(--primary-glow);
    }}
    .status-pill {{
      display: flex;
      align-items: center;
      gap: 0.4rem;
      background: rgba(16, 185, 129, 0.12);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: var(--emerald);
      padding: 0.3rem 0.75rem;
      border-radius: 9999px;
      font-size: 0.8rem;
      font-weight: 600;
    }}
    .status-dot {{
      width: 8px;
      height: 8px;
      background: var(--emerald);
      border-radius: 50%;
      box-shadow: 0 0 6px var(--emerald);
      animation: pulse 2s infinite;
    }}
    @keyframes pulse {{
      0%, 100% {{ opacity: 1; transform: scale(1); }}
      50% {{ opacity: 0.4; transform: scale(0.85); }}
    }}

    .main-wrapper {{
      flex: 1;
      display: flex;
      flex-direction: column;
    }}

    #view-client {{
      max-width: 1040px;
      margin: 1.5rem auto;
      padding: 0 1.5rem;
      width: 100%;
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }}
    .client-hero {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: var(--radius);
      padding: 1.8rem;
      backdrop-filter: blur(10px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.3);
    }}
    .client-hero h2 {{
      font-size: 1.5rem;
      color: #fff;
      margin-bottom: 0.4rem;
    }}
    .client-hero p {{
      color: var(--text-muted);
      font-size: 0.95rem;
    }}
    .search-box {{
      margin-top: 1.2rem;
      display: flex;
      gap: 0.75rem;
      max-width: 650px;
    }}
    .input-text {{
      flex: 1;
      background: rgba(7, 13, 25, 0.8);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 0.7rem 1rem;
      color: #fff;
      font-size: 0.95rem;
      font-family: inherit;
      outline: none;
      transition: border-color 0.2s;
    }}
    .input-text:focus {{
      border-color: var(--primary);
      box-shadow: 0 0 8px var(--primary-glow);
    }}
    .btn {{
      background: var(--primary);
      color: #090e17;
      border: none;
      border-radius: 8px;
      padding: 0.7rem 1.4rem;
      font-weight: 700;
      font-family: inherit;
      font-size: 0.9rem;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      transition: all 0.2s;
    }}
    .btn:hover {{
      opacity: 0.92;
      transform: translateY(-1px);
    }}
    .btn-secondary {{
      background: rgba(255, 255, 255, 0.08);
      color: #fff;
    }}
    .btn-secondary:hover {{ background: rgba(255, 255, 255, 0.15); }}
    .btn-sm {{
      padding: 0.35rem 0.75rem;
      font-size: 0.8rem;
      border-radius: 6px;
    }}
    .demo-chips {{
      margin-top: 1rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      flex-wrap: wrap;
    }}
    .demo-chips span {{
      font-size: 0.8rem;
      color: var(--text-muted);
    }}
    .chip {{
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: var(--primary);
      border-radius: 9999px;
      padding: 0.25rem 0.7rem;
      font-size: 0.8rem;
      cursor: pointer;
      font-family: inherit;
      transition: all 0.2s;
    }}
    .chip:hover {{
      background: rgba(56, 189, 248, 0.15);
      border-color: var(--primary);
    }}

    .profile-card {{
      background: var(--card-bg);
      border: 1px solid rgba(56, 189, 248, 0.3);
      border-radius: var(--radius);
      padding: 1.2rem 1.5rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 4px 16px rgba(0,0,0,0.2);
    }}
    .profile-info {{
      display: flex;
      align-items: center;
      gap: 1rem;
    }}
    .avatar {{
      width: 44px;
      height: 44px;
      background: linear-gradient(135deg, var(--indigo), var(--primary));
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.3rem;
      color: #fff;
    }}

    .client-grid {{
      display: grid;
      grid-template-columns: 1fr 1.3fr;
      gap: 1.5rem;
    }}
    @media (max-width: 850px) {{
      .client-grid {{ grid-template-columns: 1fr; }}
    }}
    .panel-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: var(--radius);
      padding: 1.4rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }}
    .panel-card h3 {{
      font-size: 1.15rem;
      color: #fff;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .veh-item, .turno-item {{
      background: rgba(10, 16, 30, 0.6);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 0.9rem 1rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      transition: border-color 0.2s;
    }}
    .veh-item:hover, .turno-item:hover {{
      border-color: rgba(56, 189, 248, 0.3);
    }}
    .patente-badge {{
      background: #000;
      color: #fff;
      border: 1px solid rgba(255, 255, 255, 0.4);
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      font-family: monospace;
      font-weight: 700;
      font-size: 0.85rem;
      letter-spacing: 1px;
    }}
    .status-badge {{
      padding: 0.25rem 0.6rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .badge-pendiente {{ background: rgba(245, 158, 11, 0.15); color: var(--amber); border: 1px solid rgba(245, 158, 11, 0.3); }}
    .badge-confirmado {{ background: rgba(56, 189, 248, 0.15); color: var(--primary); border: 1px solid rgba(56, 189, 248, 0.3); }}
    .badge-en_taller {{ background: rgba(99, 102, 241, 0.2); color: #818cf8; border: 1px solid rgba(99, 102, 241, 0.4); }}
    .badge-completado {{ background: rgba(16, 185, 129, 0.15); color: var(--emerald); border: 1px solid rgba(16, 185, 129, 0.3); }}
    .badge-cancelado {{ background: rgba(244, 63, 94, 0.15); color: var(--rose); border: 1px solid rgba(244, 63, 94, 0.3); }}

    #view-admin {{
      display: none;
      flex: 1;
      min-height: calc(100vh - 65px);
    }}
    .admin-layout {{
      display: flex;
      width: 100%;
    }}
    .sidebar {{
      width: 250px;
      background: var(--sidebar-bg);
      border-right: 1px solid var(--card-border);
      padding: 1.5rem 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }}
    .sidebar-title {{
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: var(--text-muted);
      margin-bottom: 0.5rem;
      padding-left: 0.5rem;
    }}
    .nav-item {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.7rem 1rem;
      border-radius: 8px;
      color: var(--text-muted);
      text-decoration: none;
      font-weight: 600;
      font-size: 0.9rem;
      cursor: pointer;
      transition: all 0.2s;
    }}
    .nav-item:hover {{
      background: rgba(255, 255, 255, 0.04);
      color: #fff;
    }}
    .nav-item.active {{
      background: rgba(56, 189, 248, 0.12);
      color: var(--primary);
      border-left: 3px solid var(--primary);
    }}
    .nav-badge {{
      margin-left: auto;
      background: var(--amber);
      color: #000;
      padding: 0.1rem 0.45rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 700;
    }}
    .admin-content {{
      flex: 1;
      padding: 1.8rem;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }}
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 1rem;
    }}
    .kpi-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: var(--radius);
      padding: 1.2rem;
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
    }}
    .kpi-label {{
      font-size: 0.8rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .kpi-val {{
      font-size: 1.9rem;
      font-weight: 700;
      color: #fff;
    }}

    .table-container {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: var(--radius);
      overflow: hidden;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 0.9rem;
    }}
    th {{
      background: rgba(10, 16, 30, 0.8);
      color: var(--text-muted);
      padding: 0.85rem 1rem;
      font-weight: 600;
      border-bottom: 1px solid var(--card-border);
      text-transform: uppercase;
      font-size: 0.75rem;
      letter-spacing: 0.5px;
    }}
    td {{
      padding: 0.9rem 1rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
      color: #e2e8f0;
    }}
    tr:hover td {{
      background: rgba(255, 255, 255, 0.02);
    }}
    .action-group {{
      display: flex;
      gap: 0.4rem;
    }}

    .form-row {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 0.8rem;
    }}
    .form-group {{
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
    }}
    .form-group label {{
      font-size: 0.8rem;
      color: var(--text-muted);
      font-weight: 600;
    }}
    select.input-text {{
      background-color: #0b1120;
    }}

    .toast {{
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #1e293b;
      border: 1px solid var(--primary);
      color: #fff;
      padding: 0.8rem 1.4rem;
      border-radius: 8px;
      box-shadow: 0 10px 25px rgba(0,0,0,0.5);
      z-index: 100;
      display: none;
      animation: fadeIn 0.3s;
    }}
    @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <span class="brand-icon">🔧</span>
      <div>
        <div class="brand-title">AutoFix <span class="brand-badge">__APP_NAME__</span></div>
      </div>
    </div>

    <div class="mode-switch">
      <button id="tab-client" class="mode-btn active" onclick="switchView('client')">
        👤 Portal de Clientes
      </button>
      <button id="tab-admin" class="mode-btn" onclick="switchView('admin')">
        🛠️ Panel Administrativo
      </button>
    </div>

    <div class="status-pill">
      <div class="status-dot"></div>
      <span>Taller En Línea :__PORT__</span>
    </div>
  </header>

  <div class="main-wrapper">
    <!-- PARTE 1: PORTAL DE CLIENTES -->
    <section id="view-client">
      <div class="client-hero">
        <h2>🔑 Identificación de Clientes</h2>
        <p>Ingresa tu DNI o número de teléfono registrado para consultar tus vehículos, estado de trabajos o agendar un nuevo turno.</p>

        <div class="search-box">
          <input type="text" id="dni-input" class="input-text" placeholder="Ej: 30123456 o +54 11 4455-6677" value="30123456">
          <button class="btn" onclick="buscarCliente()">🔍 Ingresar</button>
        </div>

        <div class="demo-chips">
          <span>Accesos rápidos de prueba:</span>
          <button class="chip" onclick="quickLogin('30123456')">Carlos Gómez (30123456)</button>
          <button class="chip" onclick="quickLogin('28987654')">Ana Martínez (28987654)</button>
          <button class="chip" onclick="quickLogin('33456789')">Roberto Díaz (33456789)</button>
        </div>
      </div>

      <div id="client-dashboard" style="display:none; flex-direction:column; gap:1.5rem;">
        <div class="profile-card">
          <div class="profile-info">
            <div class="avatar">👤</div>
            <div>
              <h3 id="cli-name" style="font-size:1.2rem; color:#fff;">--</h3>
              <p id="cli-meta" style="color:var(--text-muted); font-size:0.85rem;">DNI: -- | Tel: --</p>
            </div>
          </div>
          <button class="btn btn-secondary btn-sm" onclick="cerrarSesionCliente()">Cambiar Cliente</button>
        </div>

        <div class="client-grid">
          <div class="panel-card">
            <h3>
              <span>🚗 Mis Vehículos Registrados</span>
              <button class="btn btn-secondary btn-sm" onclick="toggleFormVehiculo()">+ Agregar Auto</button>
            </h3>

            <div id="form-nuevo-vehiculo" style="display:none; background:rgba(7,13,25,0.7); padding:1rem; border-radius:8px; border:1px solid var(--card-border);">
              <h4 style="font-size:0.9rem; margin-bottom:0.6rem; color:var(--primary);">Registrar Vehículo</h4>
              <div class="form-row">
                <input type="text" id="nv-patente" class="input-text" placeholder="Patente (Ej: AF 999 ZY)">
                <input type="text" id="nv-marca" class="input-text" placeholder="Marca (Ej: Toyota)">
                <input type="text" id="nv-modelo" class="input-text" placeholder="Modelo (Ej: Corolla)">
                <input type="number" id="nv-anio" class="input-text" placeholder="Año" value="2022">
              </div>
              <button class="btn btn-sm" style="margin-top:0.6rem;" onclick="guardarVehiculoCliente()">Guardar Vehículo</button>
            </div>

            <div id="lista-vehiculos-cliente" style="display:flex; flex-direction:column; gap:0.6rem;"></div>
          </div>

          <div class="panel-card">
            <h3>
              <span>📅 Mis Turnos y Reparaciones</span>
            </h3>
            <div id="lista-turnos-cliente" style="display:flex; flex-direction:column; gap:0.6rem;"></div>
          </div>
        </div>

        <div class="panel-card">
          <h3>📝 Solicitar Nuevo Turno en el Taller</h3>
          <div class="form-row">
            <div class="form-group">
              <label>Selecciona tu Vehículo:</label>
              <select id="nt-vehiculo" class="input-text"></select>
            </div>
            <div class="form-group">
              <label>Servicio Requerido:</label>
              <select id="nt-servicio" class="input-text"></select>
            </div>
            <div class="form-group">
              <label>Fecha Estimada:</label>
              <input type="date" id="nt-fecha" class="input-text">
            </div>
            <div class="form-group">
              <label>Horario:</label>
              <select id="nt-hora" class="input-text">
                <option value="08:30">08:30 hs</option>
                <option value="10:00">10:00 hs</option>
                <option value="11:30">11:30 hs</option>
                <option value="14:00">14:00 hs</option>
                <option value="16:00">16:00 hs</option>
              </select>
            </div>
          </div>
          <div class="form-group" style="margin-top:0.6rem;">
            <label>Descripción / Síntomas observados:</label>
            <input type="text" id="nt-notas" class="input-text" placeholder="Ej: Ruidos en frenos al detenerse o revisión periódica">
          </div>
          <div style="display:flex; justify-content:flex-end; margin-top:0.8rem;">
            <button class="btn" onclick="crearTurnoCliente()">📅 Confirmar Solicitud de Turno</button>
          </div>
        </div>
      </div>
    </section>

    <!-- PARTE 2: PANEL ADMINISTRATIVO -->
    <section id="view-admin">
      <div class="admin-layout">
        <aside class="sidebar">
          <div class="sidebar-title">Navegación Taller</div>
          <div class="nav-item active" onclick="showAdminTab('dashboard', this)">
            <span>📊</span> Dashboard & KPIs
          </div>
          <div class="nav-item" onclick="showAdminTab('turnos', this)">
            <span>📅</span> Gestión de Turnos
            <span class="nav-badge" id="badge-turnos-pend">0</span>
          </div>
          <div class="nav-item" onclick="showAdminTab('clientes', this)">
            <span>👥</span> Cartera Clientes
          </div>
          <div class="nav-item" onclick="showAdminTab('vehiculos', this)">
            <span>🚗</span> Vehículos
          </div>
          <div class="nav-item" onclick="showAdminTab('servicios', this)">
            <span>🔧</span> Servicios
          </div>
        </aside>

        <main class="admin-content">
          <div id="admin-sec-dashboard" class="admin-tab-sec">
            <h2 style="margin-bottom:1rem; font-size:1.4rem;">📊 Resumen Operativo del Taller</h2>
            <div class="kpi-grid">
              <div class="kpi-card" style="border-left:4px solid var(--primary);">
                <span class="kpi-label">Turnos Totales</span>
                <span class="kpi-val" id="kpi-total">0</span>
              </div>
              <div class="kpi-card" style="border-left:4px solid #818cf8;">
                <span class="kpi-label">En Taller Ahora</span>
                <span class="kpi-val" id="kpi-taller">0</span>
              </div>
              <div class="kpi-card" style="border-left:4px solid var(--amber);">
                <span class="kpi-label">Pendientes de Aprobación</span>
                <span class="kpi-val" id="kpi-pend">0</span>
              </div>
              <div class="kpi-card" style="border-left:4px solid var(--emerald);">
                <span class="kpi-label">Clientes Registrados</span>
                <span class="kpi-val" id="kpi-cli">0</span>
              </div>
            </div>

            <div style="margin-top:2rem;">
              <h3 style="margin-bottom:0.8rem; font-size:1.1rem;">⚡ Turnos en Taller y Prioritarios</h3>
              <div class="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Cliente</th>
                      <th>Vehículo</th>
                      <th>Servicio</th>
                      <th>Fecha / Hora</th>
                      <th>Estado</th>
                      <th>Acción Rápida</th>
                    </tr>
                  </thead>
                  <tbody id="tb-dashboard-turnos"></tbody>
                </table>
              </div>
            </div>
          </div>

          <div id="admin-sec-turnos" class="admin-tab-sec" style="display:none;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
              <h2 style="font-size:1.4rem;">📅 Agenda Completa de Turnos</h2>
              <div style="display:flex; gap:0.4rem;">
                <button class="btn btn-secondary btn-sm" onclick="filtrarTurnosAdmin('todos')">Todos</button>
                <button class="btn btn-secondary btn-sm" onclick="filtrarTurnosAdmin('pendiente')">Pendientes</button>
                <button class="btn btn-secondary btn-sm" onclick="filtrarTurnosAdmin('en_taller')">En Taller</button>
                <button class="btn btn-secondary btn-sm" onclick="filtrarTurnosAdmin('completado')">Completados</button>
              </div>
            </div>

            <div class="table-container">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Cliente</th>
                    <th>Vehículo</th>
                    <th>Servicio</th>
                    <th>Fecha / Hora</th>
                    <th>Estado</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody id="tb-admin-turnos"></tbody>
              </table>
            </div>
          </div>

          <div id="admin-sec-clientes" class="admin-tab-sec" style="display:none;">
            <h2 style="margin-bottom:1rem; font-size:1.4rem;">👥 Cartera de Clientes</h2>
            <div class="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Nombre y Apellido</th>
                    <th>DNI</th>
                    <th>Teléfono</th>
                    <th>Email</th>
                    <th>Fecha Registro</th>
                  </tr>
                </thead>
                <tbody id="tb-admin-clientes"></tbody>
              </table>
            </div>
          </div>

          <div id="admin-sec-vehiculos" class="admin-tab-sec" style="display:none;">
            <h2 style="margin-bottom:1rem; font-size:1.4rem;">🚗 Parque de Vehículos Registrados</h2>
            <div class="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Patente</th>
                    <th>Marca y Modelo</th>
                    <th>Año</th>
                    <th>Cliente ID</th>
                  </tr>
                </thead>
                <tbody id="tb-admin-vehiculos"></tbody>
              </table>
            </div>
          </div>

          <div id="admin-sec-servicios" class="admin-tab-sec" style="display:none;">
            <h2 style="margin-bottom:1rem; font-size:1.4rem;">🔧 Catálogo de Servicios del Taller</h2>
            <div id="grid-admin-servicios" style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:1rem;"></div>
          </div>
        </main>
      </div>
    </section>
  </div>

  <div id="toast" class="toast">Acción completada exitosamente</div>

  <script>
    let clienteActual = null;
    let serviciosCatalogo = [];

    function showToast(msg) {{
      const t = document.getElementById('toast');
      t.innerText = msg;
      t.style.display = 'block';
      setTimeout(() => {{ t.style.display = 'none'; }}, 3000);
    }}

    function switchView(view) {{
      document.getElementById('view-client').style.display = (view === 'client') ? 'flex' : 'none';
      document.getElementById('view-admin').style.display = (view === 'admin') ? 'flex' : 'none';
      document.getElementById('tab-client').classList.toggle('active', view === 'client');
      document.getElementById('tab-admin').classList.toggle('active', view === 'admin');
      if (view === 'admin') {{
        cargarAdminData();
      }}
    }}

    async function quickLogin(dni) {{
      document.getElementById('dni-input').value = dni;
      await buscarCliente();
    }}

    async function buscarCliente() {{
      const val = document.getElementById('dni-input').value.trim();
      if (!val) return;
      try {{
        const res = await fetch(`/api/v1/buscar-cliente?query=${{encodeURIComponent(val)}}`);
        const data = await res.json();
        if (data.success && data.data) {{
          clienteActual = data.data.cliente;
          renderClientDashboard(data.data);
          document.getElementById('client-dashboard').style.display = 'flex';
          showToast(`¡Bienvenido/a ${{clienteActual.nombre}}!`);
        }} else {{
          alert('Cliente no encontrado. Puedes registrarte o probar con los clientes de prueba.');
        }}
      }} catch (e) {{
        console.error(e);
        alert('Error al consultar cliente: ' + e);
      }}
    }}

    function renderClientDashboard(data) {{
      document.getElementById('cli-name').innerText = data.cliente.nombre;
      document.getElementById('cli-meta').innerText = `DNI: ${{data.cliente.dni}} | Tel: ${{data.cliente.telefono}} | ${{data.cliente.email || ''}}`;

      const lv = document.getElementById('lista-vehiculos-cliente');
      const selVeh = document.getElementById('nt-vehiculo');
      lv.innerHTML = '';
      selVeh.innerHTML = '';
      (data.vehiculos || []).forEach(v => {{
        lv.innerHTML += `
          <div class="veh-item">
            <div>
              <div style="font-weight:700; color:#fff;">${{v.marca}} ${{v.modelo}} (${{v.anio}})</div>
              <div style="color:var(--text-muted); font-size:0.8rem; margin-top:2px;">Registrado el ${{v.created_at.split('T')[0]}}</div>
            </div>
            <span class="patente-badge">${{v.patente}}</span>
          </div>`;
        selVeh.innerHTML += `<option value="${{v.id}}">${{v.marca}} ${{v.modelo}} - [${{v.patente}}]</option>`;
      }});

      const lt = document.getElementById('lista-turnos-cliente');
      lt.innerHTML = '';
      if (!data.turnos || data.turnos.length === 0) {{
        lt.innerHTML = '<div style="color:var(--text-muted); font-size:0.9rem; padding:1rem; text-align:center;">No tienes turnos registrados actualmente.</div>';
      }} else {{
        data.turnos.forEach(t => {{
          lt.innerHTML += `
            <div class="turno-item">
              <div>
                <div style="font-weight:700; color:#fff;">${{t.servicio_nombre}}</div>
                <div style="color:var(--text-muted); font-size:0.85rem; margin-top:2px;">🚗 ${{t.vehiculo_desc}} (${{t.vehiculo_patente}})</div>
                <div style="color:var(--primary); font-size:0.8rem; margin-top:4px;">📅 ${{t.fecha}} - ${{t.hora}} hs</div>
                ${{t.notas ? `<div style="color:#94a3b8; font-size:0.8rem; font-style:italic; margin-top:2px;">"${{t.notas}}"</div>` : ''}}
              </div>
              <span class="status-badge badge-${{t.estado}}">${{t.estado.replace('_', ' ')}}</span>
            </div>`;
        }});
      }}

      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      document.getElementById('nt-fecha').value = tomorrow.toISOString().split('T')[0];
    }}

    function cerrarSesionCliente() {{
      clienteActual = null;
      document.getElementById('client-dashboard').style.display = 'none';
      document.getElementById('dni-input').value = '';
    }}

    function toggleFormVehiculo() {{
      const f = document.getElementById('form-nuevo-vehiculo');
      f.style.display = (f.style.display === 'none') ? 'block' : 'none';
    }}

    async function guardarVehiculoCliente() {{
      if (!clienteActual) return;
      const pat = document.getElementById('nv-patente').value.trim();
      const mar = document.getElementById('nv-marca').value.trim();
      const mod = document.getElementById('nv-modelo').value.trim();
      const anio = parseInt(document.getElementById('nv-anio').value) || 2022;
      if (!pat || !mar || !mod) {{
        alert('Por favor completa patente, marca y modelo.');
        return;
      }}
      try {{
        const res = await fetch('/api/v1/vehiculos', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ cliente_id: clienteActual.id, patente: pat, marca: mar, modelo: mod, anio }})
        }});
        const d = await res.json();
        if (d.success) {{
          showToast('¡Vehículo registrado con éxito!');
          document.getElementById('form-nuevo-vehiculo').style.display = 'none';
          document.getElementById('nv-patente').value = '';
          document.getElementById('nv-marca').value = '';
          document.getElementById('nv-modelo').value = '';
          await buscarCliente();
        }} else {{
          alert('Error: ' + JSON.stringify(d));
        }}
      }} catch (e) {{ alert('Error: ' + e); }}
    }}

    async function crearTurnoCliente() {{
      if (!clienteActual) return;
      const vehId = document.getElementById('nt-vehiculo').value;
      const srvId = document.getElementById('nt-servicio').value;
      const fecha = document.getElementById('nt-fecha').value;
      const hora = document.getElementById('nt-hora').value;
      const notas = document.getElementById('nt-notas').value.trim();

      if (!vehId || !srvId || !fecha || !hora) {{
        alert('Por favor selecciona vehículo, servicio y fecha.');
        return;
      }}

      try {{
        const res = await fetch('/api/v1/turnos', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ cliente_id: clienteActual.id, vehiculo_id: vehId, servicio_id: srvId, fecha, hora, notas }})
        }});
        const d = await res.json();
        if (d.success) {{
          showToast('🎉 ¡Turno agendado exitosamente!');
          document.getElementById('nt-notas').value = '';
          await buscarCliente();
        }} else {{
          alert('Error: ' + JSON.stringify(d));
        }}
      }} catch (e) {{ alert('Error: ' + e); }}
    }}

    function showAdminTab(tabName, el) {{
      document.querySelectorAll('.admin-tab-sec').forEach(s => s.style.display = 'none');
      document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
      document.getElementById('admin-sec-' + tabName).style.display = 'block';
      if (el) el.classList.add('active');
    }}

    async function cargarAdminData() {{
      try {{
        const [mRes, tRes, cRes, vRes, sRes] = await Promise.all([
          fetch('/api/v1/metricas').then(r => r.json()),
          fetch('/api/v1/turnos').then(r => r.json()),
          fetch('/api/v1/clientes').then(r => r.json()),
          fetch('/api/v1/vehiculos').then(r => r.json()),
          fetch('/api/v1/servicios').then(r => r.json())
        ]);

        if (mRes.success) {{
          const m = mRes.data;
          document.getElementById('kpi-total').innerText = m.turnos_total || 0;
          document.getElementById('kpi-taller').innerText = m.turnos_en_taller || 0;
          document.getElementById('kpi-pend').innerText = m.turnos_pendientes || 0;
          document.getElementById('kpi-cli').innerText = m.clientes_total || 0;
          document.getElementById('badge-turnos-pend').innerText = m.turnos_pendientes || 0;
        }}

        const tbd = document.getElementById('tb-dashboard-turnos');
        tbd.innerHTML = '';
        (tRes.data || []).slice(0, 5).forEach(t => {{
          tbd.innerHTML += `
            <tr>
              <td><strong>${{t.cliente_nombre}}</strong></td>
              <td>${{t.vehiculo_desc}} <span class="patente-badge">${{t.vehiculo_patente}}</span></td>
              <td>${{t.servicio_nombre}}</td>
              <td>${{t.fecha}} ${{t.hora}} hs</td>
              <td><span class="status-badge badge-${{t.estado}}">${{t.estado.replace('_', ' ')}}</span></td>
              <td>
                <div class="action-group">
                  ${{t.estado === 'pendiente' ? `<button class="btn btn-sm" onclick="cambiarEstadoTurno('${{t.id}}', 'en_taller')">⚙️ A Taller</button>` : ''}}
                  ${{t.estado === 'en_taller' ? `<button class="btn btn-sm" style="background:var(--emerald); color:#fff;" onclick="cambiarEstadoTurno('${{t.id}}', 'completado')">✅ Finalizar</button>` : ''}}
                  ${{t.estado === 'confirmado' ? `<button class="btn btn-sm" onclick="cambiarEstadoTurno('${{t.id}}', 'en_taller')">⚙️ A Taller</button>` : ''}}
                </div>
              </td>
            </tr>`;
        }});

        renderTurnosAdmin(tRes.data || []);

        const tbc = document.getElementById('tb-admin-clientes');
        tbc.innerHTML = '';
        (cRes.data || []).forEach(c => {{
          tbc.innerHTML += `
            <tr>
              <td><strong>${{c.nombre}}</strong></td>
              <td><code>${{c.dni}}</code></td>
              <td>${{c.telefono}}</td>
              <td>${{c.email || '--'}}</td>
              <td>${{c.created_at.split('T')[0]}}</td>
            </tr>`;
        }});

        const tbv = document.getElementById('tb-admin-vehiculos');
        tbv.innerHTML = '';
        (vRes.data || []).forEach(v => {{
          tbv.innerHTML += `
            <tr>
              <td><span class="patente-badge">${{v.patente}}</span></td>
              <td><strong>${{v.marca}} ${{v.modelo}}</strong></td>
              <td>${{v.anio}}</td>
              <td><code>${{v.cliente_id}}</code></td>
            </tr>`;
        }});

        serviciosCatalogo = sRes.data || [];
        const gs = document.getElementById('grid-admin-servicios');
        const selSrv = document.getElementById('nt-servicio');
        gs.innerHTML = '';
        selSrv.innerHTML = '';
        serviciosCatalogo.forEach(s => {{
          gs.innerHTML += `
            <div class="panel-card">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="status-badge" style="background:rgba(56,189,248,0.15); color:var(--primary);">${{s.categoria}}</span>
                <span style="font-weight:700; color:var(--emerald); font-size:1.1rem;">$ ${{s.precio.toLocaleString('es-AR')}}</span>
              </div>
              <h4 style="font-size:1.1rem; color:#fff;">${{s.nombre}}</h4>
              <p style="color:var(--text-muted); font-size:0.85rem; line-height:1.4;">${{s.descripcion}}</p>
              <div style="color:var(--primary); font-size:0.8rem; font-weight:600;">⏱️ Duración estimada: ${{s.duracion_min}} min</div>
            </div>`;
          selSrv.innerHTML += `<option value="${{s.id}}">${{s.nombre}} - $ ${{s.precio.toLocaleString('es-AR')}} (${{s.duracion_min}}m)</option>`;
        }});

      }} catch (e) {{ console.error('Error cargando admin data: ', e); }}
    }}

    function renderTurnosAdmin(turnos) {{
      const tb = document.getElementById('tb-admin-turnos');
      tb.innerHTML = '';
      turnos.forEach(t => {{
        tb.innerHTML += `
          <tr>
            <td><code>${{t.id}}</code></td>
            <td><strong>${{t.cliente_nombre}}</strong></td>
            <td>${{t.vehiculo_desc}} <span class="patente-badge">${{t.vehiculo_patente}}</span></td>
            <td>${{t.servicio_nombre}}</td>
            <td>${{t.fecha}} ${{t.hora}}</td>
            <td><span class="status-badge badge-${{t.estado}}">${{t.estado.replace('_', ' ')}}</span></td>
            <td>
              <div class="action-group">
                <button class="btn btn-secondary btn-sm" onclick="cambiarEstadoTurno('${{t.id}}', 'en_taller')">⚙️ Taller</button>
                <button class="btn btn-secondary btn-sm" onclick="cambiarEstadoTurno('${{t.id}}', 'completado')">✅ Listo</button>
                <button class="btn btn-secondary btn-sm" onclick="cambiarEstadoTurno('${{t.id}}', 'confirmado')">🔵 Conf</button>
                <button class="btn btn-secondary btn-sm" style="color:var(--rose);" onclick="cambiarEstadoTurno('${{t.id}}', 'cancelado')">❌</button>
              </div>
            </td>
          </tr>`;
      }});
    }}

    async function filtrarTurnosAdmin(estado) {{
      const url = (estado === 'todos') ? '/api/v1/turnos' : `/api/v1/turnos?estado=${{estado}}`;
      const res = await fetch(url).then(r => r.json());
      if (res.success) renderTurnosAdmin(res.data);
    }}

    async function cambiarEstadoTurno(id, nuevoEstado) {{
      try {{
        const res = await fetch(`/api/v1/turnos/${{id}}/estado`, {{
          method: 'PUT',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ estado: nuevoEstado }})
        }});
        const d = await res.json();
        if (d.success) {{
          showToast(`Turno actualizado a "${{nuevoEstado.replace('_', ' ')}}"`);
          cargarAdminData();
          if (clienteActual) buscarCliente();
        }} else {{
          alert('Error: ' + JSON.stringify(d));
        }}
      }} catch (e) {{ alert('Error: ' + e); }}
    }}

    window.addEventListener('DOMContentLoaded', () => {{
      fetch('/api/v1/servicios').then(r => r.json()).then(sRes => {{
        if (sRes.success) {{
          serviciosCatalogo = sRes.data || [];
          const selSrv = document.getElementById('nt-servicio');
          if (selSrv) {{
            selSrv.innerHTML = '';
            serviciosCatalogo.forEach(s => {{
              selSrv.innerHTML += `<option value="${{s.id}}">${{s.nombre}} - $ ${{s.precio.toLocaleString('es-AR')}} (${{s.duracion_min}}m)</option>`;
            }});
          }}
        }}
      }});
      quickLogin('30123456');
    }});
  </script>
</body>
</html>"""


class AppHTTPRequestHandler(BaseHTTPRequestHandler):
    api_handler: Optional[ApiHandler] = None
    app_name: str = "{pname}"
    server_port: int = 8000

    def _set_cors_headers(self, status: int = 200, content_type: str = "application/json"):
        self.send_response(status)
        self.send_header("Content-Type", f"{{content_type}}; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_cors_headers(204)

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/index.html"):
            html = HTML_TEMPLATE.replace("__APP_NAME__", self.app_name).replace("__PORT__", str(self.server_port))
            self._set_cors_headers(200, "text/html")
            self.wfile.write(html.encode("utf-8"))
            return

        if self.api_handler:
            code, resp = self.api_handler.handle_request("GET", self.path)
            self._set_cors_headers(code)
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode("utf-8"))
            return

        self._set_cors_headers(404)
        self.wfile.write(json.dumps({{"error": "Ruta no encontrada"}}).encode("utf-8"))

    def do_POST(self):
        clen = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(clen).decode("utf-8") if clen > 0 else "{{}}"
        try:
            payload = json.loads(body) if body.strip() else {{}}
        except Exception:
            payload = {{}}

        if self.api_handler:
            code, resp = self.api_handler.handle_request("POST", self.path, payload)
            self._set_cors_headers(code)
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode("utf-8"))
            return

        self._set_cors_headers(404)
        self.wfile.write(json.dumps({{"error": "Ruta POST no encontrada"}}).encode("utf-8"))

    def do_PUT(self):
        clen = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(clen).decode("utf-8") if clen > 0 else "{{}}"
        try:
            payload = json.loads(body) if body.strip() else {{}}
        except Exception:
            payload = {{}}

        if self.api_handler:
            code, resp = self.api_handler.handle_request("PUT", self.path, payload)
            self._set_cors_headers(code)
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode("utf-8"))
            return

        self._set_cors_headers(404)
        self.wfile.write(json.dumps({{"error": "Ruta PUT no encontrada"}}).encode("utf-8"))

    def do_DELETE(self):
        if self.api_handler:
            code, resp = self.api_handler.handle_request("DELETE", self.path)
            self._set_cors_headers(code)
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode("utf-8"))
            return

        self._set_cors_headers(404)
        self.wfile.write(json.dumps({{"error": "Ruta DELETE no encontrada"}}).encode("utf-8"))

    def log_message(self, format, *args):
        return


def start_server(port: int = 8000, host: str = "0.0.0.0", db_path: Optional[str] = None):
    db_file = db_path or str(BASE_DIR / "data.db")
    storage = StorageRepository(db_file)
    service = AppService(storage)
    api = ApiHandler(service)

    AppHTTPRequestHandler.api_handler = api
    AppHTTPRequestHandler.server_port = port
    AppHTTPRequestHandler.app_name = "{pname}"

    server = HTTPServer((host, port), AppHTTPRequestHandler)
    print(f" Servidor de {pname} iniciado en http://{{host}}:{{port}}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\\n🛑 Servidor detenido.")
    finally:
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description=f"Servidor HTTP de {pname}")
    parser.add_argument("--port", type=int, default=8000, help="Puerto HTTP")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host")
    parser.add_argument("--db", type=str, default=None, help="Ruta SQLite3")
    parser.add_argument("--check", action="store_true", help="Smoke test")
    args = parser.parse_args()

    if args.check:
        print(f"Smoke test OK para {pname}")
        sys.exit(0)

    start_server(port=args.port, host=args.host, db_path=args.db)


if __name__ == "__main__":
    main()
'''
    (ws_dir / "main.py").write_text(main_code, encoding="utf-8")

    return [
        "app/__init__.py",
        "app/models.py",
        "app/storage.py",
        "app/service.py",
        "app/api.py",
        "main.py",
        "tests/__init__.py",
        "tests/test_models.py",
        "tests/test_storage.py",
        "tests/test_service.py",
    ]
