"""QWebChannel bridge between the embedded web dashboard (Mockup SPA) and the
Python backend.

``WebBridge`` is the integration contract between the JavaScript UI and the
existing backend services:

- It re-emits backend Qt signals from the Modbus client as JS-friendly signals
  consumed by ``Mockup/app.js``.
- It exposes ``@pyqtSlot`` methods that the JavaScript calls on user actions,
  routing them to the real backend (``ModbusClient``).

The bridge lives in the GUI thread; backend signals emitted from the Modbus
QThread are delivered here through Qt's queued connections, so it is safe to
forward them to JavaScript via this object's own signals.
"""

from typing import Any, Optional

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from ..config.config_defaults import DEFAULT_CONFIG
from ..data_access.logging_service import LoggingService
from ..data_access.repositories.davis_weather_repository import DavisWeatherRepository
from ..data_access.repositories.irradiance_repository import IrradianceRepository


class WebBridge(QObject):
    """Bridge object registered on the QWebChannel as ``"bridge"``.

    Args:
        modbus_manager: The shared ``ModbusClient`` instance (aliased
            ``ModbusManager``) created by the main window.
        parent: Optional Qt parent.
    """

    # ----- Python -> JS signals -----
    irradianceUpdated = pyqtSignal(float)
    logMessage = pyqtSignal(str, str, str)  # source, level, text
    connectionChanged = pyqtSignal(bool)
    safeStateChanged = pyqtSignal(bool)
    davisWeatherUpdated = pyqtSignal("QVariantMap")
    davisConnectionChanged = pyqtSignal(bool, str)
    davisStatusUpdated = pyqtSignal("QVariantMap")
    davisRetryExhausted = pyqtSignal(str, str)

    def __init__(self, modbus_manager: Any, davis_reader: Optional[Any] = None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.logger = LoggingService()
        self.modbus = modbus_manager
        self.davis = davis_reader
        self._connected = False
        self._auto_read = True
        self._read_interval_ms = 2000
        _db = DEFAULT_CONFIG["database"]
        # Fuente de la pestaña Análisis: por defecto el histórico medido en
        # campo, que vive en su propio archivo y no en la base de escritura.
        self._write_db_path = _db["path"]
        self._db_path = _db.get("analysis_path", _db["path"])
        self._db_table = _db.get("analysis_table", _db.get("table_name", "mediciones"))

    # ------------------------------------------------------------------
    # Backend wiring (Python -> JS relays)
    # ------------------------------------------------------------------
    def connect_backend(self) -> None:
        """Connect backend signals to this bridge's JS-facing signals."""
        self.modbus.radiacion_actualizada.connect(self._on_irradiance)
        self.modbus.log.connect(self._on_log)
        self.modbus.conexion_cambiada.connect(self._on_connection)
        self.modbus.retry_exhausted.connect(self._on_retry_exhausted)
        if self.davis is not None:
            self.davis.weather_data_updated.connect(self._on_davis_weather)
            self.davis.connection_changed.connect(self._on_davis_connection)
            self.davis.connection_lost.connect(self._on_davis_connection_lost)
            self.davis.log.connect(self._on_davis_log)
            self.davis.retry_exhausted.connect(self._on_davis_retry_exhausted)

    def disconnect_backend(self) -> None:
        """Best-effort disconnect of backend signals (used on cleanup)."""
        for signal, slot in (
            (self.modbus.radiacion_actualizada, self._on_irradiance),
            (self.modbus.log, self._on_log),
            (self.modbus.conexion_cambiada, self._on_connection),
            (self.modbus.retry_exhausted, self._on_retry_exhausted),
        ):
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                pass
        if self.davis is not None:
            for signal, slot in (
                (self.davis.weather_data_updated, self._on_davis_weather),
                (self.davis.connection_changed, self._on_davis_connection),
                (self.davis.connection_lost, self._on_davis_connection_lost),
                (self.davis.log, self._on_davis_log),
                (self.davis.retry_exhausted, self._on_davis_retry_exhausted),
            ):
                try:
                    signal.disconnect(slot)
                except (TypeError, RuntimeError):
                    pass

    def _on_irradiance(self, value: float) -> None:
        self.irradianceUpdated.emit(float(value))

    def _on_log(self, message: str) -> None:
        self.logMessage.emit("", self._classify_level(message), str(message))

    def _on_connection(self, connected: bool) -> None:
        self._connected = bool(connected)
        self.connectionChanged.emit(bool(connected))

    def _on_retry_exhausted(self, operation: str, error: str) -> None:
        in_safe = bool(getattr(self.modbus, "is_in_safe_state", lambda: True)())
        self.safeStateChanged.emit(in_safe)
        self.logMessage.emit("SISTEMA", "error", f"Reintentos agotados en {operation}: {error}")

    def _on_davis_weather(self, data: Any) -> None:
        payload = data.as_dict() if hasattr(data, "as_dict") else dict(data)
        self.davisConnectionChanged.emit(True, self._davis_connection_label(True))
        self.davisWeatherUpdated.emit(payload)
        self.davisStatusUpdated.emit(self._davis_status_payload())

    def _on_davis_connection(self, connected: bool) -> None:
        text = self._davis_connection_label(connected)
        self.davisConnectionChanged.emit(bool(connected), text)
        self.davisStatusUpdated.emit(self._davis_status_payload())

    def _on_davis_connection_lost(self, message: str) -> None:
        self.davisConnectionChanged.emit(False, message)
        self.davisStatusUpdated.emit(self._davis_status_payload())

    def _on_davis_log(self, message: str) -> None:
        self.logMessage.emit("DAVIS", self._classify_level(message), str(message))

    def _on_davis_retry_exhausted(self, operation: str, error: str) -> None:
        self.davisRetryExhausted.emit(operation, error)
        self.davisStatusUpdated.emit(self._davis_status_payload())
        self.logMessage.emit("DAVIS", "error", f"Reintentos agotados en {operation}: {error}")

    @staticmethod
    def _classify_level(message: str) -> str:
        low = message.lower()
        if any(k in low for k in ("error", "falló", "fallo", "crit", "excep")):
            return "error"
        if any(k in low for k in ("advert", "warn", "seguro", "timeout", "reintent")):
            return "warn"
        return "info"

    # ------------------------------------------------------------------
    # JS -> Python slots
    # ------------------------------------------------------------------
    @pyqtSlot()
    def readRadiation(self) -> None:
        self.modbus.read_irradiance()

    @pyqtSlot(str, int)
    def connectModbus(self, ip: str, port: int) -> None:
        """Configure host/port and connect, starting periodic reading."""
        self.modbus.ip = ip
        self.modbus.port = int(port)
        self.modbus.connect()
        if self._auto_read:
            self.modbus.iniciar(self._read_interval_ms)

    @pyqtSlot()
    def disconnectModbus(self) -> None:
        self.modbus.disconnect()

    @pyqtSlot()
    def modbusTest(self) -> None:
        if self._connected:
            self.modbus.read_irradiance()
            self.logMessage.emit("Prueba", "info", "Prueba Modbus: lectura solicitada")
        else:
            self.logMessage.emit("Prueba", "error", "Prueba Modbus: sin conexión")

    @pyqtSlot()
    def pauseReading(self) -> None:
        self.modbus.detener_lectura()

    @pyqtSlot()
    def resumeReading(self) -> None:
        self.modbus.iniciar(self._read_interval_ms)

    @pyqtSlot(bool)
    def setAutoRead(self, enabled: bool) -> None:
        self._auto_read = bool(enabled)
        if enabled:
            self.modbus.iniciar(self._read_interval_ms)
        else:
            self.modbus.detener_lectura()

    @pyqtSlot()
    def recoverSafeState(self) -> None:
        self.modbus.exit_safe_state()
        self.safeStateChanged.emit(False)

    @pyqtSlot(str, str, str, int, result=bool)
    def connectDavis(self, transport: str, serial_port: str, ip_host: str, ip_port: int) -> bool:
        """Configure and connect the Davis reader."""
        if self.davis is None:
            self.davisConnectionChanged.emit(False, "Lector Davis no disponible")
            return False
        try:
            self.davis.configure_runtime(transport, serial_port, ip_host, ip_port)
            if not self.davis.isRunning():
                self.davis.start()
            ok = bool(self.davis.connect_station())
            if ok:
                self.davis.iniciar()
            return ok
        except Exception as e:  # pragma: no cover - defensive
            self.davisConnectionChanged.emit(False, str(e))
            self.logMessage.emit("DAVIS", "error", f"Error conectando Davis: {e}")
            return False

    @pyqtSlot()
    def disconnectDavis(self) -> None:
        """Disconnect the Davis reader."""
        if self.davis is not None:
            self.davis.disconnect_station()

    @pyqtSlot()
    def readDavisOnce(self) -> None:
        """Request one Davis LOOP reading."""
        if self.davis is not None:
            self.davis.read_once()

    @pyqtSlot(result="QVariantMap")
    def getDavisStatus(self) -> dict:
        """Return the current Davis USB/IP reader status for the web UI."""
        return self._davis_status_payload()

    @pyqtSlot(int, result="QVariantList")
    def loadDavisHistory(self, range_hours: int = 0) -> list:
        """Return recent persisted Davis readings for charts."""
        try:
            repo = DavisWeatherRepository(self._write_db_path, use_pool=False)
            repo.create_table()
            return repo.get_for_hours(int(range_hours), max_rows=50000)
        except Exception as e:  # pragma: no cover - defensive
            self.logMessage.emit("SQLITE", "error", f"Error leyendo histórico Davis: {e}")
            return []

    @pyqtSlot(str, str, result=bool)
    def configureSqlite(self, db_path: str, table: str) -> bool:
        """Configure SQLite persistence without seeding measurements.

        The legacy irradiance table is created only as an empty destination for
        Modbus data. Davis readings always use the stable table
        ``davis_weather_readings`` in the same file.
        """
        try:
            ok = bool(self.modbus.configurar_sqlite(db_path, table))
            if ok:
                self._db_path = db_path
                self._db_table = table
                self._write_db_path = db_path
                repo = DavisWeatherRepository(self._write_db_path, use_pool=False)
                repo.create_table()
                if self.davis is not None and hasattr(self.davis, "configure_database_path"):
                    self.davis.configure_database_path(db_path)
                self.logMessage.emit(
                    "SQLITE",
                    "info",
                    f"Histórico Davis listo en {DavisWeatherRepository.TABLE_NAME} sin datos de prueba",
                )
            return ok
        except Exception as e:  # pragma: no cover - defensive
            self.logMessage.emit("SQLITE", "error", f"Error configurando SQLite: {e}")
            return False

    @pyqtSlot(result="QVariantList")
    def listTables(self) -> list:
        """List the tables available in the analysis database, with row counts.

        Returns:
            List of ``{name, count}`` dicts, ordered as stored (empty on error).
        """
        try:
            repo = IrradianceRepository(self._db_path, use_pool=False)
            out = []
            for name in repo.get_tables():
                if name.startswith("sqlite_") or name in ("schema_version",):
                    continue
                try:
                    rows = repo.get_records(name, None, None, raise_on_error=True)
                    out.append({"name": name, "count": len(rows)})
                except Exception:
                    continue  # tabla sin el esquema de mediciones
            return out
        except Exception as e:  # pragma: no cover - defensive
            self.logMessage.emit("SQLITE", "error", f"Error listando tablas: {e}")
            return []

    @pyqtSlot(str, result=bool)
    def setAnalysisTable(self, table: str) -> bool:
        """Point the Análisis view at another table of the analysis database."""
        if not table:
            return False
        self._db_table = table
        return True

    @pyqtSlot(str, str, result="QVariantMap")
    def loadAnalysis(self, date_from: str, date_to: str) -> dict:
        """Return stored measurements for the Análisis view from the configured DB.

        A query failure and an empty table are different situations and the UI
        must be able to tell them apart, so the result carries an explicit
        ``ok``/``error`` instead of collapsing both into an empty list.

        Args:
            date_from: Inclusive lower bound (YYYY-MM-DD) or "" for no bound.
            date_to: Inclusive upper bound (YYYY-MM-DD) or "" for no bound.

        Returns:
            ``{ok: bool, error: str, table: str, rows: [{id, fecha, hora, irradiancia}]}``
        """
        try:
            repo = IrradianceRepository(self._db_path, use_pool=False)
            rows = repo.get_records(self._db_table, date_from or None, date_to or None, raise_on_error=True)
            return {"ok": True, "error": "", "table": self._db_table, "rows": rows}
        except Exception as e:  # pragma: no cover - defensive
            msg = str(e)
            self.logMessage.emit("SQLITE", "error", f"Error leyendo análisis: {msg}")
            return {"ok": False, "error": msg, "table": self._db_table, "rows": []}

    def _davis_status_payload(self) -> dict:
        if self.davis is None:
            return {
                "available": False,
                "connected": False,
                "transport": "",
                "serial_port": "",
                "ip_host": "",
                "ip_port": 0,
                "last_error": "Lector Davis no disponible",
                "read_count": 0,
                "last_reading": {},
            }
        transport = str(self.davis._get_config("transport", "serial"))
        return {
            "available": True,
            "connected": bool(getattr(self.davis, "is_connected", False)),
            "transport": transport,
            "serial_port": str(self.davis._get_config("serial_port", "")),
            "ip_host": str(self.davis._get_config("ip_host", "")),
            "ip_port": int(self.davis._get_config("ip_port", 0)),
            "last_error": str(getattr(self.davis, "last_error", "") or ""),
            "read_count": int(getattr(self.davis, "read_count", 0) or 0),
            "last_reading": (
                self.davis.last_reading.as_dict()
                if getattr(self.davis, "last_reading", None) is not None
                else {}
            ),
        }

    def _davis_connection_label(self, connected: bool) -> str:
        if not connected:
            return "Desconectada"
        if self.davis is None:
            return "Lector Davis no disponible"
        transport = str(self.davis._get_config("transport", "serial")).lower()
        return "Conectada por Davis USB" if transport == "serial" else "Conectada por Davis IP"

    @pyqtSlot(result=str)
    def browseDbFile(self) -> str:
        """Open a native file dialog and return the chosen database path."""
        from PyQt6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(None, "Base de datos SQLite", "", "SQLite (*.db *.sqlite)")
        return path or ""
