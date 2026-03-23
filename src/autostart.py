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
