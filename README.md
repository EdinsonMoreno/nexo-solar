# Nexo Solar

Software en preparación para el SENA CIDT de Barrancabermeja. Autor: Edinson Andres Moreno Cepeda.

Esta es la base inicial de desarrollo. La integración Davis WeatherLink inició por los módulos de parsing, CRC, conversiones y configuración.

Sistema SCADA para monitoreo de irradiacion solar, adquisicion de datos Modbus, lectura meteorologica Davis WeatherLink y visualizacion geografica. Desarrollado en Python con PyQt6 y Leaflet.js.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/UI-PyQt6-green)](https://www.riverbankcomputing.com/software/pyqt/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE.txt)

## Características

- **Monitoreo en tiempo real**: Lectura de irradiacion solar via Modbus TCP desde dispositivos ESP8266
- **Mapa interactivo**: Visualizacion geografica con Leaflet.js, soporte online y offline
- **Estacion Davis WeatherLink**: Base de parsing, CRC y conversiones de unidades para paquetes LOOP
- **Almacenamiento historico**: Base de datos SQLite con pool de conexiones y sistema de migraciones
- **Arquitectura robusta**: 3 capas (backend, data_access, ui), validacion de entradas, reintentos con backoff exponencial, manejo de errores y safe state
- **Seguridad**: Credenciales encriptadas, variables de entorno, filtros de datos sensibles en logs

## Requisitos del Sistema

| Componente | Minimo | Recomendado |
|------------|--------|-------------|
| Python | 3.10 | 3.12+ |
| RAM | 2 GB | 4 GB |
| Disco | 500 MB | 1 GB |
| SO | Windows 10 / Linux / macOS | Windows 11 |

### Hardware Compatible

- ESP8266 con firmware Modbus TCP
- Estacion meteorologica Davis Vantage Pro2 con WeatherLink USB en modo VCP o adaptador IP compatible
- Cualquier dispositivo que implemente Modbus TCP en puerto 502

## Instalación

### Desarrollo

```bash
# 1. Clonar repositorio
git clone https://github.com/EdinsonMoreno/nexo-solar.git
cd nexo-solar

# 2. Crear entorno virtual
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/macOS

# 3. Instalar dependencias
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Dependencias de desarrollo (opcional)

# 4. Configurar variables de entorno
copy .env.example .env       # Windows
cp .env.example .env         # Linux/macOS
# Editar .env con tus valores

# 5. Ejecutar aplicacion
python run.py
```

### Producción (Ejecutable Windows)

```bash
# 1. Instalar PyInstaller
pip install pyinstaller

# 2. Compilar ejecutable
pyinstaller main_app.spec

# 3. El ejecutable se encuentra en dist/SolarSense_SCADA/
```

## Configuración

La configuracion se gestiona mediante archivos YAML/JSON con validacion de esquema.

1. Copia `config.example.yaml` a `config.yaml`
2. Edita los valores segun tu entorno
3. Las credenciales sensibles pueden usar variables de entorno con sintaxis `${VAR_NAME}`

```yaml
modbus:
  host: "${MODBUS_HOST}"    # Se expande desde variable de entorno
  port: 502
  timeout: 5.0
```

Ver `docs/CONFIGURATION_GUIDE.md` para referencia completa.

## Estructura del Proyecto

```
nexo-solar/
├── modbuspython/
│   ├── run.py                    # Punto de entrada
│   ├── main_app.py               # Aplicacion principal (PyQt6)
│   ├── config/                   # Configuracion externalizada
│   │   ├── config_manager.py     # ConfigurationManager (singleton)
│   │   ├── config_defaults.py    # Valores por defecto
│   │   ├── env_expander.py       # Expansion de variables de entorno
│   │   ├── credential_handler.py # Manejo de credenciales sensibles
│   │   ├── credential_encryptor.py # Encriptacion Fernet
│   │   ├── validators.py         # Validadores de configuracion
│   │   └── config_schema.json    # JSON Schema
│   ├── backend/                  # Logica de negocio
│   │   ├── validation_service.py # Servicio de validacion
│   │   ├── modbus_client.py      # Cliente Modbus (legacy)
│   │   ├── sqlite_manager.py     # SQLite manager (legacy)
│   │   └── logger.py             # Logger (legacy)
│   ├── data_access/              # Acceso a datos
│   │   ├── modbus_client.py      # Modbus TCP client (QThread)
│   │   ├── davis_weatherlink/    # Parser, CRC y modelo WeatherLink
│   │   ├── modbus_connection.py  # Operaciones de conexion
│   │   ├── modbus_reader.py      # Operaciones de lectura
│   │   ├── modbus_writer.py      # Operaciones de escritura
│   │   ├── database_manager.py   # Database manager con connection pool
│   │   ├── connection_pool.py    # Connection pool thread-safe
│   │   ├── retry_strategy.py     # Retry con backoff exponencial
│   │   ├── logging_service.py    # Logging centralizado
│   │   └── repositories/         # Patron Repository
│   │       ├── base_repository.py
│   │       ├── irradiance_repository.py
│   │       └── schema_version_repository.py
│   ├── ui/                       # Interfaz de usuario
│   │   ├── location_tab_fixed.py # Tab principal (orquestador)
│   │   ├── location_setup_tab.py # Configuracion de ubicacion
│   │   ├── monitor_tab.py        # Monitor de irradiacion
│   │   ├── diagnostic_tab.py     # Diagnostico del sistema
│   │   ├── documentation_tab.py  # Documentacion integrada
│   │   ├── map_widget.py         # Mapa Leaflet interactivo
│   │   ├── circular_gauge.py     # Indicador circular
│   │   ├── pyjs_bridge.py        # Puente Python-JavaScript
│   │   └── assets/               # Recursos (Leaflet, tiles, imagenes)
│   ├── migrations/               # Migraciones de base de datos
│   │   ├── migration_manager.py
│   │   └── versions/
│   │       ├── v1_initial_schema.py
│   │       └── v2_add_metrics_table.py
│   ├── tests/                    # Suite de pruebas
│   │   ├── unit/
│   │   ├── integration/
│   │   └── property_based/
│   └── exceptions.py             # Excepciones personalizadas
├── config.yaml                   # Configuracion (no rastreado)
├── config.example.yaml           # Ejemplo de configuracion
├── .env.example                  # Ejemplo de variables de entorno
├── requirements.txt              # Dependencias de produccion
├── requirements-dev.txt          # Dependencias de desarrollo
├── pyproject.toml                # Configuracion del proyecto
├── pytest.ini                    # Configuracion de pytest
├── .pre-commit-config.yaml       # Hooks pre-commit
└── docs/                         # Documentacion
    ├── ARCHITECTURE.md
    ├── CONFIGURATION_GUIDE.md
    ├── TROUBLESHOOTING.md
    ├── CONTRIBUTING.md
    └── DEPLOYMENT.md
```

## Uso

### Inicio Rapido

```bash
python run.py
```

La aplicacion abrira una ventana con las siguientes pestañas:

1. **Monitor**: Vista en tiempo real de irradiacion con gauges circulares
2. **Ubicacion del Equipo**: Configuracion de coordenadas geograficas con mapa
3. **Estacion Davis**: Lecturas meteorologicas en unidades de ingenieria
4. **Diagnostico**: Estado del sistema, logs y herramientas de diagnostico
5. **Analisis**: Consulta de historicos SQLite
6. **Documentacion**: Guias integradas

## Arquitectura

El proyecto sigue una arquitectura de 3 capas:

```
┌─────────────────────────────────────────────────┐
│                   UI Layer                      │
│  (PyQt6 Widgets, QWebEngineView, Leaflet.js)   │
├─────────────────────────────────────────────────┤
│               Backend Layer                     │
│  (Validation, servicios de dominio)             │
├─────────────────────────────────────────────────┤
│             Data Access Layer                   │
│  (ModbusClient, Davis WeatherLink, SQLite)      │
└─────────────────────────────────────────────────┘
```

Ver `docs/ARCHITECTURE.md` para detalles completos.

## Testing

```bash
# Ejecutar todos los tests
pytest modbuspython/tests/

# Solo tests unitarios
pytest modbuspython/tests/unit/

# Con cobertura
pytest --cov=modbuspython --cov-report=html

# Tests de propiedades (Hypothesis)
pytest modbuspython/tests/property_based/
```

### Cobertura de Tests

| Tipo | Count | Descripcion |
|------|-------|-------------|
| Unitarios | 200+ | Componentes individuales |
| Integracion | 20+ | Flujos completos |
| Property-based | 13 | Propiedades universales con Hypothesis |

## Pre-commit Hooks

El proyecto usa pre-commit para asegurar calidad de codigo:

```bash
# Instalar hooks
pre-commit install

# Ejecutar manualmente
pre-commit run --all-files
```

Hooks activos: black, flake8, mypy, bandit, print-check, yaml-check, json-check, y mas.

## Propiedades de Correctitud

El proyecto define 13 propiedades de correctitud verificadas con property-based tests:

1. Angle Range Invariant
2. Configuration Round-Trip Preservation
3. Input Validation Idempotence
4. IP Address Format Validation
5. Port Range Validation
6. SQL Identifier Injection Prevention
7. Configuration Validation Completeness
8. Error Resilience Continuation
9. Retry Logic Execution
10. Resource Cleanup Completeness
11. Database Migration Reversibility
12. Configuration Format Validity
13. Timestamp Ordering in Database

## Dependencias

### Produccion
```
PyQt6>=6.4.0
PyQt6-WebEngine>=6.4.0
pymodbus>=3.0.0
pyyaml>=6.0
jsonschema>=4.17.0
python-dotenv>=1.0.0
cryptography>=41.0.0
requests>=2.28.0
```

### Desarrollo
```
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-mock>=3.10.0
hypothesis>=6.0.0
black>=22.0.0
flake8>=5.0.0
mypy>=1.0.0
pre-commit>=3.0.0
bandit>=1.7.0
```

## Troubleshooting

| Problema | Solucion |
|----------|----------|
| No conecta a Modbus | Verificar IP/puerto en config.yaml, comprobar conectividad de red |
| Mapa no carga tiles | Verificar conexion a internet o tiles offline en `assets/tiles/` |
| Error de base de datos | Verificar permisos de escritura en `data/` |
| Credenciales no cargan | Verificar variables de entorno en `.env` |
| Visor 3D no funciona | Verificar PyQt6-WebEngine instalado |

Ver `docs/TROUBLESHOOTING.md` para guia completa.

## Contribuir

El desarrollo se realiza en `dev`, la validación en `QA` y las versiones aprobadas para despliegue en `main`. Ver [flujo de trabajo](docs/WORKFLOW.md).

## Licencia

Licencia de uso restringido. Ver [LICENSE.txt](LICENSE.txt) para detalles.

## Creditos

- **Leaflet.js** - Biblioteca de mapas interactivos
- **OpenStreetMap** - Datos de mapas
- **PyQt6** - Framework de UI
- **pymodbus** - Implementacion de protocolo Modbus
- **Edinson Andres Moreno Cepeda**

---

**¿Dudas, sugerencias o errores?** Abre un issue o contacta al equipo de desarrollo.
