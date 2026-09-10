from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtCore import Qt
import os
import re
import sys


class DocumentationTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 10, 20, 10)
        # Logo y encabezado
        logo_row = QHBoxLayout()
        logo = QLabel()
        logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../assets/Logo.png"))
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                logo.setPixmap(
                    pixmap.scaled(220, 70, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                )
            else:
                logo.setText("Nexo Solar")
                logo.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        else:
            logo.setText("Nexo Solar")
            logo.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        logo.setStyleSheet("background: transparent;")
        logo_row.addWidget(logo)
        logo_row.addStretch()
        main_layout.addLayout(logo_row)
        main_layout.addSpacing(10)

        # Botón para recargar documentación
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.btn_reload = QPushButton("🔄 Recargar Documentación")
        self.btn_reload.setStyleSheet("""
            QPushButton {
                background: #4a6741;
                color: white;
                border: 2px solid #5a7751;
                border-radius: 8px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #5a7751;
                border-color: #6a8761;
            }
            QPushButton:pressed {
                background: #3a5731;
            }
        """)
        self.btn_reload.clicked.connect(self.cargar_documentacion)
        button_layout.addWidget(self.btn_reload)

        self.btn_toggle_view = QPushButton("📝 Vista Código")
        self.btn_toggle_view.setStyleSheet("""
            QPushButton {
                background: #2980b9;
                color: white;
                border: 2px solid #3498db;
                border-radius: 8px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #3498db;
                border-color: #5dade2;
            }
            QPushButton:pressed {
                background: #1f618d;
            }
        """)
        self.btn_toggle_view.clicked.connect(self.toggle_view_mode)
        button_layout.addWidget(self.btn_toggle_view)

        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        main_layout.addSpacing(8)

        # Visor de documentación
        self.doc_viewer = QTextEdit()
        self.doc_viewer.setReadOnly(True)
        self.doc_viewer.setStyleSheet("""
            QTextEdit {
                background: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 13px;
                line-height: 1.5;
                padding: 15px;
            }
            QScrollBar:vertical {
                background: #e9ecef;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #6c757d;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #495057;
            }
        """)
        main_layout.addWidget(self.doc_viewer)

        # Cargar documentación al inicializar
        self.cargar_documentacion()

    def cargar_documentacion(self) -> None:
        """Carga y convierte el archivo Markdown a HTML para mostrar"""
        try:
            # Buscar el archivo de forma relativa, compatible con PyInstaller
            if hasattr(sys, "_MEIPASS"):
                base_dir = sys._MEIPASS
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            doc_path = os.path.join(base_dir, "modbuspython", "DOCUMENTACION_COMPLETA.md")
            if not os.path.exists(doc_path):
                self.mostrar_error(f"Archivo no encontrado: {doc_path}")
                return
            with open(doc_path, "r", encoding="utf-8") as f:
                markdown_content = f.read()

            # Convertir Markdown a HTML básico
            html_content = self.markdown_to_html(markdown_content)

            # Establecer el contenido HTML
            self.doc_viewer.setHtml(html_content)

        except Exception as e:
            self.mostrar_error(f"Error cargando documentación: {e}")

    def markdown_to_html(self, markdown_text: str) -> str:
        """Convierte Markdown básico a HTML para visualización"""
        html = markdown_text

        # Escapar caracteres HTML especiales pero preservar algunos
        html = html.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # Convertir encabezados
        html = re.sub(
            r"^# (.*?)$",
            r'<h1 style="color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; margin-top: 25px; margin-bottom: 15px; font-size: 28px;">\1</h1>',
            html,
            flags=re.MULTILINE,
        )
        html = re.sub(
            r"^## (.*?)$",
            r'<h2 style="color: #34495e; border-bottom: 2px solid #95a5a6; padding-bottom: 8px; margin-top: 20px; margin-bottom: 12px; font-size: 24px;">\1</h2>',
            html,
            flags=re.MULTILINE,
        )
        html = re.sub(
            r"^### (.*?)$",
            r'<h3 style="color: #2c3e50; margin-top: 18px; margin-bottom: 10px; font-size: 20px;">\1</h3>',
            html,
            flags=re.MULTILINE,
        )
        html = re.sub(
            r"^#### (.*?)$",
            r'<h4 style="color: #34495e; margin-top: 15px; margin-bottom: 8px; font-size: 18px;">\1</h4>',
            html,
            flags=re.MULTILINE,
        )

        # Convertir texto en negrita y cursiva
        html = re.sub(r"\*\*(.*?)\*\*", r'<strong style="color: #2c3e50;">\1</strong>', html)
        html = re.sub(r"\*(.*?)\*", r"<em>\1</em>", html)

        # Convertir código inline
        html = re.sub(
            r"`(.*?)`",
            r'<code style="background: #ecf0f1; color: #e74c3c; padding: 2px 6px; border-radius: 4px; font-family: Consolas, Monaco, monospace;">\1</code>',
            html,
        )

        # Convertir bloques de código
        html = re.sub(
            r"```(\w+)?\n(.*?)\n```",
            r'<div style="background: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 8px; margin: 10px 0; font-family: Consolas, Monaco, monospace; font-size: 12px; line-height: 1.4; overflow-x: auto;"><pre>\2</pre></div>',
            html,
            flags=re.DOTALL,
        )

        # Convertir bloques de código simples (4 espacios)
        html = re.sub(
            r"^    (.*)$",
            r'<div style="background: #34495e; color: #ecf0f1; padding: 8px 12px; border-left: 4px solid #3498db; margin: 5px 0; font-family: Consolas, Monaco, monospace; font-size: 12px;">\1</div>',
            html,
            flags=re.MULTILINE,
        )

        # Convertir listas con viñetas
        html = re.sub(r"^- (.*?)$", r'<li style="margin: 4px 0; color: #2c3e50;">\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r"(<li.*?</li>)", r'<ul style="margin: 10px 0 10px 20px; padding: 0;">\1</ul>', html)

        # Convertir listas numeradas
        html = re.sub(r"^\d+\. (.*?)$", r'<li style="margin: 4px 0; color: #2c3e50;">\1</li>', html, flags=re.MULTILINE)

        # Convertir emojis y checkmarks
        html = html.replace("✅", '<span style="color: #27ae60; font-size: 16px;">✅</span>')
        html = html.replace("❌", '<span style="color: #e74c3c; font-size: 16px;">❌</span>')
        html = html.replace("🔧", '<span style="color: #f39c12; font-size: 16px;">🔧</span>')
        html = html.replace("📊", '<span style="color: #3498db; font-size: 16px;">📊</span>')
        html = html.replace("🌞", '<span style="color: #f1c40f; font-size: 16px;">🌞</span>')
        html = html.replace("🎯", '<span style="color: #e67e22; font-size: 16px;">🎯</span>')

        # Convertir líneas horizontales
        html = re.sub(
            r"^---+$",
            r'<hr style="border: none; border-top: 2px solid #bdc3c7; margin: 20px 0;">',
            html,
            flags=re.MULTILINE,
        )

        # Convertir párrafos
        html = re.sub(r"\n\n+", '</p><p style="margin: 12px 0; line-height: 1.6; color: #2c3e50;">', html)
        html = '<p style="margin: 12px 0; line-height: 1.6; color: #2c3e50;">' + html + "</p>"

        # Convertir saltos de línea simples
        html = html.replace("\n", "<br>")

        # Estilos CSS base
        css_style = """
        <style>
        body {
            font-family: 'Segoe UI', 'Arial', sans-serif;
            line-height: 1.6;
            color: #2c3e50;
            background: #f8f9fa;
            margin: 0;
            padding: 20px;
        }
        .content {
            max-width: 1000px;
            margin: 0 auto;
        }
        </style>
        """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            {css_style}
        </head>
        <body>
            <div class="content">
                {html}
            </div>
        </body>
        </html>
        """

    def mostrar_error(self, mensaje: str) -> None:
        """Muestra un mensaje de error en el visor"""
        error_html = f"""
        <div style="background: #f8d7da; color: #721c24; padding: 15px; border: 1px solid #f5c6cb; border-radius: 8px; margin: 20px;">
            <h3 style="margin-top: 0;">❌ Error</h3>
            <p>{mensaje}</p>
            <p><strong>Posibles soluciones:</strong></p>
            <ul>
                <li>Verificar que el archivo DOCUMENTACION_COMPLETA.md existe en el directorio raíz</li>
                <li>Comprobar permisos de lectura del archivo</li>
                <li>Hacer clic en 'Recargar Documentación' para intentar nuevamente</li>
            </ul>
        </div>
        """
        self.doc_viewer.setHtml(error_html)

    def toggle_view_mode(self):
        """Alterna entre vista HTML renderizada y vista de código Markdown puro"""
        if not hasattr(self, "_view_mode"):
            self._view_mode = "html"
        if not hasattr(self, "_markdown_cache"):
            # Cachear el markdown original
            if hasattr(sys, "_MEIPASS"):
                base_dir = sys._MEIPASS
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            doc_path = os.path.join(base_dir, "modbuspython", "DOCUMENTACION_COMPLETA.md")
            if os.path.exists(doc_path):
                with open(doc_path, "r", encoding="utf-8") as f:
                    self._markdown_cache = f.read()
            else:
                self._markdown_cache = ""
        if self._view_mode == "html":
            # Cambiar a vista código
            self.doc_viewer.setPlainText(self._markdown_cache)
            self.btn_toggle_view.setText("🌐 Vista HTML")
            self._view_mode = "markdown"
        else:
            # Cambiar a vista HTML
            html_content = self.markdown_to_html(self._markdown_cache)
            self.doc_viewer.setHtml(html_content)
            self.btn_toggle_view.setText("📝 Vista Código")
            self._view_mode = "html"
