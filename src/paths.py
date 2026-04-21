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
        base = os.path.join(
            os.path.expanduser("~"),
            "Library", "Application Support", "Zeiterfassung",
        )
    else:
        xdg = os.environ.get("XDG_DATA_HOME") or os.path.join(
            os.path.expanduser("~"), ".local", "share"
        )
        base = os.path.join(xdg, "Zeiterfassung")

    os.makedirs(base, exist_ok=True)
    return base
