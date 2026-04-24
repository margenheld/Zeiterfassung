# Credentials-Ordner-Button Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the user a one-click way to open the data directory where `credentials.json` belongs — both proactively (Settings dialog) and reactively (when the send fails because the file is missing).

**Architecture:** A new module `src/platform_open.py` encapsulates the cross-platform "open folder in OS file manager" logic (dispatch over `platform.system()`). `src/ui.py` gains (a) a new section at the top of the Settings dialog with an "Ordner öffnen" button + status label showing whether `credentials.json` is present, and (b) a custom `Toplevel` dialog replacing the existing `messagebox.showerror` in `_send_report` when `credentials.json` is missing. `self.base_path` (already resolved by `paths.py::get_base_path`) is the directory passed to `open_folder`.

**Tech Stack:** Python stdlib only — `os.startfile` (Windows), `subprocess.run` with `["open", ...]` (macOS) and `["xdg-open", ...]` (Linux). Tkinter for the UI changes. `pytest` + `monkeypatch` for the unit tests, no external deps (matches the `.github/workflows/test.yml` strategy that only installs `pytest`).

**Spec reference:** `docs/superpowers/specs/2026-04-24-credentials-folder-button-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `src/platform_open.py` | Create | Cross-platform `open_folder(path)` dispatcher |
| `tests/test_platform_open.py` | Create | Unit tests for all four platform branches |
| `src/ui.py` | Modify | Settings dialog: new "Gmail-Zugangsdaten" section. `_send_report`: replace `showerror` with custom dialog. New `STATUS_OK` color constant. Import `open_folder`. |

No changes to `paths.py`, `mail.py`, `report.py`, `storage.py`, build, CI, or installer files.

---

## Chunk 1: `platform_open` module

### Task 1: Create `src/platform_open.py` with TDD

**Files:**
- Create: `src/platform_open.py`
- Test: `tests/test_platform_open.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_platform_open.py`:

```python
# tests/test_platform_open.py
import pytest
from unittest.mock import MagicMock
from src.platform_open import open_folder


def test_open_folder_windows(monkeypatch):
    monkeypatch.setattr("src.platform_open.platform.system", lambda: "Windows")
    mock_startfile = MagicMock()
    monkeypatch.setattr(
        "src.platform_open.os.startfile", mock_startfile, raising=False
    )
    open_folder(r"C:\Users\test\data")
    mock_startfile.assert_called_once_with(r"C:\Users\test\data")


def test_open_folder_macos(monkeypatch):
    monkeypatch.setattr("src.platform_open.platform.system", lambda: "Darwin")
    mock_run = MagicMock()
    monkeypatch.setattr("src.platform_open.subprocess.run", mock_run)
    open_folder("/Users/test/Library/Application Support/Zeiterfassung")
    mock_run.assert_called_once_with(
        ["open", "/Users/test/Library/Application Support/Zeiterfassung"],
        check=True,
    )


def test_open_folder_linux(monkeypatch):
    monkeypatch.setattr("src.platform_open.platform.system", lambda: "Linux")
    mock_run = MagicMock()
    monkeypatch.setattr("src.platform_open.subprocess.run", mock_run)
    open_folder("/home/test/.local/share/Zeiterfassung")
    mock_run.assert_called_once_with(
        ["xdg-open", "/home/test/.local/share/Zeiterfassung"],
        check=True,
    )


def test_open_folder_unsupported_platform_raises(monkeypatch):
    monkeypatch.setattr("src.platform_open.platform.system", lambda: "FreeBSD")
    with pytest.raises(RuntimeError, match="Unsupported platform"):
        open_folder("/tmp/whatever")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_platform_open.py -v`
Expected: All four tests fail with `ModuleNotFoundError: No module named 'src.platform_open'`.

- [ ] **Step 3: Create `src/platform_open.py` with minimal implementation**

Create the file with this content (note: `import os` and `import subprocess` as **module imports** — not symbol imports — so the tests can patch `src.platform_open.os.startfile` and `src.platform_open.subprocess.run`):

```python
# src/platform_open.py
import os
import platform
import subprocess


def open_folder(path: str) -> None:
    """Open the given directory in the OS file manager.

    Raises:
        RuntimeError: on unsupported platforms.
        OSError / subprocess.CalledProcessError: on OS-level failures
            (propagated to caller).
    """
    system = platform.system()
    if system == "Windows":
        os.startfile(path)
    elif system == "Darwin":
        subprocess.run(["open", path], check=True)
    elif system == "Linux":
        subprocess.run(["xdg-open", path], check=True)
    else:
        raise RuntimeError(f"Unsupported platform: {system}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_platform_open.py -v`
Expected: All four tests pass.

- [ ] **Step 5: Run the full test suite to confirm no regressions**

Run: `pytest -v`
Expected: All tests pass (existing + 4 new).

- [ ] **Step 6: Commit**

```bash
git add src/platform_open.py tests/test_platform_open.py
git commit -m "feat: add platform_open helper to open data folder cross-platform

New module src/platform_open.py with open_folder(path) that dispatches
over platform.system() to os.startfile (Windows), open (macOS), or
xdg-open (Linux). Errors are propagated; unsupported platforms raise
RuntimeError. Unit-tested via monkeypatch on all four branches."
```

---

## Chunk 2: Settings dialog integration

### Task 2: Add "Gmail-Zugangsdaten" section to settings dialog

**Files:**
- Modify: `src/ui.py` (constants block around line 31-50; `_open_settings` method around line 295-518)

This task has no automated tests — Tkinter UI tests are not established in this project (per spec, Section 4). Verification is manual.

- [ ] **Step 1: Add `STATUS_OK` color constant and import `open_folder`**

In `src/ui.py`, find the existing color constants block (around line 31-44) and add `STATUS_OK` next to `ACCENT`:

```python
ACCENT = "#e94560"
STATUS_OK = "#4ade80"
TEXT = "#e0e0e0"
```

In the imports block at the top of `src/ui.py` (around line 22), add the new module import after the `autostart` import:

```python
from src.autostart import enable_autostart, disable_autostart
from src.platform_open import open_folder
from src.version import VERSION
```

- [ ] **Step 2: Insert new section at top of `_open_settings`**

In `src/ui.py`, find `_open_settings` (starts at line 295). After `self._apply_combobox_style(dialog)` (around line 302) and **before** the existing `# Email` block (line 304), insert the new section. The first widget after `_apply_combobox_style` becomes the new header at `row=0`.

Insert this block immediately after `self._apply_combobox_style(dialog)`:

```python
        # Gmail-Zugangsdaten section
        tk.Label(
            dialog, text="— Gmail-Zugangsdaten —", font=FONT_BOLD,
            bg=BG, fg=TEXT_MUTED
        ).grid(row=0, column=0, columnspan=2, padx=10, pady=(8, 4))

        creds_path = os.path.join(self.base_path, "credentials.json")
        creds_present = os.path.exists(creds_path)

        tk.Label(
            dialog, text="Datenordner:", font=FONT, bg=BG, fg=TEXT
        ).grid(row=1, column=0, padx=10, pady=4, sticky="w")

        creds_row = tk.Frame(dialog, bg=BG)
        creds_row.grid(row=1, column=1, padx=10, pady=4, sticky="w")

        def open_data_folder():
            try:
                open_folder(self.base_path)
            except Exception as e:
                messagebox.showerror(
                    "Ordner konnte nicht geöffnet werden",
                    f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}",
                    parent=dialog,
                )

        tk.Button(
            creds_row, text="Ordner öffnen", command=open_data_folder,
            font=FONT, bg=CELL_BG, fg=TEXT,
            activebackground=ENTRY_BG, activeforeground=TEXT,
            relief=tk.FLAT, padx=12, pady=2, cursor="hand2"
        ).pack(side=tk.LEFT)

        if creds_present:
            status_text = "✓ credentials.json vorhanden"
            status_fg = STATUS_OK
        else:
            status_text = "✗ credentials.json fehlt"
            status_fg = ACCENT

        tk.Label(
            creds_row, text=status_text, font=FONT_SMALL,
            bg=BG, fg=status_fg
        ).pack(side=tk.LEFT, padx=(10, 0))
```

- [ ] **Step 3: Renumber all existing `.grid(row=N, ...)` calls in `_open_settings` by +2**

Every existing `.grid(row=N, ...)` call inside `_open_settings` (originally rows 0–14) shifts to rows 2–16. Apply these mappings:

| Old row | New row | What it is |
|---------|---------|------------|
| 0 | 2 | Absender label + Entry |
| 1 | 3 | Standard-Start label + Combobox |
| 2 | 4 | Standard-Ende label + Combobox |
| 3 | 5 | Standard-Pause label + Combobox |
| 4 | 6 | Empfänger label + Entry |
| 5 | 7 | Name label + Entry |
| 6 | 8 | Stundenlohn label + Entry + helper Label |
| 7 | 9 | Mail-Vorlage section header |
| 8 | 10 | Betreff label + Entry |
| 9 | 11 | Anrede label + Entry |
| 10 | 12 | Inhalt label + Text |
| 11 | 13 | Gruß label + Text |
| 12 | 14 | Platzhalter helper Label |
| 13 | 15 | Autostart Checkbutton |
| 14 | 16 | Save/Cancel `btn_frame` |

Use Edit tool with `replace_all=False` for each `.grid(row=N, ...)` call. Do them in **descending order** (row=14 → row=16 first, then row=13 → row=15, …, then row=0 → row=2) to avoid temporarily creating duplicate row numbers in the file.

**Important — disambiguation:** Several `.grid(row=N, column=0, padx=10, pady=8, sticky="w")` lines exist in *other* dialogs in `src/ui.py` (e.g. `_send_report` date-range dialog around line 869, `_open_dialog` around line 738) and look identical. Each `Edit` call's `old_string` must include the **preceding line** (the `tk.Label` / `tk.Entry` / `ttk.Combobox` widget that this `.grid` belongs to) to ensure Edit targets the call inside `_open_settings` and not a lookalike elsewhere. Example for the "Absender" entry:

```python
            relief=tk.FLAT, highlightbackground=TEXT_MUTED,
            highlightcolor=ACCENT, highlightthickness=1
        ).grid(row=0, column=1, padx=10, pady=8)
```

→ change `row=0` to `row=2`. The three preceding lines make the match unique to this widget.

- [ ] **Step 4: Verify the renumbering with grep**

Run:

```bash
grep -n "\.grid(row=" src/ui.py
```

Expected: inside `_open_settings` (lines around 295–520), the `.grid` calls now use rows 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16 (each row used once or twice for column 0/1 pairs). No duplicates of any row except the legitimate column 0/column 1 pairings.

- [ ] **Step 5: Manual UI smoke test**

Run the app from the repo:

```bash
python main.py
```

Click the gear icon (top right) to open Settings. Verify:
- New section "— Gmail-Zugangsdaten —" appears at the top.
- "Datenordner:" label with "Ordner öffnen" button next to it.
- Status label shows either "✓ credentials.json vorhanden" (green) or "✗ credentials.json fehlt" (red), matching the actual state of the repo root (which is `self.base_path` in script mode).
- Click "Ordner öffnen" — the OS file manager opens the repo root directory.
- The rest of the dialog (Absender down to Speichern/Abbrechen) renders correctly, no overlap, no missing fields.
- Save/Cancel buttons still work.

If `credentials.json` is missing in the repo root, you can create a temporary empty file to test the green status. **Safety: `credentials.json` is already in `.gitignore`** — but still delete it after the test:

```bash
touch credentials.json && python main.py   # status should now show green ✓
rm credentials.json
```

- [ ] **Step 6: Run the full test suite to confirm no regressions**

Run: `pytest -v`
Expected: All tests pass (no UI tests added, but existing tests must still pass).

- [ ] **Step 7: Commit**

```bash
git add src/ui.py
git commit -m "feat: settings dialog gains Gmail-Zugangsdaten section

New section at the top of the settings dialog with an 'Ordner öffnen'
button that opens the data directory in the OS file manager, plus a
status label showing whether credentials.json is already present
(green check or red cross). Uses the new platform_open helper. All
existing grid rows shifted down by 2."
```

---

## Chunk 3: Send-error custom dialog

### Task 3: Replace `showerror` with custom Toplevel in `_send_report`

**Files:**
- Modify: `src/ui.py` (`_send_report` method around line 809-830; new method `_show_missing_credentials_dialog`)

This task has no automated tests (same reason as Task 2). Verification is manual.

- [ ] **Step 1: Add `_show_missing_credentials_dialog` method on `App`**

In `src/ui.py`, add this method on the `App` class. A good location is **immediately before `_send_report`** (so the helper sits right next to its sole caller). Find `def _send_report(self):` and insert the new method just above it:

```python
    def _show_missing_credentials_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Keine Zugangsdaten")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.configure(bg=BG)

        tk.Label(
            dialog,
            text=(
                "credentials.json nicht gefunden.\n\n"
                "Bitte erstelle ein Google Cloud Projekt mit Gmail API "
                "und lade die OAuth2 Client-ID als credentials.json in "
                "den Datenordner."
            ),
            font=FONT, bg=BG, fg=TEXT,
            wraplength=380, justify="left",
        ).grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 12))

        def open_and_close():
            try:
                open_folder(self.base_path)
            except Exception as e:
                messagebox.showerror(
                    "Ordner konnte nicht geöffnet werden",
                    f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}",
                    parent=dialog,
                )
                return
            dialog.destroy()

        btn_frame = tk.Frame(dialog, bg=BG)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=(0, 16))

        tk.Button(
            btn_frame, text="Datenordner öffnen", command=open_and_close,
            font=FONT_BOLD, bg=ACCENT, fg="#ffffff",
            activebackground="#c73550", activeforeground="#ffffff",
            relief=tk.FLAT, padx=16, pady=4, cursor="hand2",
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            btn_frame, text="OK", command=dialog.destroy,
            font=FONT, bg=CELL_BG, fg=TEXT,
            activebackground=ENTRY_BG, activeforeground=TEXT,
            relief=tk.FLAT, padx=16, pady=4, cursor="hand2",
        ).pack(side=tk.LEFT, padx=5)
```

- [ ] **Step 2: Replace the existing `messagebox.showerror` block in `_send_report`**

In `src/ui.py`, find this block in `_send_report` (currently around lines 822-830):

```python
        if not os.path.exists(credentials_path):
            messagebox.showerror(
                "Keine Zugangsdaten",
                "credentials.json nicht gefunden.\n\n"
                "Bitte erstelle ein Google Cloud Projekt mit Gmail API "
                "und lade die OAuth2 Client-ID als credentials.json herunter.",
                parent=self.root
            )
            return
```

Replace with:

```python
        if not os.path.exists(credentials_path):
            self._show_missing_credentials_dialog()
            return
```

- [ ] **Step 3: Manual UI smoke test (file missing)**

Ensure no `credentials.json` exists in the repo root:

```bash
rm -f credentials.json
```

Run the app and click "Monat senden":

```bash
python main.py
```

(You also need a recipient set in settings, otherwise the recipient-warning fires first. Set any email, e.g. `test@example.com`, in the settings dialog and save.)

Verify:
- Custom dark-themed dialog "Keine Zugangsdaten" appears (not the native messagebox).
- Two buttons side by side: "Datenordner öffnen" (red/accent) on the left, "OK" (gray) on the right.
- Click "Datenordner öffnen" — the OS file manager opens at the repo root, dialog closes.
- Open the dialog again ("Monat senden") and click "OK" — dialog just closes, no folder opens.

- [ ] **Step 4: Manual UI smoke test (file present)**

Create a dummy credentials.json so the missing-credentials path is bypassed:

```bash
echo '{"installed":{}}' > credentials.json
```

Click "Monat senden" again — the missing-credentials dialog should NOT appear; instead you proceed to the date-range dialog (where sending will fail later because the dummy creds are invalid, but that's expected — we only care that `_show_missing_credentials_dialog` is gated correctly).

Clean up: `rm credentials.json`

- [ ] **Step 5: Run the full test suite to confirm no regressions**

Run: `pytest -v`
Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/ui.py
git commit -m "feat: custom dialog with 'Datenordner öffnen' on missing credentials

Replaces the plain messagebox.showerror in _send_report with a custom
dark-themed Toplevel that offers two actions: open the data folder
(via platform_open) so the user can drop credentials.json in, or
dismiss with OK. No auto-retry — user clicks 'Monat senden' again
once the file is in place."
```

---

## Verification checklist (post-implementation)

Before declaring done, confirm:

- [ ] `pytest -v` all green (existing tests + 4 new in `test_platform_open.py`)
- [ ] Settings dialog opens, new section visible at top, status label correct, button opens folder
- [ ] Clicking "Monat senden" without `credentials.json` shows the custom dialog (not the native messagebox)
- [ ] "Datenordner öffnen" in the custom dialog opens the folder and closes the dialog
- [ ] "OK" in the custom dialog just closes
- [ ] No regressions in the rest of the settings dialog (all fields render, save/cancel work)
- [ ] Three commits exist on the branch, one per chunk
