# Zeitraum-Auswahl vor Mail-Versand

## Problem

Der Abrechnungszeitraum ist nicht immer exakt ein Kalendermonat. Aktuell sendet "Monat senden" immer den kompletten angezeigten Monat — es gibt keine Möglichkeit, einen individuellen Zeitraum zu wählen.

## Lösung

Beim Klick auf "Monat senden" öffnet sich ein Zwischendialog mit Von/Bis-Datumswahl, bevor die Mail gesendet wird.

## Dialog-Design

```
┌─ Zeitraum wählen ────────────────────┐
│                                       │
│  Von:   [23] . [02] . [2026]         │
│  Bis:   [23] . [03] . [2026]         │
│                                       │
│           [Abbrechen]  [Senden]       │
└───────────────────────────────────────┘
```

- **Von/Bis**: Jeweils drei Dropdowns (Tag, Monat, Jahr) im deutschen Format DD.MM.YYYY
- **Standardwerte**: "Bis" = heute, "Von" = heute minus 1 Monat
- **Validierung**: Von-Datum muss vor Bis-Datum liegen, sonst Fehlermeldung
- **Senden**: Generiert Report für den gewählten Zeitraum und verschickt ihn

## Betroffene Dateien

### `src/ui.py`
- `_send_report()` zeigt zuerst den Zeitraum-Dialog
- Neuer Dialog mit Von/Bis-Dropdowns (Tag/Monat/Jahr)
- Bei Bestätigung: Report generieren und senden

### `src/report.py`
- `generate_report()` Signatur ändern: statt `(year, month, all_entries)` → `(date_from, date_to, all_entries)`
- Einträge nach Datumsbereich filtern (inklusiv Von und Bis)
- Mail-Subject und Greeting anpassen: "Zeiterfassung — DD.MM.YYYY – DD.MM.YYYY"

### Tests
- `test_report.py` an neue Signatur anpassen
- Testfälle für monatsübergreifende Zeiträume ergänzen

## Was sich NICHT ändert

- Storage, Settings, Mail-Versand-Logik, OAuth, Kalenderansicht
