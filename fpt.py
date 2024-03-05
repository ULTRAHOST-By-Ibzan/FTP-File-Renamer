import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, \
    QMessageBox, QTextEdit, QFileDialog, QDialog, QDialogButtonBox, QVBoxLayout, QTextEdit, QComboBox
from ftplib import FTP
import re
import sqlite3


class DirectoryDialog(QDialog):
    def __init__(self, parent=None):
        super(DirectoryDialog, self).__init__(parent)

        layout = QVBoxLayout(self)
        self.setWindowTitle("Ingresar directorios")
        self.resize(400, 300)
        self.directories_textedit = QTextEdit()
        layout.addWidget(self.directories_textedit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_directories(self):
        return self.directories_textedit.toPlainText().splitlines()


class FTPRenamerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('FTP File Renamer // IBZAN By ULTRAHOST')
        self.resize(400, 600)  # Establecer un tamaño personalizado
        self.initUI()
        self.load_hosts()

    def initUI(self):
        layout = QVBoxLayout()

        # Labels and LineEdits for FTP connection
        self.host_label = QLabel('Host:')
        self.host_edit = QComboBox()
        self.host_edit.setEditable(True)
        self.host_edit.currentTextChanged.connect(self.load_credentials)
        layout.addWidget(self.host_label)
        layout.addWidget(self.host_edit)

        self.user_label = QLabel('Usuario:')
        self.user_edit = QLineEdit()
        layout.addWidget(self.user_label)
        layout.addWidget(self.user_edit)

        self.password_label = QLabel('Contraseña:')
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_edit)

        self.port_label = QLabel('Puerto:')
        self.port_edit = QLineEdit()
        layout.addWidget(self.port_label)
        layout.addWidget(self.port_edit)

        # Labels and LineEdits for word replacement
        self.original_word_label = QLabel('Palabra original:')
        self.original_word_edit = QLineEdit()
        layout.addWidget(self.original_word_label)
        layout.addWidget(self.original_word_edit)

        self.replacement_word_label = QLabel('Palabra de reemplazo:')
        self.replacement_word_edit = QLineEdit()
        layout.addWidget(self.replacement_word_label)
        layout.addWidget(self.replacement_word_edit)

        # Button to select directories
        self.directory_button = QPushButton('Directorios')
        self.directory_button.clicked.connect(self.select_directories)
        layout.addWidget(self.directory_button)

        # Button to initiate FTP renaming
        self.rename_button = QPushButton('Renombrar archivos en FTP')
        self.rename_button.clicked.connect(self.rename_files_ftp)
        layout.addWidget(self.rename_button)

        # TextEdit to display terminal output
        self.output_textedit = QTextEdit()
        layout.addWidget(self.output_textedit)

        # Button to export renamed files list
        self.export_button = QPushButton('Exportar')
        self.export_button.clicked.connect(self.export_files)
        layout.addWidget(self.export_button)

        self.setLayout(layout)

    def load_hosts(self):
        # Conexión a la base de datos
        conn = sqlite3.connect('ftp_credentials.db')
        c = conn.cursor()

        # Crear tabla si no existe
        c.execute('''CREATE TABLE IF NOT EXISTS ftp_hosts
                     (host text PRIMARY KEY, username text, password text, port int)''')

        # Obtener hosts de la base de datos
        c.execute("SELECT host FROM ftp_hosts")
        hosts = c.fetchall()
        self.host_edit.addItems([host[0] for host in hosts])

        conn.commit()
        conn.close()

    def load_credentials(self, selected_host):
        # Si el host seleccionado es nuevo, limpiamos los campos
        if selected_host not in self.host_edit.currentText():
            self.user_edit.clear()
            self.password_edit.clear()
            self.port_edit.clear()
            return

        # Conexión a la base de datos
        conn = sqlite3.connect('ftp_credentials.db')
        c = conn.cursor()

        # Obtener credenciales del host seleccionado
        c.execute("SELECT * FROM ftp_hosts WHERE host=?", (selected_host,))
        credentials = c.fetchone()
        if credentials:
            self.user_edit.setText(credentials[1])
            self.password_edit.setText(credentials[2])
            self.port_edit.setText(str(credentials[3]))

        conn.commit()
        conn.close()

    def select_directories(self):
        dialog = DirectoryDialog()
        if dialog.exec_():
            self.directories_list = dialog.get_directories()
            self.output_textedit.append("Lista de directorios cargada.")

    def rename_files_ftp(self):
        host = self.host_edit.currentText()
        username = self.user_edit.text()
        password = self.password_edit.text()
        port = int(self.port_edit.text())
        original_word = self.original_word_edit.text()
        replacement_word = self.replacement_word_edit.text()

        try:
            # Expresión regular para encontrar la palabra original en el nombre de los archivos
            pattern = re.compile(re.escape(original_word))

            # Conexión al servidor FTP
            with FTP(host) as ftp:
                ftp.login(username, password, port)

                for directory in self.directories_list:
                    try:
                        # Cambiar al directorio deseado en el servidor FTP
                        ftp.cwd(directory)

                        # Obtener lista de archivos en el directorio
                        file_list = ftp.nlst()

                        # Iterar sobre los archivos en el directorio
                        for filename in file_list:
                            # Comprobar si el nombre del archivo coincide con el patrón
                            if pattern.search(filename):
                                # Renombrar el archivo reemplazando la palabra original por la de reemplazo
                                new_filename = pattern.sub(replacement_word, filename)
                                ftp.rename(filename, new_filename)
                                self.output_textedit.append(f"Archivo {filename} renombrado como {new_filename}")

                    except Exception as e:
                        self.output_textedit.append(f"No se pudo cambiar al directorio {directory}: {e}")
                        continue

            # Preguntar si desea guardar las credenciales
            reply = QMessageBox.question(self, 'Guardar credenciales',
                                         '¿Desea guardar las credenciales para este host?',
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if reply == QMessageBox.Yes:
                self.save_credentials(host, username, password, port)

            QMessageBox.information(self, 'Proceso completado',
                                    'Los archivos en el servidor FTP han sido renombrados correctamente.')

        except Exception as e:
            QMessageBox.warning(self, 'Error', f'Error al renombrar archivos en el servidor FTP: {str(e)}')

    def save_credentials(self, host, username, password, port):
        # Conexión a la base de datos
        conn = sqlite3.connect('ftp_credentials.db')
        c = conn.cursor()

        # Insertar o actualizar credenciales
        c.execute("INSERT OR REPLACE INTO ftp_hosts VALUES (?, ?, ?, ?)", (host, username, password, port))

        conn.commit()
        conn.close()

    def export_files(self):
        file_path, _ = QFileDialog.getSaveFileName(self, 'Exportar Archivos Renombrados', '', 'Text Files (*.txt)')
        if file_path:
            with open(file_path, 'w') as file:
                file.write(self.output_textedit.toPlainText())
            QMessageBox.information(self, 'Exportado', 'El archivo ha sido exportado exitosamente.')


if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = FTPRenamerApp()
    window.show()

    sys.exit(app.exec_())
