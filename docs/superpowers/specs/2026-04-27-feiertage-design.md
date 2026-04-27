# Gesetzliche Feiertage (Deutschland, nach Bundesland) — Design Spec

## Overview

Die App soll im Kalender die gesetzlichen Feiertage des vom Nutzer gewählten Bundeslandes grün markieren und beim Hover den vollen Feiertagsnamen via Tooltip anzeigen. In der Zelle steht der Name in Kurzform (truncated) analog zur bestehenden Eintrags-Darstellung mit Zeit-Range.

Standardverhalten: kein Bundesland gewählt → keine Feiertage sichtbar. Erst wenn der Nutzer in den Einstellungen sein Bundesland wählt, werden Feiertage angezeigt.

Beim Versuch, an einem Feiertag einen **neuen** Eintrag anzulegen, erscheint eine Bestätigungs-Dialogbox. Bei Bestätigung wird der Eintrag normal gespeichert und visuell wie alle anderen Einträge dargestellt (rote Umrandung). Beim Bearbeiten eines bereits existierenden Eintrags an einem Feiertag erscheint **keine** Warnung.

PDF-Bericht und HTML-Mail bleiben unverändert — Feiertage sind ein rein lokales UI-Feature.

## Scope decisions

| # | Decision | Consequence |
|---|----------|-------------|
| 1 | Datenquelle: `python-holidays` als neue Pip-Dep | Pure-Python, offline-fähig, alle 16 BL via `subdiv=`. Kein API-Call, kein Netzwerk-Risiko, kein Auth |
| 2 | Default `state = ""` (leer) → keine Feiertage | Bestandsnutzer sehen ohne Aktion keine Änderung; opt-in Verhalten |
| 3 | Keine Sub-Optionen pro Bundesland (z.B. Mariä Himmelfahrt für Bayern) | Wir liefern den Default der Lib pro `subdiv=`. Gemeindeabhängige Feiertage in BY werden nicht angezeigt — bewusste YAGNI-Entscheidung |
| 4 | Konflikt Eintrag+Feiertag: Eintrag dominiert visuell | Rote Eintragszelle wie heute; Feiertagsname wandert in den Tooltip |
| 5 | Warnung nur beim **Anlegen** eines Eintrags, nicht beim Edit | Edit eines bestehenden Eintrags soll nicht nerven |
| 6 | Bericht (PDF/Mail) bleibt unverändert | Feiertage sind lokal; Empfänger sieht weiterhin nur gearbeitete Stunden |
| 7 | Wochenansicht zeigt Feiertage analog zum Monat | Gleiche Render-Logik, nur höhere Zelle → mehr Platz für Namen |
| 8 | Versions-Bump und CHANGELOG nicht Teil dieser Spec | Wird im Release-PR gebündelt |

## Architektur

Neues Modul `src/holidays_de.py` kapselt sämtliche Feiertags-Logik. UI-Code (`ui.py`, `entry_dialog.py`) konsumiert nur die Public-API.

```
src/holidays_de.py     ← Public API: STATES, get_holidays(state, year)
src/tooltip.py         ← Wiederverwendbares Tk-Tooltip-Widget
src/theme.py           ← +HOLIDAY_BG, HOLIDAY_BG_HOVER, HOLIDAY_ACCENT
src/settings.py        ← +DEFAULTS["state"] = ""
src/dialogs/settings_dialog.py  ← +Bundesland-Combobox
src/dialogs/entry_dialog.py     ← +Feiertags-Warnung beim Anlegen
src/ui.py              ← Drei-Fall-Render: Eintrag / Feiertag / leer
```

Datenfluss beim Refresh des Kalenders:

```
App._refresh_*()
  → settings.get("state")               -- z.B. "BY"
  → holidays_de.get_holidays(state, y)  -- {date: name}, gecached
  → für jede Zelle:
      if entry: rote Zelle (+ Tooltip falls auch Feiertag)
      elif holiday: grüne Zelle + Tooltip
      else: leere Zelle wie heute
```

## Implementation

### `src/holidays_de.py` (neu)

```python
from datetime import date
from functools import lru_cache

# Code, Klartext-Label. Reihenfolge alphabetisch nach Label.
STATES: list[tuple[str, str]] = [
    ("", "— kein Bundesland —"),
    ("BW", "Baden-Württemberg"),
    ("BY", "Bayern"),
    ("BE", "Berlin"),
    ("BB", "Brandenburg"),
    ("HB", "Bremen"),
    ("HH", "Hamburg"),
    ("HE", "Hessen"),
    ("MV", "Mecklenburg-Vorpommern"),
    ("NI", "Niedersachsen"),
    ("NW", "Nordrhein-Westfalen"),
    ("RP", "Rheinland-Pfalz"),
    ("SL", "Saarland"),
    ("SN", "Sachsen"),
    ("ST", "Sachsen-Anhalt"),
    ("SH", "Schleswig-Holstein"),
    ("TH", "Thüringen"),
]

_VALID_CODES = {code for code, _ in STATES if code}


@lru_cache(maxsize=64)
def get_holidays(state_code: str, year: int) -> dict[date, str]:
    """Liefert {date: name} für gewähltes BL und Jahr.

    Leerer / ungültiger Code → leeres Dict (kein Fehler).
    Lazy-Import von ``holidays`` damit der Test-Workflow ohne
    die Lib weiterhin durchläuft.
    """
    if state_code not in _VALID_CODES:
        return {}
    import holidays
    return dict(holidays.Germany(subdiv=state_code, years=year))
```

Lazy-Import-Begründung: `tests/test_holidays_de.py` testet die Helper-Logik (leerer Code, ungültiger Code) auch ohne `holidays`-Lib im CI-Image. Tests, die echte Daten prüfen, importieren die Lib transitiv.

### `src/tooltip.py` (neu)

Klassisches Tk-Tooltip mit `Toplevel`. ~30 Zeilen, gebunden an `<Enter>`/`<Leave>`.

```python
import tkinter as tk

class _Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _event):
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(
            self.tip, text=self.text, background="#1e293b",
            foreground="#e0e0e0", relief="solid", borderwidth=1,
            padx=8, pady=4, font=("Segoe UI", 9),
        ).pack()

    def _hide(self, _event):
        if self.tip:
            self.tip.destroy()
            self.tip = None


def attach_tooltip(widget, text: str) -> None:
    """Bindet ein Tooltip an widget. Mehrfach-Aufruf ersetzt nicht — also nur einmal pro Widget."""
    _Tooltip(widget, text)
```

### `src/theme.py`

```python
HOLIDAY_BG = "#0f3a2a"
HOLIDAY_BG_HOVER = "#15523a"
HOLIDAY_ACCENT = "#4ade80"   # gleicher Grünton wie STATUS_OK
```

### `src/settings.py`

```python
DEFAULTS = {
    ...
    "hourly_rate": 0.0,
    "state": "",
}
```

Keine Migration nötig: der `_load`-Pfad merged geladene Daten in eine Default-Kopie, neue Keys werden automatisch befüllt.

### `src/dialogs/settings_dialog.py`

Neue Combobox-Zeile zwischen „Stundenlohn" (row=8) und der Mail-Vorlage-Sektion (row=9 → wird zu row=10).

```python
from src.holidays_de import STATES

label("Bundesland:", row=9)
state_var = tk.StringVar(value=settings.get("state"))
state_labels = [label for _, label in STATES]
state_combo = dark_combo(dialog, state_var, state_labels)
state_combo.grid(row=9, column=1, padx=10, pady=8)
# Initiale Auswahl auf den passenden Label-Eintrag setzen
current = settings.get("state")
for code, lbl in STATES:
    if code == current:
        state_var.set(lbl)
        break
```

In `save_settings()`:

```python
selected_label = state_var.get()
selected_code = next((code for code, lbl in STATES if lbl == selected_label), "")
settings.set("state", selected_code)
```

Alle nachfolgenden `row=`-Indizes (Mail-Vorlage, Buttons) um eins inkrementieren.

### `src/dialogs/entry_dialog.py`

Beim Speichern, **nur wenn ein neuer Eintrag** (kein bestehender unter `date_str`):

```python
state = settings.get("state")
if state and not _is_existing_entry:
    year = datetime.date.fromisoformat(date_str).year
    feiertage = get_holidays(state, year)
    holiday_date = datetime.date.fromisoformat(date_str)
    if holiday_date in feiertage:
        date_de = holiday_date.strftime("%d.%m.%Y")
        ok = messagebox.askyesno(
            "Feiertag",
            f"Der {date_de} ist {feiertage[holiday_date]} (Feiertag).\n\n"
            "Trotzdem Eintrag anlegen?",
            parent=dialog,
        )
        if not ok:
            return
```

`_is_existing_entry` wird beim Öffnen des Dialogs aus `storage.get(date_str) is not None` ermittelt und im Closure gehalten.

### `src/ui.py`

`_refresh_month` und `_refresh_week` holen vor der Schleife einmalig die Feiertage des angezeigten Jahres:

```python
state = self.settings.get("state")
holidays_map = get_holidays(state, self.year) if state else {}
```

In der Schleife wird der bisherige Zwei-Fall-Branch (Eintrag / kein Eintrag) zu drei Fällen erweitert:

```python
day_date = datetime.date(self.year, self.month, day)

if entry:
    # bisherige rote Eintrags-Zelle, unverändert
    cell = build_entry_cell(...)
    if day_date in holidays_map:
        attach_tooltip(cell, f"Feiertag: {holidays_map[day_date]}")
elif day_date in holidays_map:
    name = holidays_map[day_date]
    short = _truncate(name, 12)  # für Monatsraster
    cell = build_holiday_cell(day_text=str(day), short_name=short, ...)
    attach_tooltip(cell, name)
else:
    # bisherige leere Zelle, unverändert
    cell = build_empty_cell(...)
```

`build_holiday_cell` erstellt analog zur Eintrags-Zelle einen `Frame` mit `highlightbackground=HOLIDAY_ACCENT`, einem Tag-Label und einem zweiten Label mit dem Kurznamen. Click-Binding wie bei der leeren Zelle (öffnet `entry_dialog`).

`_truncate(name, n)`: gibt `name` zurück, falls `len(name) <= n`, sonst `name[: n - 1] + "…"`.

In `_refresh_week` analog mit `n=18` (mehr Platz vorhanden) und `day_date = dates[col]`.

Falls der Monat über zwei Jahre reicht (Dezember-Render zeigt Januar-Tage in der ersten Woche → tut er aber bei `firstweekday=0` nicht, da `monthdayscalendar` keine Out-of-Month-Tage zurückgibt) — kein Sonderfall. In der Wochenansicht spannt eine ISO-Woche im Übergang Dezember/Januar zwei Jahre; dort beide Jahre laden:

```python
years = {dates[0].year, dates[-1].year}
holidays_map: dict[date, str] = {}
if state:
    for y in years:
        holidays_map.update(get_holidays(state, y))
```

### `requirements.txt`

```
holidays
```

(kein Versions-Pin, analog zu den bestehenden Einträgen)

### `build.py`

In allen drei Plattform-Pfaden `--collect-all holidays` zu den PyInstaller-Argumenten hinzufügen, neben den bestehenden `--collect-all xhtml2pdf --collect-all reportlab`. Begründung: `holidays` lädt Locale-/Daten-Module dynamisch, ohne `--collect-all` schlägt das im gefrorenen Build still fehl.

## Tests

Neue Datei `tests/test_holidays_de.py`:

```python
from datetime import date
from src.holidays_de import get_holidays, STATES


def test_empty_state_returns_empty_dict():
    assert get_holidays("", 2026) == {}


def test_invalid_state_returns_empty_dict():
    assert get_holidays("XX", 2026) == {}


def test_bayern_has_heilige_drei_koenige():
    h = get_holidays("BY", 2026)
    assert date(2026, 1, 6) in h


def test_berlin_has_frauentag_but_not_heilige_drei_koenige():
    h = get_holidays("BE", 2026)
    assert date(2026, 3, 8) in h
    assert date(2026, 1, 6) not in h


def test_tag_der_deutschen_einheit_in_every_state():
    for code, _ in STATES:
        if not code:
            continue
        h = get_holidays(code, 2026)
        assert date(2026, 10, 3) in h


def test_states_list_starts_with_empty_option():
    assert STATES[0] == ("", "— kein Bundesland —")
```

`tests/test_holidays_de.py` importiert `holidays` transitiv über den Helper. Damit der CI-Workflow (`.github/workflows/test.yml`, der nur `pytest` installiert) trotzdem grün bleibt: `holidays` als pip-Dep zum CI-Step hinzufügen, **oder** Tests, die echte Daten prüfen, mit `pytest.importorskip("holidays")` skipbar machen. Vorzug: Lib im CI installieren — ist klein und ohne C-Deps, anders als `xhtml2pdf`.

Manuell zu verifizieren (kein Test):
- Bundesland-Combobox im Settings-Dialog speichert/lädt korrekt
- Feiertag erscheint nach BL-Wechsel ohne App-Restart
- Tooltip beim Hover am Feiertags-Tag
- Konflikt-Tag (Eintrag + Feiertag) zeigt rote Zelle und Tooltip
- Warnung beim Anlegen eines neuen Eintrags am Feiertag
- Keine Warnung beim Edit eines bestehenden Eintrags am Feiertag
- Wochenansicht zeigt Feiertag analog
- ISO-Woche im Jahresübergang lädt Feiertage beider Jahre

## Out of scope

- Andere Länder (Österreich, Schweiz). Aktuell Deutschland-only.
- Bayern-Sonderfälle Mariä Himmelfahrt / Augsburg-Friedensfest.
- Schulferien (separates Konzept, andere Datenquelle).
- Feiertage im PDF-/Mail-Bericht.
- Auto-Detect des Bundeslands über Locale.
- Versions-Bump und CHANGELOG (kommt mit dem Release-PR).
- Stundenlohn-/Soll-Stunden-Anpassung an Feiertagen.
- Migration alter `settings.json` (greift automatisch über DEFAULTS).
