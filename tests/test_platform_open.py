# tests/test_platform_open.py
import pytest
from unittest.mock import MagicMock
from src.platform_open import open_folder


def test_open_folder_windows(monkeypatch):
    monkeypatch.setattr("src.platform_open.platform.system", lambda: "Windows")
    mock_startfile = MagicMock()
    monkeypatch.setattr(
        "src.platform_open.os.startfile", mock_startfile, raising=False
    )
    open_folder(r"C:\Users\test\data")
    mock_startfile.assert_called_once_with(r"C:\Users\test\data")


def test_open_folder_macos(monkeypatch):
    monkeypatch.setattr("src.platform_open.platform.system", lambda: "Darwin")
    mock_run = MagicMock()
    monkeypatch.setattr("src.platform_open.subprocess.run", mock_run)
    open_folder("/Users/test/Library/Application Support/Zeiterfassung")
    mock_run.assert_called_once_with(
        ["open", "/Users/test/Library/Application Support/Zeiterfassung"],
        check=True,
    )


def test_open_folder_linux(monkeypatch):
    monkeypatch.setattr("src.platform_open.platform.system", lambda: "Linux")
    mock_run = MagicMock()
    monkeypatch.setattr("src.platform_open.subprocess.run", mock_run)
    open_folder("/home/test/.local/share/Zeiterfassung")
    mock_run.assert_called_once_with(
        ["xdg-open", "/home/test/.local/share/Zeiterfassung"],
        check=True,
    )


def test_open_folder_unsupported_platform_raises(monkeypatch):
    monkeypatch.setattr("src.platform_open.platform.system", lambda: "FreeBSD")
    with pytest.raises(RuntimeError, match="Unsupported platform"):
        open_folder("/tmp/whatever")
