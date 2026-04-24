# Credentials-Status Hot-Reload — Design Spec

## Overview

Small follow-up to `2026-04-24-credentials-folder-button-design.md`. The Settings dialog currently shows the `credentials.json` presence as ✓ / ✗ — but only at dialog-open time. After the user clicks "Ordner öffnen", drops the file into the folder, and switches back to the dialog, the status still reads "fehlt" until they close and reopen the dialog. This change adds a 500 ms polling loop that refreshes the status label live while the dialog is open.

This explicitly **reverses Decision #4 of the predecessor spec** ("Status checked once at dialog open, no live refresh"). The original justification (simplicity) was correct in isolation, but in practice the missing live refresh is the most natural friction point of the feature: the user just opened the folder *to put the file in*, then comes back and the dialog still says "fehlt". The polling loop costs nothing measurable.

## Scope decisions

| # | Decision | Consequence |
|---|----------|-------------|
| 1 | Trigger: 500 ms polling loop via `dialog.after` | Simple, deterministic, fires regardless of how the user adds the file (Explorer, terminal, drag-drop) |
| 2 | Polling interval hardcoded at 500 ms | Fast enough to feel instant; `os.path.exists` on a local path is not measurable. No setting. |
| 3 | Loop self-stops via `status_label.winfo_exists()` check at top of callback | When the dialog is destroyed, the next scheduled `after` fires once with no live widget; the check returns early without rescheduling. No TclError, no leftover timer. |
| 4 | Only the Settings dialog is affected — not the missing-credentials send-error dialog | The send-error dialog is transient and the user closes it to retry. Live polling there would be over-engineering. |
| 5 | No tests | UI polling, no Tkinter test infrastructure. Manual smoke test only. |

## Implementation

### Changes to `src/ui.py::_open_settings`

The existing Gmail-Zugangsdaten block constructs the status label inline and discards the handle:

```python
# current — handle discarded
tk.Label(
    creds_row, text=status_text, font=FONT_SMALL,
    bg=BG, fg=status_fg
).pack(side=tk.LEFT, padx=(10, 0))
```

New version: store the handle, then drive content + scheduling from a single `refresh_status` closure. The pre-computed `creds_present`, `status_text`, `status_fg` block is removed (the closure handles the initial render).

```python
status_label = tk.Label(
    creds_row, text="", font=FONT_SMALL, bg=BG
)
status_label.pack(side=tk.LEFT, padx=(10, 0))

def refresh_status():
    if not status_label.winfo_exists():
        return
    if os.path.exists(creds_path):
        status_label.config(
            text="✓ credentials.json vorhanden", fg=STATUS_OK
        )
    else:
        status_label.config(
            text="✗ credentials.json fehlt", fg=ACCENT
        )
    dialog.after(500, refresh_status)

refresh_status()
```

The initial `refresh_status()` call (no `after` wrapper) does two things at once: paints the label with the correct initial text/color, and schedules the next tick. No separate "initial render" branch needed.

### What stays the same

- Section header, "Datenordner:" label, "Ordner öffnen" button — unchanged.
- `STATUS_OK` constant — unchanged.
- Status text strings ("✓ credentials.json vorhanden" / "✗ credentials.json fehlt") — unchanged.
- Status colors (`STATUS_OK` green / `ACCENT` red) — unchanged.

### Files touched

| File | Change |
|------|--------|
| `src/ui.py` | Replace ~10 lines in `_open_settings` (the inline status-label construction) with the held-reference + `refresh_status` closure |

No new files. No new imports. No tests.

## Out of scope

- Hot-reload anywhere else in the UI (e.g. the missing-credentials send-error dialog, or the date-range dialog after sending fails).
- A general-purpose file-watcher abstraction.
- Configurable polling interval.
- Visual transition animation when the status flips (just a snap-change is fine for a settings panel).
