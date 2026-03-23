# Export & Autostart Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package the app as a standalone `.exe` via PyInstaller and add an autostart option that launches it minimized on Windows login.

**Architecture:** New `paths.py` module resolves the base directory for data files (frozen vs. script mode). New `autostart.py` handles platform-specific autostart via VBScript shortcut creation on Windows. `main.py` becomes the orchestrator that resolves all paths and handles `--minimized`. A `build.py` script wraps the PyInstaller command.

**Tech Stack:** Python 3, PyInstaller, tkinter, VBScript (for Windows shortcut creation)

---

## File Structure

| File | Change | Responsibility |
|------|--------|---------------|
| `src/paths.py` | **New** | Resolve base directory for data files |
| `src/autostart.py` | **New** | Platform-specific autostart enable/disable |
| `build.py` | **New** | PyInstaller build script |
| `tests/test_paths.py` | **New** | Tests for path resolution |
| `tests/test_autostart.py` | **New** | Tests for autostart logic |
| `src/main.py` | **Modify** | Use resolved paths, handle `--minimized`, determine `app_path` |
| `src/ui.py` | **Modify** | Accept `base_path`, pass resolved paths to mail, add autostart checkbox |
| `src/settings.py` | **Modify** | Add `"autostart"` to DEFAULTS |
| `.gitignore` | **Modify** | Add `dist/`, `build/`, `*.spec` |
| `requirements.txt` | **Modify** | Add `pyinstaller` |

---

## Chunk 1: Path Resolution

### Task 1: Path resolution module

**Files:**
- Create: `src/paths.py`
- Create: `tests/test_paths.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_paths.py
import os
import sys
import pytest
from src.paths import get_base_path


def test_returns_directory(tmp_path, monkeypatch):
    """get_base_path() returns a directory that exists."""
    result = get_base_path()
    assert os.path.isdir(result)


def test_script_mode_returns_project_root():
    """In script mode (not frozen), returns the project root directory."""
    # We are running as a script, so getattr(sys, 'frozen', False) is False.
    result = get_base_path()
    # The project root contains src/ and tests/
    assert os.path.isdir(os.path.join(result, "src"))
    assert os.path.isdir(os.path.join(result, "tests"))


def test_frozen_mode(tmp_path, monkeypatch):
    """In frozen mode, returns the directory containing sys.executable."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "Zeiterfassung.exe"))
    result = get_base_path()
    assert result == str(tmp_path)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_paths.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement path resolution**

```python
# src/paths.py
import os
import sys


def get_base_path():
    """Return the directory where data files should be stored.

    When running as a PyInstaller .exe (frozen): directory containing the .exe
    When running as a Python script: project root directory (parent of src/)
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_paths.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/paths.py tests/test_paths.py
git commit -m "feat: add path resolution module for frozen and script modes"
```

---

### Task 2: Wire path resolution into main.py and ui.py

**Files:**
- Modify: `src/main.py`
- Modify: `src/ui.py`

- [ ] **Step 1: Add `import os` and `import sys` to top of `src/ui.py`**

Add after `import datetime`:

```python
import os
import sys
```

- [ ] **Step 2: Update `main.py` to use resolved paths and handle `--minimized`**

Replace the entire content of `src/main.py`:

```python
# src/main.py
import os
import sys
import tkinter as tk
from src.paths import get_base_path
from src.storage import Storage
from src.settings import Settings
from src.ui import App


def main():
    base = get_base_path()
    storage = Storage(os.path.join(base, "zeiterfassung.json"))
    settings = Settings(os.path.join(base, "settings.json"))

    root = tk.Tk()
    app = App(root, storage, settings, base_path=base)

    if "--minimized" in sys.argv:
        root.iconify()

    root.mainloop()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Update `App.__init__` to accept and store `base_path`**

In `src/ui.py`, change the `__init__` signature and store `base_path`:

```python
class App:
    def __init__(self, root, storage, settings, base_path="."):
        self.root = root
        self.storage = storage
        self.settings = settings
        self.base_path = base_path
        # ... rest unchanged
```

- [ ] **Step 4: Update `_send_report` to use resolved paths**

In `src/ui.py`, replace the entire `_send_report` method. Remove the local `import os` (now at module level) and use `self.base_path` for credential paths:

Replace:
```python
    def _send_report(self):
        import os

        recipient = self.settings.get("recipient")
        if not recipient:
            messagebox.showwarning(
                "Kein Empfänger",
                "Bitte zuerst einen Empfänger in den Einstellungen angeben.",
                parent=self.root
            )
            return

        if not os.path.exists("credentials.json"):
```

With:
```python
    def _send_report(self):
        recipient = self.settings.get("recipient")
        if not recipient:
            messagebox.showwarning(
                "Kein Empfänger",
                "Bitte zuerst einen Empfänger in den Einstellungen angeben.",
                parent=self.root
            )
            return

        credentials_path = os.path.join(self.base_path, "credentials.json")
        token_path = os.path.join(self.base_path, "token.json")

        if not os.path.exists(credentials_path):
```

And replace:
```python
        try:
            service = get_gmail_service()
```

With:
```python
        try:
            service = get_gmail_service(credentials_path, token_path)
```

- [ ] **Step 5: Run all tests to verify nothing broke**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/main.py src/ui.py
git commit -m "feat: wire path resolution into main and ui for portable data paths"
```

---

## Chunk 2: Autostart

### Task 3: Add autostart to settings

**Files:**
- Modify: `src/settings.py`
- Modify: `tests/test_settings.py`

- [ ] **Step 1: Add failing test**

Append to `tests/test_settings.py`:

```python
def test_autostart_default(tmp_settings):
    assert tmp_settings.get("autostart") == False
```

- [ ] **Step 2: Run test — should FAIL**

Run: `python -m pytest tests/test_settings.py::test_autostart_default -v`
Expected: FAIL — returns `None` instead of `False`

- [ ] **Step 3: Add autostart to DEFAULTS in `src/settings.py`**

Change `DEFAULTS` dict:

```python
DEFAULTS = {
    "email": "",
    "default_pause": 30,
    "recipient": "",
    "autostart": False,
}
```

- [ ] **Step 4: Run all settings tests**

Run: `python -m pytest tests/test_settings.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/settings.py tests/test_settings.py
git commit -m "feat: add autostart field to settings defaults"
```

---

### Task 4: Autostart module

**Files:**
- Create: `src/autostart.py`
- Create: `tests/test_autostart.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_autostart.py
import os
import sys
import platform
import pytest
from unittest.mock import patch, MagicMock
from src.autostart import enable_autostart, disable_autostart, _get_startup_folder, _get_shortcut_path


@pytest.fixture
def fake_startup(tmp_path, monkeypatch):
    """Patch _get_startup_folder to return a temp directory."""
    monkeypatch.setattr("src.autostart._get_startup_folder", lambda: str(tmp_path))
    return tmp_path


@pytest.mark.skipif(platform.system() != "Windows", reason="Windows only")
class TestWindowsAutostart:

    def test_get_startup_folder_returns_existing_dir(self):
        folder = _get_startup_folder()
        assert os.path.isdir(folder)

    def test_get_shortcut_path(self, fake_startup):
        path = _get_shortcut_path()
        assert path == str(fake_startup / "Zeiterfassung.lnk")

    def test_enable_creates_shortcut(self, fake_startup):
        with patch("src.autostart.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            enable_autostart(r"C:\app\Zeiterfassung.exe", "--minimized")
            mock_run.assert_called_once()
            # Verify the VBS script was passed to cscript
            args = mock_run.call_args[0][0]
            assert args[0] == "cscript"
            assert args[1] == "//nologo"
            assert args[2].endswith(".vbs")

    def test_enable_cleans_up_vbs(self, fake_startup):
        with patch("src.autostart.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            enable_autostart(r"C:\app\Zeiterfassung.exe", "--minimized")
            # The .vbs temp file should be deleted after use
            vbs_path = mock_run.call_args[0][0][2]
            assert not os.path.exists(vbs_path)

    def test_disable_removes_shortcut(self, fake_startup):
        # Create a fake shortcut file
        shortcut = fake_startup / "Zeiterfassung.lnk"
        shortcut.write_text("fake")
        assert shortcut.exists()
        disable_autostart()
        assert not shortcut.exists()

    def test_disable_no_shortcut_no_error(self, fake_startup):
        # Should not raise even if shortcut doesn't exist
        disable_autostart()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_autostart.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement autostart module**

```python
# src/autostart.py
import os
import sys
import platform
import subprocess
import tempfile


SHORTCUT_NAME = "Zeiterfassung.lnk"


def _get_startup_folder():
    """Return the Windows startup folder path."""
    return os.path.join(
        os.environ["APPDATA"],
        "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
    )


def _get_shortcut_path():
    """Return the full path to the autostart shortcut."""
    return os.path.join(_get_startup_folder(), SHORTCUT_NAME)


def enable_autostart(target, arguments=""):
    """Create a Windows startup shortcut via VBScript.

    target: path to .exe or Python interpreter
    arguments: command-line args (e.g. "--minimized" or "path/to/main.py --minimized")
    """
    if platform.system() != "Windows":
        return

    shortcut_path = _get_shortcut_path()
    working_dir = os.path.dirname(target)

    vbs_content = f'''Set ws = CreateObject("WScript.Shell")
Set sc = ws.CreateShortcut("{shortcut_path}")
sc.TargetPath = "{target}"
sc.Arguments = "{arguments}"
sc.WorkingDirectory = "{working_dir}"
sc.Save
'''

    fd, vbs_path = tempfile.mkstemp(suffix=".vbs")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(vbs_content)
        subprocess.run(["cscript", "//nologo", vbs_path], check=True)
    finally:
        if os.path.exists(vbs_path):
            os.remove(vbs_path)


def disable_autostart():
    """Remove the Windows startup shortcut."""
    if platform.system() != "Windows":
        return

    shortcut_path = _get_shortcut_path()
    if os.path.exists(shortcut_path):
        os.remove(shortcut_path)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_autostart.py -v`
Expected: All 6 tests PASS (or skipped on non-Windows)

- [ ] **Step 5: Commit**

```bash
git add src/autostart.py tests/test_autostart.py
git commit -m "feat: add Windows autostart module with VBScript shortcut creation"
```

---

## Chunk 3: UI Integration & Build

### Task 5: Add autostart checkbox to settings dialog

**Files:**
- Modify: `src/ui.py`

- [ ] **Step 1: Add import for autostart at top of `src/ui.py`**

Add after the existing imports:

```python
from src.autostart import enable_autostart, disable_autostart
```

- [ ] **Step 2: Add autostart checkbox to `_open_settings`**

In `_open_settings`, after the recipient entry (after line 188), add:

```python
        # Autostart
        autostart_var = tk.BooleanVar(value=self.settings.get("autostart"))
        tk.Checkbutton(
            dialog, text="Autostart (minimiert bei Anmeldung)",
            variable=autostart_var, font=FONT,
            bg=BG, fg=TEXT, selectcolor=CELL_BG,
            activebackground=BG, activeforeground=TEXT,
            cursor="hand2"
        ).grid(row=3, column=0, columnspan=2, padx=10, pady=8, sticky="w")
```

Move the button frame from `row=3` to `row=4`:

```python
        btn_frame = tk.Frame(dialog, bg=BG)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=12)
```

- [ ] **Step 3: Update `save_settings` to handle autostart**

Replace the `save_settings` function inside `_open_settings`. Important: read `old_autostart` and attempt autostart change BEFORE saving other settings, so nothing is persisted if autostart fails:

```python
        def save_settings():
            new_autostart = autostart_var.get()
            old_autostart = self.settings.get("autostart")

            if new_autostart != old_autostart:
                try:
                    if new_autostart:
                        if getattr(sys, "frozen", False):
                            target = sys.executable
                            arguments = "--minimized"
                        else:
                            target = sys.executable
                            main_py = os.path.join(self.base_path, "src", "main.py")
                            arguments = f"{main_py} --minimized"
                        enable_autostart(target, arguments)
                    else:
                        disable_autostart()
                    self.settings.set("autostart", new_autostart)
                except Exception as e:
                    messagebox.showerror(
                        "Autostart-Fehler",
                        f"Autostart konnte nicht geändert werden:\n{e}",
                        parent=dialog
                    )
                    return

            self.settings.set("email", email_var.get())
            self.settings.set("default_pause", int(pause_var.get()))
            self.settings.set("recipient", recipient_var.get())
            dialog.destroy()
```

- [ ] **Step 5: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/ui.py
git commit -m "feat: add autostart checkbox to settings dialog"
```

---

### Task 6: Build script and project config

**Files:**
- Create: `build.py`
- Modify: `.gitignore`
- Modify: `requirements.txt`

- [ ] **Step 1: Create build script**

```python
# build.py
import subprocess
import sys

def build():
    cmd = [
        sys.executable, "-m", "pyinstaller",
        "--onefile",
        "--noconsole",
        "--name", "Zeiterfassung",
        "src/main.py",
    ]
    subprocess.run(cmd, check=True)

if __name__ == "__main__":
    build()
```

- [ ] **Step 2: Update `.gitignore`**

Add to `.gitignore`:

```
dist/
build/
*.spec
```

- [ ] **Step 3: Update `requirements.txt`**

Add `pyinstaller` to `requirements.txt`:

```
google-auth-oauthlib>=1.0.0
google-api-python-client>=2.0.0
pyinstaller>=6.0.0
```

- [ ] **Step 4: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add build.py .gitignore requirements.txt
git commit -m "feat: add PyInstaller build script and update project config"
```

---

## Chunk 4: Final Verification

### Task 7: Build and manual test

- [ ] **Step 1: Install PyInstaller**

Run: `pip install pyinstaller`

- [ ] **Step 2: Build the executable**

Run: `python build.py`
Expected: `dist/Zeiterfassung.exe` is created

- [ ] **Step 3: Manual test — run the .exe**

Run: `dist/Zeiterfassung.exe`
Verify:
- App opens normally
- Can create/edit time entries (data saved next to .exe)
- Settings dialog works
- "Monat senden" works (if credentials.json is in the dist/ folder)

- [ ] **Step 4: Manual test — minimized mode**

Run: `dist/Zeiterfassung.exe --minimized`
Verify:
- App starts minimized in the taskbar
- Clicking the taskbar icon restores the window

- [ ] **Step 5: Manual test — autostart toggle**

1. Open Settings → check "Autostart" → Save
2. Verify: `Zeiterfassung.lnk` exists in `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\`
3. Open Settings → uncheck "Autostart" → Save
4. Verify: `Zeiterfassung.lnk` is removed

- [ ] **Step 6: Run all tests one final time**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS
