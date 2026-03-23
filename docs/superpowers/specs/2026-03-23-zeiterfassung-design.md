# Zeiterfassung Tool — Design Spec

## Overview

A small Python/tkinter desktop tool for tracking daily work hours in a calendar-style monthly view. Users click on days to enter start/end times, and the tool calculates and displays total hours per month.

## UI Layout

Single tkinter window with three vertical sections:

### Header
- Displays current month and year (e.g. "März 2026")
- `<` and `>` buttons to navigate between months

### Calendar Grid
- 7 columns: Mo, Di, Mi, Do, Fr, Sa, So
- 5–6 rows of day cells depending on the month
- Each cell shows:
  - Day number (e.g. "23")
  - Hours worked if an entry exists (e.g. "8.5h")
- Weekend days (Sa/So) are visually distinct (light gray background)
- Cells for days outside the current month are empty

### Footer
- Label showing "Gesamt: XX:XX Stunden" — sum of all hours in the displayed month

## Day Entry Dialog

Clicking a day cell opens a `Toplevel` dialog:

- Title: the selected date
- Two input fields: Start time (HH:MM), End time (HH:MM)
- "Speichern" button: calculates hours (end - start), saves entry, updates grid
- "Löschen" button: removes the entry for that day, updates grid
- Hours are computed as simple time difference (no overnight shifts)

## Data Storage

Single JSON file (`zeiterfassung.json`) in the project directory.

```json
{
  "2026-03-23": {"start": "08:00", "end": "16:30"},
  "2026-03-24": {"start": "09:00", "end": "17:00"}
}
```

- Keys: ISO date format (YYYY-MM-DD)
- Saved immediately on "Speichern"
- Loaded on app startup (file created if missing)
- "Löschen" removes the key from the file

## Tech Stack

- Python 3
- tkinter (standard library, no external dependencies)
- json (standard library) for persistence

## Out of Scope

- Target/planned hours (Soll-Stunden)
- Break time tracking
- Export functionality
- Overnight shift support
