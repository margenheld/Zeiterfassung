# Export & Autostart — Design Spec

## Overview

Package the Zeiterfassung app as a standalone executable and add an autostart option so it launches minimized on login. Cross-platform compatible (Windows now, Linux later).

## Export als Anwendung

- **Tool:** PyInstaller
- **Build command:** `pyinstaller --onefile --noconsole --name Zeiterfassung src/main.py`
- **Output:** Single `Zeiterfassung.exe` in `dist/` folder
- **Data files:** All JSON files (`zeiterfassung.json`, `settings.json`, `credentials.json`, `token.json`) live in the same directory as the executable
- **Build script:** `build.py` at project root — uses `subprocess.run` to call PyInstaller CLI
- **`.gitignore`:** Add `dist/`, `build/`, `*.spec`

## Pfad-Auflösung (Path Resolution)

### Problem

The app currently uses relative paths like `Storage("zeiterfassung.json")`. This breaks when the app is launched from a different working directory (e.g., via autostart shortcut). Additionally, `mail.py` has hardcoded default paths for `credentials.json` and `token.json`, and `ui.py` checks `os.path.exists("credentials.json")` with a bare filename.

### Solution

New module `src/paths.py`:

```python
def get_base_path():
    """Return the directory where data files should be stored.

    When running as a PyInstaller .exe: directory containing the .exe
    When running as a Python script: project root directory
    """
```

- Uses `sys.executable` for frozen apps, `__file__`-based resolution for scripts
- `main.py` resolves all file paths and passes them through:
  - `Storage(base / "zeiterfassung.json")`
  - `Settings(base / "settings.json")`
  - `App` receives `base_path` so it can pass resolved credential paths to `get_gmail_service()` and for the `os.path.exists()` check in `_send_report`
- `get_gmail_service()` already accepts `credentials_path` and `token_path` parameters — `_send_report` passes the resolved paths
- All other modules remain unchanged — they receive full paths from callers

## Minimiert starten

- `main.py` checks for `--minimized` in `sys.argv`
- If present: calls `root.iconify()` after UI is built
- Window appears minimized in the taskbar — no system tray needed
- User clicks the taskbar icon to open it

## Autostart-Setting

### Settings Extension

```json
{"email": "", "default_pause": 30, "recipient": "", "autostart": false}
```

### UI

- New checkbox **"Autostart"** in the settings dialog, below "Empfänger"
- Autostart enable/disable is called only when the value actually changes (compare old vs. new before acting)

### Platform Logic — `src/autostart.py`

New module with two functions:

```python
def enable_autostart(target, arguments=""):
    """Create platform-specific autostart entry.

    target: path to .exe (frozen) or Python interpreter (script mode)
    arguments: command-line args, e.g. "--minimized" or "path/to/src/main.py --minimized"
    """

def disable_autostart():
    """Remove platform-specific autostart entry."""
```

**Calling convention in `main.py`:**
- Frozen (`.exe`): `enable_autostart(sys.executable, "--minimized")`
- Script mode: `enable_autostart(sys.executable, f"{path_to_main_py} --minimized")`
- `main.py` determines both values and passes them to `App`, which passes them to `enable_autostart()`

**Windows shortcut creation — VBScript approach (no pywin32 dependency):**
- Generates a small `.vbs` script that uses `WScript.Shell.CreateShortcut()` to create the `.lnk` file
- Sets `TargetPath` to `target` and `Arguments` to `arguments`
- `.vbs` is written to `tempfile.mkstemp()`, run via `subprocess.run(["cscript", "//nologo", vbs_path])`, then deleted
- Shortcut placed in `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Zeiterfassung.lnk`
- If a shortcut already exists, it is silently overwritten (desired behavior for updates)
- This avoids the `pywin32` dependency and its known issues with PyInstaller bundling

**Linux (future):**
- Creates a `.desktop` file in `~/.config/autostart/`
- `Exec=` points to the binary or `python3 path/to/src/main.py --minimized`
- Standard freedesktop autostart spec

### Error Handling

- If `enable_autostart()` or `disable_autostart()` fails (permission denied, missing folder), show a `messagebox.showerror` in the settings dialog
- The setting value is only persisted if the autostart action succeeds
- If the action fails, the checkbox reverts to its previous state

## New Files

| File | Responsibility |
|------|---------------|
| `src/paths.py` | Base path resolution (frozen vs. script) |
| `src/autostart.py` | Platform-specific autostart enable/disable |
| `build.py` | PyInstaller build script |

## Files to Modify

| File | Change |
|------|--------|
| `src/main.py` | Use `get_base_path()` for file paths, handle `--minimized`, determine `app_path` |
| `src/settings.py` | Add `"autostart"` to DEFAULTS |
| `src/ui.py` | Add autostart checkbox to settings dialog, pass resolved paths to `get_gmail_service()`, use resolved path for `os.path.exists()` credentials check in `_send_report` |
| `.gitignore` | Add `dist/`, `build/`, `*.spec` |
| `requirements.txt` | Add `pyinstaller` |

## Out of Scope

- System tray icon
- Custom app icon
- Windows installer (.msi)
- Auto-update mechanism
- Linux packaging (.deb, .rpm, AppImage)
