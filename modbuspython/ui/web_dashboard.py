"""Web dashboard host widget.

Embeds the ``Mockup/`` single-page dashboard in a ``QWebEngineView`` and wires
it to the Python backend through a :class:`~modbuspython.ui.web_bridge.WebBridge`
registered on a ``QWebChannel`` as ``"bridge"``.

This widget shares the live ``ModbusManager`` instance with the native tabs, so
both UIs reflect the same backend state during the incremental migration.
"""

import os
from typing import Any, Optional

from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PyQt6.QtWebChannel import QWebChannel

from ..data_access.logging_service import LoggingService
from .web_bridge import WebBridge


def _mockup_index_path() -> str:
    """Absolute path to Mockup/index.html (repo_root/Mockup/index.html)."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, "..", "..", "Mockup", "index.html"))


class LoggingWebPage(QWebEnginePage):
    """QWebEnginePage that forwards JavaScript console output to the app log.

    Without this, JS errors inside the embedded dashboard are silently swallowed
    and never reach the Python log, which makes the web UI undebuggable.
    """

    def __init__(self, logger: LoggingService, parent: Optional[Any] = None) -> None:
        super().__init__(parent)
        self._logger = logger

    def javaScriptConsoleMessage(self, level, message, line_number, source_id) -> None:
        source = os.path.basename(source_id) if source_id else "?"
        text = f"[JS] {source}:{line_number} {message}"
        try:
            if level == QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
                self._logger.error(text)
            elif level == QWebEnginePage.JavaScriptConsoleMessageLevel.WarningMessageLevel:
                self._logger.warning(text)
            else:
                self._logger.info(text)
        except Exception:
            print(text)


class WebDashboard(QWidget):
    """Container widget that renders the web dashboard and owns the bridge."""

    def __init__(self, modbus_manager: Any, davis_reader: Optional[Any] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.logger = LoggingService()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.view = QWebEngineView()
        self.view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # El dashboard se sirve desde disco: cachearlo solo provoca que la UI
        # quede desactualizada respecto de los archivos del repo.
        try:
            QWebEngineProfile.defaultProfile().setHttpCacheType(QWebEngineProfile.HttpCacheType.NoCache)
            QWebEngineProfile.defaultProfile().clearHttpCache()
        except Exception as e:  # pragma: no cover - defensive
            self.logger.debug(f"Could not disable WebEngine HTTP cache: {e}")

        # Reencaminar la consola JS al log de la aplicacion
        self.page = LoggingWebPage(self.logger, self.view)
        self.view.setPage(self.page)

        try:
            from PyQt6.QtWebEngineCore import QWebEngineSettings

            settings = self.view.settings()
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        except Exception as e:  # pragma: no cover - defensive
            self.logger.debug(f"Could not set WebEngine local-access attributes: {e}")

        # QWebChannel + bridge
        self.channel = QWebChannel(self.view.page())
        self.bridge = WebBridge(modbus_manager, davis_reader=davis_reader)
        self.channel.registerObject("bridge", self.bridge)
        self.view.page().setWebChannel(self.channel)
        self.bridge.connect_backend()

        index_path = _mockup_index_path()
        if not os.path.exists(index_path):
            self.logger.error(f"Mockup index not found at {index_path}")
        self.view.load(QUrl.fromLocalFile(index_path))

        layout.addWidget(self.view)

    def cleanup(self) -> None:
        """Release the bridge, channel and web page."""
        self.logger.debug("WebDashboard cleanup: releasing resources")
        try:
            self.bridge.disconnect_backend()
        except Exception as e:
            self.logger.error(f"Error disconnecting bridge backend: {e}")
        try:
            self.channel.deregisterObject(self.bridge)
        except (RuntimeError, AttributeError):
            pass
        try:
            self.view.setParent(None)
            self.view.deleteLater()
            self.bridge.deleteLater()
            self.channel.deleteLater()
        except Exception as e:
            self.logger.error(f"Error cleaning up web dashboard: {e}")

    def closeEvent(self, event) -> None:
        self.cleanup()
        super().closeEvent(event)
