from PyQt5 import QtCore, QtWidgets

from info.info_window import Ui_Dialog


class InfoWindow(QtWidgets.QDialog):
    """
    Info-Fenster-Klasse für die Anzeige von Programminformationen.

    Diese Klasse erweitert das generierte UI und stellt eine vollständige
    Info-Dialog-Funktionalität zur Verfügung.
    """

    def __init__(self, parent=None):
        """
        Initialisiert das Info-Fenster.

        Args:
            parent: Das übergeordnete Widget (optional)
        """
        super(InfoWindow, self).__init__(parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.setup_connections()
        self.setup_dialog()

    def setup_connections(self):
        """Verbindet die UI-Elemente mit ihren entsprechenden Funktionen."""
        self.ui.pushButton_ok.clicked.connect(self.accept)

    def setup_dialog(self):
        """Konfiguriert die Dialog-Eigenschaften."""
        # Dialog modal machen
        self.setModal(True)

        # Fenster-Flags setzen
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.WindowTitleHint)

        # Text-Editor auf nur-lesen setzen
        self.ui.plainTextEdit.setReadOnly(True)

        # Fenster zentrieren
        self.center_window()

    def center_window(self):
        """Zentriert das Fenster auf dem Bildschirm."""
        if self.parent():
            # Zentrieren relativ zum Eltern-Fenster
            parent_geometry = self.parent().geometry()
            x = parent_geometry.x() + (parent_geometry.width() - self.width()) // 2
            y = parent_geometry.y() + (parent_geometry.height() - self.height()) // 2
            self.move(x, y)
        else:
            # Zentrieren auf dem Bildschirm
            screen = QtWidgets.QApplication.desktop().screenGeometry()
            x = (screen.width() - self.width()) // 2
            y = (screen.height() - self.height()) // 2
            self.move(x, y)

    def set_info_text(self, text):
        """
        Setzt einen benutzerdefinierten Info-Text.

        Args:
            text (str): Der anzuzeigende Text
        """
        self.ui.plainTextEdit.setPlainText(text)

    def get_info_text(self):
        """
        Gibt den aktuellen Info-Text zurück.

        Returns:
            str: Der aktuelle Text im Info-Fenster
        """
        return self.ui.plainTextEdit.toPlainText()

    @staticmethod
    def show_info(parent=None, custom_text=None):
        """
        Statische Methode zum einfachen Anzeigen des Info-Fensters.

        Args:
            parent: Das übergeordnete Widget (optional)
            custom_text (str): Benutzerdefinierter Text (optional)

        Returns:
            int: Dialog-Ergebnis (QDialog.Accepted oder QDialog.Rejected)
        """
        dialog = InfoWindow(parent)
        if custom_text:
            dialog.set_info_text(custom_text)
        return dialog.exec_()


# Beispiel für die Verwendung der Klasse
if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)

    # Einfache Verwendung
    InfoWindow.show_info()

    # Oder mit benutzerdefiniertem Text
    # InfoWindow.show_info(custom_text="Benutzerdefinierte Informationen hier...")

    sys.exit(app.exec_())
