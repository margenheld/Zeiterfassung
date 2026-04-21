# Zeiterfassung – Projekthinweise

Kleines Windows-Tool zur Zeiterfassung (Tkinter + Python), das PDF-Berichte erzeugt und per Gmail verschickt.

## Release-Prozess

Releases werden automatisch von `.github/workflows/release.yml` erzeugt, sobald ein PR nach `master` gemerged wird, der ein `release:major`, `release:minor` oder `release:patch` Label trägt.

Ablauf vor dem Merge:
1. `src/version.py` im PR auf die neue Version setzen (z.B. `VERSION = "1.5.0"`).
2. `CHANGELOG.md` im PR aktualisieren.
3. Passendes `release:*` Label am PR setzen (Label steuert nur den Trigger, nicht die Versionsnummer).
4. PR mergen — Workflow liest die Version aus `src/version.py`, bricht ab falls der Tag `vX.Y.Z` bereits existiert, baut das Installer-Exe und veröffentlicht das Release.

Der Workflow pusht **nichts** nach `master`. Versionsbump gehört in den PR.

## Branch Protection

`master` ist protected: direkte Pushes erfordern Admin-Bypass. Im Normalfall über PR arbeiten. Für Notfall-Fixes am CI kann der Repo-Owner direkt pushen.

## Build

```
python build.py
```

`build.py` ruft PyInstaller mit `--onefile --noconsole` auf und benötigt zwingend `--collect-all xhtml2pdf --collect-all reportlab`, sonst schlägt die PDF-Erzeugung im gebauten Exe stumm fehl.

## Installation & Daten

Installierte App liegt unter `C:\Users\marge\AppData\Local\Programs\Zeiterfassung\`.
Benutzerdaten (Entries, Settings, `token.json`, `credentials.json`) liegen im selben Verzeichnis wie die Exe — `src/paths.py` unterscheidet zwischen Frozen-Modus (`os.path.dirname(sys.executable)`) und Repo-Modus.

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
