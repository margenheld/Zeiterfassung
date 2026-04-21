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
    return os.path.join(
        os.path.expanduser("~"),
        "Library", "LaunchAgents", f"{MACOS_LABEL}.plist",
    )


def _linux_desktop_path():
    return os.path.join(
        os.path.expanduser("~"),
        ".config", "autostart", "Zeiterfassung.desktop",
    )


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
