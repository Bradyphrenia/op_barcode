# Barcode-Leser

Ein Python-basiertes GUI-Tool zum Lesen und Verarbeiten von Barcodes mit einer benutzerfreundlichen Oberfläche.

## Übersicht

Der Barcode-Leser ist eine Desktop-Anwendung, die mit PyQt5 entwickelt wurde und es Benutzern ermöglicht, Barcode-Daten einzugeben und zu verarbeiten. Die Anwendung kann verschiedene Barcode-Informationen wie GTIN, Seriennummern, Referenznummern und Ablaufdaten extrahieren und anzeigen.

## Features

- **Barcode-Eingabe**: Manuelle Eingabe oder Einlesen von Barcode-Daten
- **Datenextraktion**: Automatische Extraktion von:
  - GTIN (Global Trade Item Number)
  - Seriennummer
  - Referenznummer
  - Ablaufdatum
- **Validierung**: Überprüfung der eingegebenen Daten
- **JSON-Integration**: Unterstützung für JSON-Dateien zur Datenverarbeitung
- **Benutzerfreundliche GUI**: Intuitive Benutzeroberfläche mit deutschen Labels

## Systemanforderungen

- Python 3.13.5 oder höher
- PyQt5
- macOS Sonoma (entwickelt für aarch64)

## Installation

1. Klonen Sie das Repository:

bash git clone <repository-url> cd op_barcode

2. Erstellen Sie eine virtuelle Umgebung:
```bash
python -m venv venv
source venv/bin/activate  # Auf macOS/Linux
```

3. Installieren Sie die Abhängigkeiten:

pip install -r requirements.txt

## Verwendung
Starten Sie die Anwendung mit:


python barcode.py


### Hauptfunktionen
1. **Barcode eingeben**: Geben Sie den Barcode in das entsprechende Feld ein
2. **Lesen**: Klicken Sie auf "Lesen", um die Barcode-Daten zu verarbeiten
3. **Daten überprüfen**: Die extrahierten Informationen werden in den entsprechenden Feldern angezeigt
4. **JSON-Datei auswählen**: Über das Menü "Datei" können Sie eine JSON-Datei zur Datenverarbeitung auswählen

## Projektstruktur
``` 
op_barcode/
├── barcode.py              # Hauptanwendung
├── mainwindow/             # GUI-Komponenten
│   ├── mainwindow.py       # Hauptfenster-Logik
│   ├── mainwindow.ui       # UI-Design
│   └── m_window.py         # Zusätzliche Fenster-Funktionen
├── data/                   # Datenverzeichnis
├── requirements.txt        # Python-Abhängigkeiten
├── setup.py               # Setup-Skript
└── README.md              # Diese Datei
```
## Konfiguration
- : Konfigurationsdatei für JSON-Einstellungen `json_file.cfg`
- : JSON-Datei mit Artikeldaten `table-EP_ARTIKEL.json` (nicht Inhalt dieses Repo's)

## Entwicklung
Das Projekt verwendet:
- für die GUI **PyQt5**
- **Python 3.13.5** als Laufzeitumgebung
- **virtualenv** für die Paketverwaltung

## Lizenz
[Lizenzinformationen hier einfügen]
## Autor
[Autor-Informationen hier einfügen]
## Beiträge
Beiträge sind willkommen! Bitte erstellen Sie einen Pull Request oder öffnen Sie ein Issue für Verbesserungsvorschläge.
