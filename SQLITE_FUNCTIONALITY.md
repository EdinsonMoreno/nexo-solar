# SQLite

La aplicación persiste mediciones en una base SQLite local configurada en `database.path` (por defecto `data/solarsense.db`). El acceso actual se encuentra principalmente en `modbuspython/data_access/`, con `DatabaseManager`, `ConnectionPool` y repositorios. `backend/sqlite_manager.py` y `ui/sqlite_dialog.py` son módulos heredados que pueden permanecer por compatibilidad.

## Configuración

```yaml
database:
  path: "data/solarsense.db"
  table_name: "measurements"
  connection_pool_size: 5
```

La aplicación crea la carpeta o el esquema cuando el flujo correspondiente lo necesita. Los nombres de tablas e identificadores se validan; los valores deben parametrizarse en consultas.

## Operación segura

- Detenga la aplicación antes de copiar o restaurar la base.
- Haga respaldos de `data/` sin subirlos al repositorio.
- Si aparece “database is locked”, cierre exploradores SQLite y procesos duplicados.
- Consulte el esquema y las migraciones del código antes de modificar tablas manualmente.

SQLite es almacenamiento local; no hay un servidor de base de datos ni una API de consulta pública.
