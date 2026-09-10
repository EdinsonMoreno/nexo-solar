"""Nexo Solar main application.

This module provides the main application window and entry point for the
Nexo Solar system. It initializes all components, manages tabs,
and handles application lifecycle.

Requirements validated: 1.4, 6.2, 10.1, 10.2, 10.3, 10.4, 10.9
"""

import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt
from typing import Optional
from .ui.web_dashboard import WebDashboard
from .data_access.modbus_client import ModbusClient as ModbusManager
from .data_access.davis_weatherlink import DavisWeatherLinkReader
from .ui.splash_screen import NexoSolarSplashScreen
from .data_access.logging_service import LoggingService
from .config.config_manager import ConfigurationManager
from .config.config_defaults import DEFAULT_CONFIG
from pathlib import Path


class MainWindow(QMainWindow):
    """Main application window for Nexo Solar.

    Provides the main UI with tabbed interface for monitoring, location,
    diagnostics, and documentation. Manages Modbus client lifecycle and
    handles graceful shutdown with resource cleanup.

    Attributes:
        config: Configuration manager instance
        logger: Logging service instance
        modbus_manager: Modbus client for device communication
        tabs: Tab widget containing all application tabs
    Requirements validated: 1.4, 6.2, 10.1, 10.2, 10.3, 10.4, 10.9
    """

    def __init__(self, config: Optional[ConfigurationManager] = None) -> None:
        """Initialize the main application window.

        Args:
            config: Optional ConfigurationManager instance. If None, uses defaults.

        Requirements validated: 1.4, 2.1, 2.2
        """
        self.config: Optional[ConfigurationManager] = config
        self.logger: LoggingService = LoggingService()
        self.modbus_manager: ModbusManager
        self.davis_reader: DavisWeatherLinkReader

        self.logger.info("Starting MainWindow initialization")
        super().__init__()
        self.setWindowTitle("Nexo Solar")
        self.setMinimumSize(1400, 800)
        self.setStyleSheet("QMainWindow { background: #0d1117; }")

        self._setup_modbus()
        self._setup_davis_reader()
        self._setup_dashboard()
        self.logger.info("MainWindow initialization completed successfully")

    def _setup_dashboard(self) -> None:
        """Set the embedded web dashboard (Mockup SPA) as the main UI."""
        self.dashboard = WebDashboard(modbus_manager=self.modbus_manager, davis_reader=self.davis_reader)
        self.setCentralWidget(self.dashboard)

    def _setup_modbus(self) -> None:
        """Initialize and start the Modbus client."""
        modbus_defaults = DEFAULT_CONFIG["modbus"]
        if self.config:
            modbus_config = self.config.modbus_config
            modbus_enabled = bool(modbus_config.get("enabled", modbus_defaults.get("enabled", False)))
            modbus_host = modbus_config.get("host", modbus_defaults["host"])
            modbus_port = modbus_config.get("port", modbus_defaults["port"])
        else:
            modbus_enabled = bool(modbus_defaults.get("enabled", False))
            modbus_host = modbus_defaults["host"]
            modbus_port = modbus_defaults["port"]

        self.logger.debug(f"Creating ModbusManager with host={modbus_host}, port={modbus_port}")
        self.modbus_manager = ModbusManager(ip=modbus_host, port=modbus_port, config_manager=self.config)
        self.modbus_manager.retry_exhausted.connect(self._on_retry_exhausted)
        if modbus_enabled:
            self.modbus_manager.start()
            self.logger.debug("ModbusClient thread started")
        else:
            self.logger.info("ModbusClient startup skipped because modbus.enabled=false")

    def _setup_davis_reader(self) -> None:
        """Initialize the Davis WeatherLink reader thread."""
        self.davis_reader = DavisWeatherLinkReader(config_manager=self.config)
        self.davis_reader.retry_exhausted.connect(self._on_davis_retry_exhausted)
        self.davis_reader.start()
        self.logger.debug("DavisWeatherLinkReader thread started")

    def _on_retry_exhausted(self, operation: str, error_message: str) -> None:
        """Handle retry exhaustion signal from ModbusClient.

        Shows critical error notification to user when retry limit is exceeded.
        Indicates if system has entered safe state.

        Args:
            operation: Name of failed operation (e.g., "Connection", "Read Radiation")
            error_message: Detailed error message

        Requirements validated: 4.10
        """
        self.logger.error(f"Retry exhausted for operation '{operation}': {error_message}")

        # Determine if system is in safe state
        safe_state_msg = ""
        if self.modbus_manager.is_in_safe_state():
            safe_state_msg = "\n\n⚠️ El sistema ha entrado en MODO SEGURO. Las operaciones de escritura están deshabilitadas hasta que se resuelva el problema."

        # Show critical error dialog to user
        QMessageBox.critical(
            self,
            f"Error Crítico: {operation}",
            f"La operación '{operation}' ha fallado después de todos los intentos de reintento.\n\n"
            f"Detalles del error:\n{error_message}\n\n"
            f"Por favor, verifique:\n"
            f"• La conexión de red al dispositivo Modbus\n"
            f"• Que el dispositivo esté encendido y accesible\n"
            f"• La configuración de IP y puerto{safe_state_msg}",
        )

        self.logger.info(f"User notified about retry exhaustion for operation: {operation}")

    def _on_davis_retry_exhausted(self, operation: str, error_message: str) -> None:
        """Log Davis retry exhaustion without interrupting application startup."""
        self.logger.error(f"Davis retry exhausted for operation '{operation}': {error_message}")

    def closeEvent(self, event) -> None:
        """Handle application close event with proper resource cleanup.

        Stops ModbusClient thread gracefully, cleans up all tabs, clears
        QWebEngine cache, and closes log handlers. Ensures no resource leaks.

        Args:
            event: Qt close event

        Requirements validated: 10.1, 10.2, 10.3, 10.4, 10.7, 10.8, 10.9
        """
        self.logger.info("Application closing, cleaning up resources")

        self._cleanup_dashboard()
        self._stop_davis_reader()
        self._stop_modbus_client()
        self._clear_web_engine_cache()
        self._close_log_handlers()

        self.logger.info("Application closed successfully")
        event.accept()

    def _cleanup_dashboard(self) -> None:
        """Clean up the web dashboard (bridge, channel, web page)."""
        try:
            if hasattr(self, "dashboard"):
                self.dashboard.cleanup()
        except Exception as e:
            self.logger.error(f"Error cleaning up dashboard: {e}")

    def _stop_modbus_client(self) -> None:
        """Stop the ModbusClient thread gracefully."""
        if hasattr(self, "modbus_manager"):
            try:
                self.modbus_manager.stop()
                self.logger.debug("ModbusClient thread stopped")
            except Exception as e:
                self.logger.error(f"Error stopping ModbusClient: {e}")

    def _stop_davis_reader(self) -> None:
        """Stop the Davis reader thread gracefully."""
        if hasattr(self, "davis_reader"):
            try:
                self.davis_reader.stop()
                self.logger.debug("DavisWeatherLinkReader thread stopped")
            except Exception as e:
                self.logger.error(f"Error stopping DavisWeatherLinkReader: {e}")

    def _clear_web_engine_cache(self) -> None:
        """Clean up QWebEngine cache and temporary files."""
        try:
            from PyQt6.QtWebEngineCore import QWebEngineProfile

            # Get the default profile and clear all caches
            profile = QWebEngineProfile.defaultProfile()
            profile.clearHttpCache()
            profile.clearAllVisitedLinks()
            self.logger.debug("QWebEngine cache cleared")
        except ImportError:
            self.logger.debug("QWebEngineCore not available, skipping web cache cleanup")
        except Exception as e:
            self.logger.error(f"Error clearing QWebEngine cache: {e}")

    def _close_log_handlers(self) -> None:
        """Flush and close all log handlers."""
        try:
            if hasattr(self, "logger") and hasattr(self.logger, "_logger") and self.logger._logger:
                for handler in self.logger._logger.handlers[:]:
                    handler.flush()
                    handler.close()
                    self.logger._logger.removeHandler(handler)
                self.logger.debug("Log handlers flushed and closed")
        except Exception as e:
            # Use stderr as logger might be unavailable
            sys.stderr.write(f"Error closing log handlers: {e}\n")


def main() -> int:
    """Run the Nexo Solar application.

    Initializes configuration, logging, and Qt application. Shows splash screen
    during startup and launches the main window.

    Returns:
        int: Application exit code

    Requirements validated: 1.4, 2.1, 2.7, 5.1, 5.2, 5.3
    """
    # Ajuste para recursos PyInstaller
    if hasattr(sys, "_MEIPASS"):
        os.chdir(sys._MEIPASS)

    # Load configuration at startup
    from .config.config_manager import ConfigurationManager

    config = ConfigurationManager()
    config_path = Path("config.yaml")
    schema_path = Path("modbuspython/config/config_schema.json")

    try:
        config.load_config(config_path, schema_path)
    except FileNotFoundError as e:
        # Schema file is required - cannot proceed without it
        sys.stderr.write(f"CRITICAL: Configuration schema not found: {e}\n")
        sys.stderr.write("Application cannot start without config_schema.json\n")
        sys.exit(1)
    except Exception as e:
        # Other errors during config load - log and use defaults
        sys.stderr.write(f"WARNING: Error loading configuration: {e}\n")
        sys.stderr.write("Using default configuration values\n")

    # Initialize logging service with configuration
    logger = LoggingService()
    logging_config = config.logging_config
    logger.setup(
        log_file=Path(logging_config.get("file_path", "logs/nexo_solar.log")),
        level=logging_config.get("level", "INFO"),
        max_bytes=logging_config.get("max_bytes", 10485760),
        backup_count=logging_config.get("backup_count", 5),
    )
    logger.info("Nexo Solar application starting")
    logger.info(f"Configuration loaded from: {config_path}")

    # Verify schema version and apply pending migrations on startup (Requirement 13.7)
    db_config = config.database_config
    db_path = db_config.get("path", "nexo_solar.db")
    try:
        from .data_access.database_manager import SchemaVersionRepository
        from .migrations.migration_manager import MigrationManager
        from .exceptions import MigrationError

        schema_repo = SchemaVersionRepository(db_path=db_path, use_pool=False)
        current_version = schema_repo.get_schema_version()
        version_info = schema_repo.get_version_info()
        logger.info(
            f"Database schema version verified: {current_version}",
            version=current_version,
            applied_at=version_info.get("applied_at") if version_info else None,
        )

        # Apply any pending migrations
        migration_manager = MigrationManager(db_path=db_path)
        pending = migration_manager.get_pending_migrations()
        if pending:
            logger.info(f"Applying {len(pending)} pending migrations")
            try:
                applied = migration_manager.apply_all_pending()
                logger.info(f"Successfully applied migrations: v{applied}")
            except MigrationError as e:
                logger.error(f"Migration failed, application will continue with current schema: {e}")
                # Log details but don't crash - existing functionality may still work
                sys.stderr.write(f"WARNING: Database migration failed: {e}\n")
                sys.stderr.write("Application will continue with current schema version.\n")
        else:
            logger.info("No pending migrations to apply")

    except Exception as e:
        logger.warning(f"Could not verify schema version or apply migrations: {e}. Continuing with startup.")

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    # Pantalla de carga futurista
    splash = NexoSolarSplashScreen()
    splash.show()
    app.processEvents()
    # Paleta personalizada estilo LabVIEW
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(188, 190, 192))
    palette.setColor(QPalette.ColorRole.Base, QColor(224, 224, 224))
    palette.setColor(QPalette.ColorRole.Button, QColor(211, 211, 211))
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.black)
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.black)
    palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 95, 163))
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
    app.setPalette(palette)
    # Simular carga de módulos pesados (puedes actualizar el mensaje dinámico aquí)
    splash.set_dynamic_message("Cargando módulos principales...")
    window = MainWindow(config=config)
    window.show()
    splash.finish(window)
    logger.info("Nexo Solar application started successfully")
    return int(app.exec())


if __name__ == "__main__":
    sys.exit(main())
