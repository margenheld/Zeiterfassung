# src/paths.py
import os
import sys


def get_base_path():
    """Return the directory where data files should be stored.

    When running as a PyInstaller .exe (frozen): directory containing the .exe
    When running as a Python script: project root directory (parent of src/)
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
