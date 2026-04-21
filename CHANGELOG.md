# Changelog

## v1.4.0
- Wochen-Gruppierung im E-Mail- und PDF-Bericht mit Wochenüberschrift und Wochensumme je KW
- UTF-8-Fix: Umlaute und ß im E-Mail-Body und Betreff werden korrekt dargestellt
- Sichtbare Fehlermeldungen beim Mail-Versand (inkl. Traceback), wenn der PDF-/Sende-Schritt fehlschlägt
- PyInstaller-Build bündelt jetzt xhtml2pdf- und reportlab-Submodule, damit die PDF-Erzeugung in der installierten Version funktioniert
- Einstellungen: Feld "E-Mail" heißt jetzt "Absender" (analog zu "Empfänger")

## v1.3.0
- Stundenlohn-Einstellung mit Bruttolohn-Anzeige im Footer (nur lokal sichtbar)
- Rechtsklick auf Tageseintrag zum Löschen
- Versionsnummer im Fenstertitel
- GitHub Actions Workflow für automatische Tests

## v1.2.0
- App-Icon und Taskbar-Integration (Windows & Linux)
- Feste Fenstergröße
- PyInstaller-Build mit gebündelten Assets

## v1.1.0
- PDF-Report-Generierung
- HTML E-Mail-Vorlagen mit Dark-Mode-Styling
- Mail-Einstellungen (Betreff, Anrede, Inhalt, Gruß)
- Datumsbereich-Auswahl für Reports
- Standard-Arbeitszeiten konfigurierbar (Start, Ende, Pause)

## v1.0.0
- Kalenderansicht mit Monatsübersicht
- Zeiterfassung (Start, Ende, Pause)
- Gmail OAuth2 E-Mail-Versand
- Empfänger-Einstellung
- Windows-Autostart
- Dark-Mode UI
