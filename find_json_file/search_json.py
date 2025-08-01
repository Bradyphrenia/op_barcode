import sys
from typing import Optional

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox

from .file_open import Ui_FileOpenDialog


class FileOpenDialog(QDialog, Ui_FileOpenDialog):
    """
    Dialog für die Dateiauswahl.
    """

    # Benutzerdefiniertes Signal für den Open-Button
    file_opened = pyqtSignal(str)  # Signal mit Dateipfad als Parameter

    # Dateifilter
    FILE_FILTERS = "Alle Dateien (*.*);;JSON-Dateien (*.json)"

    def __init__(self):
        super().__init__()
        self._selected_file_path: Optional[str] = None
        self._initialize_dialog()

    def _initialize_dialog(self) -> None:
        """Initialisiert den Dialog."""
        self._setup_ui()
        self._connect_signals()
        self._setup_initial_state()

    def _setup_ui(self) -> None:
        """Richtet die Benutzeroberfläche ein."""
        try:
            self.ui = Ui_FileOpenDialog()
            self.ui.setupUi(self)
        except Exception as e:
            self._show_critical_error(f"UI konnte nicht eingerichtet werden: {str(e)}")

    def _connect_signals(self) -> None:
        """Stellt Signal-Slot-Verbindungen her."""
        signal_connections = [(self.ui.browseButton, 'clicked', self._browse_file),
                              (self.ui.openButton, 'clicked', self._handle_open_button_clicked),
                              (self.ui.cancelButton, 'clicked', self.reject)]

        for widget, signal, slot in signal_connections:
            try:
                getattr(widget, signal).connect(slot)
            except AttributeError as e:
                self._show_warning(f"UI-Element nicht gefunden: {str(e)}")

    def _handle_open_button_clicked(self) -> None:
        """Behandelt das Klicken auf den Open-Button."""
        if self._selected_file_path:
            # Signal mit dem ausgewählten Dateipfad emittieren
            self.file_opened.emit(self._selected_file_path)
        self.accept()

    def _setup_initial_state(self) -> None:
        """Setzt den initialen Zustand des Dialogs."""
        try:
            self.ui.openButton.setEnabled(False)
            self.ui.statusLabel.setText("Bereit")
        except AttributeError:
            pass  # UI-Elemente eventuell nicht vorhanden

    def _browse_file(self) -> None:
        """Öffnet den Datei-Browser."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Datei auswählen", "", self.FILE_FILTERS)

        if file_path:
            self._handle_file_selection(file_path)

    def _handle_file_selection(self, file_path: str) -> None:
        """Behandelt die Dateiauswahl."""
        self._selected_file_path = file_path

        try:
            self.ui.pathLineEdit.setText(file_path)
            self.ui.openButton.setEnabled(True)
            self.ui.statusLabel.setText("Datei ausgewählt")
            with open('json_file.cfg', 'w') as file:
                file.write(file_path)
                file.close()

        except AttributeError:
            # UI-Elemente eventuell nicht vorhanden
            pass

    def _handle_file_accepted(self) -> None:
        """Behandelt die Annahme einer Dateiauswahl."""
        file_path = self.selected_file_path
        if file_path:
            print(f"Datei ausgewählt: {file_path}")
        else:
            print("Keine Datei ausgewählt")

    def _handle_dialog_cancelled(self) -> None:
        """Behandelt das Abbrechen des Dialogs."""
        pass

    def _handle_unexpected_error(self, error: Exception) -> None:
        """Behandelt unerwartete Fehler."""
        QMessageBox.critical(None, "Unerwarteter Fehler", f"Ein unerwarteter Fehler ist aufgetreten: {str(error)}")

    def _show_critical_error(self, message: str) -> None:
        """Zeigt einen kritischen Fehler an und beendet die Anwendung."""
        QMessageBox.critical(None, "Kritischer Fehler", message)
        sys.exit(1)

    def _show_warning(self, message: str) -> None:
        """Zeigt eine Warnung an."""
        QMessageBox.warning(self, "Warnung", message)

    @property
    def selected_file_path(self) -> Optional[str]:
        """Gibt den ausgewählten Dateipfad zurück."""
        return self._selected_file_path


def main():
    """Haupteinstiegspunkt der Anwendung."""
    app = QApplication(sys.argv)
    file_open_dialog = FileOpenDialog()

    # Beispiel für die Verbindung des Signals mit einem Slot
    def on_file_opened(file_path: str):
        print(f"Signal empfangen: Datei geöffnet - {file_path}")

    file_open_dialog.file_opened.connect(on_file_opened)
    file_open_dialog.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
