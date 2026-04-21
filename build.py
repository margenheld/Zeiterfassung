# build.py
import os
import subprocess
import sys

from src.version import VERSION

INNO_COMPILER = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "Programs", "Inno Setup 6", "ISCC.exe",
)


def build_exe():
    print(f"Building Zeiterfassung v{VERSION} ...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--noconsole",
        "--name", "Zeiterfassung",
        "--icon", "assets/margenheld-icon.ico",
        "--add-data", "assets;assets",
        "--collect-all", "xhtml2pdf",
        "--collect-all", "reportlab",
        "src/main.py",
    ]
    subprocess.run(cmd, check=True)


def build_installer():
    if not os.path.exists(INNO_COMPILER):
        print(f"Inno Setup not found at {INNO_COMPILER} — skipping installer.")
        return
    print(f"Building installer v{VERSION} ...")
    cmd = [INNO_COMPILER, f"/DAppVer={VERSION}", "installer.iss"]
    subprocess.run(cmd, check=True)
    print(f"Installer created: dist/Zeiterfassung_Setup.exe")


if __name__ == "__main__":
    build_exe()
    build_installer()
