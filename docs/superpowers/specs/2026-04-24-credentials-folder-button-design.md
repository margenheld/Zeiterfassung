# Credentials-Ordner-Button — Design Spec

## Overview

Add a one-click way for the user to open the data directory where `credentials.json` belongs. Today, a new user (especially on macOS) has no obvious way to find `~/Library/Application Support/Zeiterfassung/` from inside the app. This forces them to consult docs or guess. The fix exposes the path through the UI in two places:

1. **Settings dialog** — a new section "Gmail-Zugangsdaten" with an "Ordner öffnen" button and a status label showing whether `credentials.json` is already present.
2. **Send-error dialog** — when the user clicks "Monat senden" without `credentials.json`, the existing error message is replaced by a custom dialog with two buttons: "Datenordner öffnen" and "OK".

A new module `src/platform_open.py` encapsulates the cross-platform open-in-file-manager logic.

## Scope decisions (settled during brainstorming)

| # | Decision | Consequence |
|---|----------|-------------|
| 1 | Both placements (settings + send-error dialog) | Settings = default discovery path; send-error = the moment it actually matters |
| 2 | Custom `Toplevel` for the send-error dialog (not `messagebox.askyesno`) | Consistent dark theme, two clearly labeled buttons; ~30 lines of dialog code |
| 3 | Status label in settings (✓ vorhanden / ✗ fehlt) | Answers "am I done?" without making the user open Finder/Explorer |
| 4 | Status checked once at dialog open (no live refresh) | Simple; user can close and reopen the dialog to re-check |
| 5 | New module `src/platform_open.py` (not added to `paths.py`, not inlined in `ui.py`) | Matches existing module style (`mail.py`, `autostart.py`); keeps `paths.py` pure; keeps `ui.py` from growing further |
| 6 | No UI tests | Tkinter UI tests are not established in this project; only `platform_open.py` is unit-tested |

## Guiding principles

1. **Discoverable, not magical.** The button opens a folder. It does not auto-download credentials, auto-validate them, or watch the filesystem. The user is in control.
2. **Errors are visible.** Per `CLAUDE.md` ("UI-Fehler sichtbar machen"), failures from `open_folder` (missing `xdg-open`, `os.startfile` raising) are shown via `messagebox.showerror` with `traceback.format_exc()` — never swallowed.
3. **Reuse existing infrastructure.** `self.base_path` is already the resolved data directory (via `paths.py::get_base_path`). On frozen macOS/Linux it is also guaranteed to exist (`os.makedirs(base, exist_ok=True)` in `paths.py`). No new path resolution logic needed.

---

## 1. New module — `src/platform_open.py`

### Public API

```python
def open_folder(path: str) -> None:
    """Open the given directory in the OS file manager.

    Raises:
        RuntimeError: on unsupported platforms.
        OSError / subprocess.CalledProcessError: on OS-level failures
            (propagated to caller).
    """
```

### Implementation

Dispatch on `platform.system()`:

| Platform | Call |
|----------|------|
| `Windows` | `os.startfile(path)` |
| `Darwin`  | `subprocess.run(["open", path], check=True)` |
| `Linux`   | `subprocess.run(["xdg-open", path], check=True)` |
| anything else | `raise RuntimeError(f"Unsupported platform: {system}")` |

No swallowing of errors. The caller (UI) wraps the call in try/except and shows a `messagebox.showerror` with a traceback.

### Import constraint

The module uses `import os` and `import subprocess` (module imports, **not** `from os import startfile` / `from subprocess import run`). This is required so the unit tests can patch the calls via `src.platform_open.os.startfile` and `src.platform_open.subprocess.run`.

---

## 2. Settings dialog — new section "Gmail-Zugangsdaten"

### Placement

A new section is inserted **at the top** of the settings dialog (above "Absender"). Rationale: it's a setup precondition for sending, not a tweakable preference. Putting it first is the most discoverable spot for new users.

### Layout

```
— Gmail-Zugangsdaten —
Datenordner:  [ Ordner öffnen ]   ✓ credentials.json vorhanden
                                  (or ✗ credentials.json fehlt)

Absender:     [ ... ]
Standard-Start: ...
(rest of dialog unchanged)
```

### Widget details

- **Section header** (`tk.Label`): `— Gmail-Zugangsdaten —` in `FONT_BOLD`, `bg=BG`, `fg=TEXT_MUTED`. Same style as the existing `— Mail-Vorlage —` header (`src/ui.py:396-397`).
- **Label** (`tk.Label`): `Datenordner:` in `FONT`, `bg=BG`, `fg=TEXT`.
- **Button** (`tk.Button`): text `Ordner öffnen`, styled like the "Monat senden" footer button (`bg=CELL_BG`, `fg=TEXT`, `relief=tk.FLAT`, `cursor="hand2"`).
- **Status label** (`tk.Label`): one of two strings, color depends on state:
  - `✓ credentials.json vorhanden` — color `#4ade80` (green; new constant `STATUS_OK` in `ui.py`)
  - `✗ credentials.json fehlt` — color `ACCENT` (`#e94560`, existing)

### Status check

Computed once when the dialog opens:

```python
creds_path = os.path.join(self.base_path, "credentials.json")
creds_present = os.path.exists(creds_path)
```

No `trace_add`, no polling. If the user copies the file in and wants visual confirmation, they close and reopen the dialog.

### Button handler

```python
def open_data_folder():
    try:
        open_folder(self.base_path)
    except Exception as e:
        messagebox.showerror(
            "Ordner konnte nicht geöffnet werden",
            f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}",
            parent=dialog,
        )
```

### Grid impact

Existing rows in `_open_settings` (currently 0–14) shift down by 2 — one row for the section header, one row for the label/button/status row. All `.grid(row=N, ...)` calls in the method are renumbered accordingly. No layout rework beyond the renumber.

---

## 3. Send-error dialog — custom `Toplevel`

### Replaces

The current block in `_send_report` at `src/ui.py:822-830`:

```python
if not os.path.exists(credentials_path):
    messagebox.showerror(
        "Keine Zugangsdaten",
        "credentials.json nicht gefunden.\n\n..."
        parent=self.root,
    )
    return
```

### New flow

```python
if not os.path.exists(credentials_path):
    self._show_missing_credentials_dialog()
    return
```

### Dialog `_show_missing_credentials_dialog(self)`

A new method on `App`. Builds and shows a modal `Toplevel`:

- `title("Keine Zugangsdaten")`
- `grab_set()`, `resizable(False, False)`, `configure(bg=BG)`
- Body: a `tk.Label` with `wraplength=380`, `justify="left"`, containing:

  > `credentials.json nicht gefunden.`
  >
  > `Bitte erstelle ein Google Cloud Projekt mit Gmail API und lade die OAuth2 Client-ID als credentials.json in den Datenordner.`

- Two buttons in a `tk.Frame` at the bottom, packed left-to-right (matching the existing `Speichern` / `Abbrechen` order in `_open_settings`):
  - **"Datenordner öffnen"** (ACCENT-styled, like "Speichern", `pack(side=tk.LEFT, padx=5)`): calls `open_folder(self.base_path)`, then `dialog.destroy()`. Errors → `messagebox.showerror` with traceback (parent=dialog).
  - **"OK"** (CELL_BG-styled, like "Abbrechen", `pack(side=tk.LEFT, padx=5)`): calls `dialog.destroy()`.

### No auto-retry

Clicking "Datenordner öffnen" does not re-trigger the send. The user copies `credentials.json` into the opened folder and clicks "Monat senden" again. Keeps the control flow linear.

---

## 4. Tests — `tests/test_platform_open.py`

Four unit tests, all using `monkeypatch`:

```python
def test_open_folder_windows(monkeypatch):
    # platform.system() → "Windows"
    # os.startfile mocked, asserts called with the given path

def test_open_folder_macos(monkeypatch):
    # platform.system() → "Darwin"
    # subprocess.run mocked, asserts ["open", path], check=True

def test_open_folder_linux(monkeypatch):
    # platform.system() → "Linux"
    # subprocess.run mocked, asserts ["xdg-open", path], check=True

def test_open_folder_unsupported_platform(monkeypatch):
    # platform.system() → "FreeBSD"
    # asserts RuntimeError raised
```

### Cross-platform test gotcha

`os.startfile` does not exist on macOS/Linux. `monkeypatch.setattr` would raise `AttributeError` when patching it on those platforms. Use `raising=False`:

```python
monkeypatch.setattr("src.platform_open.os.startfile", mock, raising=False)
```

This lets the Windows test run on the Linux CI runner (`ubuntu-latest`), matching the existing test workflow strategy.

### Why no UI tests

`tests/` currently contains only storage, time-utils, and report tests — no Tkinter widget tests. Adding UI tests for the settings button or the missing-credentials dialog would require introducing Tkinter test infrastructure, which is out of scope for this change. The UI wiring is small enough to verify manually on each platform during release testing.

### CI fit

The new tests depend only on `platform`, `os`, and `subprocess` — no third-party deps, so they run under `.github/workflows/test.yml` which only installs `pytest` (per `CLAUDE.md`).

---

## File touches summary

| File | Change |
|------|--------|
| `src/platform_open.py` | **new** — `open_folder(path)` + dispatch |
| `src/ui.py` | new section in `_open_settings`; renumber existing grid rows; new `_show_missing_credentials_dialog`; replace `messagebox.showerror` block in `_send_report`; add `STATUS_OK` color constant; import `open_folder` |
| `tests/test_platform_open.py` | **new** — four unit tests |

No changes to `paths.py`, `mail.py`, `report.py`, `storage.py`, build, CI, or installer files.

---

## Out of scope

- Auto-creating the data directory if missing on Windows (already created by `paths.py` on macOS/Linux; on frozen Windows it's the install dir, always present).
- Validating that `credentials.json` is a real Google OAuth2 client file (file-presence check only).
- Watching the filesystem for `credentials.json` to appear and updating the status label live.
- Auto-retrying the send after the user clicks "Datenordner öffnen".
- A "credentials.json einfügen" file-picker that copies a chosen file into the data dir (could be a future addition; explicitly deferred).
