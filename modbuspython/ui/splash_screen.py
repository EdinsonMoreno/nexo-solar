from PyQt6.QtWidgets import QSplashScreen, QLabel
from PyQt6.QtGui import QPixmap, QFont, QColor, QPainter, QLinearGradient
from PyQt6.QtCore import Qt
import os


class NexoSolarSplashScreen(QSplashScreen):
    def __init__(self, parent=None):
        # Cargar imagen de fondo (puedes reemplazar por tu logo o imagen futurista)
        splash_img_path = os.path.join(os.path.dirname(__file__), "assets", "splash_futurista.png")
        if os.path.exists(splash_img_path):
            pixmap = QPixmap(splash_img_path)
        else:
            # Si no hay imagen, crear fondo degradado programáticamente
            pixmap = QPixmap(600, 340)
            pixmap.fill(QColor("#0a1a2f"))
            painter = QPainter(pixmap)
            gradient = QLinearGradient(0, 0, 600, 340)
            gradient.setColorAt(0, QColor("#0a1a2f"))
            gradient.setColorAt(1, QColor("#1e90ff"))
            painter.fillRect(0, 0, 600, 340, gradient)
            painter.end()
        super().__init__(pixmap)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setWindowOpacity(0.97)
        # Texto principal
        self.label = QLabel("Nexo Solar", self)
        self.label.setStyleSheet("color: #00ffe7; font-size: 32px; font-weight: bold; text-shadow: 0 0 8px #00ffe7;")
        self.label.setFont(QFont("Consolas", 28, QFont.Weight.Bold))
        self.label.move(40, 40)
        # Subtítulo
        self.subtitle = QLabel("Cargando sistema...", self)
        self.subtitle.setStyleSheet("color: #ffffff; font-size: 18px; background: transparent;")
        self.subtitle.setFont(QFont("Consolas", 16))
        self.subtitle.move(42, 90)
        # Línea decorativa
        self.line = QLabel(self)
        self.line.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00ffe7, stop:1 #1e90ff); border-radius: 2px;"
        )
        self.line.setGeometry(40, 80, 320, 4)
        # Logo pequeño (opcional)
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "LogoNexoSolar.png")
        if os.path.exists(logo_path):
            logo = QPixmap(logo_path).scaled(
                80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            self.logo_label = QLabel(self)
            self.logo_label.setPixmap(logo)
            self.logo_label.move(480, 30)
        # Mensaje dinámico (puedes actualizarlo desde fuera)
        self.dynamic_label = QLabel("Inicializando módulos...", self)
        self.dynamic_label.setStyleSheet("color: #00ffe7; font-size: 14px; background: transparent;")
        self.dynamic_label.setFont(QFont("Consolas", 12))
        self.dynamic_label.move(42, 130)

    def set_dynamic_message(self, msg):
        self.dynamic_label.setText(msg)
