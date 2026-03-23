# tests/test_autostart.py
import os
import sys
import platform
import pytest
from unittest.mock import patch, MagicMock
from src.autostart import enable_autostart, disable_autostart, _get_startup_folder, _get_shortcut_path


@pytest.fixture
def fake_startup(tmp_path, monkeypatch):
    """Patch _get_startup_folder to return a temp directory."""
    monkeypatch.setattr("src.autostart._get_startup_folder", lambda: str(tmp_path))
    return tmp_path


@pytest.mark.skipif(platform.system() != "Windows", reason="Windows only")
class TestWindowsAutostart:

    def test_get_startup_folder_returns_existing_dir(self):
        folder = _get_startup_folder()
        assert os.path.isdir(folder)

    def test_get_shortcut_path(self, fake_startup):
        path = _get_shortcut_path()
        assert path == str(fake_startup / "Zeiterfassung.lnk")

    def test_enable_creates_shortcut(self, fake_startup):
        with patch("src.autostart.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            enable_autostart(r"C:\app\Zeiterfassung.exe", "--minimized")
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args[0] == "cscript"
            assert args[1] == "//nologo"
            assert args[2].endswith(".vbs")

    def test_enable_cleans_up_vbs(self, fake_startup):
        with patch("src.autostart.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            enable_autostart(r"C:\app\Zeiterfassung.exe", "--minimized")
            vbs_path = mock_run.call_args[0][0][2]
            assert not os.path.exists(vbs_path)

    def test_disable_removes_shortcut(self, fake_startup):
        shortcut = fake_startup / "Zeiterfassung.lnk"
        shortcut.write_text("fake")
        assert shortcut.exists()
        disable_autostart()
        assert not shortcut.exists()

    def test_disable_no_shortcut_no_error(self, fake_startup):
        disable_autostart()
