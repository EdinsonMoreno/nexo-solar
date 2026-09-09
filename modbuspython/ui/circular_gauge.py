"""
Gauge semicircular personalizado para mostrar irradiancia solar
Estilo similar a LabVIEW con gradiente de colores
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QPaintEvent
from PyQt6.QtCore import Qt, QRect
from typing import Optional, List, Tuple
import math


class CircularGauge(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(300, 200)
        self.setMaximumSize(600, 400)

        # Configuración del gauge
        self.min_value: float = 0
        self.max_value: float = 2000
        self.current_value: float = 0
        self.start_angle: int = 180  # Empezar desde la izquierda (180°)
        self.span_angle: int = 180  # Cubrir 180° (semicírculo)

        # Configuración de colores (gradiente como en la imagen)
        self.colors: List[Tuple[float, QColor]] = [
            (0, QColor(0, 255, 0)),  # Verde para valores bajos
            (400, QColor(128, 255, 0)),  # Verde-amarillo
            (800, QColor(255, 255, 0)),  # Amarillo
            (1200, QColor(255, 128, 0)),  # Naranja
            (1600, QColor(255, 0, 0)),  # Rojo
            (2000, QColor(139, 0, 0)),  # Rojo oscuro para máximo
        ]

    def setRange(self, min_val: float, max_val: float) -> None:
        """Establecer el rango del gauge"""
        self.min_value = min_val
        self.max_value = max_val
        self.update()

    def setValue(self, value: float) -> None:
        """Establecer el valor actual"""
        self.current_value = max(self.min_value, min(value, self.max_value))
        self.update()

    def value(self) -> float:
        """Obtener el valor actual"""
        return self.current_value

    def getColorForValue(self, value: float) -> QColor:
        """Obtener color basado en el valor"""
        for i, (threshold, color) in enumerate(self.colors):
            if value <= threshold:
                if i == 0:
                    return color
                # Interpolar entre colores
                prev_threshold, prev_color = self.colors[i - 1]
                ratio = (value - prev_threshold) / (threshold - prev_threshold)

                r = int(prev_color.red() + (color.red() - prev_color.red()) * ratio)
                g = int(prev_color.green() + (color.green() - prev_color.green()) * ratio)
                b = int(prev_color.blue() + (color.blue() - prev_color.blue()) * ratio)

                return QColor(r, g, b)

        return self.colors[-1][1]  # Retornar el último color si excede

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Obtener dimensiones
        width = self.width()
        height = self.height()

        # Calcular el rectángulo para el arco
        side = min(width, height * 2) - 40  # Dejar margen
        gauge_rect = QRect((width - side) // 2, height - side // 2 + 20, side, side)

        # Dibujar el fondo del gauge (gris)
        painter.setPen(QPen(QColor(150, 150, 150), 8))
        painter.drawArc(gauge_rect, self.start_angle * 16, self.span_angle * 16)

        # Dibujar segmentos de colores
        segment_angle = self.span_angle / len(self.colors)
        for i, (threshold, color) in enumerate(self.colors):
            start = self.start_angle + i * segment_angle
            painter.setPen(QPen(color, 12))
            painter.drawArc(gauge_rect, int(start * 16), int(segment_angle * 16))

        # Calcular la posición de la aguja
        value_ratio = (self.current_value - self.min_value) / (self.max_value - self.min_value)
        needle_angle = self.start_angle - value_ratio * self.span_angle

        # Dibujar la aguja
        center_x = width // 2
        center_y = height - 20
        radius = side // 2 - 30

        needle_x = center_x + radius * math.cos(math.radians(needle_angle))
        needle_y = center_y - radius * math.sin(math.radians(needle_angle))

        # Aguja roja gruesa
        painter.setPen(QPen(QColor(200, 0, 0), 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(center_x, center_y, int(needle_x), int(needle_y))

        # Centro de la aguja
        painter.setBrush(QBrush(QColor(100, 100, 100)))
        painter.setPen(QPen(QColor(50, 50, 50), 2))
        painter.drawEllipse(center_x - 8, center_y - 8, 16, 16)

        # Dibujar marcas principales
        painter.setPen(QPen(QColor(50, 50, 50), 2))
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))

        # Marcas de valores
        major_ticks = [0, 400, 800, 1200, 1600, 2000]
        for tick_value in major_ticks:
            tick_ratio = tick_value / (self.max_value - self.min_value)
            tick_angle = self.start_angle + tick_ratio * self.span_angle

            # Posición de la marca
            inner_radius = radius - 15
            outer_radius = radius - 5

            inner_x = center_x + inner_radius * math.cos(math.radians(tick_angle))
            inner_y = center_y - inner_radius * math.sin(math.radians(tick_angle))
            outer_x = center_x + outer_radius * math.cos(math.radians(tick_angle))
            outer_y = center_y - outer_radius * math.sin(math.radians(tick_angle))

            painter.drawLine(int(inner_x), int(inner_y), int(outer_x), int(outer_y))

            # Etiquetas de texto
            text_radius = radius + 15
            text_x = center_x + text_radius * math.cos(math.radians(tick_angle))
            text_y = center_y - text_radius * math.sin(math.radians(tick_angle))

            painter.drawText(int(text_x - 20), int(text_y + 5), 40, 20, Qt.AlignmentFlag.AlignCenter, str(tick_value))

        # Dibujar marcas menores
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        minor_ticks = [200, 600, 1000, 1400, 1800]
        for tick_value in minor_ticks:
            tick_ratio = tick_value / (self.max_value - self.min_value)
            tick_angle = self.start_angle + tick_ratio * self.span_angle

            inner_radius = radius - 10
            outer_radius = radius - 5

            inner_x = center_x + inner_radius * math.cos(math.radians(tick_angle))
            inner_y = center_y - inner_radius * math.sin(math.radians(tick_angle))
            outer_x = center_x + outer_radius * math.cos(math.radians(tick_angle))
            outer_y = center_y - outer_radius * math.sin(math.radians(tick_angle))

            painter.drawLine(int(inner_x), int(inner_y), int(outer_x), int(outer_y))

        painter.end()
