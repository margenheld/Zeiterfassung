# macOS & Linux Releases — Design Spec

## Overview

Extend the existing Windows-only release pipeline to also produce installable artefacts for macOS and Linux. The result of a `release:*`-labelled PR merge is a GitHub Release with four assets:

| Platform | Artefact |
|----------|----------|
| Windows | `Zeiterfassung_Setup.exe` (unchanged) |
| macOS Apple Silicon | `Zeiterfassung-<ver>-arm64.dmg` |
| macOS Intel | `Zeiterfassung-<ver>-x86_64.dmg` |
| Linux x86_64 | `Zeiterfassung-<ver>-x86_64.AppImage` |

The Windows pipeline stays behaviourally identical. All macOS and Linux support is additive.

## Scope decisions (settled during brainstorming)

| # | Decision | Consequence |
|---|----------|-------------|
| 1 | Internal tool, unsigned on all platforms | No Apple Developer ID, no notarization; Gatekeeper warning on macOS is accepted (right-click → Open, or `xattr -d com.apple.quarantine`) |
| 2 | Linux format: AppImage only | Single-file, runs on most distros; no `.deb`/`.rpm`/tarball |
| 3 | macOS: ARM and Intel as separate DMGs | No Universal Binary; two runners, two assets |
| 4 | Autostart implemented for all three platforms | macOS: LaunchAgent plist; Linux: `.desktop` file; Windows unchanged |
| 5 | macOS UI regressions accepted | Native-gray `tk.Button` (ignores `bg`/`fg`) is okay; no button refactor; no per-platform font fallback |

## Guiding principles

1. **Additive, not disruptive.** The Windows build path stays byte-for-byte compatible. All platform-specific code is gated by `platform.system()`; no existing Windows logic is rewritten.
2. **Single source of truth for version.** `src/version.py` remains the only place the version lives. `installer.iss` reads it via `/DAppVer=…` as today; macOS/Linux builds interpolate it into artefact names.
3. **Per-platform pack tools installed only in CI.** Local dev machines are not required to have `create-dmg` or `appimagetool` unless the developer is building for that platform locally.
4. **Cross-platform tests on `ubuntu-latest`.** All new unit tests mock `platform.system()` and run on the existing test CI runner. No macOS/Linux-specific test infrastructure.

---

## 1. Path handling — `src/paths.py`

### Problem

`get_base_path()` returns `os.path.dirname(sys.executable)` in frozen mode. On macOS inside a signed `.app` bundle, that directory is read-only (and Gatekeeper quarantine rejects writes). Writing `token.json` / `settings.json` there fails silently at runtime.

### New behaviour

```python
def get_base_path():
    if not getattr(sys, "frozen", False):
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root

    system = platform.system()
    if system == "Windows":
        return os.path.dirname(sys.executable)                              # unchanged
    if system == "Darwin":
        base = os.path.expanduser("~/Library/Application Support/Zeiterfassung")
    else:  # Linux and anything else
        xdg = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
        base = os.path.join(xdg, "Zeiterfassung")

    os.makedirs(base, exist_ok=True)
    return base
```

### Windows stays as is — explicit non-goal

Existing Windows installs have `zeiterfassung.json`, `settings.json`, `token.json`, `credentials.json` **next to the executable**. Inno Setup installs into `{autopf}` (see `installer.iss:6`), which expands depending on the elevation prompt to `{userpf}` (per-user, the default with `PrivilegesRequired=lowest`) or `{commonpf}` (all users, if the UAC dialog is accepted). Both variants are writable for the installing user. Migrating data into `%LOCALAPPDATA%\Zeiterfassung` would require discovery + move logic + coordination with running instances. The cost-benefit does not justify the risk — Windows behaviour is frozen.

### `credentials.json` placement on macOS/Linux

`credentials.json` is downloaded manually from the Google Cloud Console by the user; the app does not create it. On macOS/Linux it must now be placed inside a hidden Library/XDG directory, which is inconvenient.

**Resolution:** The existing error path in `src/mail.py:89-93` (`FileNotFoundError("credentials.json nicht gefunden …")`) is extended to include the resolved, platform-correct target path. No file picker / copy button. One-time setup cost is accepted.

### Tests (`tests/test_paths.py`)

Parametrised, all running on `ubuntu-latest` via `platform.system()` mocking:

- `test_paths_frozen_windows_returns_exe_dir`
- `test_paths_frozen_macos_returns_library_support_and_creates_dir`
- `test_paths_frozen_linux_respects_xdg_data_home`
- `test_paths_frozen_linux_falls_back_to_local_share`
- `test_paths_repo_mode_unchanged` — parametrised over `platform.system() ∈ {Windows, Darwin, Linux}` so dev-mode on a Mac laptop is covered explicitly.

---

## 2. Icon handling

### New asset

`assets/margenheld-icon.icns`, generated once from the existing PNG (via `iconutil` on a Mac or Pillow), committed to the repo. No runtime generation.

### `src/ui.py:74-81` — guard `iconbitmap`

`root.iconbitmap("*.ico")` raises `TclError` on macOS. Fix — `ico_path` and `png_path` come from the existing two lines above (derived from `base_path + "assets/margenheld-icon.{ico,png}"`, unchanged):

```python
ico_path = os.path.join(base_path, "assets", "margenheld-icon.ico")
png_path = os.path.join(base_path, "assets", "margenheld-icon.png")
if platform.system() == "Windows" and os.path.exists(ico_path):
    self.root.iconbitmap(ico_path)
if os.path.exists(png_path):
    icon = tk.PhotoImage(file=png_path)
    self.root.iconphoto(True, icon)
    self._icon_ref = icon
```

The `iconphoto(.png)` fallback handles window icons on macOS and Linux.

### Dock icon on macOS

PyInstaller with `--windowed -D --icon …icns --osx-bundle-identifier com.margenheld.zeiterfassung` writes `CFBundleIconFile` into the `.app`'s `Info.plist` automatically. No additional runtime code.

### Explicit non-goals

- No per-platform font fallback (decision 5).
- No `tk.Button` → `ttk.Button` refactor (decision 5).
- No `ctypes.windll` changes (already `try/except`-guarded).

### Tests

None — `ui.py` has no existing unit-test harness; adding one is out of scope. Verified by the first macOS smoke test.

---

## 3. Autostart — `src/autostart.py`

### Public API unchanged

`enable_autostart(target, arguments="")` and `disable_autostart()` keep their signatures — the module's contract is stable. `ui.py::save_settings` (`ui.py:442-463`) still needs a small extension: it must compute the correct `target` per platform (see "What is `target` on each platform" below). The call site is unchanged, but the platform-dependent `target` resolution is new logic inside `save_settings`.

### Dispatcher structure

```python
def enable_autostart(target, arguments=""):
    system = platform.system()
    if system == "Windows":   _enable_windows(target, arguments)
    elif system == "Darwin":  _enable_macos(target, arguments)
    elif system == "Linux":   _enable_linux(target, arguments)

def disable_autostart():
    system = platform.system()
    if system == "Windows":   _disable_windows()
    elif system == "Darwin":  _disable_macos()
    elif system == "Linux":   _disable_linux()
```

The current VBScript/`cscript` logic becomes `_enable_windows` / `_disable_windows` unchanged.

### macOS: LaunchAgent plist

Path: `~/Library/LaunchAgents/com.margenheld.zeiterfassung.plist`

Written via `plistlib.dump()` from the Python stdlib (no manual XML escaping):

```
Label:            com.margenheld.zeiterfassung
ProgramArguments: [<target>, "--minimized"]
RunAtLoad:        true
ProcessType:      Interactive
```

Then `subprocess.run(["launchctl", "load", "-w", plist_path], check=True)`. `-w` persists the load across logins.

Note: `launchctl load` is technically deprecated in favour of `launchctl bootstrap gui/<uid> <plist>` on macOS 10.10+, but `load` still works reliably and avoids fiddling with the current console user's UID. We stay on `load -w` for simplicity; the modern form is a future hardening option if we ever hit issues.

`_disable_macos`: `launchctl unload <plist>`, then `os.remove`. Both steps tolerate "already absent" state (wrap each in a try/except that swallows `FileNotFoundError` / non-zero exit).

### Linux: `.desktop` file

Path: `~/.config/autostart/Zeiterfassung.desktop`

Plain-text INI content:

```
[Desktop Entry]
Type=Application
Name=Zeiterfassung
Exec=<target> --minimized
Hidden=false
X-GNOME-Autostart-enabled=true
```

Freedesktop-standard; recognised by GNOME, KDE, XFCE, Cinnamon. No activation call — session managers read the directory at login. `_disable_linux`: `os.remove`, tolerating absence.

### What is `target` on each platform

Determined in `src/ui.py::save_settings` and passed to `enable_autostart()`:

| Platform | Mode | `target` |
|----------|------|----------|
| Windows | frozen | `sys.executable` |
| macOS | frozen (`.app`) | `sys.executable` (= `…/Zeiterfassung.app/Contents/MacOS/Zeiterfassung`) |
| Linux | frozen (AppImage) | **`os.environ.get("APPIMAGE") or sys.executable`** — `sys.executable` points into the extracted `/tmp/_MEIxxx` runtime and is invalidated when the AppImage exits; `$APPIMAGE` is the persistent path set by the AppImage runtime. The `or`-fallback covers the case of a developer running the PyInstaller binary directly (without AppImage wrap) — autostart then points at the raw binary, which is still usable locally. |
| any | repo (script) | `sys.executable` (= Python), with `arguments=f"{main_py} --minimized"` |

The AppImage special case lives in `ui.py`, not `autostart.py`, keeping the autostart module platform-logic-only. A unit test covers the `APPIMAGE`-unset fallback explicitly.

### Tests (`tests/test_autostart.py`)

Extended from 4 to ~10 tests, parametrised via `platform.system()` mocking and `tmp_path` for home directory:

- `test_enable_macos_writes_plist_with_correct_content` (verifies via `plistlib.load`)
- `test_enable_macos_invokes_launchctl_load`
- `test_disable_macos_removes_plist_and_unloads`
- `test_enable_linux_writes_desktop_file_with_correct_exec_line`
- `test_disable_linux_removes_desktop_file`

Plus in `tests/test_ui.py` (new small file) or `tests/test_autostart.py`:

- `test_save_settings_computes_appimage_target_when_set` (monkeypatch `APPIMAGE=/path/foo.AppImage`, verify `enable_autostart` is called with that as `target`)
- `test_save_settings_falls_back_to_sys_executable_when_appimage_unset`

Existing Windows tests unchanged.

---

## 4. Build pipeline — `build.py`

### Dispatcher

```python
def main():
    system = platform.system()
    if system == "Windows":  build_windows()
    elif system == "Darwin": build_macos()
    elif system == "Linux":  build_linux()
    else: sys.exit(f"Unsupported platform: {system}")
```

Existing `build_exe()` + `build_installer()` become `build_windows()` unchanged.

### macOS build

```
pyinstaller \
  --windowed -D \
  --name Zeiterfassung \
  --icon assets/margenheld-icon.icns \
  --osx-bundle-identifier com.margenheld.zeiterfassung \
  --add-data "assets:assets" \
  --collect-all xhtml2pdf \
  --collect-all reportlab \
  src/main.py
```

→ `dist/Zeiterfassung.app`

Then:

```
create-dmg \
  --volname "Zeiterfassung" \
  --window-size 500 300 \
  --icon "Zeiterfassung.app" 125 150 \
  --app-drop-link 375 150 \
  "dist/Zeiterfassung-<ver>-<arch>.dmg" \
  "dist/Zeiterfassung.app"
```

`<arch>` is `platform.machine()` (`arm64` or `x86_64`). Local build dep: `brew install create-dmg`.

### Linux build

```
pyinstaller \
  --onefile \
  --name Zeiterfassung \
  --add-data "assets:assets" \
  --collect-all xhtml2pdf \
  --collect-all reportlab \
  src/main.py
```

→ `dist/Zeiterfassung` (single binary).

AppDir built by the script:

```
dist/AppDir/
├── AppRun                              # symlink → usr/bin/Zeiterfassung
├── Zeiterfassung.desktop               # consumed by appimagetool
├── margenheld-icon.png
└── usr/bin/Zeiterfassung               # the binary
```

Then:

```
appimagetool dist/AppDir dist/Zeiterfassung-<ver>-x86_64.AppImage
```

Local build dep: `appimagetool` binary on `PATH` (single AppImage download).

### Cross-platform details

- `--add-data` separator follows PyInstaller's convention (`;` on Windows, `:` elsewhere). This happens to match `os.pathsep` on all three target platforms, so `"assets" + os.pathsep + "assets"` is the pragmatic way to assemble the argument.
- `--collect-all xhtml2pdf --collect-all reportlab` is mandatory on every platform (per CLAUDE.md — without it, PDF generation silently fails in frozen mode).
- No `.spec` file is committed. CLI arguments remain the source of truth; `*.spec` is already gitignored.

### Artefact matrix

| Platform | Runner | Artefact |
|----------|--------|----------|
| Windows | `windows-latest` | `dist/Zeiterfassung_Setup.exe` |
| macOS ARM | `macos-latest` | `dist/Zeiterfassung-<ver>-arm64.dmg` |
| macOS Intel | `macos-13` | `dist/Zeiterfassung-<ver>-x86_64.dmg` |
| Linux | `ubuntu-latest` | `dist/Zeiterfassung-<ver>-x86_64.AppImage` |

### Non-goals for `build.py`

- No automatic `.icns` generation from `.png` (committed once, deterministic).
- No cross-compilation. `build.py` runs on the target platform.
- No signing / notarization (decision 1).

---

## 5. Release workflow — `.github/workflows/release.yml`

### Job graph

```
                pre-check (ubuntu-latest)
                        │
        ┌───────────────┼────────────┬───────────────┐
        ▼               ▼            ▼               ▼
  build-windows  build-macos-arm  build-macos-x86  build-linux
        └───────────────┴────────────┴───────────────┘
                        ▼
                     publish
```

### `pre-check` job

- Checkout, read `src/version.py`, output `version`.
- `git rev-parse v<version>` — fail with actionable message if tag exists ("bump `src/version.py` before merging").
- Runs on `ubuntu-latest` (cheapest).

All build jobs declare `needs: pre-check` and consume its `version` output. This prevents spending four parallel build minutes when the version bump was forgotten.

### Build jobs

Each build job:

1. Checkout
2. `actions/setup-python@v5` with `python-version: '3.10'`
3. `pip install -r requirements.txt pyinstaller`
4. Platform-specific pack tool setup (see below)
5. `python build.py`
6. `actions/upload-artifact@v4` with the platform's artefact

Platform-specific pack tool setup:

| Job | Extra setup |
|-----|-------------|
| `build-windows` | Install Inno Setup via `Invoke-WebRequest` (as today) |
| `build-macos-arm` / `build-macos-x86` | `brew install create-dmg` |
| `build-linux` | `sudo apt-get install -y libfuse2`, `curl -L <appimagetool-url> -o appimagetool && chmod +x && sudo mv /usr/local/bin/` |

### `publish` job

- `needs: [build-windows, build-macos-arm, build-macos-x86, build-linux]`
- `runs-on: ubuntu-latest`, `permissions: contents: write`
- Downloads all four artefacts via `actions/download-artifact@v4`
- Configures git user, creates + pushes tag `v<version>`
- `gh release create v<version> <all four assets> --title "Zeiterfassung v<version>" --generate-notes`

**Atomic semantics:** The tag is only pushed after all four build jobs have succeeded. A failed macOS-Intel build aborts the entire publish step; no half-complete release gets created. This is a behavioural change from today's single-job workflow but desired.

**Partial failure recovery:** If `publish` fails *after* the tag has been pushed (e.g. `gh release create` network hiccup), a simple re-run of the workflow is blocked by `pre-check`'s "tag already exists" guard. Recovery procedure (documented in `CLAUDE.md` under release notes):

1. Delete the orphan tag locally and on the remote: `git tag -d v<ver>` + `git push origin :refs/tags/v<ver>`.
2. Re-run the workflow from the PR's Actions view, or alternatively bump `src/version.py` to the next patch and re-merge.

Tag-delete is a rare manual step for a rare failure mode; automating it would require admin-bypass permissions in the workflow, which we avoid.

### `on:` trigger unchanged

`pull_request: types: [closed], branches: [master]`, filter `merged == true && contains(labels, 'release:*')`.

### Test workflow unchanged

`.github/workflows/test.yml` keeps running `pytest` on `ubuntu-latest` without installing `requirements.txt` (CLAUDE.md explains why: transitive `pycairo` requires Cairo system headers and breaks CI). The new path/autostart tests run there because they mock `platform.system()`.

### Cost note

The repository is public. GitHub Actions minutes on public repositories are unlimited; the `macos-latest` / `macos-13` multiplier (10× the Linux rate) has no billing consequence.

---

## 6. Documentation

`README.md` updates:

- Platform badge: `Windows | macOS | Linux` (currently `Windows | Linux`).
- Platform compatibility table: add macOS column, mark features implemented (calendar, PDF, mail, autostart, window icon).
- Installation section: add macOS (DMG drag-to-Applications) and Linux (AppImage `chmod +x`) instructions.
- First-launch Gatekeeper hint for macOS: right-click → Open, or `xattr -dr com.apple.quarantine /Applications/Zeiterfassung.app` (recursive, on the bundle path).
- `credentials.json` placement paths per platform.

`CLAUDE.md` updates: keep Windows-centric build notes, add short section pointing `build.py` is platform-aware and lists the per-platform local build tool prereqs.

---

## 7. Testing & acceptance

### Automated (runs on `ubuntu-latest` in `test.yml`)

- All new `test_paths.py` and `test_autostart.py` cases pass.
- Existing tests continue to pass.

### Manual smoke test (once per new platform, after first release build)

1. Download the artefact from GitHub Releases.
2. Install (DMG: drag to Applications; AppImage: `chmod +x` + double-click).
3. Launch → window and icon correct.
4. Create an entry for today → appears in the calendar.
5. Close and reopen the app → entry persists (confirms data path).
6. Edit a mail template in Settings, save, reopen → change persists.
7. Enable autostart, log out and back in → app starts minimised.
8. Disable autostart, log back in → app does not start.
9. Place `credentials.json` at the platform-correct location, click "Monat senden", complete OAuth flow → email arrives with correct umlauts and PDF attachment.

### Definition of Done

1. All automated tests green.
2. First release build (version bump e.g. `1.x.0`) produces all four artefacts without error.
3. Smoke test completed successfully on all three new platforms.
4. `README.md` reflects tri-platform support.

---

## Out of scope

- Code signing / Apple notarization (decision 1).
- Universal macOS binary via `lipo` (decision 3).
- Linux `.deb` / `.rpm` / tarball packages (decision 2).
- `tk.Button` refactor to `ttk.Button` for macOS visual parity (decision 5).
- Per-platform font selection (decision 5).
- System tray / menu-bar icon on any platform.
- Auto-update mechanism.
- Windows data-path migration (stays next-to-exe).
- UI unit tests for `ui.py`.
