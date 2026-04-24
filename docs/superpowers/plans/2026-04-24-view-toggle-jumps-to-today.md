# View-Toggle Jumps to Today Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Monat/Woche toggle in the header always land on today's month / today's KW, instead of preserving the previously displayed scroll position via inverse-mode lookup.

**Architecture:** Single-file change to `src/ui.py::_set_view`. Both branches replaced with a single `today = datetime.date.today()` lookup followed by per-mode field assignment. The early-return guard, `_update_toggle_style()` call, and `_refresh()` call stay exactly as they are. No changes to `_prev`/`_next` (arrow nav keeps its relative behaviour).

**Tech Stack:** stdlib `datetime`. Already imported at the top of `src/ui.py`.

**Spec reference:** `docs/superpowers/specs/2026-04-24-view-toggle-jumps-to-today-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `src/ui.py` | Modify | Replace 11 lines inside `_set_view` (lines 252-262) with the today-based assignment |

No other files. No tests (behaviour is purely state-mutation; the existing test suite must continue to pass).

---

## Chunk 1: Toggle resets to today

### Task 1: Replace `_set_view` branches with today-based assignment

**Files:**
- Modify: `src/ui.py` (`_set_view`, lines 249-265)

This task has no automated tests. Verification: `python -m pytest -v` (no regressions). Manual smoke test is the controller's job.

- [ ] **Step 1: Apply the edit**

In `src/ui.py`, find this exact block in `_set_view` (currently lines 249-265):

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
```

Replace with:

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

**Key changes:**
- Removed: the `first_day` and `monday` intermediate variables (and their inline comments)
- Removed: `datetime.date(self.year, self.month, 1)` and `datetime.date.fromisocalendar(self.iso_year, self.current_week, 1)` — both used the *previously displayed* state to derive the new state
- Added: single `today = datetime.date.today()` lookup at the top of the post-guard body
- Both branches now read from `today` instead of from `self.year`/`self.month`/`self.iso_year`/`self.current_week`
- The early-return guard (`if mode == self.view_mode: return`), the assignment to `self.view_mode`, the `_update_toggle_style()` call, and the `_refresh()` call all stay byte-for-byte identical

- [ ] **Step 2: Confirm no leftover references**

Run:

```bash
grep -n "first_day\|fromisocalendar" src/ui.py
```

Expected: no matches. Both names only existed in the replaced block.

- [ ] **Step 3: Run the full test suite**

Run: `python -m pytest -v`
Expected: 86 tests pass, no regressions.

- [ ] **Step 4: SKIP — manual UI smoke test (controller's job)**

- [ ] **Step 5: Commit**

```bash
git add src/ui.py
git commit -m "feat: monat/woche toggle resets to today

Both directions of the view toggle now land on today's month / today's
KW instead of preserving the previously displayed scroll position via
inverse-mode lookup. Arrow nav (_prev/_next) keeps its relative
behaviour. The toggle becomes a 'reset to current' gesture."
```

---

## Verification checklist (post-implementation)

- [ ] `python -m pytest -v` all green (86 tests, unchanged count)
- [ ] `grep -n "first_day\|fromisocalendar" src/ui.py` returns empty
- [ ] Manual smoke test (controller): scroll to a different month with the arrow buttons, switch to Woche → land on today's KW. Scroll to a different KW, switch to Monat → land on today's month. Click "Monat" while in Monat view (or "Woche" while in Woche) → nothing happens (early-return guard).
- [ ] One commit on the branch with the message above
