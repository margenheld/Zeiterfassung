# Zeiterfassung Tool Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python/tkinter time tracking tool with a calendar grid UI and JSON persistence.

**Architecture:** Three modules — `storage.py` for JSON persistence, `ui.py` for the tkinter UI (calendar grid, dialogs), and `main.py` as entry point. Storage is decoupled from UI via a simple class interface.

**Tech Stack:** Python 3, tkinter, json (all standard library)

---

## File Structure

| File | Responsibility |
|------|---------------|
| `src/storage.py` | Load/save/delete time entries from JSON file |
| `src/ui.py` | tkinter window: header, calendar grid, footer, day entry dialog |
| `src/main.py` | Entry point — creates Storage + App, runs mainloop |
| `tests/test_storage.py` | Tests for storage layer |
| `tests/test_time_calc.py` | Tests for time calculation and validation logic |

---

## Chunk 1: Storage Layer

### Task 1: Storage class — save and load entries

**Files:**
- Create: `src/storage.py`
- Create: `tests/test_storage.py`

- [ ] **Step 1: Write failing tests for Storage**

```python
# tests/test_storage.py
import os
import json
import pytest
from src.storage import Storage

@pytest.fixture
def tmp_storage(tmp_path):
    return Storage(str(tmp_path / "test.json"))

def test_load_empty(tmp_storage):
    assert tmp_storage.get_all() == {}

def test_save_and_load(tmp_storage):
    tmp_storage.save("2026-03-23", "08:00", "16:30")
    entries = tmp_storage.get_all()
    assert entries["2026-03-23"] == {"start": "08:00", "end": "16:30"}

def test_delete_entry(tmp_storage):
    tmp_storage.save("2026-03-23", "08:00", "16:30")
    tmp_storage.delete("2026-03-23")
    assert "2026-03-23" not in tmp_storage.get_all()

def test_delete_nonexistent(tmp_storage):
    tmp_storage.delete("2026-01-01")  # should not raise

def test_persistence(tmp_path):
    path = str(tmp_path / "test.json")
    s1 = Storage(path)
    s1.save("2026-03-23", "08:00", "16:30")
    s2 = Storage(path)
    assert s2.get_all()["2026-03-23"] == {"start": "08:00", "end": "16:30"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_storage.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.storage'`

- [ ] **Step 3: Implement Storage class**

```python
# src/storage.py
import json
import os

class Storage:
    def __init__(self, filepath="zeiterfassung.json"):
        self.filepath = filepath
        self._data = {}
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, "r", encoding="utf-8") as f:
                self._data = json.load(f)

    def _save_to_disk(self):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get_all(self):
        return dict(self._data)

    def get(self, date_str):
        return self._data.get(date_str)

    def save(self, date_str, start, end):
        self._data[date_str] = {"start": start, "end": end}
        self._save_to_disk()

    def delete(self, date_str):
        if date_str in self._data:
            del self._data[date_str]
            self._save_to_disk()
```

- [ ] **Step 4: Create `src/__init__.py` and `tests/__init__.py`**

Create empty `src/__init__.py` and `tests/__init__.py` files so Python treats them as packages.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_storage.py -v`
Expected: All 5 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/ tests/
git commit -m "feat: add Storage class with JSON persistence and tests"
```

---

## Chunk 2: Time Calculation & Validation

### Task 2: Time parsing, validation, and hour calculation

**Files:**
- Create: `src/time_utils.py`
- Create: `tests/test_time_calc.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_time_calc.py
import pytest
from src.time_utils import parse_time, calculate_hours, validate_entry

def test_parse_valid_time():
    assert parse_time("08:00") == (8, 0)
    assert parse_time("16:30") == (16, 30)

def test_parse_invalid_time():
    assert parse_time("abc") is None
    assert parse_time("25:00") is None
    assert parse_time("12:60") is None
    assert parse_time("") is None

def test_calculate_hours():
    assert calculate_hours("08:00", "16:30") == 8.5
    assert calculate_hours("09:00", "17:00") == 8.0
    assert calculate_hours("06:00", "06:30") == 0.5

def test_validate_entry_valid():
    ok, msg = validate_entry("08:00", "16:30")
    assert ok is True

def test_validate_entry_invalid_format():
    ok, msg = validate_entry("abc", "16:30")
    assert ok is False

def test_validate_entry_end_before_start():
    ok, msg = validate_entry("17:00", "08:00")
    assert ok is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_time_calc.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement time_utils**

```python
# src/time_utils.py

def parse_time(time_str):
    """Parse HH:MM string. Returns (hours, minutes) or None if invalid."""
    try:
        parts = time_str.split(":")
        if len(parts) != 2:
            return None
        h, m = int(parts[0]), int(parts[1])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            return None
        return (h, m)
    except (ValueError, AttributeError):
        return None

def calculate_hours(start_str, end_str):
    """Calculate decimal hours between two HH:MM strings."""
    start = parse_time(start_str)
    end = parse_time(end_str)
    if start is None or end is None:
        return 0.0
    start_min = start[0] * 60 + start[1]
    end_min = end[0] * 60 + end[1]
    return round((end_min - start_min) / 60, 2)

def validate_entry(start_str, end_str):
    """Validate a time entry. Returns (ok, error_message)."""
    start = parse_time(start_str)
    if start is None:
        return False, "Startzeit ungültig (Format: HH:MM)"
    end = parse_time(end_str)
    if end is None:
        return False, "Endzeit ungültig (Format: HH:MM)"
    start_min = start[0] * 60 + start[1]
    end_min = end[0] * 60 + end[1]
    if end_min <= start_min:
        return False, "Endzeit muss nach Startzeit liegen"
    return True, ""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_time_calc.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/time_utils.py tests/test_time_calc.py
git commit -m "feat: add time parsing, validation, and hour calculation with tests"
```

---

## Chunk 3: UI — Calendar Grid & Main Window

### Task 3: Build the tkinter UI

**Files:**
- Create: `src/ui.py`
- Create: `src/main.py`

- [ ] **Step 1: Implement the calendar UI**

```python
# src/ui.py
import tkinter as tk
from tkinter import messagebox
import calendar
import datetime
from src.storage import Storage
from src.time_utils import calculate_hours, validate_entry

DAYS_DE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
MONTHS_DE = [
    "", "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember"
]

class App:
    def __init__(self, root, storage):
        self.root = root
        self.storage = storage
        self.root.title("Zeiterfassung")

        today = datetime.date.today()
        self.year = today.year
        self.month = today.month

        self._build_header()
        self._build_grid()
        self._build_footer()
        self._refresh()

    def _build_header(self):
        frame = tk.Frame(self.root)
        frame.pack(fill=tk.X, padx=10, pady=(10, 0))

        tk.Button(frame, text="<", command=self._prev_month, width=3).pack(side=tk.LEFT)
        self.header_label = tk.Label(frame, text="", font=("Arial", 14, "bold"))
        self.header_label.pack(side=tk.LEFT, expand=True)
        tk.Button(frame, text=">", command=self._next_month, width=3).pack(side=tk.RIGHT)

    def _build_grid(self):
        self.grid_frame = tk.Frame(self.root)
        self.grid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def _build_footer(self):
        self.footer_label = tk.Label(self.root, text="Gesamt: 0.0h", font=("Arial", 12))
        self.footer_label.pack(pady=(0, 10))

    def _prev_month(self):
        if self.month == 1:
            self.month = 12
            self.year -= 1
        else:
            self.month -= 1
        self._refresh()

    def _next_month(self):
        if self.month == 12:
            self.month = 1
            self.year += 1
        else:
            self.month += 1
        self._refresh()

    def _refresh(self):
        self.header_label.config(text=f"{MONTHS_DE[self.month]} {self.year}")

        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        # Column headers
        for col, day_name in enumerate(DAYS_DE):
            lbl = tk.Label(self.grid_frame, text=day_name, font=("Arial", 10, "bold"))
            lbl.grid(row=0, column=col, sticky="nsew", padx=1, pady=1)

        # Calendar weeks
        cal = calendar.Calendar(firstweekday=0)  # Monday first
        entries = self.storage.get_all()
        total_hours = 0.0

        for row, week in enumerate(cal.monthdayscalendar(self.year, self.month), start=1):
            for col, day in enumerate(week):
                if day == 0:
                    # Day outside current month
                    lbl = tk.Label(self.grid_frame, text="", relief=tk.FLAT)
                    lbl.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)
                    continue

                date_str = f"{self.year}-{self.month:02d}-{day:02d}"
                entry = entries.get(date_str)

                text = str(day)
                if entry:
                    hours = calculate_hours(entry["start"], entry["end"])
                    text += f"\n{hours}h"
                    total_hours += hours

                is_weekend = col >= 5
                bg = "#e0e0e0" if is_weekend else "#ffffff"
                if entry:
                    bg = "#d4edda" if not is_weekend else "#c8d6c0"

                cell = tk.Label(
                    self.grid_frame, text=text, relief=tk.RIDGE,
                    bg=bg, width=8, height=3, cursor="hand2"
                )
                cell.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)
                cell.bind("<Button-1>", lambda e, d=date_str: self._open_dialog(d))

        self.footer_label.config(text=f"Gesamt: {round(total_hours, 2)}h")

        # Make grid columns expand evenly
        for col in range(7):
            self.grid_frame.columnconfigure(col, weight=1)

    def _open_dialog(self, date_str):
        dialog = tk.Toplevel(self.root)
        dialog.title(date_str)
        dialog.resizable(False, False)
        dialog.grab_set()

        entry = self.storage.get(date_str)

        tk.Label(dialog, text="Start (HH:MM):").grid(row=0, column=0, padx=10, pady=5)
        start_var = tk.StringVar(value=entry["start"] if entry else "")
        tk.Entry(dialog, textvariable=start_var, width=10).grid(row=0, column=1, padx=10, pady=5)

        tk.Label(dialog, text="Ende (HH:MM):").grid(row=1, column=0, padx=10, pady=5)
        end_var = tk.StringVar(value=entry["end"] if entry else "")
        tk.Entry(dialog, textvariable=end_var, width=10).grid(row=1, column=1, padx=10, pady=5)

        def save():
            ok, msg = validate_entry(start_var.get(), end_var.get())
            if not ok:
                messagebox.showerror("Fehler", msg, parent=dialog)
                return
            self.storage.save(date_str, start_var.get(), end_var.get())
            dialog.destroy()
            self._refresh()

        def delete():
            self.storage.delete(date_str)
            dialog.destroy()
            self._refresh()

        btn_frame = tk.Frame(dialog)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)
        tk.Button(btn_frame, text="Speichern", command=save).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Löschen", command=delete).pack(side=tk.LEFT, padx=5)
```

- [ ] **Step 2: Create the entry point**

```python
# src/main.py
from src.storage import Storage
from src.ui import App
import tkinter as tk

def main():
    storage = Storage("zeiterfassung.json")
    root = tk.Tk()
    app = App(root, storage)
    root.mainloop()

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Manual test — run the app**

Run: `python -m src.main`
Expected: Window opens showing current month calendar grid. Click a day, enter times, save. Verify entry appears in grid and `zeiterfassung.json` is created.

- [ ] **Step 4: Commit**

```bash
git add src/ui.py src/main.py
git commit -m "feat: add tkinter calendar UI with day entry dialog"
```

---

## Chunk 4: Final Verification

### Task 4: Run all tests and verify

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 2: Final manual test**

Run: `python -m src.main`
Verify:
- Month navigation works (< and >)
- Clicking a day opens dialog
- Entering valid times saves and shows hours in cell
- Invalid times show error
- "Löschen" removes entry
- Footer shows correct total
- Weekend cells are gray
- Closing and reopening preserves data

- [ ] **Step 3: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: address issues from final verification"
```
