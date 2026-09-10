# Nexo Solar - Architecture Documentation

## Overview

Nexo Solar is a real-time solar and meteorological monitoring system. It reads irradiance through the existing Modbus TCP path, keeps geographic configuration through Leaflet.js, and adds a Davis WeatherLink parsing layer for weather station readings.

The station supported by this version has no movement motors. The active web UI and `WebBridge` do not expose mode switching, angle commands, motor setpoints, solar tracking, or the 3D movement viewer. Legacy movement modules remain in the repository only to avoid a high-risk deletion while older tests still import them.

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                      PRESENTATION                           │
│  ┌─────────────┐ ┌──────────────┐ ┌─────────────────────┐  │
│  │ MonitorTab  │ │LocationTabs  │ │ DiagnosticTab       │  │
│  │ (gauges,    │ │(map, solar   │ │ (logs, system       │  │
│  │  charts)    │ │ calc, 3D)    │ │  status)            │  │
│  └──────┬──────┘ └──────┬───────┘ └──────────┬──────────┘  │
│         │               │                     │             │
│  ┌──────▼───────────────▼─────────────────────▼──────────┐  │
│  │              MainWindow (QTabWidget)                  │  │
│  └──────────────────────┬────────────────────────────────┘  │
└─────────────────────────┼───────────────────────────────────┘
                          │ Signals/Slots
┌─────────────────────────▼───────────────────────────────────┐
│                       BUSINESS LOGIC                        │
│  ┌──────────────────┐  ┌─────────────────┐                 │
│  │AngleStateManager │  │ ValidationSvc   │                 │
│  │ (modes, angles,  │  │ (input sanit.,  │                 │
│  │  auto/manual)    │  │  range checks)  │                 │
│  └────────┬─────────┘  └────────┬────────┘                 │
│           │                     │                          │
│  ┌────────▼─────────┐  ┌────────▼────────┐                 │
│  │  SolarCalcs      │  │ ConfigurationManager             │
│  │ (HRA, declination│  │ (YAML/JSON, env │                 │
│  │  altitude, azimuth)│ │  vars, schema)  │                 │
│  └──────────────────┘  └─────────────────┘                 │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                     DATA ACCESS                             │
│  ┌──────────────────┐  ┌─────────────────┐  ┌───────────┐  │
│  │  ModbusClient    │  │ DatabaseManager │  │  Logging  │  │
│  │  (QThread)       │  │ (connection pool│  │  Service  │  │
│  │                  │  │  context mgr)   │  │           │  │
│  │ ┌──────────────┐ │  │                 │  │ ┌───────┐ │  │
│  │ │ModbusConnect │ │  │ ┌─────────────┐ │  │ │Sensitive│ │  │
│  │ │ModbusReader  │ │  │ │Repositories │ │  │ │Filter │ │  │
│  │ │ModbusWriter  │ │  │ └─────────────┘ │  │ └───────┘ │  │
│  │ └──────────────┘ │  └─────────────────┘  └───────────┘  │
│  │ ┌──────────────┐ │  ┌─────────────────┐                 │
│  │ │RetryStrategy │ │  │ MigrationManager│                 │
│  │ │(exp. backoff)│ │  │ (schema version)│                 │
│  │ └──────────────┘ │  └─────────────────┘                 │
│  └──────────────────┘                                     │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    EXTERNAL SYSTEMS                         │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ ESP8266     │  │ SQLite DB    │  │ OpenStreetMap    │   │
│  │ (Modbus TCP)│  │ (file-based) │  │ (tiles/Leaflet)  │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Layer Responsibilities

### 1. Presentation Layer (`modbuspython/ui/`)

Responsible for all user interface concerns. Contains PyQt6 widgets and QML/HTML views.

| Module | Responsibility |
|--------|---------------|
| `main_app.py` | Application entry point, main window, tab management |
| `monitor_tab.py` | Real-time irradiance display with circular gauges |
| `location_setup_tab.py` | Equipment location with map and geocoding search |
| `diagnostic_tab.py` | System diagnostics and log viewer |
| `map_widget.py` | Leaflet.js interactive map (QWebEngineView) |
| `pyjs_bridge.py` | Python-JavaScript communication bridge |

**Rules:**
- No business logic in UI layer
- Communicate via PyQt6 signals/slots
- Use ValidationService before sending data to backend

### 2. Business Logic Layer (`modbuspython/backend/`)

Contains application business rules and domain logic.

| Module | Responsibility |
|--------|---------------|
| `validation_service.py` | Input validation and sanitization |
| `modbus_client.py` | Legacy Modbus client (being migrated to data_access) |
| `sqlite_manager.py` | Legacy SQLite manager (being migrated to data_access) |

**Rules:**
- No UI code in backend layer
- No direct database connections (use data_access layer)
- Use exceptions from `exceptions.py`

### 3. Data Access Layer (`modbuspython/data_access/`)

Handles all external I/O operations.

| Module | Responsibility |
|--------|---------------|
| `modbus_client.py` | Threaded Modbus TCP client (QThread) |
| `modbus_connection.py` | Connection establishment with retry |
| `modbus_reader.py` | Irradiance reading with retry logic |
| `davis_weatherlink/` | Davis WeatherLink model, CRC, conversions and LOOP parser |
| `database_manager.py` | Connection pooling and context managers |
| `connection_pool.py` | Thread-safe SQLite connection pool |
| `retry_strategy.py` | Exponential backoff retry mechanism |
| `logging_service.py` | Centralized logging with rotation |
| `repositories/` | Repository pattern for data access |

**Rules:**
- No business logic in data access layer
- All I/O must be non-blocking (use threads/async)
- Use RetryStrategy for network operations

### 4. Configuration (`modbuspython/config/`)

Externalized configuration management.

| Module | Responsibility |
|--------|---------------|
| `config_manager.py` | ConfigurationManager singleton |
| `config_defaults.py` | Default configuration values |
| `env_expander.py` | Environment variable expansion |
| `credential_handler.py` | Sensitive value encryption/masking |
| `credential_encryptor.py` | Fernet-based encryption |
| `validators.py` | Configuration value validators |

### 5. Migrations (`modbuspython/migrations/`)

Database schema versioning and migration management.

| Module | Responsibility |
|--------|---------------|
| `migration_manager.py` | Migration discovery and execution |
| `versions/` | Individual migration scripts (upgrade/downgrade) |

## Design Patterns

### Singleton
- `ConfigurationManager`: Single source of truth for configuration
- `LoggingService`: Centralized logging instance

### Repository
- `BaseRepository`: Common database operations
- `IrradianceRepository`: Irradiance measurement data access
- `SchemaVersionRepository`: Schema version tracking

### Strategy
- `RetryStrategy`: Pluggable retry logic with exponential backoff

### Observer (PyQt6 Signals)
- `ModbusClient` emits signals: `radiacion_actualizada`, `conexion_cambiada`, `log`, `retry_exhausted`
- `AngleStateManager` emits: `angles_changed`
- UI widgets connect to these signals for reactive updates

### Factory
- `ConnectionPool`: Creates and manages database connections

## Data Flow

### Irradiance Reading Flow
```
Timer (QThread)
  → ModbusClient.read_irradiance()
    → ModbusReader.read_irradiance()
      → ModbusTcpClient.read_input_registers()
        → Convert raw value (÷100)
        → Emit radiacion_actualizada signal
          → UI updates gauge
        → Save to SQLite via IrradianceRepository
```

### Solar Tracker Flow
```
User enters coordinates (LocationSetupTab)
  → Coordinates applied to SolarTrackerTab
    → calculate_hra() + calculate_decl() + calculate_alt() + calculate_az()
      → Results displayed in UI
        → If auto mode: AngleStateManager sends setpoints
          → ModbusWriter.write_setpoints()
            → ModbusTcpClient.write_register()
```

### Configuration Flow
```
Application startup
  → ConfigurationManager.load_config()
    → Load .env variables (python-dotenv)
    → Parse YAML/JSON config file
    → Expand ${VAR} references
    → Decrypt sensitive values
    → Validate against JSON schema
    → Semantic validation (IP, port, SQL identifiers)
    → Fallback to defaults if validation fails
```

## Error Handling

### Exception Hierarchy
```
NexoSolarException
├── ConfigurationError
├── ValidationError
├── ModbusConnectionError
├── ModbusOperationError
├── DatabaseError
└── MigrationError
```

### Retry Strategy
Network operations use exponential backoff:
```
Attempt 1: immediate
Attempt 2: delay * 2^0 = 1s
Attempt 3: delay * 2^1 = 2s
Max delay: 30s
```

### Safe State
When critical errors occur (e.g., all retries exhausted during write):
1. System enters safe state
2. Write operations are blocked
3. Reading continues if possible
4. User must manually exit safe state

## Security

| Measure | Implementation |
|---------|---------------|
| Credential storage | Fernet encryption in config |
| Environment variables | python-dotenv with ${VAR} expansion |
| Log masking | SensitiveDataFilter in LoggingService |
| File permissions | 0o600 on config files (Unix) |
| SQL injection prevention | SQLIdentifierValidator + parameterized queries |
| Input validation | ValidationService on all user inputs |

## Concurrency Model

```
Main Thread (UI)
├── PyQt6 event loop
├── Signal/slot connections
└── Widget rendering

ModbusClient Thread (QThread)
├── QTimer for periodic reads
├── Modbus TCP I/O
├── Retry logic
└── SQLite writes

Thread Communication
└── PyQt6 signals (thread-safe)
```

## Testing Strategy

| Type | Location | Purpose |
|------|----------|---------|
| Unit | `tests/unit/` | Individual component behavior |
| Integration | `tests/integration/` | Cross-component flows |
| Property-based | `tests/property_based/` | Universal properties (Hypothesis) |

### Property-Based Tests (13 Properties)
Each property test uses Hypothesis to generate random inputs and verify invariants hold universally.

## Module Dependencies

```
ui/ → backend/ → data_access/
  ↓       ↓           ↓
config/ ←─────────────┘
```

- UI depends on backend and config
- Backend depends on data_access and config
- Data access depends on config (for retry settings)
- Config is independent (no internal dependencies)
- migrations depends on data_access (DatabaseManager)
