# Contribuir

Este repositorio privado usa Python 3.10–3.13.

```bash
python -m venv .venv
source .venv/bin/activate             # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp modbuspython/config.example.yaml config.yaml
```

No existe `requirements-dev.txt`. El workflow instala sus herramientas adicionales explícitamente.

## Organización

`run.py` es el punto de entrada; `modbuspython/` contiene UI, backend, acceso a datos, configuración, migraciones y pruebas. Mantenga la dirección `ui → backend → data_access` y use `config` para valores configurables.

## Verificaciones

```bash
black --check --diff modbuspython/
flake8 modbuspython/ --count --select=E9,F63,F7,F82 --show-source --statistics
mypy modbuspython/ --ignore-missing-imports --no-strict-optional
pytest modbuspython/tests/unit/ -v --cov=modbuspython --cov-fail-under=60
pytest modbuspython/tests/integration/ -v
pytest modbuspython/tests/property_based/ -v
python -m modbuspython.tests.check_circular_imports
```

La fuente de verdad del CI es `.github/workflows/test.yml`; algunas comprobaciones no bloquean el job. Para Qt sin pantalla use `QT_QPA_PLATFORM=offscreen`.

Describa en cada pull request el problema, la configuración y las pruebas ejecutadas. No incluya secretos, bases SQLite, `.env` ni artefactos generados. Respete [WORKFLOW.md](WORKFLOW.md).
