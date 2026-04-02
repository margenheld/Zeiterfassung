# Kalenderwoche-Ansicht (KW-View)

**Datum:** 2026-04-02
**Status:** Approved

## Zusammenfassung

Neue Wochenansicht neben der bestehenden Monatsansicht. Ein Toggle-Switch im Header schaltet zwischen beiden Ansichten um. Die Wochenansicht zeigt eine einzelne ISO-Kalenderwoche (Mo-So) mit denselben Zell-Interaktionen wie die Monatsansicht.

## Ansatz

View-State in der bestehenden `App`-Klasse (`src/ui.py`). Ein `self.view_mode`-Flag ("month" / "week") steuert, was `_refresh()` rendert. Kein neues File, kein Refactor -- minimaler Umbau.

## Design

### 1. Header-Anpassung

- **Toggle-Switch:** Zwei Buttons ("Monat" / "Woche") im Header, zwischen Pfeilen und Titel
- **Aktiver Modus:** Accent-Farbe (`#e94560`), inaktiver Modus dezent
- **Monats-Modus (bestehend):**
  - Titel: `"April 2026"`
  - Pfeile: monatsweise Navigation
- **Wochen-Modus (neu):**
  - Titel: `"KW 14 · 2026"`
  - Pfeile: wochenweise Navigation

### 2. Wochen-Grid

- **Layout:** 7 Spalten (Mo-So), Wochentag-Header oben, **1 Datenzeile** statt 4-6
- **Zellen:** Identisches Verhalten wie Monatsansicht (Klick = Edit-Dialog, Rechtsklick = Löschen)
- **Zellengröße:** Deutlich mehr vertikaler Platz pro Zelle (nur 1 Zeile statt 4-6)
- **Wochenenden:** Weiterhin `WEEKEND_BG`-Hintergrund
- **Inhalt pro Zelle:** Tagesnummer + Zeitspanne (z.B. "7" und "09:30-17:00")

### 3. Footer-Anpassung

- **Wochen-Modus:** "Gesamt: X.Xh" zeigt die Stunden der angezeigten Woche
- **"Monat senden"-Button:** Bleibt sichtbar und funktional (öffnet Datums-Range-Dialog wie bisher)

### 4. State-Management

- **Neuer State:** `self.view_mode` ("month" / "week"), `self.current_week` (ISO-KW-Nummer)
- **App-Start:** Monatsansicht (wie bisher)
- **Monat → Woche:** Springt zur ersten KW des aktuell angezeigten Monats
- **Woche → Monat:** Springt zum Monat, der den Montag der aktuellen KW enthält

### 5. Betroffene Methoden in `src/ui.py`

| Methode | Änderung |
|---------|----------|
| `__init__()` | `self.view_mode = "month"`, `self.current_week` initialisieren |
| `_build_header()` | Toggle-Switch-Buttons einfügen |
| `_refresh()` | Dispatch auf `_refresh_month()` / `_refresh_week()` basierend auf `view_mode` |
| `_refresh_month()` | Bestehende Monats-Grid-Logik (aus `_refresh()` extrahiert) |
| `_refresh_week()` | Neue Methode: Wochen-Grid mit 7 Zellen bauen |
| `_prev_month()` / `_next_month()` | In Wochen-Modus: KW-Navigation statt Monats-Navigation |
| Footer-Update in `_refresh()` | Stunden basierend auf `view_mode` berechnen |

### 6. KW-Berechnung

- Python `datetime.date.isocalendar()` liefert ISO-KW
- Montag der KW: `datetime.date.fromisocalendar(year, week, 1)`
- Sonntag: Montag + 6 Tage
- Alle 7 Tage der Woche iterieren, Einträge aus Storage laden
