import datetime
import json
import os


class Storage:
    def __init__(self, filepath="zeiterfassung.json"):
        self.filepath = filepath
        self._data = {}
        self._load()

    def _load(self):
        if not os.path.exists(self.filepath):
            return
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        except (json.JSONDecodeError, ValueError):
            # Corrupt file: rename it so the user can recover it manually
            # rather than silently overwriting on the next save.
            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            os.replace(self.filepath, f"{self.filepath}.corrupt-{stamp}")
            self._data = {}

    def _save_to_disk(self):
        # Atomic write: temp file + replace, so a crash mid-write
        # cannot leave the data file half-written.
        tmp = self.filepath + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
        try:
            os.replace(tmp, self.filepath)
        except OSError:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise

    def get_all(self):
        return dict(self._data)

    def get(self, date_str):
        return self._data.get(date_str)

    def save(self, date_str, start, end, pause=0):
        self._data[date_str] = {"start": start, "end": end, "pause": pause}
        self._save_to_disk()

    def delete(self, date_str):
        if date_str in self._data:
            del self._data[date_str]
            self._save_to_disk()
