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
