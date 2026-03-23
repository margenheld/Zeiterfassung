import pytest
from src.settings import Settings

@pytest.fixture
def tmp_settings(tmp_path):
    return Settings(str(tmp_path / "settings.json"))

def test_defaults(tmp_settings):
    assert tmp_settings.get("email") == ""
    assert tmp_settings.get("default_pause") == 30

def test_save_and_load(tmp_settings):
    tmp_settings.set("email", "test@example.com")
    assert tmp_settings.get("email") == "test@example.com"

def test_set_default_pause(tmp_settings):
    tmp_settings.set("default_pause", 45)
    assert tmp_settings.get("default_pause") == 45

def test_persistence(tmp_path):
    path = str(tmp_path / "settings.json")
    s1 = Settings(path)
    s1.set("email", "test@example.com")
    s1.set("default_pause", 15)
    s2 = Settings(path)
    assert s2.get("email") == "test@example.com"
    assert s2.get("default_pause") == 15

def test_corrupted_file(tmp_path):
    path = str(tmp_path / "settings.json")
    with open(path, "w") as f:
        f.write("not json{{{")
    s = Settings(path)
    assert s.get("email") == ""
    assert s.get("default_pause") == 30

def test_recipient_default(tmp_settings):
    assert tmp_settings.get("recipient") == ""
