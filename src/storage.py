import json
import os

class Storage:
    def __init__(self, filepath="zeiterfassung.json"):
        self.filepath = filepath
        self._data = {}
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, "r", encoding="utf-8") as f:
                self._data = json.load(f)

    def _save_to_disk(self):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get_all(self):
        return dict(self._data)

    def get(self, date_str):
        return self._data.get(date_str)

    def save(self, date_str, start, end):
        self._data[date_str] = {"start": start, "end": end}
        self._save_to_disk()

    def delete(self, date_str):
        if date_str in self._data:
            del self._data[date_str]
            self._save_to_disk()
