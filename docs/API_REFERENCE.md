# Referencia de API Interna

## Índice

1. [Módulos de Datos](#módulos-de-datos)
2. [Módulos de Backend](#módulos-de-backend)
3. [Módulos de UI](#módulos-de-ui)
4. [Módulos de Configuración](#módulos-de-configuración)
5. [Módulos de Migración](#módulos-de-migración)

---

## Módulos de Datos

### `modbuspython.data_access.modbus_connection`

Gestiona la conexión Modbus TCP con reintentos.

```python
class ModbusConnection:
    def __init__(self, host: str, port: int, timeout: float, retry_strategy: RetryStrategy)
    def connect(self) -> ModbusTcpClient
    def disconnect(self, client: ModbusTcpClient) -> None
    def is_connected(self, client: Optional[ModbusTcpClient]) -> bool
```

**Ejemplo de uso:**
```python
from modbuspython.data_access.modbus_connection import ModbusConnection
from modbuspython.data_access.retry_strategy import RetryStrategy

retry = RetryStrategy(max_attempts=3, base_delay=1.0)
conn = ModbusConnection("192.168.1.100", 502, 5.0, retry)
client = conn.connect()
```

---

### `modbuspython.data_access.modbus_reader`

Lee datos de registros Modbus con lógica de reintento.

```python
class ModbusReader:
    def __init__(self, connection: ModbusConnection, repository: IrradianceRepository)
    def read_irradiance(self, register: int) -> float
    def read_register(self, client: ModbusTcpClient, register: int) -> int
```

**Ejemplo de uso:**
```python
from modbuspython.data_access.modbus_reader import ModbusReader

reader = ModbusReader(conn, repo)
irradiance = reader.read_irradiance(register=4)  # Returns value / 100
```

---

### `modbuspython.data_access.modbus_writer`

Escribe valores en registros Modbus con estado seguro.

```python
class ModbusWriter:
    def __init__(self, connection: ModbusConnection, angle_manager: AngleStateManager)
    def write_setpoints(self, client: ModbusTcpClient, rotation: float, elevation: float) -> bool
    def write_register(self, client: ModbusTcpClient, register: int, value: int) -> bool
    def enter_safe_state(self) -> None
    def exit_safe_state(self) -> None
    def is_safe_state(self) -> bool
```

**Ejemplo de uso:**
```python
from modbuspython.data_access.modbus_writer import ModbusWriter

writer = ModbusWriter(conn, angle_mgr)
writer.write_setpoints(client, rotation=180.0, elevation=45.0)
```

---

### `modbuspython.data_access.modbus_client`

Cliente Modbus principal (QThread) que orquesta conexión, lectura y escritura.

```python
class ModbusClient(QThread):
    # Señales
    radiacion_actualizada = pyqtSignal(float)
    conexion_cambiada = pyqtSignal(bool)
    log = pyqtSignal(str, str)
    retry_exhausted = pyqtSignal(str)

    def __init__(self, config: dict)
    def run(self) -> None
    def stop(self) -> None
    def set_angles(self, rotation: float, elevation: float) -> None
```

**Conexión de señales:**
```python
client = ModbusClient(config)
client.radiacion_actualizada.connect(self.update_gauge)
client.conexion_cambiada.connect(self.update_connection_status)
client.start()
```

---

### `modbuspython.data_access.connection_pool`

Pool de conexiones SQLite thread-safe.

```python
class ConnectionPool:
    def __init__(self, db_path: str, max_connections: int = 5)
    def get_connection(self) -> sqlite3.Connection
    def release_connection(self, conn: sqlite3.Connection) -> None
    def close_all(self) -> None
    def get_stats(self) -> dict
```

**Uso con context manager:**
```python
from modbuspython.data_access.connection_pool import ConnectionPool

pool = ConnectionPool("data/solarsense.db", max_connections=5)
with pool.get_connection() as conn:
    cursor = conn.execute("SELECT * FROM measurements")
```

---

### `modbuspython.data_access.repositories.base`

Clase base para el patrón Repository.

```python
class BaseRepository:
    def __init__(self, pool: ConnectionPool)
    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor
    def executemany(self, query: str, params_list: list) -> None
    def fetchone(self, query: str, params: tuple = ()) -> Optional[tuple]
    def fetchall(self, query: str, params: tuple = ()) -> list
```

---

### `modbuspython.data_access.repositories.irradiance`

Acceso a datos de irradiación.

```python
class IrradianceRepository(BaseRepository):
    def insert_measurement(self, timestamp: str, irradiance: float, rotation: float, elevation: float) -> None
    def get_latest(self) -> Optional[dict]
    def get_history(self, limit: int = 100) -> list
    def get_by_date_range(self, start: str, end: str) -> list
    def get_average(self, start: str, end: str) -> float
```

---

### `modbuspython.data_access.repositories.schema_version`

Gestión de versiones de esquema.

```python
class SchemaVersionRepository(BaseRepository):
    def get_current_version(self) -> int
    def set_version(self, version: int) -> None
    def ensure_schema_table(self) -> None
```

---

### `modbuspython.data_access.retry_strategy`

Estrategia de reintentos con backoff exponencial.

```python
class RetryStrategy:
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0, max_delay: float = 30.0)
    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any
    def get_delay(self, attempt: int) -> float
```

---

### `modbuspython.data_access.logging_service`

Servicio de logging centralizado con rotación y filtro de datos sensibles.

```python
class LoggingService:
    def __init__(self, log_file: str = "logs/solarsense.log", level: str = "INFO", max_bytes: int = 10485760, backup_count: int = 5)
    def get_logger(self, name: str) -> logging.Logger
    def set_level(self, level: str) -> None
    def add_sensitive_key(self, key: str) -> None
```

---

## Módulos de Backend

### `modbuspython.backend.angle_state_manager`

Gestiona el estado de ángulos y modos del tracker solar.

```python
class AngleStateManager(QObject):
    # Señales
    angles_changed = pyqtSignal(float, float)

    def __init__(self, config: dict)
    def set_mode(self, mode: str) -> None  # "auto" o "manual"
    def get_mode(self) -> str
    def set_angles(self, rotation: float, elevation: float) -> None
    def get_angles(self) -> dict
    def is_auto_mode(self) -> bool
```

---

### `modbuspython.backend.solar_calcs`

Cálculos de posición solar.

```python
def calculate_hra(lat: float, lon: float, timezone: int) -> float
def calculate_declination(day_of_year: int) -> float
def calculate_altitude(lat: float, declination: float, hra: float) -> float
def calculate_azimuth(lat: float, declination: float, hra: float) -> float
def calculate_solar_angles(lat: float, lon: float, timezone: int) -> dict
```

**Ejemplo de uso:**
```python
from modbuspython.backend.solar_calcs import calculate_solar_angles

angles = calculate_solar_angles(lat=19.4326, lon=-99.1332, timezone=-6)
# Returns: {"hra": ..., "declination": ..., "altitude": ..., "azimuth": ...}
```

---

### `modbuspython.backend.validation_service`

Validación y sanitización de entrada de usuario.

```python
class ValidationService:
    def validate_ip(self, ip: str) -> bool
    def validate_port(self, port: int) -> bool
    def validate_angle(self, angle: float, min_angle: float, max_angle: float) -> bool
    def validate_coordinates(self, lat: float, lon: float) -> bool
    def sanitize_string(self, value: str) -> str
```

---

## Módulos de Configuración

### `modbuspython.config.config_manager`

Gestor de configuración singleton.

```python
class ConfigurationManager:
    def __init__(self, config_path: str = "config.yaml")
    def get(self, key: str, default: Any = None) -> Any
    def set(self, key: str, value: Any) -> None
    def reload(self) -> None
    def validate(self) -> bool
```

**Acceso a secciones:**
```python
config = ConfigurationManager()
host = config.get("modbus.host")
port = config.get("modbus.port", 502)
modbus_config = config.modbus_config
db_config = config.database_config
```

---

### `modbuspython.config.credential_encryptor`

Cifrado de credenciales usando Fernet.

```python
class CredentialEncryptor:
    def __init__(self, key: Optional[bytes] = None)
    def encrypt(self, plaintext: str) -> str
    def decrypt(self, ciphertext: str) -> str
    def generate_key(self) -> bytes
```

---

## Módulos de UI

### `modbuspython.ui.monitor_tab`

Tab de monitor con gauges circulares y gráficos.

```python
class MonitorTab(QWidget):
    def __init__(self, modbus_client: ModbusClient, config: ConfigurationManager)
    def update_radiation(self, value: float) -> None
    def update_connection_status(self, connected: bool) -> None
    def add_chart_point(self, timestamp: str, value: float) -> None
```

---

### `modbuspython.ui.location_setup_tab`

Tab de ubicación con mapa y búsqueda geocoding.

```python
class LocationSetupTab(QWidget):
    def __init__(self, config: ConfigurationManager)
    def set_coordinates(self, lat: float, lon: float) -> None
    def get_coordinates(self) -> dict
    def search_location(self, query: str) -> None
```

---

### `modbuspython.ui.solar_tracker_tab`

Tab de rastreo solar automático.

```python
class SolarTrackerTab(QWidget):
    def __init__(self, config: ConfigurationManager, angle_manager: AngleStateManager)
    def update_solar_angles(self, angles: dict) -> None
    def set_coordinates(self, lat: float, lon: float) -> None
    def calculate_and_display(self) -> None
```

---

### `modbuspython.ui.manual_control_panel`

Panel de control manual de ángulos con visor 3D.

```python
class ManualControlPanel(QWidget):
    def __init__(self, config: ConfigurationManager, modbus_client: ModbusClient)
    def set_angles(self, rotation: float, elevation: float) -> None
    def update_3d_viewer(self, rotation: float, elevation: float) -> None
    def validate_and_send(self) -> None
```

---

## Módulos de Migración

### `modbuspython.migrations.migration_manager`

Gestor de migraciones de base de datos.

```python
class MigrationManager:
    def __init__(self, db_path: str, migrations_dir: str = "migrations/versions")
    def run_migrations(self) -> None
    def get_current_version(self) -> int
    def get_available_migrations(self) -> list
    def migrate_to(self, target_version: int) -> None
    def rollback(self, target_version: int) -> None
```

---

## Excepciones

### Jerarquía de Excepciones

```python
class SolarSenseException(Exception)
class ConfigurationError(SolarSenseException)
class ValidationError(SolarSenseException)
class ModbusConnectionError(SolarSenseException)
class ModbusOperationError(SolarSenseException)
class DatabaseError(SolarSenseException)
class MigrationError(SolarSenseException)
```

**Uso:**
```python
from modbuspython.exceptions import ModbusConnectionError

try:
    client = connect_modbus(host, port)
except ModbusConnectionError as e:
    logger.error(f"Failed to connect: {e}")
```

---

## Diagrama de Dependencias

```
ui/ → backend/ → data_access/
  ↓       ↓           ↓
config/ ←─────────────┘
  ↓
migrations/ → data_access/
```

**Reglas:**
- UI nunca importa directamente de data_access
- Backend usa data_access para I/O
- Config es independiente
- Migraciones depende de data_access
