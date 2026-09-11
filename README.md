# Nexo Solar

Repositorio privado del proyecto Nexo Solar del SENA CIDT de Barrancabermeja. La aplicación, escrita en Python y PyQt6, adquiere variables meteorológicas desde Davis WeatherLink por USB/Serial o IP, calcula indicadores solares y conserva datos en SQLite.

> **Estado actual:** la interfaz operativa está en `Mockup/` y se ejecuta embebida en PyQt6 mediante `modbuspython/ui/web_dashboard.py`. El backend Davis WeatherLink vive en `modbuspython/data_access/davis_weatherlink/`.

## Requisitos

- Python 3.10 o posterior.
- Dependencias de `requirements.txt`.
- Para usar datos reales: una estación Davis con datalogger USB/Serial o un logger IP compatible.
- En Linux, las bibliotecas del sistema necesarias para Qt pueden ser requeridas por la distribución.

## Descargas e instaladores

Las versiones estables se publican desde ramas separadas por plataforma:

- Windows: rama `production/windows`, instalador `NexoSolar-Setup-Windows-x64.exe`.
- Fedora: rama `production/fedora`, paquete `nexo-solar-*.rpm`.

Los instaladores se descargan desde [GitHub Releases](https://github.com/EdinsonMoreno/nexo-solar/releases). En este repositorio privado debe iniciar sesión con una cuenta autorizada para ver las descargas.

También puede generar los instaladores manualmente:

```bash
# Fedora, desde la rama production/fedora
scripts/build_fedora_rpm.sh 1.0.0
```

```powershell
# Windows, desde la rama production/windows en PowerShell
.\scripts\build_windows_installer.ps1 -Version 1.0.0
```

Los artefactos quedan en `dist/installers/` junto con `SHA256SUMS.txt`.

## Instalación y primera ejecución

Desde la raíz del repositorio (la carpeta que contiene `run.py`):

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp modbuspython/config.example.yaml config.yaml  # Windows: copy ...
python run.py
```

`config.yaml`, `.env`, `data/` y `logs/` son locales y no se rastrean. La aplicación puede crear la configuración predeterminada; revise [la guía de configuración](docs/CONFIGURATION_GUIDE.md) antes de conectar hardware.

## Uso y UI

`run.py` prepara el `PYTHONPATH` e invoca `modbuspython.main_app:main`; no ejecute `modbuspython/main_app.py` como script. Al iniciar, la aplicación muestra una pantalla de carga con barra de progreso mientras prepara configuración, base de datos, servicios e interfaz web.

## Pruebas y CI

```bash
pytest modbuspython/tests/unit/ -v
pytest modbuspython/tests/integration/ -v
pytest modbuspython/tests/property_based/ -v
python -m modbuspython.tests.check_circular_imports
```

El workflow vigente es `.github/workflows/test.yml`: prueba Python 3.10–3.13, ejecuta Black, Flake8, Pylint, MyPy, pruebas unitarias, integración, property-based y análisis de seguridad. Algunas comprobaciones están marcadas para no bloquear el job (`continue-on-error`).

## Estructura

```text
run.py                         # punto de entrada real
modbuspython/main_app.py       # ventana y arranque PyQt6
modbuspython/backend/           # reglas de dominio y cálculos
modbuspython/data_access/       # Modbus, SQLite, logging y reintentos
modbuspython/config/            # carga y validación de configuración
modbuspython/ui/                # widgets y dashboard web
modbuspython/tests/             # pruebas y verificaciones auxiliares
Mockup/                         # maqueta HTML/CSS/JavaScript
docs/                           # guías de uso y desarrollo
```

## Documentación

- [Ejecutar](RUNNING.md)
- [Configuración](docs/CONFIGURATION_GUIDE.md)
- [Arquitectura](docs/ARCHITECTURE.md)
- [Pruebas](modbuspython/tests/README.md)
- [Solución de problemas](docs/TROUBLESHOOTING.md)
- [Contribución](docs/CONTRIBUTING.md)
- [Seguridad](SECURITY.md)
- [Cambios](CHANGELOG.md)

## Licencia

El alcance legal y la licencia se mantienen en [LICENSE.txt](LICENSE.txt).
