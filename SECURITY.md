# Política de seguridad

Este es un repositorio privado. No publique detalles de una vulnerabilidad en un issue público.

## Reportar una vulnerabilidad

Abra un **issue privado** en el repositorio o contacte directamente al mantenedor por el canal privado disponible para los colaboradores. Incluya:

- descripción y componente afectado;
- pasos mínimos para reproducirla;
- impacto observado o posible;
- versión, sistema operativo y configuración relevante (sin secretos).

No se publican aquí direcciones de correo, claves PGP ni tiempos de respuesta inventados. El mantenedor coordinará el análisis y la divulgación según el caso.

## Prácticas para colaboradores

- No confirme credenciales, tokens, claves ni bases de datos en Git.
- Mantenga `.env` y `config.yaml` fuera del control de versiones.
- Use consultas parametrizadas y los validadores existentes para identificadores SQL.
- Revise que los logs no contengan información sensible.
- Mantenga actualizadas las dependencias y revise los resultados de las comprobaciones del workflow.

## Alcance técnico documentado

La aplicación usa Modbus TCP, SQLite, PyQt6 y el filtrado de datos sensibles de `LoggingService`. Davis WeatherLink no forma parte del código ejecutable actual: únicamente existe una especificación en `.kiro/specs/davis-weatherlink-reader/`.

La licencia y el alcance legal del proyecto permanecen en [LICENSE.txt](LICENSE.txt).
