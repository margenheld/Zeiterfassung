# Zeiterfassung

Desktop-App zur Erfassung von Arbeitszeiten mit Kalenderansicht, PDF-Report und automatischem Gmail-Versand.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

## Features

- **Kalenderansicht** — Monatsübersicht mit Tageseinträgen (Start, Ende, Pause)
- **PDF-Report** — Automatische Generierung als druckfreundliches PDF
- **E-Mail-Versand** — HTML-E-Mail mit PDF-Anhang über Gmail API (OAuth2)
- **Zeitraumwahl** — Flexibler Datumsbereich für Reports
- **Einstellungen** — E-Mail-Vorlagen mit Platzhaltern, Standardpause, Empfänger
- **Autostart** — Optionaler minimierter Start bei Anmeldung (Windows, macOS, Linux)
- **Dark Mode UI** — Modernes dunkles Design
- **Standalone .exe** — Per PyInstaller als einzelne Datei paketierbar

## Projektstruktur

```
Zeiterfassung/
├── src/
│   ├── main.py          # Einstiegspunkt
│   ├── ui.py            # Tkinter-GUI (Kalender, Dialoge, Einstellungen)
│   ├── storage.py       # JSON-basierte Speicherung der Zeiteinträge
│   ├── settings.py      # Einstellungen mit Standardwerten
│   ├── report.py        # HTML- & PDF-Reportgenerierung
│   ├── mail.py          # Gmail OAuth2-Authentifizierung & Versand
│   ├── autostart.py     # Plattformabhängiger Autostart (Windows/macOS/Linux)
│   ├── time_utils.py    # Zeitberechnung und Validierung
│   └── paths.py         # Pfadauflösung (Script- vs. Frozen-Modus)
├── tests/               # pytest-Testdateien
├── assets/
│   └── margenheld-icon  # App-Icon (.png + .ico + .icns)
├── docs/
│   └── gmail-setup.md   # Gmail-Einrichtungsanleitung
├── build.py             # PyInstaller-Buildskript
├── Zeiterfassung.spec   # PyInstaller-Konfiguration
├── requirements.txt     # Python-Abhängigkeiten
├── settings.json        # Benutzereinstellungen (wird automatisch erstellt)
└── zeiterfassung.json   # Gespeicherte Zeiteinträge (wird automatisch erstellt)
```

## Installation

### Fertige Releases

Vorgefertigte Installer für alle drei Plattformen gibt es unter [Releases](../../releases):

**Windows**
Lade `Zeiterfassung_Setup.exe` und führe den Installer aus. App installiert nach `%LOCALAPPDATA%\Programs\Zeiterfassung\`.

**macOS**
Lade `Zeiterfassung-<ver>-arm64.dmg` (Apple Silicon) oder `Zeiterfassung-<ver>-x86_64.dmg` (Intel) herunter. Öffne das DMG und ziehe die App in den Applications-Ordner. Beim ersten Start: Rechtsklick auf die App → „Öffnen" (Gatekeeper-Warnung bestätigen), oder im Terminal:

```bash
xattr -dr com.apple.quarantine /Applications/Zeiterfassung.app
```

Der Build ist nicht signiert — dieser Schritt ist einmalig nötig.

**Linux**
Lade `Zeiterfassung-<ver>-x86_64.AppImage` herunter:

```bash
chmod +x Zeiterfassung-<ver>-x86_64.AppImage
./Zeiterfassung-<ver>-x86_64.AppImage
```

Voraussetzung: `libfuse2` installiert (`sudo apt install libfuse2` unter Debian/Ubuntu).

### Aus dem Source-Code

#### Voraussetzungen

- Python 3.10+
- Windows 10/11, macOS 12+ oder Linux (mit Tkinter)

#### Linux: Tkinter installieren

Tkinter ist unter Linux nicht immer vorinstalliert:

```bash
# Debian / Ubuntu
sudo apt install python3-tk

# Fedora
sudo dnf install python3-tkinter

# Arch
sudo pacman -S tk
```

#### Setup

```bash
# Repository klonen
git clone <repo-url>
cd Zeiterfassung

# Abhängigkeiten installieren
pip install -r requirements.txt

# App starten
python -m src.main
```

#### Abhängigkeiten

| Paket | Zweck |
|-------|-------|
| `google-auth-oauthlib` | OAuth2-Authentifizierung für Gmail |
| `google-api-python-client` | Gmail API Client |
| `xhtml2pdf` | PDF-Generierung aus HTML |
| `pyinstaller` | Paketierung als Standalone-Binary |

## Gmail API einrichten

Damit die App E-Mails versenden kann, muss einmalig ein Google Cloud Projekt mit Gmail API eingerichtet werden.

### 1. Google Cloud Projekt erstellen

1. [Google Cloud Console](https://console.cloud.google.com/) öffnen
2. Projekt-Dropdown → **Neues Projekt** → Name: "Zeiterfassung" → **Erstellen**

### 2. Gmail API aktivieren

1. **APIs & Dienste** → **Bibliothek**
2. Nach "Gmail API" suchen → **Aktivieren**

### 3. OAuth-Zustimmungsbildschirm

1. **APIs & Dienste** → **OAuth-Zustimmungsbildschirm**
2. **Extern** → **Erstellen**
3. Ausfüllen:
   - App-Name: "Zeiterfassung"
   - Support-E-Mail: deine Gmail-Adresse
   - Entwickler-E-Mail: deine Gmail-Adresse
4. **Speichern und fortfahren**
5. Bei **Bereiche**: `gmail.send` hinzufügen → **Aktualisieren** → **Speichern**
6. Bei **Testnutzer**: deine Gmail-Adresse hinzufügen → **Speichern**

### 4. OAuth2 Client-ID erstellen

1. **APIs & Dienste** → **Anmeldedaten**
2. **Anmeldedaten erstellen** → **OAuth-Client-ID**
3. Anwendungstyp: **Desktopanwendung** → Name: "Zeiterfassung" → **Erstellen**
4. **JSON herunterladen** → als `credentials.json` speichern:
   - **Entwicklung (aus dem Source):** im Projekt-Root
   - **Windows (installiert):** `%LOCALAPPDATA%\Programs\Zeiterfassung\`
   - **macOS (installiert):** `~/Library/Application Support/Zeiterfassung/`
   - **Linux (AppImage):** `~/.local/share/Zeiterfassung/` (oder `$XDG_DATA_HOME/Zeiterfassung/`)

### 5. Erster Versand

1. App starten
2. Unter **Einstellungen** (⚙) E-Mail und Empfänger eintragen
3. **Monat senden** klicken
4. Browser öffnet sich → mit Google anmelden → Zugriff erlauben
5. `token.json` wird automatisch erstellt — ab jetzt kein erneutes Anmelden nötig

### Hinweise

- Die App läuft im **Test-Modus** — nur eingetragene Testnutzer können sich authentifizieren
- Das Token wird automatisch erneuert; bei Ablauf öffnet sich der Browser erneut
- `credentials.json` und `token.json` gehören **nicht** ins Repository

## Einstellungen

Über das Zahnrad-Symbol (⚙) im Header konfigurierbar:

| Einstellung | Beschreibung |
|-------------|-------------|
| **E-Mail** | Eigene Gmail-Adresse (Absender) |
| **Empfänger** | E-Mail-Adresse für den Report |
| **Name** | Vollständiger Name (erscheint im PDF) |
| **Standard-Pause** | Standardmäßige Pausendauer in Minuten |
| **Betreff** | E-Mail-Betreff mit Platzhaltern |
| **Begrüßung** | Anrede im E-Mail-Text |
| **Inhalt** | E-Mail-Body mit Platzhaltern |
| **Grußformel** | Abschluss der E-Mail (Zeilenumbrüche mit `\n`) |
| **Autostart** | App minimiert bei Systemanmeldung starten (Windows/macOS/Linux) |

### Platzhalter in E-Mail-Vorlagen

| Platzhalter | Wird ersetzt durch |
|-------------|-------------------|
| `{zeitraum}` | Datumsbereich, z.B. "01.03.2026 – 31.03.2026" |
| `{gesamt}` | Gesamtstunden, z.B. "168.5h" |

## Build

```bash
python build.py
```

`build.py` erkennt die Plattform via `platform.system()` und baut das passende Artefakt:

| Plattform | Voraussetzung | Ausgabe |
|-----------|---------------|---------|
| Windows | [Inno Setup 6](https://jrsoftware.org/isdl.php) unter `%LOCALAPPDATA%\Programs\Inno Setup 6\` | `dist/Zeiterfassung_Setup.exe` |
| macOS | `brew install create-dmg` | `dist/Zeiterfassung-<ver>-<arch>.dmg` |
| Linux | `apt install libfuse2` + `appimagetool` auf `$PATH` | `dist/Zeiterfassung-<ver>-<arch>.AppImage` |

Fehlt das Pack-Tool, überspringt `build.py` den Pack-Schritt mit Warnung — der PyInstaller-Build läuft trotzdem durch.

## Plattform-Kompatibilität

Die App läuft auf **Windows, macOS und Linux**. Plattformspezifische Features werden automatisch erkannt:

| Feature | Windows | macOS | Linux |
|---------|---------|-------|-------|
| Kalender & Zeiterfassung | ✓ | ✓ | ✓ |
| PDF-Report & E-Mail-Versand | ✓ | ✓ | ✓ |
| Einstellungen & Vorlagen | ✓ | ✓ | ✓ |
| Taskbar-Icon (AppUserModelID) | ✓ | — (nicht nötig) | — (nicht nötig) |
| Window-Icon | ✓ (`.ico`) | ✓ (`.png` Fallback) | ✓ (`.png` Fallback) |
| Autostart bei Anmeldung | ✓ (VBScript-Shortcut) | ✓ (LaunchAgent plist) | ✓ (`.desktop`-Datei) |
| Standalone-Binary (PyInstaller) | ✓ (`.exe`) | ✓ (`.app` Bundle) | ✓ (AppImage) |

## Tests

```bash
pytest tests/
```

## Datenspeicherung

Alle Daten werden lokal als JSON gespeichert:

- **zeiterfassung.json** — Zeiteinträge (Schlüssel: ISO-Datum `YYYY-MM-DD`)
- **settings.json** — Benutzereinstellungen
- **token.json** — Gmail OAuth-Token (wird automatisch erneuert)

Speicherort je nach Plattform (siehe `src/paths.py`):

| Plattform | Pfad |
|-----------|------|
| Windows (installiert) | `%LOCALAPPDATA%\Programs\Zeiterfassung\` |
| macOS (installiert) | `~/Library/Application Support/Zeiterfassung/` |
| Linux (AppImage) | `$XDG_DATA_HOME/Zeiterfassung/` (Fallback `~/.local/share/Zeiterfassung/`) |
| Entwicklung (Source) | Projekt-Root |
