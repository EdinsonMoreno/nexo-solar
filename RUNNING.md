# Ejecutar la aplicación

## Método recomendado

Ejecute desde la raíz del repositorio:

```bash
python run.py
```

El script raíz configura la ruta de importación y llama a `modbuspython.main_app.main`. Es la forma soportada para evitar errores de importación.

## Preparación

```bash
python -m venv .venv
source .venv/bin/activate          # Linux/macOS
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp modbuspython/config.example.yaml config.yaml
```

Edite `config.yaml` con la dirección y registros de su dispositivo Modbus. Cree `.env` solo si necesita variables locales. Consulte `docs/CONFIGURATION_GUIDE.md`.

## No ejecutar así

```bash
python modbuspython/main_app.py
```

Ese archivo usa imports de paquete y no está diseñado para ejecutarse directamente. También existe `python -m modbuspython.main_app`, pero `python run.py` es el método recomendado.

## Problemas de arranque

1. Confirme que está en la carpeta donde existe `run.py`.
2. Active el entorno virtual correcto.
3. Compruebe `pip install -r requirements.txt`.
4. Si usa Linux, instale las bibliotecas Qt requeridas por su distribución.
5. Revise `logs/solarsense.log` y [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).
