# Zeiterfassung – Projekthinweise

Kleines Desktop-Tool zur Zeiterfassung (Tkinter + Python) für Windows, macOS und Linux, das PDF-Berichte erzeugt und per Gmail verschickt.

## Release-Prozess

Releases werden automatisch von `.github/workflows/release.yml` erzeugt, sobald ein PR nach `master` gemerged wird, der ein `release:major`, `release:minor` oder `release:patch` Label trägt.

Ablauf vor dem Merge:
1. `src/version.py` im PR auf die neue Version setzen (z.B. `VERSION = "1.5.0"`).
2. `CHANGELOG.md` im PR aktualisieren.
3. Passendes `release:*` Label am PR setzen (Label steuert nur den Trigger, nicht die Versionsnummer).
4. PR mergen — Workflow liest die Version aus `src/version.py`, bricht ab falls der Tag `vX.Y.Z` bereits existiert, baut das Installer-Exe und veröffentlicht das Release.

Der Workflow pusht **nichts** nach `master`. Versionsbump gehört in den PR.

## Recovery bei teilweise fehlgeschlagenem Release

Wenn der `publish`-Job nach dem Tag-Push fehlschlägt (z.B. `gh release create` Netzwerkproblem), blockiert der Pre-Check beim Re-Run die erneute Ausführung wegen "tag already exists". Ablauf:

1. Tag lokal und remote löschen:
   ```
   git tag -d v<ver>
   git push origin :refs/tags/v<ver>
   ```
2. Workflow im PR unter Actions → „Re-run all jobs" erneut starten.

Alternative: `src/version.py` auf die nächste Patch-Version bumpen und einen neuen Release-PR mergen.

## Branch Protection

`master` ist protected: direkte Pushes erfordern Admin-Bypass. Im Normalfall über PR arbeiten. Für Notfall-Fixes am CI kann der Repo-Owner direkt pushen.

## Build

```
python build.py
```

`build.py` ist ein Plattform-Dispatcher und ruft PyInstaller je nach `platform.system()` unterschiedlich auf. Auf allen drei Plattformen sind `--collect-all xhtml2pdf --collect-all reportlab` zwingend — ohne sie schlägt die PDF-Erzeugung im gebauten Artefakt stumm fehl.

## Cross-Platform Builds

`build.py` ist plattformabhängig:

| Plattform | Voraussetzung | Ausgabe |
|-----------|---------------|---------|
| Windows | Inno Setup 6 unter `%LOCALAPPDATA%\Programs\Inno Setup 6\` | `dist/Zeiterfassung_Setup.exe` |
| macOS | `brew install create-dmg` | `dist/Zeiterfassung-<ver>-arm64.dmg` (CI baut nur Apple Silicon; Intel-Runner `macos-13` hat de-facto unbrauchbare Queue-Zeiten) |
| Linux | `apt install libfuse2` + `appimagetool` auf `$PATH` | `dist/Zeiterfassung-<ver>-<arch>.AppImage` |

Fehlt das Pack-Tool lokal, überspringt `build.py` den Pack-Schritt mit Warnung — der PyInstaller-Build läuft trotzdem durch. Das ist für Local-Dev gewollt.

## Installation & Daten

Installierte App und Benutzerdaten liegen je nach Plattform:

| Plattform | Installation | Benutzerdaten (Entries, Settings, `token.json`, `credentials.json`) |
|-----------|--------------|--------------------------------------------------------------------|
| Windows | `%LOCALAPPDATA%\Programs\Zeiterfassung\` | Gleiches Verzeichnis wie die Exe |
| macOS | `/Applications/Zeiterfassung.app` | `~/Library/Application Support/Zeiterfassung/` |
| Linux | Beliebige AppImage-Datei | `$XDG_DATA_HOME/Zeiterfassung/` (Fallback `~/.local/share/Zeiterfassung/`) |

`src/paths.py::get_base_path` dispatched über `platform.system()` und unterscheidet zwischen Frozen- und Repo-Modus.

## UI-Fehler sichtbar machen

`--noconsole` unterdrückt stderr. Fehler aus dem Sendepfad (Gmail, PDF-Erzeugung) **müssen** per `messagebox.showerror` mit `traceback.format_exc()` angezeigt werden — sonst klickt der Nutzer auf „Senden", nichts passiert, und es gibt keine Spur.

## UTF-8 im Mail-Pipeline

Damit Umlaute/ß nicht als Mojibake ankommen, gelten drei Pflichten:
- HTML-Body: `<meta charset="utf-8">` im `<head>`
- `MIMEText(html, "html", _charset="utf-8")`
- Betreff: `Header(subject, "utf-8")`

## Tests / CI

`.github/workflows/test.yml` installiert **nur** `pytest`, nicht `requirements.txt`. Grund: `pycairo` (transitive Dep von `xhtml2pdf`) braucht Cairo-Systemheader auf Ubuntu und bricht sonst den CI-Build. Der Import von `xhtml2pdf` in `src/report.py::generate_pdf` ist lazy, daher laufen die Report-Tests ohne die Lib.

Lokal: `pytest` aus dem Repo-Root. Alle Tests müssen vor dem PR-Merge grün sein.

## Struktur

- `src/ui.py` — Tkinter-GUI, Sende-Dialog
- `src/report.py` — HTML-Mail und PDF (dark-Theme / light-Theme), gruppiert pro ISO-Kalenderwoche
- `src/mail.py` — Gmail-API-Wrapper
- `src/time_utils.py` — Stundenberechnung, KW-Labels
- `src/paths.py` — Datenverzeichnis (frozen vs. repo)
- `src/version.py` — Einzige Quelle für die App-Version
- `installer.iss` — Inno Setup Script, Version wird per `/DAppVer=...` vom Workflow übergeben
