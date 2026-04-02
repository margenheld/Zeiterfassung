# Kalenderwoche-Ansicht Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a weekly (KW) view alongside the existing monthly view, switchable via a toggle in the header.

**Architecture:** Add `view_mode`, `iso_year`, and `current_week` state to the existing `App` class. The `_refresh()` method dispatches to `_refresh_month()` or `_refresh_week()`. Navigation methods become generic. A toggle switch in the header controls the mode.

**Tech Stack:** Python 3, tkinter, datetime (ISO calendar)

**Spec:** `docs/superpowers/specs/2026-04-02-kalenderwoche-ansicht-design.md`

---

## Chunk 1: Week Utility Functions + Tests

### Task 1: Add week helper functions to `time_utils.py`

**Files:**
- Modify: `src/time_utils.py`
- Create: `tests/test_week_utils.py`

- [ ] **Step 1: Write failing tests for week helpers**

Create `tests/test_week_utils.py`:

```python
import datetime
from src.time_utils import get_week_dates, get_week_label


def test_get_week_dates_regular():
    """KW 14 of 2026: Mon Mar 30 - Sun Apr 5"""
    dates = get_week_dates(2026, 14)
    assert len(dates) == 7
    assert dates[0] == datetime.date(2026, 3, 30)  # Monday
    assert dates[6] == datetime.date(2026, 4, 5)    # Sunday


def test_get_week_dates_year_boundary():
    """KW 1 of 2026 starts on Mon Dec 29, 2025"""
    dates = get_week_dates(2026, 1)
    assert dates[0] == datetime.date(2025, 12, 29)
    assert dates[6] == datetime.date(2026, 1, 4)


def test_get_week_dates_kw53():
    """2020 has KW 53"""
    dates = get_week_dates(2020, 53)
    assert dates[0] == datetime.date(2020, 12, 28)
    assert dates[6] == datetime.date(2021, 1, 3)


def test_get_week_label():
    assert get_week_label(2026, 14) == "KW 14 \u00b7 2026"
    assert get_week_label(2020, 53) == "KW 53 \u00b7 2020"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_week_utils.py -v`
Expected: FAIL with ImportError (functions don't exist yet)

- [ ] **Step 3: Implement week helpers**

Add `import datetime` at the **top** of `src/time_utils.py` (before existing functions), then append the two new functions at the end:

```python
import datetime


def get_week_dates(iso_year, iso_week):
    """Return list of 7 datetime.date objects (Mon-Sun) for the given ISO week."""
    monday = datetime.date.fromisocalendar(iso_year, iso_week, 1)
    return [monday + datetime.timedelta(days=i) for i in range(7)]


def get_week_label(iso_year, iso_week):
    """Return display label like 'KW 14 \u00b7 2026'."""
    return f"KW {iso_week} \u00b7 {iso_year}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_week_utils.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/time_utils.py tests/test_week_utils.py
git commit -m "feat: add week date helper functions with tests"
```

---

## Chunk 2: State + Header Toggle + Generic Navigation

### Task 2: Add view state, toggle switch, and generic navigation

**Files:**
- Modify: `src/ui.py:50-84` (App.__init__)
- Modify: `src/ui.py:86-114` (App._build_header)
- Modify: `src/ui.py:137-151` (navigation methods)

Note: The header, navigation, and view-switching changes are done atomically in one task. This avoids a broken state where buttons reference methods that don't exist yet.

- [ ] **Step 1: Add view state to `__init__`**

In `src/ui.py`, after line 79 (`self.month = today.month`), add:

```python
        self.view_mode = "month"  # "month" or "week"
        iso = today.isocalendar()
        self.iso_year = iso[0]
        self.current_week = iso[1]
```

- [ ] **Step 2: Add import for `get_week_dates` and `get_week_label`**

In `src/ui.py` line 10, change:

```python
from src.time_utils import calculate_hours, validate_entry
```

to:

```python
from src.time_utils import calculate_hours, validate_entry, get_week_dates, get_week_label
```

- [ ] **Step 3: Replace `_prev_month` / `_next_month` with generic `_prev` / `_next`**

Remove `_prev_month` and `_next_month` methods (lines 137-151). Replace with:

```python
    def _prev(self):
        if self.view_mode == "month":
            if self.month == 1:
                self.month = 12
                self.year -= 1
            else:
                self.month -= 1
        else:
            dates = get_week_dates(self.iso_year, self.current_week)
            prev_monday = dates[0] - datetime.timedelta(days=7)
            iso = prev_monday.isocalendar()
            self.iso_year = iso[0]
            self.current_week = iso[1]
        self._refresh()

    def _next(self):
        if self.view_mode == "month":
            if self.month == 12:
                self.month = 1
                self.year += 1
            else:
                self.month += 1
        else:
            dates = get_week_dates(self.iso_year, self.current_week)
            next_monday = dates[0] + datetime.timedelta(days=7)
            iso = next_monday.isocalendar()
            self.iso_year = iso[0]
            self.current_week = iso[1]
        self._refresh()
```

- [ ] **Step 4: Add `_set_view` and `_update_toggle_style` methods** (after `_next`):

```python
    def _set_view(self, mode):
        if mode == self.view_mode:
            return
        if mode == "week":
            # Jump to first KW of current month
            first_day = datetime.date(self.year, self.month, 1)
            iso = first_day.isocalendar()
            self.iso_year = iso[0]
            self.current_week = iso[1]
        else:
            # Jump to month containing Monday of current week
            monday = datetime.date.fromisocalendar(self.iso_year, self.current_week, 1)
            self.year = monday.year
            self.month = monday.month
        self.view_mode = mode
        self._update_toggle_style()
        self._refresh()

    def _update_toggle_style(self):
        if self.view_mode == "month":
            self.btn_month.config(bg=ACCENT, fg="#ffffff", activebackground=ACCENT, activeforeground="#ffffff")
            self.btn_week.config(bg=CELL_BG, fg=TEXT_MUTED, activebackground=ENTRY_BG, activeforeground=TEXT)
        else:
            self.btn_week.config(bg=ACCENT, fg="#ffffff", activebackground=ACCENT, activeforeground="#ffffff")
            self.btn_month.config(bg=CELL_BG, fg=TEXT_MUTED, activebackground=ENTRY_BG, activeforeground=TEXT)
```

- [ ] **Step 5: Replace `_build_header` with toggle switch version**

Replace the entire `_build_header` method with:

```python
    def _build_header(self):
        frame = tk.Frame(self.root, bg=BG)
        frame.pack(fill=tk.X, padx=10, pady=(10, 0))

        tk.Button(
            frame, text="\u2039", command=self._prev, width=3,
            font=FONT_BOLD, bg=CELL_BG, fg=ACCENT,
            activebackground=ENTRY_BG, activeforeground=ACCENT,
            relief=tk.FLAT, cursor="hand2"
        ).pack(side=tk.LEFT)

        # Toggle switch frame
        toggle_frame = tk.Frame(frame, bg=BG)
        toggle_frame.pack(side=tk.LEFT, padx=10)

        self.btn_month = tk.Button(
            toggle_frame, text="Monat", command=lambda: self._set_view("month"),
            font=FONT_SMALL, width=6, relief=tk.FLAT, cursor="hand2",
            bg=ACCENT, fg="#ffffff",
            activebackground=ACCENT, activeforeground="#ffffff"
        )
        self.btn_month.pack(side=tk.LEFT, padx=(0, 1))

        self.btn_week = tk.Button(
            toggle_frame, text="Woche", command=lambda: self._set_view("week"),
            font=FONT_SMALL, width=6, relief=tk.FLAT, cursor="hand2",
            bg=CELL_BG, fg=TEXT_MUTED,
            activebackground=ENTRY_BG, activeforeground=TEXT
        )
        self.btn_week.pack(side=tk.LEFT)

        self.header_label = tk.Label(
            frame, text="", font=FONT_HEADER, bg=BG, fg="#ffffff"
        )
        self.header_label.pack(side=tk.LEFT, expand=True)

        tk.Button(
            frame, text="\u2699", command=self._open_settings, width=3,
            font=FONT_BOLD, bg=CELL_BG, fg=TEXT_MUTED,
            activebackground=ENTRY_BG, activeforeground=TEXT,
            relief=tk.FLAT, cursor="hand2"
        ).pack(side=tk.RIGHT)

        tk.Button(
            frame, text="\u203a", command=self._next, width=3,
            font=FONT_BOLD, bg=CELL_BG, fg=ACCENT,
            activebackground=ENTRY_BG, activeforeground=ACCENT,
            relief=tk.FLAT, cursor="hand2"
        ).pack(side=tk.RIGHT, padx=(0, 5))
```

- [ ] **Step 6: Run app to verify toggle and navigation work**

Run: `python -m src.main`
Expected: Toggle buttons visible, arrows navigate, switching modes changes header text. Week mode won't show content yet (that's the next task).

- [ ] **Step 7: Commit**

```bash
git add src/ui.py
git commit -m "feat: add view state, toggle switch, and generic navigation"
```

---

## Chunk 3: Week Grid Rendering + Window Geometry

### Task 3: Implement week grid rendering

Note: Both `_refresh_month` and `_refresh_week` handle their own footer update (total hours + brutto). This duplication is intentional -- each view calculates totals differently.

**Files:**
- Modify: `src/ui.py:406-500` (_refresh method)

- [ ] **Step 1: Extract month grid logic into `_refresh_month`**

Rename the current `_refresh` body into `_refresh_month` and create a new `_refresh` that dispatches:

```python
    def _refresh(self):
        if self.view_mode == "month":
            self.header_label.config(text=f"{MONTHS_DE[self.month]} {self.year}")
            self._refresh_month()
        else:
            self.header_label.config(
                text=get_week_label(self.iso_year, self.current_week)
            )
            self._refresh_week()
```

Move the existing `_refresh` body (from line 409 `# Build new grid off-screen...` through line 500) into `_refresh_month(self)`. Keep the header update in `_refresh` as shown above, and remove the header line from `_refresh_month`.

- [ ] **Step 2: Run app in month mode to verify no regression**

Run: `python -m src.main`
Expected: Month view works exactly as before

- [ ] **Step 3: Implement `_refresh_week`**

Add after `_refresh_month`:

```python
    def _refresh_week(self):
        new_frame = tk.Frame(self.root, bg=BG)

        # Column headers
        for col, day_name in enumerate(DAYS_DE):
            fg = TEXT_MUTED if col < 5 else "#6c6c80"
            lbl = tk.Label(
                new_frame, text=day_name, font=FONT_BOLD,
                bg=BG, fg=fg
            )
            lbl.grid(row=0, column=col, sticky="nsew", padx=2, pady=2)

        dates = get_week_dates(self.iso_year, self.current_week)
        entries = self.storage.get_all()
        total_hours = 0.0

        for col, day_date in enumerate(dates):
            date_str = day_date.isoformat()
            entry = entries.get(date_str)
            is_weekend = col >= 5
            day_num = day_date.day

            fg = TEXT
            if is_weekend and not entry:
                fg = "#6c6c80"

            if entry:
                pause = entry.get("pause", 0)
                hours = calculate_hours(entry["start"], entry["end"], pause_minutes=pause)
                total_hours += hours
                bg = WEEKEND_ENTRY_BG if is_weekend else ENTRY_BG
                cell = tk.Frame(
                    new_frame, bg=bg, relief=tk.SOLID,
                    highlightbackground=ACCENT, highlightthickness=1,
                    cursor="hand2"
                )
                day_lbl = tk.Label(
                    cell, text=str(day_num), font=FONT,
                    bg=bg, fg=TEXT, cursor="hand2"
                )
                day_lbl.pack(pady=(8, 0))
                time_lbl = tk.Label(
                    cell, text=f"{entry['start']}-{entry['end']}",
                    font=FONT_SMALL, bg=bg, fg=TEXT_MUTED, cursor="hand2"
                )
                time_lbl.pack(pady=(0, 8))
                hover_bg = WEEKEND_ENTRY_BG_HOVER if is_weekend else ENTRY_BG_HOVER
                for w in (cell, day_lbl, time_lbl):
                    w.bind("<Button-1>", lambda e, d=date_str: self._open_dialog(d))
                    w.bind("<Button-3>", lambda e, d=date_str: self._delete_entry(d))
                    w.bind("<Enter>", lambda e, c=cell, dl=day_lbl, tl=time_lbl, hb=hover_bg: self._cell_hover(c, dl, tl, hb))
                    w.bind("<Leave>", lambda e, c=cell, dl=day_lbl, tl=time_lbl, ob=bg: self._cell_hover(c, dl, tl, ob))
            else:
                bg = WEEKEND_BG if is_weekend else CELL_BG
                hover_bg = WEEKEND_BG_HOVER if is_weekend else CELL_BG_HOVER
                cell = tk.Label(
                    new_frame, text=str(day_num), font=FONT,
                    bg=bg, fg=fg, relief=tk.FLAT,
                    width=8, height=5, cursor="hand2"
                )
                cell.bind("<Button-1>", lambda e, d=date_str: self._open_dialog(d))
                cell.bind("<Enter>", lambda e, c=cell, hb=hover_bg: c.config(bg=hb))
                cell.bind("<Leave>", lambda e, c=cell, ob=bg: c.config(bg=ob))

            cell.grid(row=1, column=col, sticky="nsew", padx=2, pady=2)

        for col in range(7):
            new_frame.columnconfigure(col, weight=1)

        # Swap frames
        self.grid_frame.destroy()
        self.grid_frame = new_frame
        self.grid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5,
                             before=self.footer_label.master)

        # Footer
        rate = self.settings.get("hourly_rate") or 0
        if rate > 0:
            brutto = round(total_hours * rate, 2)
            self.footer_label.config(
                text=f"Gesamt: {round(total_hours, 2)}h  \u2014  {brutto:.2f} \u20ac brutto"
            )
        else:
            self.footer_label.config(text=f"Gesamt: {round(total_hours, 2)}h")
```

- [ ] **Step 4: Run app and test week view**

Run: `python -m src.main`
Expected: Toggle to "Woche" shows 7 cells for current week, arrows navigate weekly, footer shows weekly hours

- [ ] **Step 5: Commit**

```bash
git add src/ui.py
git commit -m "feat: implement week grid rendering with footer"
```

### Task 4: Adjust window geometry for view modes

**Files:**
- Modify: `src/ui.py` (_refresh method)

- [ ] **Step 1: Add geometry adjustment to `_refresh`**

Update `_refresh` to adjust window size after rendering:

```python
    def _refresh(self):
        if self.view_mode == "month":
            self.header_label.config(text=f"{MONTHS_DE[self.month]} {self.year}")
            self._refresh_month()
        else:
            self.header_label.config(
                text=get_week_label(self.iso_year, self.current_week)
            )
            self._refresh_week()
        # Let tkinter compute the required size, then resize window
        self.root.update_idletasks()
        self.root.geometry("")
```

The `self.root.geometry("")` call tells tkinter to resize the window to fit its content. This makes the window smaller for week view (1 row) and larger for month view (4-6 rows) automatically.

- [ ] **Step 2: Run app and verify geometry adjusts on toggle**

Run: `python -m src.main`
Expected: Window shrinks when switching to week view, grows back when switching to month view

- [ ] **Step 3: Commit**

```bash
git add src/ui.py
git commit -m "feat: adjust window geometry when switching view modes"
```

---

## Chunk 4: Final Verification

### Task 5: Full test run and manual verification

- [ ] **Step 1: Run all existing tests**

Run: `python -m pytest tests/ -v`
Expected: All tests pass (no regressions)

- [ ] **Step 2: Manual smoke test checklist**

1. App starts in month view (default)
2. Toggle to week view -- shows current KW with 7 day columns
3. Navigate weeks with arrows -- KW number updates in header
4. Toggle back to month -- shows correct month
5. Click a day cell in week view -- edit dialog opens
6. Save an entry -- cell updates with time range
7. Right-click a cell in week view -- deletes entry
8. Footer shows weekly hours in week view
9. "Monat senden" button still works from week view
10. Year boundary: navigate to KW 1 of next year, verify dates are correct

- [ ] **Step 3: Final commit if any fixes were needed**

```bash
git add -u
git commit -m "fix: address issues found during smoke testing"
```
