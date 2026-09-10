from PyQt6.QtWidgets import QSplashScreen, QLabel, QProgressBar
from PyQt6.QtGui import QPixmap, QFont, QColor, QPainter, QLinearGradient, QPen
from PyQt6.QtCore import Qt
import os


class NexoSolarSplashScreen(QSplashScreen):
    """Startup screen with progress feedback for long application loading."""

    def __init__(self, parent=None):
        self._progress_value = 0

        splash_img_path = os.path.join(os.path.dirname(__file__), "assets", "splash_futurista.png")
        if os.path.exists(splash_img_path):
            pixmap = QPixmap(splash_img_path)
        else:
            pixmap = self._create_default_background()

        super().__init__(pixmap)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setWindowOpacity(0.97)

        self.label = QLabel("Nexo Solar", self)
        self.label.setStyleSheet("color: #f6fff8; font-size: 34px; font-weight: 700; background: transparent;")
        self.label.setFont(QFont("Inter", 30, QFont.Weight.Bold))
        self.label.setGeometry(42, 42, 420, 48)

        self.subtitle = QLabel("Banco de pruebas solar y meteorológico", self)
        self.subtitle.setStyleSheet("color: #d6f5dc; font-size: 17px; background: transparent;")
        self.subtitle.setFont(QFont("Inter", 14))
        self.subtitle.setGeometry(44, 96, 420, 28)

        self.line = QLabel(self)
        self.line.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #34c759, stop:0.55 #f2b705, stop:1 #1f6feb);"
            "border-radius: 2px;"
        )
        self.line.setGeometry(44, 132, 378, 4)

        logo_path = os.path.join(os.path.dirname(__file__), "assets", "LogoNexoSolar.png")
        if os.path.exists(logo_path):
            logo = QPixmap(logo_path).scaled(
                80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            self.logo_label = QLabel(self)
            self.logo_label.setPixmap(logo)
            self.logo_label.setGeometry(576, 38, 92, 92)

        self.dynamic_label = QLabel("Preparando entorno de ejecución...", self)
        self.dynamic_label.setStyleSheet("color: #f6fff8; font-size: 15px; background: transparent;")
        self.dynamic_label.setFont(QFont("Inter", 12))
        self.dynamic_label.setGeometry(44, 258, 620, 28)

        self.progress_label = QLabel("0 %", self)
        self.progress_label.setStyleSheet("color: #d6f5dc; font-size: 13px; background: transparent;")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.progress_label.setGeometry(578, 292, 86, 20)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setGeometry(44, 318, 620, 16)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                background: rgba(246, 255, 248, 0.18);
                border: 1px solid rgba(214, 245, 220, 0.35);
                border-radius: 8px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #34c759, stop:0.55 #f2b705, stop:1 #1f6feb);
                border-radius: 7px;
            }
            """
        )

        self.footer = QLabel("SENA CIDT · Barrancabermeja", self)
        self.footer.setStyleSheet("color: rgba(246, 255, 248, 0.74); font-size: 12px; background: transparent;")
        self.footer.setFont(QFont("Inter", 10))
        self.footer.setGeometry(44, 362, 360, 24)

    def set_dynamic_message(self, msg):
        self.set_progress(self._progress_value, msg)

    def set_progress(self, value, message):
        """Update the visible startup progress and current stage text."""
        self._progress_value = max(0, min(100, int(value)))
        self.dynamic_label.setText(message)
        self.progress_bar.setValue(self._progress_value)
        self.progress_label.setText(f"{self._progress_value} %")
        self.repaint()

    def set_error(self, message):
        """Show a startup error on the splash screen before the app exits."""
        self.dynamic_label.setText(message)
        self.dynamic_label.setStyleSheet("color: #ffd2cc; font-size: 15px; background: transparent;")
        self.progress_label.setText("Error")
        self.repaint()

    def _create_default_background(self):
        """Create a lightweight branded background without external assets."""
        width = 708
        height = 408
        pixmap = QPixmap(width, height)
        pixmap.fill(QColor("#123f22"))

        painter = QPainter(pixmap)
        gradient = QLinearGradient(0, 0, width, height)
        gradient.setColorAt(0, QColor("#0f2e1a"))
        gradient.setColorAt(0.52, QColor("#12641f"))
        gradient.setColorAt(1, QColor("#071319"))
        painter.fillRect(0, 0, width, height, gradient)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(242, 183, 5, 72), 2))
        painter.drawArc(width - 226, -88, 286, 286, 200 * 16, 116 * 16)
        painter.setPen(QPen(QColor(31, 111, 235, 65), 1))
        painter.drawLine(72, 218, width - 84, 164)
        painter.drawLine(72, 236, width - 84, 182)
        painter.setBrush(QColor(246, 255, 248, 24))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(24, 24, width - 48, height - 48, 18, 18)
        painter.end()
        return pixmap
