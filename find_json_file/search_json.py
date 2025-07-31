import sys
import os
from pathlib import Path
from typing import Optional
from PyQt5.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox
from PyQt5.QtCore import QFileInfo

# Import der kompilierten UI-Klasse
try:
    from file_open import Ui_FileOpenDialog
except ImportError as e:
    print(f"Fehler beim Importieren der UI-Klasse: {e}")
    print("Stellen Sie sicher, dass file_open.py existiert und korrekt generiert wurde.")
    sys.exit(1)


class FileOpenDialog(QDialog):
    """
    Dialog für die Dateiauswahl mit Vorschaufunktion.
    """

    # Konstanten
    MAX_PREVIEW_SIZE = 1024 * 1024  # 1MB
    MAX_PREVIEW_CHARS = 1000

    # Dateifilter
    FILE_FILTERS = "Alle Dateien (*.*);;Textdateien (*.txt);;Python-Dateien (*.py);;JSON-Dateien (*.json);;CSV-Dateien (*.csv)"

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
        signal_connections = [
            (self.ui.browseButton, 'clicked', self._browse_file),
            (self.ui.openButton, 'clicked', self.accept),
            (self.ui.cancelButton, 'clicked', self.reject)
        ]

        for widget, signal, slot in signal_connections:
            try:
                getattr(widget, signal).connect(slot)
            except AttributeError as e:
                self._show_warning(f"UI-Element nicht gefunden: {str(e)}")

    def _setup_initial_state(self) -> None:
        """Setzt den initialen Zustand des Dialogs."""
        try:
            self.ui.openButton.setEnabled(False)
            self.ui.statusLabel.setText("Bereit")
        except AttributeError:
            pass  # UI-Elemente eventuell nicht vorhanden

    def _browse_file(self) -> None:
        """Öffnet den Datei-Browser."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Datei auswählen",
            "",
            self.FILE_FILTERS
        )

        if file_path:
            self._handle_file_selection(file_path)

    def _handle_file_selection(self, file_path: str) -> None:
        """Behandelt die Dateiauswahl."""
        self._selected_file_path = file_path

        try:
            self.ui.pathLineEdit.setText(file_path)
            self.ui.openButton.setEnabled(True)
            self.ui.statusLabel.setText("Datei ausgewählt")
            # self._load_preview(file_path)
        except AttributeError:
            # UI-Elemente eventuell nicht vorhanden
            pass









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


class FileDialogApplication:
    """
    Hauptanwendungsklasse für den Datei-Dialog.
    """

    def __init__(self):
        self.app = QApplication(sys.argv)

    def run(self) -> None:
        """Startet die Anwendung."""
        try:
            dialog = FileOpenDialog()
            result = dialog.exec_()

            if result == QDialog.Accepted:
                self._handle_file_accepted(dialog)
            else:
                self._handle_dialog_cancelled()

        except Exception as e:
            self._handle_unexpected_error(e)
        finally:
            sys.exit()

    def _handle_file_accepted(self, dialog: FileOpenDialog) -> None:
        """Behandelt die Annahme einer Dateiauswahl."""
        file_path = dialog.selected_file_path
        if file_path:
            print(f"Datei ausgewählt: {file_path}")
        else:
            print("Keine Datei ausgewählt")

    def _handle_dialog_cancelled(self) -> None:
        """Behandelt das Abbrechen des Dialogs."""
        pass

    def _handle_unexpected_error(self, error: Exception) -> None:
        """Behandelt unerwartete Fehler."""
        QMessageBox.critical(
            None,
            "Unerwarteter Fehler",
            f"Ein unerwarteter Fehler ist aufgetreten: {str(error)}"
        )


def main():
    """Haupteinstiegspunkt der Anwendung."""
    app = FileDialogApplication()
    app.run()


if __name__ == "__main__":
    main()