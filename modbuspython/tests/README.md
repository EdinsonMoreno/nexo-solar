# Pruebas y verificaciones

Las pruebas están organizadas en `unit/`, `integration/` y `property_based/`. Desde la raíz:

```bash
pytest modbuspython/tests/unit/ -v
pytest modbuspython/tests/integration/ -v
pytest modbuspython/tests/property_based/ -v
python -m modbuspython.tests.check_circular_imports
```

Para una ejecución sin pantalla Qt:

```bash
QT_QPA_PLATFORM=offscreen pytest modbuspython/tests/unit/ -v
```

`check_circular_imports.py` analiza imports y reglas de capas; su reporte puede generarse localmente y no debe confirmarse si contiene artefactos. La configuración y los umbrales efectivos del CI están en `.github/workflows/test.yml` y `pyproject.toml`.
