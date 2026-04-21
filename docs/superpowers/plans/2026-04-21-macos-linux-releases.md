# macOS & Linux Releases Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing Windows-only release pipeline to also produce unsigned installable artefacts (DMG, AppImage) for macOS ARM + Intel and Linux x86_64, keeping the Windows build behaviourally identical.

**Architecture:** All platform-specific code is gated by `platform.system()`. Core modules (`paths.py`, `autostart.py`, `build.py`) become dispatchers with Windows/macOS/Linux branches. Data directory on macOS is `~/Library/Application Support/Zeiterfassung`, on Linux `$XDG_DATA_HOME/Zeiterfassung` (fallback `~/.local/share/Zeiterfassung`), Windows unchanged. Autostart via LaunchAgent plist (macOS) and `~/.config/autostart/*.desktop` (Linux). CI release workflow splits into `pre-check` → 4 parallel builds → `publish`, tag pushed only after all builds pass.

**Tech Stack:** PyInstaller (all platforms), Inno Setup (Windows, unchanged), create-dmg (macOS, `brew install`), appimagetool + libfuse2 (Linux), `plistlib` stdlib, GitHub Actions matrix with `actions/upload-artifact@v4` + `actions/download-artifact@v4`.

**Spec reference:** `docs/superpowers/specs/2026-04-21-macos-linux-releases-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `src/paths.py` | Modify | Platform-aware data-directory resolution |
| `src/autostart.py` | Modify | Dispatcher + macOS LaunchAgent + Linux `.desktop` helpers |
| `src/ui.py` | Modify | Guard `iconbitmap` on non-Windows; platform-aware autostart target in `save_settings` |
| `src/mail.py` | Modify | Extend `FileNotFoundError` to surface resolved `credentials_path` |
| `build.py` | Modify | Dispatcher: `build_windows` (unchanged), `build_macos`, `build_linux` |
| `.github/workflows/release.yml` | Rewrite | Split into `pre-check` → 4 parallel build jobs → `publish` |
| `assets/margenheld-icon.icns` | Create (binary) | macOS `.app` bundle icon |
| `tests/test_paths.py` | Modify | Parametrised tests across all 3 platforms |
| `tests/test_autostart.py` | Modify | Add macOS + Linux unit tests |
| `tests/test_ui_autostart_target.py` | Create | Tests for AppImage env-var target resolution |
| `README.md` | Modify | Tri-platform install + Gatekeeper hint |
| `CLAUDE.md` | Modify | Per-platform build-tool prereqs + partial-failure recovery |

---

## Chunk 1: Path resolution foundation

### Task 1: Platform-aware `get_base_path`

**Files:**
- Modify: `src/paths.py`
- Test: `tests/test_paths.py`

- [ ] **Step 1: Replace the existing `test_frozen_mode` with parametrised tests and add the platform-specific cases**

Replace `tests/test_paths.py` contents with:

```python
# tests/test_paths.py
import os
import sys
import pytest
from src.paths import get_base_path


def test_returns_directory():
    result = get_base_path()
    assert os.path.isdir(result)


@pytest.mark.parametrize("system", ["Windows", "Darwin", "Linux"])
def test_repo_mode_returns_project_root(system, monkeypatch):
    monkeypatch.setattr("src.paths.platform.system", lambda: system)
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    result = get_base_path()
    assert os.path.isdir(os.path.join(result, "src"))
    assert os.path.isdir(os.path.join(result, "tests"))


def test_frozen_windows_returns_exe_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("src.paths.platform.system", lambda: "Windows")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "Zeiterfassung.exe"))
    assert get_base_path() == str(tmp_path)


def test_frozen_macos_returns_library_support_and_creates_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("src.paths.platform.system", lambda: "Darwin")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    result = get_base_path()
    expected = str(tmp_path / "Library" / "Application Support" / "Zeiterfassung")
    assert result == expected
    assert os.path.isdir(result)


def test_frozen_linux_respects_xdg_data_home(tmp_path, monkeypatch):
    monkeypatch.setattr("src.paths.platform.system", lambda: "Linux")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    xdg = tmp_path / "xdg"
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg))
    result = get_base_path()
    assert result == str(xdg / "Zeiterfassung")
    assert os.path.isdir(result)


def test_frozen_linux_falls_back_to_local_share(tmp_path, monkeypatch):
    monkeypatch.setattr("src.paths.platform.system", lambda: "Linux")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    result = get_base_path()
    assert result == str(tmp_path / ".local" / "share" / "Zeiterfassung")
    assert os.path.isdir(result)
```

- [ ] **Step 2: Run tests, confirm the new cases fail**

Run: `pytest tests/test_paths.py -v`
Expected: the four new frozen-{macos,linux-xdg,linux-fallback} tests fail (result differs from expected), parametrised repo-mode tests pass, windows test passes.

- [ ] **Step 3: Update `src/paths.py` to the new dispatcher**

Replace file contents:

```python
# src/paths.py
import os
import platform
import sys


def get_base_path():
    """Return the directory where data files should be stored.

    Script mode: repo root (parent of src/).
    Frozen Windows: directory containing the .exe (unchanged for compatibility).
    Frozen macOS: ~/Library/Application Support/Zeiterfassung.
    Frozen Linux/other: $XDG_DATA_HOME/Zeiterfassung or ~/.local/share/Zeiterfassung.

    Ensures the directory exists on macOS/Linux.
    """
    if not getattr(sys, "frozen", False):
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    system = platform.system()
    if system == "Windows":
        return os.path.dirname(sys.executable)
    if system == "Darwin":
        base = os.path.expanduser("~/Library/Application Support/Zeiterfassung")
    else:
        xdg = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
        base = os.path.join(xdg, "Zeiterfassung")

    os.makedirs(base, exist_ok=True)
    return base
```

- [ ] **Step 4: Run tests, confirm all pass**

Run: `pytest tests/test_paths.py -v`
Expected: all 7 tests pass.

- [ ] **Step 5: Run the full test suite to confirm no regressions**

Run: `pytest`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add src/paths.py tests/test_paths.py
git commit -m "feat(paths): platform-aware data directory for macOS and Linux"
```

---

### Task 2: Extend `credentials.json` error message

**Files:**
- Modify: `src/mail.py:88-93`

- [ ] **Step 1: Update the FileNotFoundError to include the resolved path**

Edit `src/mail.py`, replace the block at lines 88–93:

```python
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(
                f"credentials.json nicht gefunden unter:\n{credentials_path}\n\n"
                "Bitte erstelle ein Google Cloud Projekt mit Gmail API "
                "und lade die OAuth2 Client-ID dort ab."
            )
```

- [ ] **Step 2: Run tests, confirm nothing broke**

Run: `pytest`
Expected: all green (existing mail tests do not assert on this message).

- [ ] **Step 3: Commit**

```bash
git add src/mail.py
git commit -m "feat(mail): surface resolved credentials path in error message"
```

---

## Chunk 2: Icon and UI guards

### Task 3: Guard `iconbitmap` on non-Windows

**Files:**
- Modify: `src/ui.py:73-81`

- [ ] **Step 1: Add `import platform` at the top of `src/ui.py`**

Add next to the other stdlib imports, directly after the existing `import os` line:

```python
import platform
```

- [ ] **Step 2: Guard the `iconbitmap` call**

Replace lines 76–77 (`if os.path.exists(ico_path): self.root.iconbitmap(ico_path)`) with:

```python
        if platform.system() == "Windows" and os.path.exists(ico_path):
            self.root.iconbitmap(ico_path)
```

- [ ] **Step 3: Sanity check the file still parses**

Run: `python -c "import ast; ast.parse(open('src/ui.py', encoding='utf-8').read())"`
Expected: no output (exit 0).

- [ ] **Step 4: Run full test suite**

Run: `pytest`
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add src/ui.py
git commit -m "fix(ui): guard iconbitmap behind Windows check"
```

---

### Task 4: Generate and commit `.icns`

**Files:**
- Create: `assets/margenheld-icon.icns` (binary)

- [ ] **Step 1: Generate the `.icns` from the existing PNG**

On a Mac, run (from repo root):

```bash
mkdir -p /tmp/Zeiterfassung.iconset
sips -z 16 16    assets/margenheld-icon.png --out /tmp/Zeiterfassung.iconset/icon_16x16.png
sips -z 32 32    assets/margenheld-icon.png --out /tmp/Zeiterfassung.iconset/icon_16x16@2x.png
sips -z 32 32    assets/margenheld-icon.png --out /tmp/Zeiterfassung.iconset/icon_32x32.png
sips -z 64 64    assets/margenheld-icon.png --out /tmp/Zeiterfassung.iconset/icon_32x32@2x.png
sips -z 128 128  assets/margenheld-icon.png --out /tmp/Zeiterfassung.iconset/icon_128x128.png
sips -z 256 256  assets/margenheld-icon.png --out /tmp/Zeiterfassung.iconset/icon_128x128@2x.png
sips -z 256 256  assets/margenheld-icon.png --out /tmp/Zeiterfassung.iconset/icon_256x256.png
sips -z 512 512  assets/margenheld-icon.png --out /tmp/Zeiterfassung.iconset/icon_256x256@2x.png
sips -z 512 512  assets/margenheld-icon.png --out /tmp/Zeiterfassung.iconset/icon_512x512.png
sips -z 1024 1024 assets/margenheld-icon.png --out /tmp/Zeiterfassung.iconset/icon_512x512@2x.png
iconutil -c icns -o assets/margenheld-icon.icns /tmp/Zeiterfassung.iconset
rm -rf /tmp/Zeiterfassung.iconset
```

**If no Mac available**, use Pillow:

```bash
pip install Pillow
python -c "
from PIL import Image
img = Image.open('assets/margenheld-icon.png')
img.save('assets/margenheld-icon.icns', format='ICNS', sizes=[(16,16),(32,32),(64,64),(128,128),(256,256),(512,512),(1024,1024)])
"
```

- [ ] **Step 2: Verify the file exists and is non-empty**

Run: `ls -la assets/margenheld-icon.icns`
Expected: file size > 10 KB.

- [ ] **Step 3: Commit the binary**

```bash
git add assets/margenheld-icon.icns
git commit -m "chore(assets): add macOS .icns icon"
```

---

## Chunk 3: Autostart macOS + Linux

### Task 5: macOS LaunchAgent autostart

**Files:**
- Modify: `src/autostart.py`
- Test: `tests/test_autostart.py`

- [ ] **Step 1: Write the failing macOS tests**

Append to `tests/test_autostart.py` (before the module ends, add these new imports at the top of the file first):

```python
import plistlib
from src.autostart import (
    _macos_plist_path,
    _linux_desktop_path,
)
```

Then add:

```python
class TestMacOSAutostart:
    @pytest.fixture
    def fake_home(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setattr("src.autostart.platform.system", lambda: "Darwin")
        agents = tmp_path / "Library" / "LaunchAgents"
        agents.mkdir(parents=True)
        return tmp_path

    def test_plist_path(self, fake_home):
        assert _macos_plist_path() == str(
            fake_home / "Library" / "LaunchAgents" / "com.margenheld.zeiterfassung.plist"
        )

    def test_enable_writes_plist_with_correct_content(self, fake_home):
        with patch("src.autostart.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            enable_autostart("/Applications/Zeiterfassung.app/Contents/MacOS/Zeiterfassung", "--minimized")
        plist_path = _macos_plist_path()
        assert os.path.exists(plist_path)
        with open(plist_path, "rb") as f:
            data = plistlib.load(f)
        assert data["Label"] == "com.margenheld.zeiterfassung"
        assert data["ProgramArguments"] == [
            "/Applications/Zeiterfassung.app/Contents/MacOS/Zeiterfassung",
            "--minimized",
        ]
        assert data["RunAtLoad"] is True
        assert data["ProcessType"] == "Interactive"

    def test_enable_invokes_launchctl_load(self, fake_home):
        with patch("src.autostart.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            enable_autostart("/Applications/Zeiterfassung.app/Contents/MacOS/Zeiterfassung", "--minimized")
        call = mock_run.call_args_list[-1]
        args = call[0][0]
        assert args[:3] == ["launchctl", "load", "-w"]
        assert args[3] == _macos_plist_path()

    def test_disable_unloads_and_removes_plist(self, fake_home):
        plist_path = _macos_plist_path()
        with open(plist_path, "w") as f:
            f.write("<plist/>")
        with patch("src.autostart.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            disable_autostart()
        assert mock_run.call_args[0][0][:2] == ["launchctl", "unload"]
        assert not os.path.exists(plist_path)

    def test_disable_tolerates_missing_plist(self, fake_home):
        with patch("src.autostart.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            disable_autostart()
```

- [ ] **Step 2: Run the tests to confirm they fail**

Run: `pytest tests/test_autostart.py::TestMacOSAutostart -v`
Expected: ImportError for `_macos_plist_path` — exactly the contract we are about to add.

- [ ] **Step 3: Implement the macOS branch in `src/autostart.py`**

Rewrite `src/autostart.py`:

```python
# src/autostart.py
import os
import platform
import plistlib
import subprocess
import tempfile


SHORTCUT_NAME = "Zeiterfassung.lnk"
MACOS_LABEL = "com.margenheld.zeiterfassung"


def _get_startup_folder():
    return os.path.join(
        os.environ["APPDATA"],
        "Microsoft", "Windows", "Start Menu", "Programs", "Startup",
    )


def _get_shortcut_path():
    return os.path.join(_get_startup_folder(), SHORTCUT_NAME)


def _macos_plist_path():
    return os.path.expanduser(f"~/Library/LaunchAgents/{MACOS_LABEL}.plist")


def _linux_desktop_path():
    return os.path.expanduser("~/.config/autostart/Zeiterfassung.desktop")


def enable_autostart(target, arguments=""):
    """Enable autostart on the current platform.

    target: path to executable (Windows .exe, macOS .app binary, Linux AppImage/binary)
    arguments: whitespace-separated CLI args
    """
    system = platform.system()
    if system == "Windows":
        _enable_windows(target, arguments)
    elif system == "Darwin":
        _enable_macos(target, arguments)
    elif system == "Linux":
        _enable_linux(target, arguments)


def disable_autostart():
    system = platform.system()
    if system == "Windows":
        _disable_windows()
    elif system == "Darwin":
        _disable_macos()
    elif system == "Linux":
        _disable_linux()


def _enable_windows(target, arguments):
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


def _disable_windows():
    shortcut_path = _get_shortcut_path()
    if os.path.exists(shortcut_path):
        os.remove(shortcut_path)


def _enable_macos(target, arguments):
    plist_path = _macos_plist_path()
    os.makedirs(os.path.dirname(plist_path), exist_ok=True)

    program_args = [target]
    if arguments:
        program_args.extend(arguments.split())

    plist = {
        "Label": MACOS_LABEL,
        "ProgramArguments": program_args,
        "RunAtLoad": True,
        "ProcessType": "Interactive",
    }
    with open(plist_path, "wb") as f:
        plistlib.dump(plist, f)

    subprocess.run(["launchctl", "load", "-w", plist_path], check=True)


def _disable_macos():
    plist_path = _macos_plist_path()
    if os.path.exists(plist_path):
        try:
            subprocess.run(["launchctl", "unload", plist_path], check=False)
        except FileNotFoundError:
            pass
        try:
            os.remove(plist_path)
        except FileNotFoundError:
            pass


def _enable_linux(target, arguments):
    desktop_path = _linux_desktop_path()
    os.makedirs(os.path.dirname(desktop_path), exist_ok=True)

    exec_line = target if not arguments else f"{target} {arguments}"
    content = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Zeiterfassung\n"
        f"Exec={exec_line}\n"
        "Hidden=false\n"
        "X-GNOME-Autostart-enabled=true\n"
    )
    with open(desktop_path, "w", encoding="utf-8") as f:
        f.write(content)


def _disable_linux():
    desktop_path = _linux_desktop_path()
    if os.path.exists(desktop_path):
        try:
            os.remove(desktop_path)
        except FileNotFoundError:
            pass
```

- [ ] **Step 4: Run the macOS tests, confirm they pass**

Run: `pytest tests/test_autostart.py::TestMacOSAutostart -v`
Expected: all 5 pass.

- [ ] **Step 5: Run the full autostart test module and confirm Windows tests still work (skipped on Linux CI)**

Run: `pytest tests/test_autostart.py -v`
Expected: Windows tests skipped on non-Windows; macOS tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/autostart.py tests/test_autostart.py
git commit -m "feat(autostart): macOS LaunchAgent support"
```

---

### Task 6: Linux `.desktop` autostart

**Files:**
- Test: `tests/test_autostart.py` (append)

(Implementation already in place from Task 5; only tests remain.)

- [ ] **Step 1: Append Linux tests to `tests/test_autostart.py`**

```python
class TestLinuxAutostart:
    @pytest.fixture
    def fake_home(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setattr("src.autostart.platform.system", lambda: "Linux")
        return tmp_path

    def test_desktop_path(self, fake_home):
        assert _linux_desktop_path() == str(
            fake_home / ".config" / "autostart" / "Zeiterfassung.desktop"
        )

    def test_enable_writes_desktop_file(self, fake_home):
        enable_autostart("/opt/Zeiterfassung.AppImage", "--minimized")
        path = _linux_desktop_path()
        assert os.path.exists(path)
        content = open(path, encoding="utf-8").read()
        assert "Exec=/opt/Zeiterfassung.AppImage --minimized" in content
        assert "Type=Application" in content
        assert "Name=Zeiterfassung" in content

    def test_enable_without_arguments_has_no_trailing_space(self, fake_home):
        enable_autostart("/opt/Zeiterfassung.AppImage", "")
        content = open(_linux_desktop_path(), encoding="utf-8").read()
        assert "Exec=/opt/Zeiterfassung.AppImage\n" in content

    def test_disable_removes_desktop_file(self, fake_home):
        path = _linux_desktop_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write("fake")
        disable_autostart()
        assert not os.path.exists(path)

    def test_disable_tolerates_missing_file(self, fake_home):
        disable_autostart()
```

- [ ] **Step 2: Run and confirm all Linux tests pass**

Run: `pytest tests/test_autostart.py::TestLinuxAutostart -v`
Expected: all 5 pass.

- [ ] **Step 3: Full test suite green**

Run: `pytest`
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add tests/test_autostart.py
git commit -m "test(autostart): Linux .desktop autostart coverage"
```

---

### Task 7: Platform-aware autostart target in `ui.py`

**Files:**
- Modify: `src/ui.py:451-461`
- Create: `tests/test_ui_autostart_target.py`

- [ ] **Step 1: Extract the target-resolution logic into a module-level helper**

In `src/ui.py`, add this function just above the `class App:` line (so tests can import it without creating a Tk root):

```python
def resolve_autostart_target(base_path):
    """Return (target, arguments) for the current runtime/platform.

    Frozen Windows/macOS: the executable itself.
    Frozen Linux: $APPIMAGE if set (persistent path), otherwise sys.executable.
    Script mode: Python interpreter + main.py.
    """
    if getattr(sys, "frozen", False):
        if platform.system() == "Linux":
            target = os.environ.get("APPIMAGE") or sys.executable
        else:
            target = sys.executable
        return target, "--minimized"
    main_py = os.path.join(base_path, "src", "main.py")
    return sys.executable, f"{main_py} --minimized"
```

- [ ] **Step 2: Replace the inline logic in `save_settings` (lines 451–471 — the entire `if new_autostart != old_autostart:` block) with a call to the helper**

```python
            if new_autostart != old_autostart:
                try:
                    if new_autostart:
                        target, arguments = resolve_autostart_target(self.base_path)
                        enable_autostart(target, arguments)
                    else:
                        disable_autostart()
                    self.settings.set("autostart", new_autostart)
                except Exception as e:
                    messagebox.showerror(
                        "Autostart-Fehler",
                        f"Autostart konnte nicht geändert werden:\n{e}",
                        parent=dialog,
                    )
                    return
```

- [ ] **Step 3: Create `tests/test_ui_autostart_target.py`**

```python
# tests/test_ui_autostart_target.py
import sys
import pytest
from src.ui import resolve_autostart_target


def test_repo_mode_returns_python_interpreter(monkeypatch):
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    target, args = resolve_autostart_target("/repo")
    assert target == sys.executable
    assert args.endswith("main.py --minimized")
    assert "/repo" in args or "\\repo" in args


def test_frozen_windows_uses_sys_executable(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "Zeiterfassung.exe"))
    monkeypatch.setattr("src.ui.platform.system", lambda: "Windows")
    target, args = resolve_autostart_target("/ignored")
    assert target == str(tmp_path / "Zeiterfassung.exe")
    assert args == "--minimized"


def test_frozen_macos_uses_sys_executable(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "Zeiterfassung"))
    monkeypatch.setattr("src.ui.platform.system", lambda: "Darwin")
    target, args = resolve_autostart_target("/ignored")
    assert target == str(tmp_path / "Zeiterfassung")
    assert args == "--minimized"


def test_frozen_linux_prefers_appimage_env(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", "/tmp/_MEIxxx/Zeiterfassung")
    monkeypatch.setattr("src.ui.platform.system", lambda: "Linux")
    monkeypatch.setenv("APPIMAGE", "/home/u/Apps/Zeiterfassung.AppImage")
    target, args = resolve_autostart_target("/ignored")
    assert target == "/home/u/Apps/Zeiterfassung.AppImage"
    assert args == "--minimized"


def test_frozen_linux_falls_back_to_sys_executable(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "Zeiterfassung"))
    monkeypatch.setattr("src.ui.platform.system", lambda: "Linux")
    monkeypatch.delenv("APPIMAGE", raising=False)
    target, args = resolve_autostart_target("/ignored")
    assert target == str(tmp_path / "Zeiterfassung")
    assert args == "--minimized"
```

- [ ] **Step 4: Run the new tests, confirm all pass**

Run: `pytest tests/test_ui_autostart_target.py -v`
Expected: all 5 pass.

- [ ] **Step 5: Full test suite green**

Run: `pytest`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/ui.py tests/test_ui_autostart_target.py
git commit -m "feat(ui): platform-aware autostart target incl. AppImage env fallback"
```

---

## Chunk 4: Build pipeline

### Task 8: Dispatcher + macOS DMG build

**Files:**
- Modify: `build.py`

- [ ] **Step 1: Rewrite `build.py`**

```python
# build.py
import os
import platform
import shutil
import subprocess
import sys

from src.version import VERSION


def _pyinstaller_common(extra_args):
    """Return the PyInstaller command with the mandatory flags prepended."""
    # PyInstaller's --add-data separator: ';' on Windows, ':' elsewhere.
    # os.pathsep happens to match, so we use it.
    add_data = f"assets{os.pathsep}assets"
    return [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--name", "Zeiterfassung",
        "--add-data", add_data,
        "--collect-all", "xhtml2pdf",
        "--collect-all", "reportlab",
        *extra_args,
        "src/main.py",
    ]


def build_windows():
    inno_compiler = os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        "Programs", "Inno Setup 6", "ISCC.exe",
    )

    print(f"Building Zeiterfassung v{VERSION} (Windows) ...")
    cmd = _pyinstaller_common([
        "--onefile",
        "--noconsole",
        "--icon", "assets/margenheld-icon.ico",
    ])
    subprocess.run(cmd, check=True)

    if not os.path.exists(inno_compiler):
        print(f"Inno Setup not found at {inno_compiler} — skipping installer.")
        return
    print(f"Building installer v{VERSION} ...")
    subprocess.run([inno_compiler, f"/DAppVer={VERSION}", "installer.iss"], check=True)
    print("Installer created: dist/Zeiterfassung_Setup.exe")


def build_macos():
    print(f"Building Zeiterfassung v{VERSION} (macOS) ...")
    cmd = _pyinstaller_common([
        "--windowed",
        "-D",
        "--icon", "assets/margenheld-icon.icns",
        "--osx-bundle-identifier", "com.margenheld.zeiterfassung",
    ])
    subprocess.run(cmd, check=True)

    arch = platform.machine()
    dmg_name = f"Zeiterfassung-{VERSION}-{arch}.dmg"
    dmg_path = os.path.join("dist", dmg_name)

    if shutil.which("create-dmg") is None:
        print("create-dmg not found on PATH — install with 'brew install create-dmg'. Skipping DMG.")
        return

    if os.path.exists(dmg_path):
        os.remove(dmg_path)

    print(f"Building DMG: {dmg_name} ...")
    subprocess.run([
        "create-dmg",
        "--volname", "Zeiterfassung",
        "--window-size", "500", "300",
        "--icon", "Zeiterfassung.app", "125", "150",
        "--app-drop-link", "375", "150",
        dmg_path,
        "dist/Zeiterfassung.app",
    ], check=True)
    print(f"DMG created: {dmg_path}")


def build_linux():
    print(f"Building Zeiterfassung v{VERSION} (Linux) ...")
    cmd = _pyinstaller_common([
        "--onefile",
    ])
    subprocess.run(cmd, check=True)

    if shutil.which("appimagetool") is None:
        print("appimagetool not found on PATH — skipping AppImage.")
        return

    appdir = os.path.join("dist", "AppDir")
    if os.path.exists(appdir):
        shutil.rmtree(appdir)
    os.makedirs(os.path.join(appdir, "usr", "bin"))

    shutil.copy2("dist/Zeiterfassung", os.path.join(appdir, "usr", "bin", "Zeiterfassung"))
    os.chmod(os.path.join(appdir, "usr", "bin", "Zeiterfassung"), 0o755)

    shutil.copy2("assets/margenheld-icon.png", os.path.join(appdir, "margenheld-icon.png"))

    desktop = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Zeiterfassung\n"
        "Exec=Zeiterfassung\n"
        "Icon=margenheld-icon\n"
        "Categories=Office;\n"
    )
    with open(os.path.join(appdir, "Zeiterfassung.desktop"), "w", encoding="utf-8") as f:
        f.write(desktop)

    apprun = os.path.join(appdir, "AppRun")
    with open(apprun, "w", encoding="utf-8") as f:
        f.write('#!/bin/sh\nHERE="$(dirname "$(readlink -f "${0}")")"\nexec "$HERE/usr/bin/Zeiterfassung" "$@"\n')
    os.chmod(apprun, 0o755)

    appimage_name = f"Zeiterfassung-{VERSION}-x86_64.AppImage"
    appimage_path = os.path.join("dist", appimage_name)
    if os.path.exists(appimage_path):
        os.remove(appimage_path)

    print(f"Building AppImage: {appimage_name} ...")
    env = os.environ.copy()
    env["ARCH"] = "x86_64"
    subprocess.run(["appimagetool", appdir, appimage_path], check=True, env=env)
    print(f"AppImage created: {appimage_path}")


def main():
    system = platform.system()
    if system == "Windows":
        build_windows()
    elif system == "Darwin":
        build_macos()
    elif system == "Linux":
        build_linux()
    else:
        sys.exit(f"Unsupported platform: {system}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke-check the script imports cleanly**

Run: `python -c "import ast; ast.parse(open('build.py', encoding='utf-8').read())"`
Expected: no output.

- [ ] **Step 3: Run the full test suite**

Run: `pytest`
Expected: all green (no tests touch build.py, but this confirms no stale imports).

- [ ] **Step 4: Commit**

```bash
git add build.py
git commit -m "feat(build): platform-aware dispatcher for macOS DMG and Linux AppImage"
```

---

## Chunk 5: Release workflow and docs

### Task 9: Rewrite `release.yml` with pre-check / matrix / publish

**Files:**
- Modify: `.github/workflows/release.yml`

- [ ] **Step 1: Rewrite the workflow**

```yaml
name: Release

on:
  pull_request:
    types: [closed]
    branches: [master]

jobs:
  pre-check:
    if: >
      github.event.pull_request.merged == true &&
      (contains(github.event.pull_request.labels.*.name, 'release:major') ||
       contains(github.event.pull_request.labels.*.name, 'release:minor') ||
       contains(github.event.pull_request.labels.*.name, 'release:patch'))
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.version }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Read version
        id: version
        shell: bash
        run: |
          VERSION=$(python -c "from src.version import VERSION; print(VERSION)")
          echo "version=${VERSION}" >> "$GITHUB_OUTPUT"
          echo "Releasing v${VERSION}"

      - name: Fail if tag already exists
        shell: bash
        run: |
          git fetch --tags
          if git rev-parse "v${{ steps.version.outputs.version }}" >/dev/null 2>&1; then
            echo "::error::Tag v${{ steps.version.outputs.version }} already exists. Bump src/version.py in your PR before merging."
            exit 1
          fi

  build-windows:
    needs: pre-check
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install -r requirements.txt pyinstaller
      - name: Install Inno Setup
        shell: powershell
        run: |
          $url = "https://jrsoftware.org/download.php/is.exe"
          Invoke-WebRequest -Uri $url -OutFile "$env:TEMP\innosetup.exe"
          $target = "$env:LOCALAPPDATA\Programs\Inno Setup 6"
          Start-Process -FilePath "$env:TEMP\innosetup.exe" `
            -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/DIR=$target" `
            -Wait
      - name: Build
        run: python build.py
      - uses: actions/upload-artifact@v4
        with:
          name: windows
          path: dist/Zeiterfassung_Setup.exe

  build-macos-arm:
    needs: pre-check
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install -r requirements.txt pyinstaller
      - name: Install create-dmg
        run: brew install create-dmg
      - name: Build
        run: python build.py
      - uses: actions/upload-artifact@v4
        with:
          name: macos-arm
          path: dist/Zeiterfassung-*-arm64.dmg

  build-macos-x86:
    needs: pre-check
    runs-on: macos-13
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install -r requirements.txt pyinstaller
      - name: Install create-dmg
        run: brew install create-dmg
      - name: Build
        run: python build.py
      - uses: actions/upload-artifact@v4
        with:
          name: macos-x86
          path: dist/Zeiterfassung-*-x86_64.dmg

  build-linux:
    needs: pre-check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y libfuse2
      - name: Install appimagetool
        run: |
          curl -L -o appimagetool "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
          chmod +x appimagetool
          sudo mv appimagetool /usr/local/bin/
      - name: Install Python dependencies
        run: pip install -r requirements.txt pyinstaller
      - name: Build
        run: python build.py
      - uses: actions/upload-artifact@v4
        with:
          name: linux
          path: dist/Zeiterfassung-*-x86_64.AppImage

  publish:
    needs: [pre-check, build-windows, build-macos-arm, build-macos-x86, build-linux]
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4

      - uses: actions/download-artifact@v4
        with:
          path: dist
          merge-multiple: true

      - name: List downloaded artefacts
        run: ls -la dist/

      - name: Tag and publish release
        shell: bash
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          VERSION="${{ needs.pre-check.outputs.version }}"
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git tag "v${VERSION}"
          git push origin "v${VERSION}"
          gh release create "v${VERSION}" \
            dist/Zeiterfassung_Setup.exe \
            dist/Zeiterfassung-${VERSION}-arm64.dmg \
            dist/Zeiterfassung-${VERSION}-x86_64.dmg \
            dist/Zeiterfassung-${VERSION}-x86_64.AppImage \
            --title "Zeiterfassung v${VERSION}" \
            --generate-notes
```

- [ ] **Step 2: Validate YAML**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml', encoding='utf-8'))"`
Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: split release workflow into pre-check, matrix build, and publish"
```

---

### Task 10: README + CLAUDE.md documentation

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update `README.md`**

Sections to add/update (exact copy at author's discretion — content requirements):

- Platform badge at top: change from `Windows | Linux` to `Windows | macOS | Linux`.
- Installation section, add macOS subsection:
  - "Lade `Zeiterfassung-<ver>-arm64.dmg` (Apple Silicon) oder `Zeiterfassung-<ver>-x86_64.dmg` (Intel) aus den [Releases](…) herunter."
  - "Öffne das DMG, ziehe die App in den Applications-Ordner."
  - "Beim ersten Start: Rechtsklick auf die App → „Öffnen" (Gatekeeper-Warnung bestätigen), oder im Terminal: `xattr -dr com.apple.quarantine /Applications/Zeiterfassung.app`."
- Installation section, add Linux subsection:
  - "Lade `Zeiterfassung-<ver>-x86_64.AppImage` aus den [Releases](…) herunter."
  - "`chmod +x Zeiterfassung-<ver>-x86_64.AppImage` → Doppelklick oder direkt ausführen."
- `credentials.json` placement paths per platform:
  - Windows: neben der Exe (`%LOCALAPPDATA%\Programs\Zeiterfassung\`).
  - macOS: `~/Library/Application Support/Zeiterfassung/`.
  - Linux: `~/.local/share/Zeiterfassung/` (oder `$XDG_DATA_HOME/Zeiterfassung/`).

- [ ] **Step 2: Update `CLAUDE.md`**

Add a new section "Cross-Platform Builds" after the existing "Build" section:

````markdown
## Cross-Platform Builds

`build.py` ist plattformabhängig:

| Plattform | Voraussetzung | Ausgabe |
|-----------|---------------|---------|
| Windows | Inno Setup 6 unter `%LOCALAPPDATA%\Programs\Inno Setup 6\` | `dist/Zeiterfassung_Setup.exe` |
| macOS | `brew install create-dmg` | `dist/Zeiterfassung-<ver>-<arch>.dmg` (arch = `arm64` oder `x86_64`) |
| Linux | `apt install libfuse2` + `appimagetool` auf `$PATH` | `dist/Zeiterfassung-<ver>-x86_64.AppImage` |

Die mandatorischen PyInstaller-Flags (`--collect-all xhtml2pdf --collect-all reportlab`) gelten auf allen drei Plattformen; ohne sie schlägt die PDF-Erzeugung im gebauten Artefakt stumm fehl.
````

And add a "Recovery bei teilweise fehlgeschlagenem Release" section after "Release-Prozess":

````markdown
## Recovery bei teilweise fehlgeschlagenem Release

Wenn der `publish`-Job nach dem Tag-Push fehlschlägt (z.B. `gh release create` Netzwerkproblem), blockiert der Pre-Check beim Re-Run die erneute Ausführung wegen "tag already exists". Ablauf:

1. Tag lokal und remote löschen:
   ```
   git tag -d v<ver>
   git push origin :refs/tags/v<ver>
   ```
2. Workflow im PR unter Actions → „Re-run all jobs" erneut starten.

Alternative: `src/version.py` auf die nächste Patch-Version bumpen und einen neuen Release-PR mergen.
````

- [ ] **Step 3: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs: tri-platform install, Gatekeeper hint, partial-release recovery"
```

---

### Task 11: Final verification

- [ ] **Step 1: Full test suite green**

Run: `pytest`
Expected: all pass.

- [ ] **Step 2: Workflow lint**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml', encoding='utf-8')); yaml.safe_load(open('.github/workflows/test.yml', encoding='utf-8'))"`
Expected: no output.

- [ ] **Step 3: Git log sanity check**

Run: `git log --oneline -15`
Expected: approximately the following commits, in order:

```
docs: tri-platform install, Gatekeeper hint, partial-release recovery
ci: split release workflow into pre-check, matrix build, and publish
feat(build): platform-aware dispatcher for macOS DMG and Linux AppImage
feat(ui): platform-aware autostart target incl. AppImage env fallback
test(autostart): Linux .desktop autostart coverage
feat(autostart): macOS LaunchAgent support
chore(assets): add macOS .icns icon
fix(ui): guard iconbitmap behind Windows check
feat(mail): surface resolved credentials path in error message
feat(paths): platform-aware data directory for macOS and Linux
```

- [ ] **Step 4: Manual acceptance — deferred until first release build**

Per spec §7 "Manual smoke test (once per new platform, after first release build)": smoke-test the produced DMG on macOS and the AppImage on Linux. Not part of this plan's merge gate; tracked separately once the first `release:minor` PR produces artefacts.

---

## Done-definition

1. All 10 tasks' commits on `master` (or the feature branch).
2. `pytest` green in CI (`test.yml`).
3. Release workflow YAML valid.
4. Next `release:*` PR produces four artefacts (one Windows EXE, two DMGs, one AppImage).
5. README documents tri-platform install and Gatekeeper hint.
