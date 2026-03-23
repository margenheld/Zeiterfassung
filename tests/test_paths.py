# tests/test_paths.py
import os
import sys
import pytest
from src.paths import get_base_path


def test_returns_directory(tmp_path, monkeypatch):
    """get_base_path() returns a directory that exists."""
    result = get_base_path()
    assert os.path.isdir(result)


def test_script_mode_returns_project_root():
    """In script mode (not frozen), returns the project root directory."""
    result = get_base_path()
    assert os.path.isdir(os.path.join(result, "src"))
    assert os.path.isdir(os.path.join(result, "tests"))


def test_frozen_mode(tmp_path, monkeypatch):
    """In frozen mode, returns the directory containing sys.executable."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "Zeiterfassung.exe"))
    result = get_base_path()
    assert result == str(tmp_path)
