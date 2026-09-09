import os


from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QComboBox,
    QLineEdit,
    QPushButton,
    QLabel,
    QMessageBox,
    QFileDialog,
)


from PyQt6.QtCore import pyqtSignal


from ..backend import sqlite_manager


from ..exceptions import DatabaseError


import sqlite3


class SQLiteConfigDialog(QDialog):

    # Señal que emite (ruta_db, nombre_tabla) cuando se acepta la configuración

    configuracion_aceptada = pyqtSignal(str, str)

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setWindowTitle("Configurar Base de Datos SQLite")

        self.setModal(True)

        self.resize(450, 300)

        self.ruta_db = "./data/irradiancia.db"

        self.setup_ui()

        self.cargar_tablas()

    def setup_ui(self):

        layout = QVBoxLayout(self)

        # Grupo para selección de base de datos

        db_group = QGroupBox("Base de Datos")

        db_layout = QVBoxLayout(db_group)

        db_path_layout = QHBoxLayout()

        self.db_path_label = QLabel(f"Archivo: {self.ruta_db}")

        self.btn_cambiar_db = QPushButton("Cambiar...")

        self.btn_cambiar_db.clicked.connect(self.cambiar_base_datos)

        db_path_layout.addWidget(self.db_path_label)

        db_path_layout.addWidget(self.btn_cambiar_db)

        db_layout.addLayout(db_path_layout)

        layout.addWidget(db_group)

        # Grupo para selección de tabla

        tabla_group = QGroupBox("Tabla de Datos")

        tabla_layout = QVBoxLayout(tabla_group)

        # Opción 1: Tabla existente

        tabla_layout.addWidget(QLabel("Usar tabla existente:"))

        self.combo_tablas = QComboBox()

        self.combo_tablas.currentTextChanged.connect(self.on_tabla_existente_seleccionada)

        tabla_layout.addWidget(self.combo_tablas)

        # Opción 2: Nueva tabla

        tabla_layout.addWidget(QLabel("O crear nueva tabla:"))

        self.input_nueva_tabla = QLineEdit()

        self.input_nueva_tabla.setPlaceholderText("Nombre de la nueva tabla...")

        self.input_nueva_tabla.textChanged.connect(self.on_nueva_tabla_escrita)

        tabla_layout.addWidget(self.input_nueva_tabla)

        layout.addWidget(tabla_group)

        # Información del esquema

        info_group = QGroupBox("Esquema de la Tabla")

        info_layout = QVBoxLayout(info_group)

        info_layout.addWidget(QLabel("Columnas: id (AUTO), fecha (TEXT), hora (TEXT), irradiancia (REAL)"))

        layout.addWidget(info_group)

        # Botones de acción

        botones_layout = QHBoxLayout()

        self.btn_aceptar = QPushButton("Aceptar")

        self.btn_cancelar = QPushButton("Cancelar")

        self.btn_aceptar.clicked.connect(self.aceptar)

        self.btn_cancelar.clicked.connect(self.reject)

        botones_layout.addWidget(self.btn_aceptar)

        botones_layout.addWidget(self.btn_cancelar)

        layout.addLayout(botones_layout)

        # Estado inicial

        self.btn_aceptar.setEnabled(False)

    def cambiar_base_datos(self):
        """Permite al usuario seleccionar una base de datos diferente"""

        archivo, _ = QFileDialog.getSaveFileName(
            self,
            "Seleccionar Base de Datos SQLite",
            self.ruta_db,
            "Base de datos SQLite (*.db);;Todos los archivos (*)",
        )

        if archivo:

            self.ruta_db = archivo

            self.db_path_label.setText(f"Archivo: {self.ruta_db}")

            self.cargar_tablas()

    def cargar_tablas(self):
        """Carga las tablas existentes de la base de datos"""

        self.combo_tablas.clear()

        self.combo_tablas.addItem("-- Seleccionar tabla --")

        try:

            # Crear directorio si no existe

            os.makedirs(os.path.dirname(self.ruta_db), exist_ok=True)

            conn = sqlite_manager.connect_db(self.ruta_db)

            tablas = sqlite_manager.get_tables(conn)
            conn.close()

            for tabla in tablas:

                self.combo_tablas.addItem(tabla)

        except Exception as e:

            QMessageBox.warning(self, "Error", f"Error cargando tablas: {e}")

    def on_tabla_existente_seleccionada(self, texto):
        """Se ejecuta cuando se selecciona una tabla existente"""

        if texto and texto != "-- Seleccionar tabla --":

            self.input_nueva_tabla.clear()

            self.btn_aceptar.setEnabled(True)

        else:

            self.validar_estado()

    def on_nueva_tabla_escrita(self, texto):
        """Se ejecuta cuando se escribe el nombre de una nueva tabla"""

        if texto.strip():

            self.combo_tablas.setCurrentIndex(0)  # Resetear combo

            self.validar_nueva_tabla(texto)

        else:

            self.validar_estado()

    def validar_nueva_tabla(self, nombre):
        """Valida el nombre de la nueva tabla"""

        nombre = nombre.strip()

        if not nombre:

            self.btn_aceptar.setEnabled(False)
            return

        # Validar nombre usando sqlite_manager

        if not sqlite_manager.validate_table_name(nombre):

            self.input_nueva_tabla.setStyleSheet("QLineEdit { background-color: #ffeeee; }")

            self.btn_aceptar.setEnabled(False)
            return

        # Verificar que no existe ya

        try:

            conn = sqlite_manager.connect_db(self.ruta_db)

            tablas_existentes = sqlite_manager.get_tables(conn)
            conn.close()

            if nombre in tablas_existentes:

                self.input_nueva_tabla.setStyleSheet("QLineEdit { background-color: #ffffee; }")

                self.btn_aceptar.setEnabled(False)
                return

        except (DatabaseError, sqlite3.Error, OSError):

            # Si no podemos verificar tablas existentes, permitir continuar

            # El error se manejará cuando se intente crear la tabla

            pass

        # Nombre válido

        self.input_nueva_tabla.setStyleSheet("")

        self.btn_aceptar.setEnabled(True)

    def validar_estado(self):
        """Valida el estado general del diálogo"""

        tabla_seleccionada = self.combo_tablas.currentText() and self.combo_tablas.currentText() != "-- Seleccionar tabla --"

        nueva_tabla = self.input_nueva_tabla.text().strip()

        self.btn_aceptar.setEnabled(tabla_seleccionada or bool(nueva_tabla))

    def aceptar(self):
        """Procesa la configuración y emite la señal"""

        try:

            # Determinar tabla a usar

            if self.input_nueva_tabla.text().strip():

                tabla = self.input_nueva_tabla.text().strip()

                # Validar nombre

                if not sqlite_manager.validate_table_name(tabla):

                    QMessageBox.warning(self, "Error", "Nombre de tabla inválido. Use solo letras, números y guiones bajos.")
                    return

                # Verificar que no existe

                conn = sqlite_manager.connect_db(self.ruta_db)

                tablas_existentes = sqlite_manager.get_tables(conn)
                conn.close()

                if tabla in tablas_existentes:

                    QMessageBox.warning(
                        self, "Error", f"La tabla '{tabla}' ya existe. Selecciónela de la lista o use otro nombre."
                    )
                    return

            else:

                tabla = self.combo_tablas.currentText()

                if not tabla or tabla == "-- Seleccionar tabla --":

                    QMessageBox.warning(self, "Error", "Debe seleccionar una tabla o crear una nueva.")
                    return

            # Emitir señal con la configuración

            self.configuracion_aceptada.emit(self.ruta_db, tabla)

            self.accept()

        except Exception as e:

            QMessageBox.critical(self, "Error", f"Error configurando SQLite: {e}")
