# Settings & Pause Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add settings (email, default pause) and per-day pause tracking that subtracts from work hours.

**Architecture:** New `Settings` class for settings.json persistence. Extend `calculate_hours` with pause parameter. Extend `Storage.save` to include pause. Add gear button + settings dialog and pause dropdown in day dialog to UI.

**Tech Stack:** Python 3, tkinter, json (all standard library)

---

## File Structure

| File | Change |
|------|--------|
| `src/settings.py` | **New** — Settings class for loading/saving settings.json |
| `src/time_utils.py` | **Modify** — add `pause_minutes` param to `calculate_hours` |
| `src/storage.py` | **Modify** — extend `save()` to accept pause parameter |
| `src/ui.py` | **Modify** — gear button, settings dialog, pause field in day dialog, pause in calculation |
| `src/main.py` | **Modify** — create Settings, pass to App |
| `tests/test_settings.py` | **New** — tests for Settings class |
| `tests/test_time_calc.py` | **Modify** — add tests for pause parameter |
| `tests/test_storage.py` | **Modify** — add test for pause in save/load |

---

## Chunk 1: Settings Class

### Task 1: Settings class — load and save settings

**Files:**
- Create: `src/settings.py`
- Create: `tests/test_settings.py`

- [ ] **Step 1: Write failing tests for Settings**

```python
# tests/test_settings.py
import pytest
from src.settings import Settings

@pytest.fixture
def tmp_settings(tmp_path):
    return Settings(str(tmp_path / "settings.json"))

def test_defaults(tmp_settings):
    assert tmp_settings.get("email") == ""
    assert tmp_settings.get("default_pause") == 30

def test_save_and_load(tmp_settings):
    tmp_settings.set("email", "test@example.com")
    assert tmp_settings.get("email") == "test@example.com"

def test_set_default_pause(tmp_settings):
    tmp_settings.set("default_pause", 45)
    assert tmp_settings.get("default_pause") == 45

def test_persistence(tmp_path):
    path = str(tmp_path / "settings.json")
    s1 = Settings(path)
    s1.set("email", "test@example.com")
    s1.set("default_pause", 15)
    s2 = Settings(path)
    assert s2.get("email") == "test@example.com"
    assert s2.get("default_pause") == 15

def test_corrupted_file(tmp_path):
    path = str(tmp_path / "settings.json")
    with open(path, "w") as f:
        f.write("not json{{{")
    s = Settings(path)
    assert s.get("email") == ""
    assert s.get("default_pause") == 30
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_settings.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement Settings class**

```python
# src/settings.py
import json
import os

DEFAULTS = {
    "email": "",
    "default_pause": 30,
}

class Settings:
    def __init__(self, filepath="settings.json"):
        self.filepath = filepath
        self._data = dict(DEFAULTS)
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                self._data.update(loaded)
            except (json.JSONDecodeError, ValueError):
                self._data = dict(DEFAULTS)

    def _save_to_disk(self):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, key):
        return self._data.get(key, DEFAULTS.get(key))

    def set(self, key, value):
        self._data[key] = value
        self._save_to_disk()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_settings.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/settings.py tests/test_settings.py
git commit -m "feat: add Settings class for email and default pause"
```

---

## Chunk 2: Extend calculate_hours and Storage with pause

### Task 2: Add pause_minutes to calculate_hours

**Files:**
- Modify: `src/time_utils.py`
- Modify: `tests/test_time_calc.py`

- [ ] **Step 1: Add failing tests for pause parameter**

Append to `tests/test_time_calc.py`:

```python
def test_calculate_hours_with_pause():
    assert calculate_hours("08:00", "16:30", pause_minutes=30) == 8.0
    assert calculate_hours("09:00", "17:00", pause_minutes=60) == 7.0
    assert calculate_hours("08:00", "16:30", pause_minutes=0) == 8.5

def test_calculate_hours_default_no_pause():
    # Existing behavior unchanged when pause_minutes not provided
    assert calculate_hours("08:00", "16:30") == 8.5
```

- [ ] **Step 2: Run tests to verify new tests fail**

Run: `python -m pytest tests/test_time_calc.py -v`
Expected: FAIL — `TypeError: calculate_hours() got an unexpected keyword argument 'pause_minutes'`

- [ ] **Step 3: Update calculate_hours**

Change the function signature in `src/time_utils.py`:

```python
def calculate_hours(start_str, end_str, pause_minutes=0):
    """Calculate decimal hours between two HH:MM strings, minus pause."""
    start = parse_time(start_str)
    end = parse_time(end_str)
    if start is None or end is None:
        return 0.0
    start_min = start[0] * 60 + start[1]
    end_min = end[0] * 60 + end[1]
    return round((end_min - start_min - pause_minutes) / 60, 2)
```

- [ ] **Step 4: Run all time_calc tests**

Run: `python -m pytest tests/test_time_calc.py -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/time_utils.py tests/test_time_calc.py
git commit -m "feat: add pause_minutes parameter to calculate_hours"
```

### Task 3: Extend Storage.save to include pause

**Files:**
- Modify: `src/storage.py`
- Modify: `tests/test_storage.py`

- [ ] **Step 1: Add failing test for pause in storage**

Append to `tests/test_storage.py`:

```python
def test_save_with_pause(tmp_storage):
    tmp_storage.save("2026-03-23", "08:00", "16:30", pause=30)
    entry = tmp_storage.get("2026-03-23")
    assert entry == {"start": "08:00", "end": "16:30", "pause": 30}

def test_save_default_pause_zero(tmp_storage):
    tmp_storage.save("2026-03-23", "08:00", "16:30")
    entry = tmp_storage.get("2026-03-23")
    assert entry == {"start": "08:00", "end": "16:30", "pause": 0}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_storage.py -v`
Expected: FAIL — `TypeError: save() got an unexpected keyword argument 'pause'`

- [ ] **Step 3: Update Storage.save**

In `src/storage.py`, change `save` method:

```python
def save(self, date_str, start, end, pause=0):
    self._data[date_str] = {"start": start, "end": end, "pause": pause}
    self._save_to_disk()
```

- [ ] **Step 4: Update existing storage tests**

The existing `test_save_and_load` and `test_persistence` tests assert entries without a `pause` key. Since `save()` now always writes `pause`, update those assertions:

In `test_save_and_load`:
```python
assert entries["2026-03-23"] == {"start": "08:00", "end": "16:30", "pause": 0}
```

In `test_persistence`:
```python
assert s2.get_all()["2026-03-23"] == {"start": "08:00", "end": "16:30", "pause": 0}
```

- [ ] **Step 5: Run all storage tests**

Run: `python -m pytest tests/test_storage.py -v`
Expected: All 7 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/storage.py tests/test_storage.py
git commit -m "feat: extend Storage.save with pause parameter"
```

---

## Chunk 3: UI Changes

### Task 4: Add gear button, settings dialog, pause in day dialog

**Files:**
- Modify: `src/ui.py`
- Modify: `src/main.py`

- [ ] **Step 1: Update App.__init__ to accept settings**

In `src/ui.py`, change the constructor:

```python
class App:
    def __init__(self, root, storage, settings):
        self.root = root
        self.storage = storage
        self.settings = settings
        # ... rest unchanged
```

- [ ] **Step 2: Add gear button to header**

In `_build_header`, add a gear button to the right of the `>` button. Add this **after** the `>` button in source order (since `side=tk.RIGHT` packs right-to-left, it will appear to the right of `>`):

```python
tk.Button(
    frame, text="\u2699", command=self._open_settings, width=3,
    font=FONT_BOLD, bg=CELL_BG, fg=TEXT_MUTED,
    activebackground=ENTRY_BG, activeforeground=TEXT,
    relief=tk.FLAT, cursor="hand2"
).pack(side=tk.RIGHT, padx=(0, 5))
```

- [ ] **Step 3: Add _open_settings method**

```python
def _open_settings(self):
    dialog = tk.Toplevel(self.root)
    dialog.title("Einstellungen")
    dialog.resizable(False, False)
    dialog.grab_set()
    dialog.configure(bg=BG)

    # Email
    tk.Label(
        dialog, text="E-Mail:", font=FONT, bg=BG, fg=TEXT
    ).grid(row=0, column=0, padx=10, pady=8, sticky="w")

    email_var = tk.StringVar(value=self.settings.get("email"))
    email_entry = tk.Entry(
        dialog, textvariable=email_var, width=25, font=FONT,
        bg=CELL_BG, fg=TEXT, insertbackground=ACCENT,
        relief=tk.FLAT, highlightbackground=TEXT_MUTED,
        highlightcolor=ACCENT, highlightthickness=1
    )
    email_entry.grid(row=0, column=1, padx=10, pady=8)

    # Default pause
    tk.Label(
        dialog, text="Standard-Pause (Min):", font=FONT, bg=BG, fg=TEXT
    ).grid(row=1, column=0, padx=10, pady=8, sticky="w")

    pause_values = [str(m) for m in range(0, 125, 5)]
    pause_var = tk.StringVar(value=str(self.settings.get("default_pause")))

    # Reuse dark combobox style
    style = ttk.Style(dialog)
    style.theme_use("clam")
    style.configure(
        "Dark.TCombobox",
        fieldbackground=CELL_BG, background=CELL_BG,
        foreground=TEXT, arrowcolor=ACCENT,
        bordercolor=TEXT_MUTED, lightcolor=CELL_BG, darkcolor=CELL_BG,
        selectbackground=ENTRY_BG, selectforeground=TEXT
    )
    style.map("Dark.TCombobox",
        fieldbackground=[("readonly", CELL_BG)],
        selectbackground=[("readonly", CELL_BG)],
        selectforeground=[("readonly", TEXT)],
        bordercolor=[("focus", ACCENT)],
    )
    dialog.option_add("*TCombobox*Listbox.background", CELL_BG)
    dialog.option_add("*TCombobox*Listbox.foreground", TEXT)
    dialog.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
    dialog.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
    dialog.option_add("*TCombobox*Listbox.font", FONT)

    pause_cb = ttk.Combobox(
        dialog, textvariable=pause_var, values=pause_values,
        width=8, font=FONT, style="Dark.TCombobox", state="readonly"
    )
    pause_cb.grid(row=1, column=1, padx=10, pady=8)

    def save_settings():
        self.settings.set("email", email_var.get())
        self.settings.set("default_pause", int(pause_var.get()))
        dialog.destroy()

    def cancel():
        dialog.destroy()

    btn_frame = tk.Frame(dialog, bg=BG)
    btn_frame.grid(row=2, column=0, columnspan=2, pady=12)

    tk.Button(
        btn_frame, text="Speichern", command=save_settings, font=FONT_BOLD,
        bg=ACCENT, fg="#ffffff",
        activebackground="#c73550", activeforeground="#ffffff",
        relief=tk.FLAT, padx=16, pady=4, cursor="hand2"
    ).pack(side=tk.LEFT, padx=5)

    tk.Button(
        btn_frame, text="Abbrechen", command=cancel, font=FONT,
        bg=CELL_BG, fg=TEXT,
        activebackground=ENTRY_BG, activeforeground=TEXT,
        relief=tk.FLAT, padx=16, pady=4, cursor="hand2"
    ).pack(side=tk.LEFT, padx=5)
```

- [ ] **Step 4: Add pause dropdown to day entry dialog**

In `_open_dialog`, after the Ende combobox (row 1), add:

```python
tk.Label(
    dialog, text="Pause (Min):", font=FONT, bg=BG, fg=TEXT
).grid(row=2, column=0, padx=10, pady=8, sticky="w")

pause_values = [str(m) for m in range(0, 125, 5)]
default_pause = self.settings.get("default_pause")
if entry and "pause" in entry:
    current_pause = str(entry["pause"])
else:
    current_pause = str(default_pause) if not entry else "0"
pause_var = tk.StringVar(value=current_pause)

pause_cb = ttk.Combobox(
    dialog, textvariable=pause_var, values=pause_values,
    width=8, font=FONT, style="Dark.TCombobox", state="readonly"
)
pause_cb.grid(row=2, column=1, padx=10, pady=8)
```

Move button frame to row 3. Update save to include pause:

```python
def save():
    ok, msg = validate_entry(start_var.get(), end_var.get())
    if not ok:
        messagebox.showerror("Fehler", msg, parent=dialog)
        return
    self.storage.save(date_str, start_var.get(), end_var.get(), pause=int(pause_var.get()))
    dialog.destroy()
    self._refresh()
```

- [ ] **Step 5: Update _refresh to use pause in calculation**

In `_refresh`, change the hours calculation:

```python
if entry:
    pause = entry.get("pause", 0)
    hours = calculate_hours(entry["start"], entry["end"], pause_minutes=pause)
    text += f"\n{hours}h"
    total_hours += hours
```

- [ ] **Step 6: Update main.py**

```python
# src/main.py
from src.storage import Storage
from src.settings import Settings
from src.ui import App
import tkinter as tk

def main():
    storage = Storage("zeiterfassung.json")
    settings = Settings("settings.json")
    root = tk.Tk()
    app = App(root, storage, settings)
    root.mainloop()

if __name__ == "__main__":
    main()
```

- [ ] **Step 7: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 8: Manual test**

Run: `python -m src.main`
Verify:
- Gear button visible in header, opens settings dialog
- Email field works, default pause dropdown works
- Settings persist after closing and reopening
- Day dialog shows pause dropdown, pre-filled with default
- Hours displayed in cells and footer account for pause
- Editing existing entry shows saved pause value

- [ ] **Step 9: Commit**

```bash
git add src/ui.py src/main.py
git commit -m "feat: add settings dialog and pause field in day entry"
```
