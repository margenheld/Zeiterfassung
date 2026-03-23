# UI Redesign — Dark Modern

## Overview

Restyle the existing tkinter UI from default/light appearance to a dark modern theme. Only `src/ui.py` changes — no new files, no new dependencies.

## Color Palette

| Role | Color |
|------|-------|
| Window background | `#1a1a2e` |
| Cell background | `#16213e` |
| Weekend cells | `#0f3460` |
| Accent (entries, highlights) | `#e94560` |
| Primary text | `#e0e0e0` |
| Muted text | `#888888` |
| Entry cell background | `#1a3a5c` |
| Entry cell border | `#e94560` |
| Weekend entry cell | `#1a3050` |

## Font

Segoe UI (Windows-native, modern feel). Fallback: Arial.

## Main Window Changes

- Root and all frames: dark background (`#1a1a2e`)
- Navigation buttons: background `#16213e`, text `#e94560`, no relief/flat style, rounded feel
- Month/year label: white (`#ffffff`), bold
- Day column headers: muted text (`#888888`)
- Day cells: `#16213e` background, `#e0e0e0` text, rounded appearance (RIDGE relief removed, use FLAT or SOLID)
- Weekend cells: `#0f3460` background
- Cells with entries: `#1a3a5c` background, `#e94560` border, hours shown in accent color
- Empty (outside-month) cells: match window background, no border
- Footer "Gesamt" label: accent color (`#e94560`), bold
- Cursor remains "hand2" on day cells

## Dialog Changes

- Toplevel background: `#1a1a2e`
- Labels: `#e0e0e0` text on dark background
- Entry fields: `#16213e` background, `#e0e0e0` text, `#e94560` insert cursor color
- "Speichern" button: `#e94560` background, white text
- "Löschen" button: `#16213e` background, `#e0e0e0` text
- All widgets match dark theme, no default white elements visible

## Out of Scope

- No structural/layout changes
- No new features
- No new files or dependencies
