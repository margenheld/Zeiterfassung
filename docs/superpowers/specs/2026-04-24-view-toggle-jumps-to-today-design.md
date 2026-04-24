# View-Toggle Jumps to Today — Design Spec

## Overview

Today, switching between the Monat/Woche toggle in the header preserves "where you were": switching to Woche jumps to the first KW of the currently displayed month, switching to Monat jumps to the month containing the currently displayed week's Monday. After scrolling to a different month/KW with the arrow buttons, this means the toggle remembers your scroll position rather than resetting it.

The user wants the opposite: **toggling between views should always land on today's month / today's KW**, regardless of where the navigation was scrolled to. The toggle becomes a "reset to current" gesture.

## Scope decisions

| # | Decision | Consequence |
|---|----------|-------------|
| 1 | Both directions jump to today (symmetric) | Toggle = reset, no asymmetry to remember |
| 2 | Only `_set_view` is changed; arrow nav (`_prev`/`_next`) keeps its current behaviour | Arrow nav still moves relative to where you are; only the toggle resets |
| 3 | `view_mode` is preserved if you click the same toggle twice (the existing `if mode == self.view_mode: return` early-return stays) | Clicking "Woche" while in week view does nothing — no surprise reset |
| 4 | No new tests | The change replaces ~6 lines of branching logic with simpler "set to today" assignments. No unit-testable surface change. |

## Implementation

### `src/ui.py::_set_view` (current ~lines 247–263)

Replace both branches with a single `today = datetime.date.today()` lookup, then assign per mode:

```python
def _set_view(self, mode):
    if mode == self.view_mode:
        return
    today = datetime.date.today()
    if mode == "week":
        iso = today.isocalendar()
        self.iso_year = iso[0]
        self.current_week = iso[1]
    else:
        self.year = today.year
        self.month = today.month
    self.view_mode = mode
    self._update_toggle_style()
    self._refresh()
```

The early-return guard (`if mode == self.view_mode: return`), the `_update_toggle_style()` call, and the `_refresh()` call stay exactly as they are.

### Callers

`_set_view` has exactly two call sites, both inside `_build_header`:

- `tk.Button(... command=lambda: self._set_view("month") ...)` (the "Monat" toggle button)
- `tk.Button(... command=lambda: self._set_view("week") ...)` (the "Woche" toggle button)

Both intentionally affected. No external callers.

## Out of scope

- Changing what the arrow buttons do (`_prev`/`_next`) — they keep their relative-navigation behaviour.
- Adding a separate "Heute"-Button (the toggle now serves that purpose for the active view).
- Persisting the view mode across app restarts.
- Animation / visual feedback when the view jumps.
