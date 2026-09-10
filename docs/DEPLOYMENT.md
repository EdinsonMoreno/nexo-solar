# Instalación y operación

La aplicación es una GUI local; no hay Dockerfile, API HTTP ni instalador generado por el workflow.

```bash
git clone <URL-privada-del-repositorio>
cd <directorio-del-repositorio>
python -m venv .venv
source .venv/bin/activate             # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp modbuspython/config.example.yaml config.yaml
python run.py
```

Configure `modbus.host`, `modbus.port` y los registros antes de usar hardware. El dispositivo y el equipo deben compartir una red que permita Modbus TCP. `data/` contiene SQLite y `logs/` los registros; ambos requieren permisos de escritura.

En Linux instale Python, `python3-venv`, Qt y las bibliotecas XCB que requiera su distribución. En Windows ejecute desde el entorno virtual. `main_app.spec` y PyInstaller existen como materiales, pero no forman parte del CI ni garantizan un instalador.

Conserve copias de `data/` y de la configuración sin exponer secretos. Antes de actualizar, detenga la aplicación, respalde SQLite, actualice dependencias y ejecute las pruebas. No documentamos Docker, puertos HTTP ni servicios de producción porque no están presentes.
