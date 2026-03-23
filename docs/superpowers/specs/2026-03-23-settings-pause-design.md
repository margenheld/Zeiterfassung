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

- Loaded on app startup; created with defaults if missing
- Managed by the existing `Storage` pattern (new `Settings` class or extend storage)

## Day Entry Dialog Changes

Add a third field below Start/Ende:

- **Pause (Min):** dropdown, 5-min steps from 0 to 120
- Pre-filled with `default_pause` from settings when creating a new entry
- Pre-filled with the stored per-day value when editing an existing entry
- Saved per day in `zeiterfassung.json`

## Data Format Changes

**zeiterfassung.json** entries gain a `pause` field (integer, minutes):

```json
{"2026-03-23": {"start": "08:00", "end": "16:30", "pause": 30}}
```

- Backward compatibility: existing entries without `pause` field use `default_pause` from settings, or 0 if no settings exist

## Hour Calculation Changes

- Current: `end - start`
- New: `end - start - pause_minutes`
- Applies to: cell display, footer total
- `calculate_hours` in `time_utils.py` gets an optional `pause_minutes` parameter (default 0)

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
