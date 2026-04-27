# Gesetzliche Feiertage Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Im Kalender zeigt die App die gesetzlichen Feiertage des in den Einstellungen gewählten Bundeslandes (DE). Feiertage werden grün markiert, der Kurzname steht in der Zelle, Tooltip beim Hover zeigt den vollen Namen, Warnung beim Anlegen eines Eintrags am Feiertag.

**Architecture:** Neues Modul `src/holidays_de.py` kapselt `python-holidays` mit `lru_cache`. Neues Modul `src/tooltip.py` für ein wiederverwendbares Tk-Tooltip-Widget. UI lädt Feiertage einmal pro Refresh und rendert eine dritte Zellen-Variante (grün) zwischen den bestehenden zwei (rote Eintragszelle / leere Zelle). Eintrag-Dialog warnt nur beim **Anlegen** (nicht beim Edit).

**Tech Stack:** Python 3.10, Tkinter, [python-holidays](https://pypi.org/project/holidays/), pytest.

**Spec:** `docs/superpowers/specs/2026-04-27-feiertage-design.md`

---

## Task 1: Pip-Dependency `holidays` ergänzen

Vor allem anderen, sonst können Tests die Lib nicht importieren.

**Files:**
- Modify: `requirements.txt`
- Modify: `.github/workflows/test.yml`

- [ ] **Step 1: `requirements.txt` ergänzen**

Datei aktuell:
```
google-auth-oauthlib>=1.0.0
google-api-python-client>=2.0.0
xhtml2pdf>=0.2.11
pyinstaller>=6.0.0
```

Eine Zeile hinzufügen (kein Versions-Pin, analog Bestand):
```
holidays
```

- [ ] **Step 2: CI-Workflow erweitert `holidays` mitinstallieren**

In `.github/workflows/test.yml`, Zeile 13 (`- run: pip install pytest`) ändern zu:
```yaml
      - run: pip install pytest holidays
```

`holidays` hat keine C-Deps und installiert in Sekunden — kein CI-Risiko (anders als `xhtml2pdf` wegen Cairo).

- [ ] **Step 3: Lokal installieren und Import-Smoke-Test**

```bash
pip install holidays
python -c "import holidays; print(holidays.Germany(subdiv='BY', years=2026)[__import__('datetime').date(2026, 10, 3)])"
```
Erwartung: `Tag der Deutschen Einheit`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt .github/workflows/test.yml
git commit -m "deps: add python-holidays for state-aware German holidays"
```

---

## Task 2: `src/holidays_de.py` mit Tests (TDD)

Helper-Modul liefert die Feiertage und kapselt das Caching.

**Files:**
- Create: `src/holidays_de.py`
- Test: `tests/test_holidays_de.py`

- [ ] **Step 1: Failing-Test schreiben**

Neue Datei `tests/test_holidays_de.py`:
```python
from datetime import date

from src.holidays_de import STATES, get_holidays


def test_states_list_starts_with_empty_option():
    assert STATES[0] == ("", "— kein Bundesland —")


def test_states_list_contains_all_16_bundeslaender():
    codes = {code for code, _ in STATES if code}
    expected = {
        "BW", "BY", "BE", "BB", "HB", "HH", "HE", "MV",
        "NI", "NW", "RP", "SL", "SN", "ST", "SH", "TH",
    }
    assert codes == expected


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
        assert date(2026, 10, 3) in get_holidays(code, 2026)
```

- [ ] **Step 2: Tests laufen lassen — alle FAIL**

```bash
pytest tests/test_holidays_de.py -v
```
Erwartung: `ModuleNotFoundError: No module named 'src.holidays_de'`

- [ ] **Step 3: `src/holidays_de.py` schreiben**

```python
from datetime import date
from functools import lru_cache

# Code-Label-Paare. Reihenfolge alphabetisch nach Klartext-Label.
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
    """Liefert {date: name} für gewähltes Bundesland und Jahr.

    Leerer oder ungültiger Code → leeres Dict (silent fallback,
    damit ein versehentlich falsch gespeicherter Code keinen Crash auslöst).
    """
    if state_code not in _VALID_CODES:
        return {}
    import holidays
    return dict(holidays.Germany(subdiv=state_code, years=year))
```

- [ ] **Step 4: Tests laufen lassen — alle PASS**

```bash
pytest tests/test_holidays_de.py -v
```
Erwartung: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add src/holidays_de.py tests/test_holidays_de.py
git commit -m "feat(holidays): state-aware DE holidays helper with cache"
```

---

## Task 3: `src/tooltip.py` Widget

Tk-Tooltip — ~30 Zeilen, manuell verifiziert. Tk hat nichts Eingebautes.

**Files:**
- Create: `src/tooltip.py`

- [ ] **Step 1: `src/tooltip.py` schreiben**

```python
import tkinter as tk


class _Tooltip:
    """Hover-Tooltip an ein beliebiges Tk-Widget binden."""

    def __init__(self, widget: tk.Widget, text: str):
        self.widget = widget
        self.text = text
        self.tip: tk.Toplevel | None = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, _event):
        if self.tip is not None or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(
            self.tip,
            text=self.text,
            background="#1e293b",
            foreground="#e0e0e0",
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=4,
            font=("Segoe UI", 9),
        ).pack()

    def _hide(self, _event):
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None


def attach_tooltip(widget: tk.Widget, text: str) -> None:
    """Bindet ein Tooltip an widget. Mehrfachaufruf erzeugt mehrere Tooltips — Aufrufer ist verantwortlich, das nur einmal pro Widget zu tun."""
    _Tooltip(widget, text)
```

- [ ] **Step 2: Smoke-Importtest laufen lassen**

Nur dass das Modul importierbar ist:
```bash
python -c "from src.tooltip import attach_tooltip; print('ok')"
```
Erwartung: `ok`

- [ ] **Step 3: Commit**

```bash
git add src/tooltip.py
git commit -m "feat(ui): tk hover tooltip widget"
```

---

## Task 4: Theme-Konstanten

**Files:**
- Modify: `src/theme.py:1-31` (oben im Datei, bei den anderen Farb-Konstanten)

- [ ] **Step 1: `src/theme.py` editieren**

Nach Zeile 27 (`WEEKEND_ENTRY_BG_HOVER = "#223e60"`), drei neue Konstanten einfügen:

```python

# Holiday cell colors (green analog to red ACCENT for entries)
HOLIDAY_BG = "#0f3a2a"
HOLIDAY_BG_HOVER = "#15523a"
HOLIDAY_ACCENT = "#4ade80"  # gleicher Grünton wie STATUS_OK
```

- [ ] **Step 2: Importbarkeit checken**

```bash
python -c "from src.theme import HOLIDAY_BG, HOLIDAY_BG_HOVER, HOLIDAY_ACCENT; print(HOLIDAY_ACCENT)"
```
Erwartung: `#4ade80`

- [ ] **Step 3: Commit**

```bash
git add src/theme.py
git commit -m "feat(theme): green palette for holiday cells"
```

---

## Task 5: Settings-Default

**Files:**
- Modify: `src/settings.py:4-17` (DEFAULTS-Dict)

- [ ] **Step 1: Default ergänzen**

`DEFAULTS` um `"state": ""` ergänzen, am Ende vor der schließenden Klammer (nach `"hourly_rate"`):

```python
DEFAULTS = {
    "email": "",
    "default_start": "08:00",
    "default_end": "16:00",
    "default_pause": 30,
    "recipient": "",
    "autostart": False,
    "name": "",
    "mail_subject": "Zeiterfassung — {zeitraum}",
    "mail_greeting": "Sehr geehrte Damen und Herren,",
    "mail_content": "anbei erhalten Sie meine Zeiterfassung für den Zeitraum {zeitraum}.",
    "mail_closing": "Mit freundlichen Grüßen",
    "hourly_rate": 0.0,
    "state": "",
}
```

- [ ] **Step 2: Default-Verhalten verifizieren**

```bash
python -c "from src.settings import DEFAULTS; assert DEFAULTS['state'] == ''; print('ok')"
```
Erwartung: `ok`

`Settings._load` merged geladene JSON-Werte in eine Default-Kopie — alte `settings.json`-Dateien werden also automatisch um den Key ergänzt, kein Migrations-Code nötig.

- [ ] **Step 3: Commit**

```bash
git add src/settings.py
git commit -m "feat(settings): add 'state' key for selected Bundesland"
```

---

## Task 6: Settings-Dialog Combobox

Bundesland-Auswahl in den Einstellungen.

**Files:**
- Modify: `src/dialogs/settings_dialog.py`

- [ ] **Step 1: Import ergänzen**

In `src/dialogs/settings_dialog.py`, am Ende der Imports (nach Zeile 14 `from src.time_utils import validate_entry`):

```python
from src.holidays_de import STATES
```

- [ ] **Step 2: Combobox einfügen, alle nachfolgenden `row=`-Indizes inkrementieren**

In Zeile ~98–104 steht der Stundenlohn-Block (row=8). Direkt **nach** dem Stundenlohn-Block (also vor der Mail-Vorlage-Sektion in Zeile 106) einfügen:

```python
    label("Bundesland:", row=9)
    state_labels = [lbl for _, lbl in STATES]
    current_code = settings.get("state")
    current_label = next(
        (lbl for code, lbl in STATES if code == current_code),
        STATES[0][1],
    )
    state_var = tk.StringVar(value=current_label)
    dark_combo(dialog, state_var, state_labels).grid(row=9, column=1, padx=10, pady=8)
```

Anschließend **alle nachfolgenden `row=`-Werte um 1 erhöhen**:
- `row=9` (Mail-Vorlage-Header) → `row=10`
- `row=10` (Betreff) → `row=11`
- `row=11` (Anrede) → `row=12`
- `row=12` (Inhalt) → `row=13`
- `row=13` (Gruß) → `row=14`
- `row=14` (Platzhalter-Hinweis) → `row=15`
- `row=15` (Autostart-Checkbox) → `row=16`
- `row=16` (Buttons) → `row=17`

- [ ] **Step 3: Speichern-Logik ergänzen**

In `save_settings()` (nach `settings.set("hourly_rate", ...)`, vor `on_change()`):

```python
        selected_label = state_var.get()
        selected_code = next(
            (code for code, lbl in STATES if lbl == selected_label),
            "",
        )
        settings.set("state", selected_code)
```

- [ ] **Step 4: Manuell verifizieren**

```bash
python -m src.main
```
Settings öffnen → „Bundesland"-Dropdown vorhanden → Auswahl „Bayern" → Speichern → Settings-Dialog erneut öffnen → „Bayern" steht weiterhin drin.

Auch `settings.json` checken: enthält jetzt `"state": "BY"`.

- [ ] **Step 5: Commit**

```bash
git add src/dialogs/settings_dialog.py
git commit -m "feat(settings): Bundesland selector in settings dialog"
```

---

## Task 7: Eintrag-Dialog Feiertags-Warnung

Warnung nur beim **Anlegen** eines neuen Eintrags an einem Feiertag.

**Files:**
- Modify: `src/dialogs/entry_dialog.py`

- [ ] **Step 1: Imports ergänzen**

Aktuelle Imports (Zeile 1–8):
```python
import tkinter as tk
from tkinter import messagebox

from src.theme import (
    BG, FONT, PAUSE_VALUES, TEXT, TIME_VALUES,
    apply_combobox_style, dark_combo, primary_button, secondary_button,
)
from src.time_utils import validate_entry
```

Ergänzen:
```python
import datetime

from src.holidays_de import get_holidays
```

- [ ] **Step 2: Holiday-Check in `save()` einbauen**

In `save()` (Zeile 48–55):
```python
    def save():
        ok, msg = validate_entry(start_var.get(), end_var.get(), pause_minutes=int(pause_var.get()))
        if not ok:
            messagebox.showerror("Fehler", msg, parent=dialog)
            return
        storage.save(date_str, start_var.get(), end_var.get(), pause=int(pause_var.get()))
        dialog.destroy()
        on_change()
```

Ersetzen durch:
```python
    def save():
        ok, msg = validate_entry(start_var.get(), end_var.get(), pause_minutes=int(pause_var.get()))
        if not ok:
            messagebox.showerror("Fehler", msg, parent=dialog)
            return

        # Feiertags-Warnung nur beim Anlegen, nicht beim Edit (entry is None)
        if entry is None:
            state = settings.get("state")
            if state:
                day = datetime.date.fromisoformat(date_str)
                feiertage = get_holidays(state, day.year)
                if day in feiertage:
                    date_de = day.strftime("%d.%m.%Y")
                    confirm = messagebox.askyesno(
                        "Feiertag",
                        f"Der {date_de} ist {feiertage[day]} (Feiertag).\n\n"
                        "Trotzdem Eintrag anlegen?",
                        parent=dialog,
                    )
                    if not confirm:
                        return

        storage.save(date_str, start_var.get(), end_var.get(), pause=int(pause_var.get()))
        dialog.destroy()
        on_change()
```

`entry` ist die Variable aus Zeile 23 (`entry = storage.get(date_str)`). `entry is None` heißt: an diesem Datum existierte kein Eintrag, das ist also ein Anlegen.

- [ ] **Step 3: Manuell verifizieren**

Voraussetzung: `state` ist auf `BY` gesetzt (Bayern).

1. App starten (`python -m src.main`).
2. Auf den 6.1.2026 (Heilige Drei Könige in BY) klicken — Dialog öffnet sich.
3. „Speichern" → es erscheint Warnung „Der 06.01.2026 ist Heilige Drei Könige (Feiertag)…".
4. „Nein" → Dialog bleibt offen, kein Eintrag in `entries.json`.
5. Erneut „Speichern", dieses Mal „Ja" → Eintrag wird gespeichert.
6. Erneut auf den 6.1.2026 klicken → Dialog öffnet, dieses Mal **ohne** Warnung beim erneuten Speichern (weil `entry is not None`).

- [ ] **Step 4: Commit**

```bash
git add src/dialogs/entry_dialog.py
git commit -m "feat(entry): warn when creating entry on a public holiday"
```

---

## Task 8: `ui.py` — Helper, Holiday-Cell, Monatsansicht

Drei-Fall-Render in `_refresh_month`. Helper für Truncation und Holiday-Zelle. Tooltip am Eintrag, der zugleich Feiertag ist.

**Files:**
- Modify: `src/ui.py`

- [ ] **Step 1: Imports ergänzen**

Aktuelle Imports (Zeile 1–24). Ergänzen:

In Zeile 11 nach `from src.time_utils import …`:
```python
from src.holidays_de import get_holidays
from src.tooltip import attach_tooltip
```

In den Theme-Import (Zeile 18–24) ergänzen:
- `HOLIDAY_BG`, `HOLIDAY_BG_HOVER`, `HOLIDAY_ACCENT`

So:
```python
from src.theme import (
    BG, CELL_BG, WEEKEND_BG, ACCENT, TEXT, TEXT_MUTED,
    ENTRY_BG, WEEKEND_ENTRY_BG, WEEKEND_FG,
    HOLIDAY_BG, HOLIDAY_BG_HOVER, HOLIDAY_ACCENT,
    FONT, FONT_BOLD, FONT_HEADER, FONT_FOOTER, FONT_SMALL,
    CELL_BG_HOVER, WEEKEND_BG_HOVER, ENTRY_BG_HOVER, WEEKEND_ENTRY_BG_HOVER,
    icon_button, secondary_button, set_toggle_active, toggle_button,
)
```

- [ ] **Step 2: `_truncate` Helper als Klassenmethode**

Direkt vor `_cell_hover` (Zeile 400, am Ende der Klasse) einfügen:
```python
    @staticmethod
    def _truncate(text: str, max_len: int) -> str:
        if len(text) <= max_len:
            return text
        return text[: max_len - 1] + "…"
```

- [ ] **Step 3: `_build_holiday_cell` Helper**

Direkt nach `_truncate` einfügen — analog zur Eintragszelle, nur grün und mit Feiertagsname statt Zeit-Range:

```python
    def _build_holiday_cell(self, parent, day_text, name, max_name_len, on_click):
        """Grüne Feiertagszelle. Layout analog zur Eintragszelle."""
        cell = tk.Frame(
            parent, bg=HOLIDAY_BG, relief=tk.SOLID,
            highlightbackground=HOLIDAY_ACCENT, highlightthickness=1,
            cursor="hand2",
        )
        day_lbl = tk.Label(
            cell, text=day_text, font=FONT,
            bg=HOLIDAY_BG, fg=TEXT, cursor="hand2",
        )
        day_lbl.pack(pady=(4, 0))
        name_lbl = tk.Label(
            cell, text=self._truncate(name, max_name_len),
            font=FONT_SMALL, bg=HOLIDAY_BG, fg=TEXT_MUTED, cursor="hand2",
        )
        name_lbl.pack(pady=(0, 4))

        for w in (cell, day_lbl, name_lbl):
            w.bind("<Button-1>", lambda e: on_click())
            w.bind("<Enter>", lambda e, c=cell, dl=day_lbl, nl=name_lbl:
                self._cell_hover(c, dl, nl, HOLIDAY_BG_HOVER))
            w.bind("<Leave>", lambda e, c=cell, dl=day_lbl, nl=name_lbl:
                self._cell_hover(c, dl, nl, HOLIDAY_BG))
            attach_tooltip(w, name)
        return cell
```

- [ ] **Step 4: `_refresh_month` erweitern**

In `_refresh_month` (Zeile 220–312), am Anfang vor der Schleife (nach `total_hours = 0.0`, Zeile ~236):

```python
        state = self.settings.get("state")
        holidays_map = get_holidays(state, self.year) if state else {}
```

Innerhalb der Schleife (Zeile 246–294) wird der Branch umgebaut. Aktuell:
```python
                if entry:
                    # ... rote Zelle ...
                else:
                    # ... leere Zelle ...
```

Wird zu:
```python
                day_date = datetime.date(self.year, self.month, day)

                if entry:
                    # ... unverändert: rote Zelle ...
                    # NEU: am Ende der Eintrags-Branch, nach den Bind-Schleifen:
                    if day_date in holidays_map:
                        for w in (cell, day_lbl, time_lbl):
                            attach_tooltip(w, f"Feiertag: {holidays_map[day_date]}")
                elif day_date in holidays_map:
                    cell = self._build_holiday_cell(
                        new_frame,
                        day_text=str(day),
                        name=holidays_map[day_date],
                        max_name_len=12,
                        on_click=lambda d=date_str: self._open_dialog(d),
                    )
                else:
                    # ... unverändert: leere Zelle ...
```

Konkret: in der bestehenden `if entry:`-Branch (Zeilen 256–281), unmittelbar **nach** der `for w in (cell, day_lbl, time_lbl):`-Schleife einfügen:
```python
                    if day_date in holidays_map:
                        for w in (cell, day_lbl, time_lbl):
                            attach_tooltip(w, f"Feiertag: {holidays_map[day_date]}")
```

Und der `else:`-Branch (Zeile 282) wird zu `elif day_date in holidays_map:` (mit dem `_build_holiday_cell`-Aufruf), gefolgt von einem neuen `else:` für die leere Zelle.

`day_date` muss am Anfang der inneren Schleife (vor dem `if entry:`) definiert werden:
```python
                day_date = datetime.date(self.year, self.month, day)
```

- [ ] **Step 5: Smoke-Test (Tests laufen weiterhin grün)**

```bash
pytest tests/ -v
```
Erwartung: alle bestehenden Tests + die 7 aus Task 2 grün.

- [ ] **Step 6: Manuell verifizieren — Monat**

1. Settings: BL = Bayern.
2. April 2026 anzeigen → 3.4. (Karfreitag) und 6.4. (Ostermontag) sind grün, mit verkürztem Namen, Tooltip beim Hover zeigt vollen Namen.
3. Auf einen grünen Tag klicken → Eintrag-Dialog öffnet, beim Speichern Warnung.
4. Settings: BL zurück auf „— kein Bundesland —" → keine grünen Zellen mehr.
5. Settings: BL = Berlin → 8.3. (Frauentag, fällt 2026 auf einen Sonntag — visuell überlagert mit WEEKEND_BG, das ist okay) — wechsle zu März 2026 und prüfe.
6. Tag mit Eintrag UND Feiertag (z.B. an Karfreitag einen Eintrag erstellen): rote Zelle wie bisher, Tooltip zeigt aber „Feiertag: Karfreitag".

- [ ] **Step 7: Commit**

```bash
git add src/ui.py
git commit -m "feat(ui): green holiday cells in month view with tooltip"
```

---

## Task 9: `ui.py` — Wochenansicht analog

`_refresh_week` (Zeile 314–398) bekommt dieselbe Drei-Fall-Logik. ISO-Wochen können zwei Jahre überspannen — deshalb beide Jahre in `holidays_map` mergen.

**Files:**
- Modify: `src/ui.py:314-398`

- [ ] **Step 1: Holidays für beide Jahre laden**

Am Anfang von `_refresh_week`, vor der Schleife (nach Zeile 329 `spans = week_spans_months(...)`):

```python
        state = self.settings.get("state")
        holidays_map: dict[datetime.date, str] = {}
        if state:
            for y in {dates[0].year, dates[-1].year}:
                holidays_map.update(get_holidays(state, y))
```

- [ ] **Step 2: Schleife auf Drei-Fall-Render umbauen**

Innerhalb der Schleife (Zeile 331–379) — in der bestehenden `if entry:`-Branch (Zeile 341–366), nach der `for w in (cell, day_lbl, time_lbl):`-Schleife:
```python
                if day_date in holidays_map:
                    for w in (cell, day_lbl, time_lbl):
                        attach_tooltip(w, f"Feiertag: {holidays_map[day_date]}")
```

Der `else:`-Branch (Zeile 367) wird zu:
```python
            elif day_date in holidays_map:
                cell = self._build_holiday_cell(
                    new_frame,
                    day_text=day_text,
                    name=holidays_map[day_date],
                    max_name_len=18,
                    on_click=lambda d=date_str: self._open_dialog(d),
                )
            else:
                # ... unverändert: leere Zelle ...
```

Hinweis: in der Wochenansicht wird `day_date` bereits aus `dates[col]` abgeleitet (Zeile 331 `for col, day_date in enumerate(dates):`) — das `day_date` heißt im Loop tatsächlich so. Reuse.

- [ ] **Step 3: Smoke-Test**

```bash
pytest tests/ -v
```
Erwartung: alle Tests grün.

- [ ] **Step 4: Manuell verifizieren — Woche**

1. Settings: BL = Bayern.
2. Wochenansicht aktivieren, Karwoche 2026 (KW 14) anzeigen → 3.4. (Karfreitag) grün.
3. KW über Jahresgrenze testen (z.B. KW 53 von 2026, falls anwendbar — sonst KW 1 von 2027 mit Neujahr) — Feiertag wird trotzdem grün gerendert.
4. Tooltip funktioniert.
5. Klick auf grünen Tag öffnet Dialog mit Warnung.

- [ ] **Step 5: Commit**

```bash
git add src/ui.py
git commit -m "feat(ui): green holiday cells in week view"
```

---

## Task 10: PyInstaller — `--collect-all holidays`

Damit die Lib im gefrorenen Build die mitgelieferten Daten findet.

**Files:**
- Modify: `build.py:11-25`

- [ ] **Step 1: `_pyinstaller_common` ergänzen**

In `build.py`, in `_pyinstaller_common`, die `--collect-all`-Liste ergänzen:

```python
        "--collect-all", "xhtml2pdf",
        "--collect-all", "reportlab",
        "--collect-all", "holidays",
```

- [ ] **Step 2: Lokal Build testen (Windows)**

```bash
python build.py
```
Erwartung: Build durchläuft. `dist/Zeiterfassung.exe` (oder Setup.exe wenn Inno Setup vorhanden) wird erzeugt.

- [ ] **Step 3: Manuell — gebaute App testen**

`dist/Zeiterfassung.exe` (bzw. Setup) starten → Settings → BL = Bayern → 6.1.2026 ist grün im Kalender.

- [ ] **Step 4: Commit**

```bash
git add build.py
git commit -m "build: collect-all holidays for PyInstaller bundle"
```

---

## Task 11: Final-Check & PR

- [ ] **Step 1: Vollständiger Testlauf**

```bash
pytest tests/ -v
```
Erwartung: alle grün.

- [ ] **Step 2: CLAUDE.md prüfen**

Lies `CLAUDE.md` durch, ob in der „Tests / CI"-Sektion Updates nötig sind (z.B. Hinweis auf `holidays`-Dep im CI-Workflow). Falls ja: ergänzen, separat committen.

- [ ] **Step 3: Branch pushen, PR erstellen**

```bash
git push -u origin feature/feiertage
gh pr create --title "feat: gesetzliche Feiertage nach Bundesland" --body "$(cat <<'EOF'
## Summary
- Bundesland in den Einstellungen wählbar; Default leer (opt-in)
- Feiertage des gewählten BL erscheinen grün im Monats- und Wochenraster
- Tooltip beim Hover zeigt den vollen Feiertagsnamen
- Beim Anlegen eines Eintrags an einem Feiertag erscheint eine Bestätigungs-Warnung
- PDF-/Mail-Bericht bleibt unverändert (rein lokales UI-Feature)

## Test plan
- [ ] BL = Bayern: 6.1.2026, 3.4./6.4. (Ostern), 1.5., 3.10. grün
- [ ] BL = Berlin: 8.3.2026 grün, 6.1. nicht
- [ ] Default „kein BL": keine Feiertage
- [ ] Eintrag an Feiertag → Warnung beim Speichern; bei „Ja" wird gespeichert (rote Zelle, Tooltip mit Feiertagsname)
- [ ] Edit eines bestehenden Eintrags → keine Warnung
- [ ] Wochenansicht: Feiertage analog
- [ ] Wechsel BL im Settings-Dialog reflektiert sofort (kein Restart)
- [ ] Gebauter PyInstaller-Build zeigt Feiertage (Daten sind gebündelt)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Hinweis: PR-Branch sitzt aktuell auf `ci/release-fixes`. Wenn dieser PR vorher merged wurde, sollte `feature/feiertage` per `git rebase master` auf das neue master rebased werden, bevor du den PR drüber öffnest — sonst sind die Refactor-Commits doppelt.

Versions-Bump (`src/version.py`) und CHANGELOG-Eintrag werden in einem separaten Release-PR gebündelt — nicht hier.

---

## Out of scope (siehe Spec)

- Andere Länder, Bayern-Sonderfälle (Mariä Himmelfahrt / Augsburg-Friedensfest), Schulferien.
- Feiertage in PDF-/Mail-Bericht.
- Stundenlohn-/Soll-Stunden-Anpassung.
- Versions-Bump und CHANGELOG.
