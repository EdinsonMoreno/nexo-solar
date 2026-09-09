# Funcionalidad SQLite - Almacenamiento Automático de Datos de Irradiancia

## Descripción
Se ha implementado una funcionalidad completa para almacenar automáticamente las lecturas de irradiancia en una base de datos SQLite local. Esta funcionalidad no interfiere con la lógica existente de Modbus y cálculos, simplemente se suscribe a la señal `radiacion_actualizada` para guardar los registros.

## Archivos Implementados

### 1. `backend/sqlite_manager.py`
Módulo que maneja todas las operaciones SQLite:
- **`conectar_db(ruta)`**: Conecta/crea base de datos SQLite
- **`obtener_tablas(conn)`**: Lista tablas existentes
- **`crear_tabla(conn, nombre)`**: Crea tabla con esquema fijo
- **`insertar_registro(conn, tabla, fecha, hora, irradiancia)`**: Inserta nuevo registro
- **`validar_nombre_tabla(nombre)`**: Valida nombres según reglas SQLite
- **`obtener_estadisticas_tabla(conn, tabla)`**: Obtiene estadísticas básicas

### 2. `ui/sqlite_dialog.py`
Diálogo de configuración SQLite:
- Permite seleccionar base de datos existente o crear nueva
- ComboBox para tablas existentes
- Campo de texto para crear nuevas tablas
- Validación en tiempo real de nombres de tabla
- Manejo de errores y confirmaciones

### 3. Modificaciones en `backend/modbus_client.py`
Se agregaron métodos al `ModbusManager`:
- **`configurar_sqlite(ruta_db, tabla)`**: Configura almacenamiento SQLite
- **`_guardar_en_sqlite(irradiancia)`**: Guarda registro automáticamente
- Integración en `leer_radiacion()` para guardado automático

### 4. Modificaciones en `ui/monitor_tab.py`
Se agregó interfaz de usuario:
- Botón "📊 Configurar Base de Datos SQLite"
- Método `abrir_configuracion_sqlite()` para mostrar diálogo
- Método `configurar_sqlite()` para manejar la configuración
- Mensajes de confirmación y error

## Esquema de Tabla
Todas las tablas de irradiancia tienen el mismo esquema:
```sql
CREATE TABLE nombre_tabla (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    hora TEXT NOT NULL,
    irradiancia REAL NOT NULL
)
```

## Flujo de Uso

1. **Configuración Inicial**:
   - Clic en "📊 Configurar Base de Datos SQLite" en la pestaña Monitor
   - Seleccionar base de datos (por defecto: `./data/irradiancia.db`)
   - Elegir tabla existente o crear nueva
   - Confirmar configuración

2. **Almacenamiento Automático**:
   - Una vez configurado, cada lectura de irradiancia se guarda automáticamente
   - Los registros incluyen fecha, hora y valor de irradiancia
   - El guardado es transparente y no interfiere con la operación normal

3. **Validaciones**:
   - Nombres de tabla válidos (letras, números, guiones bajos, no empezar con número)
   - Verificación de tablas existentes
   - Manejo de errores de SQLite

## Ubicación de Datos
- **Directorio**: `./data/`
- **Base de datos por defecto**: `irradiancia.db`
- **Tablas**: Definidas por el usuario

## Características Técnicas
- Usa `sqlite3` de la biblioteca estándar de Python (sin dependencias externas)
- Transacciones automáticas con `commit()` después de cada inserción
- Manejo robusto de errores con `try/except`
- Validación de entrada para prevenir inyección SQL
- Interfaz no bloqueante (no afecta lecturas Modbus)

## Ejemplo de Datos Almacenados
```
id | fecha      | hora     | irradiancia
---|------------|----------|------------
1  | 2025-06-04 | 10:30:15 | 850.5
2  | 2025-06-04 | 10:30:16 | 867.2
3  | 2025-06-04 | 10:30:17 | 891.8
```

## Estadísticas Disponibles
El sistema puede mostrar:
- Número total de registros
- Valor mínimo de irradiancia
- Valor máximo de irradiancia
- Promedio de irradiancia
- Fecha/hora del último registro

## Notas de Implementación
- La funcionalidad es completamente opcional
- No modifica la lógica existente de Modbus
- Se puede configurar y reconfigurar en cualquier momento
- Los archivos de base de datos son portables y estándar SQLite
