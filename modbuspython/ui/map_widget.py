# Widget de mapa interactivo basado en Leaflet y QWebEngineView.
# Si WebEngine no está disponible, muestra un modo fallback con coordenadas y enlaces externos.

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView

    _webengine_imported = True
except ImportError:
    QWebEngineView = None
    _webengine_imported = False
from PyQt6.QtCore import pyqtSignal, QUrl
from PyQt6.QtGui import QFont
from ..data_access.logging_service import LoggingService
import os
import sys


class MapWidget(QWidget):
    # Señal para notificar cuando se selecciona una ubicación en el mapa
    location_selected = pyqtSignal(float, float)

    def __init__(self, lat=19.4326, lon=-99.1332, zoom=13, parent=None):
        super().__init__(parent)
        self.logger = LoggingService()
        self.lat = lat
        self.lon = lon
        self.zoom = zoom
        self._webengine_available = _webengine_imported
        # Layout principal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        # Información de coordenadas (siempre visible)
        self.coords_label = QLabel(f"📍 Lat: {lat:.6f}, Lon: {lon:.6f}")
        self.coords_label.setStyleSheet("""
            QLabel {
                background: #e8f4fd;
                color: #2c3e50;
                padding: 8px;
                border: 1px solid #3498db;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.coords_label)
        if self._webengine_available:
            try:
                self.logger.info("Inicializando QWebEngineView")
                self.webview = QWebEngineView()
                # Permitir acceso a recursos locales y remotos
                try:
                    from PyQt6.QtWebEngineCore import QWebEngineSettings

                    self.webview.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
                    self.webview.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
                except Exception as e:
                    self.logger.debug(f"No se pudo establecer LocalContentCanAccessFileUrls/RemoteUrls: {e}")
                layout.addWidget(self.webview)
                self.setMinimumHeight(400)
                self.setMaximumHeight(600)
                # Conectar evento de carga para saber si el HTML se renderizó correctamente
                self.webview.loadFinished.connect(self._on_load_finished)
                self.logger.info("QWebEngineView creado exitosamente")
                # Cargar el HTML estático del mapa
                self.generate_map(lat, lon, zoom)
                self.webview.page().urlChanged.connect(self._on_url_changed)
            except Exception as e:
                self.logger.error(f"Error inicializando WebEngine: {e}")
                self._webengine_available = False
                self._create_fallback_widget(layout)
        else:
            self.logger.warning("WebEngine no disponible, se usará modo fallback")
            self._create_fallback_widget(layout)

    def _create_fallback_widget(self, layout):
        """
        Crea un widget alternativo cuando WebEngine no está disponible.
        Muestra solo coordenadas y enlaces a Google Maps/OpenStreetMap.
        """
        fallback_widget = QWidget()
        fallback_widget.setStyleSheet("""
            QWidget {
                background: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 8px;
            }
        """)
        fallback_layout = QVBoxLayout(fallback_widget)
        fallback_layout.setContentsMargins(20, 20, 20, 20)

        # Título
        title = QLabel("🗺️ Visor de Mapas")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        fallback_layout.addWidget(title)

        # Información
        info = QLabel("WebEngine no disponible. Mostrando información básica de coordenadas.")
        info.setStyleSheet("color: #6c757d; margin-bottom: 15px;")
        fallback_layout.addWidget(info)

        # Coordenadas actuales
        self.fallback_coords = QLabel()
        self.fallback_coords.setStyleSheet("""
            QLabel {
                background: white;
                padding: 15px;
                border: 1px solid #ced4da;
                border-radius: 5px;
                font-family: monospace;
                font-size: 14px;
                color: #495057;
            }
        """)
        self._update_fallback_coords()
        fallback_layout.addWidget(self.fallback_coords)

        # Botones para servicios externos
        buttons_layout = QHBoxLayout()

        self.btn_google_maps = QPushButton("🌍 Abrir en Google Maps")
        self.btn_google_maps.setStyleSheet("""
            QPushButton {
                background: #4285f4;
                color: white;
                border: none;
                padding: 10px 15px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background: #3367d6; }
        """)
        self.btn_google_maps.clicked.connect(self._open_google_maps)
        buttons_layout.addWidget(self.btn_google_maps)

        self.btn_openstreetmap = QPushButton("🗺️ Abrir en OpenStreetMap")
        self.btn_openstreetmap.setStyleSheet("""
            QPushButton {
                background: #7ebc6f;
                color: white;
                border: none;
                padding: 10px 15px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background: #6da55f; }
        """)
        self.btn_openstreetmap.clicked.connect(self._open_openstreetmap)
        buttons_layout.addWidget(self.btn_openstreetmap)

        fallback_layout.addLayout(buttons_layout)
        fallback_layout.addStretch()

        layout.addWidget(fallback_widget)
        self.setMinimumHeight(300)
        self.setMaximumHeight(400)

    def generate_map(self, lat, lon, zoom):
        """Generate and load the map with given coordinates and zoom level."""
        self.logger.info(f"Cargando mapa estático: lat={lat}, lon={lon}, zoom={zoom}")
        self.lat = lat
        self.lon = lon
        self.zoom = zoom
        self.coords_label.setText(f"📍 Lat: {lat:.6f}, Lon: {lon:.6f}")
        if not self._webengine_available:
            self.logger.warning("WebEngine no disponible, usando fallback")
            self._update_fallback_coords()
            return
        try:
            # Soporte para PyInstaller (sys._MEIPASS)
            if hasattr(sys, "_MEIPASS"):
                # En el ejecutable, los recursos están en 'ui/assets/mapa.html'
                html_path = os.path.join(sys._MEIPASS, "ui", "assets", "mapa.html")
            else:
                # En desarrollo, están en 'modbuspython/ui/assets/mapa.html'
                html_path = os.path.join(os.path.dirname(__file__), "assets", "mapa.html")
            if not os.path.exists(html_path):
                raise Exception(f"No se encontró el archivo de mapa: {html_path}")
            url = QUrl.fromLocalFile(os.path.abspath(html_path))
            self.logger.debug(f"Cargando URL: {url.toString()}")
            self.webview.setUrl(url)
        except Exception as e:
            self.logger.error(f"Error cargando mapa: {e}")
            self._show_error_message(lat, lon, str(e))

    def _show_error_message(self, lat, lon, error_msg):
        """Muestra un mensaje de error cuando no se puede cargar el mapa."""
        simple_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error - Mapa</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    text-align: center;
                    margin: 50px;
                    background-color: #f5f5f5;
                }}
                .error-container {{
                    background-color: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    max-width: 400px;
                    margin: 0 auto;
                }}
                .coordinates {{
                    background-color: #e7f3ff;
                    padding: 10px;
                    border-radius: 4px;
                    margin: 10px 0;
                    font-family: monospace;
                }}
            </style>
        </head>
        <body>
            <div class="error-container">
                <h3>⚠️ Error cargando mapa</h3>
                <div class="coordinates">
                    <strong>Coordenadas:</strong><br>
                    Latitud: {lat:.6f}<br>
                    Longitud: {lon:.6f}
                </div>
                <p><strong>Error:</strong> {error_msg}</p>
                <p>Intente recargar la aplicación o verifique la conexión a internet.</p>
            </div>
        </body>
        </html>
        """
        self.webview.setHtml(simple_html)

    def set_location(self, lat, lon, zoom=None):
        """Actualiza la ubicación del mapa y mueve el marcador en el mapa interactivo."""
        self.lat = lat
        self.lon = lon
        if zoom is not None:
            self.zoom = zoom
        self.coords_label.setText(f"📍 Lat: {lat:.6f}, Lon: {lon:.6f}")
        if not self._webengine_available:
            self._update_fallback_coords()
        else:
            # Ejecutar JS para mover el marcador y centrar el mapa
            js = f"setMapLocation({lat}, {lon});"
            self.webview.page().runJavaScript(js)

    def _on_url_changed(self, url):
        """Detecta si el hash contiene lat/lon seleccionados."""
        url_str = url.toString()
        if "#" not in url_str:
            return

        hash_part = url_str.split("#", 1)[1]
        if "lat=" not in hash_part or "lng=" not in hash_part:
            return

        try:
            lat, lng = self._parse_coordinates_from_hash(hash_part)
            if lat is not None and lng is not None:
                self.location_selected.emit(lat, lng)
        except Exception as e:
            self.logger.error(f"Error procesando coordenadas: {e}")

    def _parse_coordinates_from_hash(self, hash_part: str) -> tuple:
        """Parse latitude and longitude from URL hash parameters.

        Args:
            hash_part: The hash portion of the URL containing parameters

        Returns:
            tuple: (lat, lng) or (None, None) if not found
        """
        params = hash_part.split("&")
        lat = None
        lng = None

        for param in params:
            if param.startswith("lat="):
                lat = float(param.replace("lat=", ""))
            elif param.startswith("lng="):
                lng = float(param.replace("lng=", ""))

        return lat, lng

    def closeEvent(self, event):
        """Limpia recursos al cerrar el widget."""
        self.cleanup()
        event.accept()

    def cleanup(self):
        """Clean up QWebEngineView resources and temporary files."""
        self.logger.debug("MapWidget cleanup: releasing resources")

        # Clean up QWebEngineView resources
        if self._webengine_available and hasattr(self, "webview"):
            try:
                # Disconnect signals to prevent callbacks during cleanup
                try:
                    self.webview.loadFinished.disconnect()
                except TypeError:
                    pass  # Signal was not connected

                try:
                    self.webview.page().urlChanged.disconnect()
                except TypeError:
                    pass  # Signal was not connected

                # Stop any ongoing page loading
                self.webview.stop()

                # Load blank page to release resources
                self.webview.setHtml("")

                # Delete the web page and view
                if self.webview.page():
                    self.webview.page().deleteLater()
                self.webview.deleteLater()

                self.logger.debug("QWebEngineView resources released")
            except Exception as e:
                self.logger.error(f"Error cleaning up QWebEngineView: {e}")

    def __del__(self):
        """Destructor para asegurar limpieza de recursos."""
        if hasattr(self, "logger"):
            self.logger.debug("MapWidget destructor called")

    def _update_fallback_coords(self):
        """Actualiza la información de coordenadas en el widget fallback"""
        if hasattr(self, "fallback_coords"):
            coord_text = f"""
Coordenadas Actuales:
  Latitud:  {self.lat:.6f}°
  Longitud: {self.lon:.6f}°
  Zoom:     {self.zoom}

Información Solar:
  Hemisferio: {'Norte' if self.lat >= 0 else 'Sur'}
  Zona UTC:   {int(self.lon / 15):.0f}

Haga clic en los botones para ver la ubicación
en servicios de mapas externos.
            """
            self.fallback_coords.setText(coord_text.strip())

    def _open_google_maps(self):
        """Abre la ubicación en Google Maps"""
        import webbrowser

        url = f"https://maps.google.com/?q={self.lat},{self.lon}&z={self.zoom}"
        webbrowser.open(url)

    def _open_openstreetmap(self):
        """Abre la ubicación en OpenStreetMap"""
        import webbrowser

        url = f"https://www.openstreetmap.org/?mlat={self.lat}&mlon={self.lon}&zoom={self.zoom}"
        webbrowser.open(url)

    def _on_load_finished(self, success):
        """Se ejecuta cuando la página web termina de cargar"""
        if success:
            self.logger.info("Página web cargada exitosamente")
        else:
            self.logger.error("Error cargando página web")
            # Intentar obtener el contenido para debugging
            self.webview.page().toHtml(self._debug_html_content)

    def _debug_html_content(self, html_content):
        """Callback para debugging del contenido HTML"""
        self.logger.debug(f"Contenido HTML (primeros 200 chars): {html_content[:200]}...")
