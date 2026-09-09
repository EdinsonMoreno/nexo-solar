# Prácticas del Banco de Pruebas de Radiación Solar SCADA

## Práctica #1 – Evaluación del comportamiento de la irradiancia

**Alcance:**
Explorar el impacto de factores reales del entorno en la medición de radiación solar.

**Objetivo:**
Identificar variaciones en la irradiancia captada bajo diferentes condiciones ambientales y horarios usando el modo manual del banco de pruebas.

**Procedimiento de laboratorio:**

1. Encender el sistema y activar el modo manual en LabVIEW.
2. Medir irradiancia en:

   * Zona despejada
   * Zona parcialmente sombreada
   * Zona cubierta
3. Repetir el proceso en la mañana, mediodía y tarde.
4. Registrar hora, condiciones ambientales y lecturas.

**Resultados esperados:**

* Registro comparativo de irradiancia bajo diversas condiciones.
* Comprensión del impacto de sombras y horarios.

**Actividad:**

* Tabla con lecturas.
* Gráfico comparativo irradiancia vs. condición.
* Conclusión breve.

---

## Práctica #2 – Visualización de datos en tiempo real

**Alcance:**
Uso de interfaz de visualización para monitorear irradiancia vía Wi-Fi.

**Objetivo:**
Familiarizar al estudiante con LabVIEW para análisis e interpretación de datos solares.

**Procedimiento de laboratorio:**

1. Conectar Arduino UNO vía Wi-Fi.
2. Verificar protocolo TCP.
3. Cargar interfaz en LabVIEW y presionar "Conectar".
4. Visualizar mediciones en tiempo real.

**Resultados esperados:**

* Visualización continua de valores de irradiancia.
* Gráfica dinámica en LabVIEW.

**Actividad:**

* Cambiar ubicación del sensor y observar variaciones.
* Capturas de pantalla con cielo despejado vs. nublado.
* Registrar el valor máximo observado en 5 minutos.

---

## Práctica #3 – Control manual del piranómetro

**Alcance:**
Orientación precisa del sensor para análisis de irradiancia en zonas específicas.

**Objetivo:**
Desarrollar habilidades para operar el modo manual y correlacionar orientación con radiación solar.

**Procedimiento de laboratorio:**

1. Encender el sistema y abrir LabVIEW.
2. Seleccionar modo "Manual".
3. Ingresar ángulos de acimut (X) y elevación (Y).
4. Ejecutar movimiento y registrar lecturas.
5. Repetir con distintos ángulos.

**Resultados esperados:**

* Lecturas según posición.
* Comparación entre zonas.

**Actividad:**

* Apuntar a tres zonas: cielo abierto, sombra parcial, zona cubierta.
* Registrar irradiancia y elaborar tabla comparativa.

---

## Práctica #4 – Seguimiento solar automático

**Alcance:**
Simulación de sistema real de seguimiento solar con orientación automatizada.

**Objetivo:**
Evaluar precisión y comportamiento del algoritmo de seguimiento astronómico implementado.

**Procedimiento de laboratorio:**

1. Encender el sistema y abrir LabVIEW.
2. Ingresar ubicación, fecha y hora.
3. Observar movimiento del sensor.
4. Registrar hora, posición y lectura.

**Resultados esperados:**

* Movimiento automático hacia el sol.
* Lectura estable de irradiancia.
* Comportamiento estable del sistema PID.

**Actividad:**

* Realizar pruebas en tres momentos del día.
* Registrar y comparar ángulos y niveles de radiación.

---

## Práctica #5 – Análisis de datos desde la base de datos

**Alcance:**
Desarrollar habilidades en análisis de datos técnicos provenientes del sistema solar.

**Objetivo:**
Extraer y analizar datos registrados en la base de datos SQLite.

**Procedimiento de laboratorio:**

1. Abrir software de SQLite y cargar base de datos.
2. Navegar a la tabla `solar_data`.
3. Exportar datos como archivo `.csv`.
4. Abrir en Excel o Google Sheets.
5. Filtrar por variables.
6. Calcular estadísticas (promedio, máximo, mínimo).
7. Generar gráfica de tendencia.

**Resultados esperados:**

* Lectura y análisis de datos.
* Visualización gráfica de la irradiancia.

**Actividad:**

* Tabla con irradiancia por hora.
* Identificar hora de mayor radiación.
* Comparar dos días diferentes.
