import json
from unittest.mock import patch

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

def test_autostart_default(tmp_settings):
    assert tmp_settings.get("autostart") == False


def test_last_update_check_at_default(tmp_settings):
    assert tmp_settings.get("last_update_check_at") == ""


def test_dismissed_version_default(tmp_settings):
    assert tmp_settings.get("dismissed_version") == ""


def test_set_many_writes_once(tmp_settings):
    """set_many ruft _save_to_disk genau einmal auf."""
    with patch.object(tmp_settings, "_save_to_disk") as mock_save:
        tmp_settings.set_many({"email": "a@b.de", "default_pause": 45})
    assert mock_save.call_count == 1


def test_set_many_updates_data(tmp_settings):
    tmp_settings.set_many({"email": "a@b.de", "default_pause": 45})
    assert tmp_settings.get("email") == "a@b.de"
    assert tmp_settings.get("default_pause") == 45


def test_set_many_empty_is_noop(tmp_settings):
    """Leeres Dict triggert keinen Disk-Write."""
    with patch.object(tmp_settings, "_save_to_disk") as mock_save:
        tmp_settings.set_many({})
    mock_save.assert_not_called()


def test_set_is_wrapper_around_set_many(tmp_settings):
    with patch.object(tmp_settings, "_save_to_disk") as mock_save:
        tmp_settings.set("email", "x@y.de")
    assert mock_save.call_count == 1
    assert tmp_settings.get("email") == "x@y.de"


def _write_json(tmp_path, payload):
    path = tmp_path / "settings.json"
    with open(path, "w", encoding="utf-8") as f:
        f.write(payload)
    return str(path)


def test_load_casts_string_to_int(tmp_path):
    path = _write_json(tmp_path, json.dumps({"default_pause": "30"}))
    s = Settings(path)
    assert s.get("default_pause") == 30


def test_load_keeps_default_when_int_cast_fails(tmp_path, caplog):
    path = _write_json(tmp_path, json.dumps({"default_pause": "abc"}))
    with caplog.at_level("WARNING"):
        s = Settings(path)
    assert s.get("default_pause") == 30
    assert any("default_pause" in rec.message for rec in caplog.records)


def test_load_bool_strictness_string_value(tmp_path, caplog):
    path = _write_json(tmp_path, json.dumps({"autostart": "true"}))
    with caplog.at_level("WARNING"):
        s = Settings(path)
    assert s.get("autostart") is False
    assert any("autostart" in rec.message for rec in caplog.records)


def test_load_bool_strictness_int_value(tmp_path, caplog):
    path = _write_json(tmp_path, json.dumps({"autostart": 1}))
    with caplog.at_level("WARNING"):
        s = Settings(path)
    assert s.get("autostart") is False


def test_load_int_for_float_default(tmp_path):
    path = _write_json(tmp_path, json.dumps({"hourly_rate": 25}))
    s = Settings(path)
    assert s.get("hourly_rate") == 25.0
    assert isinstance(s.get("hourly_rate"), float)


def test_load_unknown_key_is_ignored(tmp_path):
    path = _write_json(tmp_path, json.dumps({"old_field": "x", "email": "a@b.de"}))
    s = Settings(path)
    assert s.get("old_field") is None
    assert s.get("email") == "a@b.de"


def test_load_toplevel_not_dict_resets_to_defaults(tmp_path, caplog):
    path = _write_json(tmp_path, json.dumps([1, 2, 3]))
    with caplog.at_level("WARNING"):
        s = Settings(path)
    assert s.get("default_pause") == 30
    assert s.get("email") == ""
    assert any("Toplevel" in rec.message or "toplevel" in rec.message for rec in caplog.records)
