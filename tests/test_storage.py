import pytest
from src.storage import Storage

@pytest.fixture
def tmp_storage(tmp_path):
    return Storage(str(tmp_path / "test.json"))

def test_load_empty(tmp_storage):
    assert tmp_storage.get_all() == {}

def test_save_and_load(tmp_storage):
    tmp_storage.save("2026-03-23", "08:00", "16:30")
    entries = tmp_storage.get_all()
    assert entries["2026-03-23"] == {"start": "08:00", "end": "16:30"}

def test_delete_entry(tmp_storage):
    tmp_storage.save("2026-03-23", "08:00", "16:30")
    tmp_storage.delete("2026-03-23")
    assert "2026-03-23" not in tmp_storage.get_all()

def test_delete_nonexistent(tmp_storage):
    tmp_storage.delete("2026-01-01")  # should not raise

def test_persistence(tmp_path):
    path = str(tmp_path / "test.json")
    s1 = Storage(path)
    s1.save("2026-03-23", "08:00", "16:30")
    s2 = Storage(path)
    assert s2.get_all()["2026-03-23"] == {"start": "08:00", "end": "16:30"}
