# Flujo de trabajo

Repositorio privado del proyecto Nexo Solar.

## Ramas

- `dev`: desarrollo.
- `QA`: validación de cambios.
- `main`: versión aprobada.

## Promoción

1. Trabaje en `dev`.
2. Abra un pull request hacia `QA` y ejecute las pruebas aplicables.
3. Corrija en `dev` y vuelva a validar.
4. Tras aprobar, promueva `QA` hacia `main`.

El workflow real es `.github/workflows/test.yml`; se ejecuta en push y pull request para las tres ramas, prueba Python 3.10–3.13 y no construye instaladores. No hay despliegue automático documentado.

La configuración local, SQLite, datos, logs y entornos virtuales quedan fuera de Git. Copie `modbuspython/config.example.yaml` a `config.yaml`. Davis WeatherLink solo está especificado en `.kiro/specs/davis-weatherlink-reader/`.
