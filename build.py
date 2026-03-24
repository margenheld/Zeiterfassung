# build.py
import subprocess
import sys

def build():
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--noconsole",
        "--name", "Zeiterfassung",
        "--icon", "assets/margenheld-icon.ico",
        "--add-data", "assets;assets",
        "src/main.py",
    ]
    subprocess.run(cmd, check=True)

if __name__ == "__main__":
    build()
