# build.py
import subprocess
import sys

def build():
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--noconsole",
        "--name", "Zeiterfassung",
        "src/main.py",
    ]
    subprocess.run(cmd, check=True)

if __name__ == "__main__":
    build()
