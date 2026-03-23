# Settings & Pause Feature — Design Spec

## Overview

Add a settings dialog (email, default pause) and per-day pause tracking. Work hours are calculated as `end - start - pause`.

## Settings Dialog

- Opened via a gear button (⚙) in the top-right of the header bar
- `Toplevel` window, dark-themed (matching existing UI)
- Fields:
  - **E-Mail:** text entry field for email address (for future time report submission)
  - **Standard-Pause (Min):** dropdown, 5-min steps from 0 to 120, default: 30
- Buttons: "Speichern" (saves + closes), "Abbrechen" (closes without saving)

## Settings Storage

New file `settings.json` in project directory.

```json
{"email": "user@example.com", "default_pause": 30}
```

- Loaded on app startup; created with defaults (`email: ""`, `default_pause: 30`) if missing or corrupted
- Managed by a new `Settings` class (same pattern as `Storage`)
- Settings dialog pre-populates fields with current saved values

## Day Entry Dialog Changes

Add a third field below Start/Ende:

- **Pause (Min):** dropdown showing values as plain numbers (0, 5, 10, ..., 120), 5-min steps
- Pre-filled with `default_pause` from settings when creating a new entry
- Pre-filled with the stored per-day value when editing an existing entry
- Saved per day in `zeiterfassung.json`

## Data Format Changes

**zeiterfassung.json** entries gain a `pause` field (integer, minutes):

```json
{"2026-03-23": {"start": "08:00", "end": "16:30", "pause": 30}}
```

- Backward compatibility: existing entries without `pause` field are treated as pause=0 on display (no migration, no silent default application)

## Hour Calculation Changes

- Current: `calculate_hours("08:00", "16:30")` → converts to minutes, subtracts, returns decimal hours
- New: `calculate_hours("08:00", "16:30", pause_minutes=30)` → same, but also subtracts pause minutes before converting to hours
- Example: (16:30 - 08:00) = 510min - 30min pause = 480min = 8.0h
- No validation that pause < work duration (user responsibility, small tool)
- Applies to: cell display, footer total

## Files to Modify/Create

| File | Change |
|------|--------|
| `src/settings.py` | New — Settings class for loading/saving settings.json |
| `src/time_utils.py` | Modify — add `pause_minutes` param to `calculate_hours` |
| `src/ui.py` | Modify — gear button, settings dialog, pause field in day dialog |
| `src/main.py` | Modify — create Settings instance, pass to App |
| `tests/test_settings.py` | New — tests for Settings class |
| `tests/test_time_calc.py` | Modify — tests for pause parameter |

## Out of Scope

- Email sending functionality (just store the address for now)
- Email validation
- Per-weekday default pauses
