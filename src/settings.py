import json
import os

DEFAULTS = {
    "email": "",
    "default_start": "08:00",
    "default_end": "16:00",
    "default_pause": 30,
    "recipient": "",
    "autostart": False,
    "name": "",
    "mail_subject": "Zeiterfassung — {zeitraum}",
    "mail_greeting": "Sehr geehrte Damen und Herren,",
    "mail_content": "anbei erhalten Sie meine Zeiterfassung für den Zeitraum {zeitraum}.",
    "mail_closing": "Mit freundlichen Grüßen",
    "hourly_rate": 0.0,
    "state": "",
    "last_update_check_at": "",
    "dismissed_version": "",
}

class Settings:
    def __init__(self, filepath="settings.json"):
        self.filepath = filepath
        self._data = dict(DEFAULTS)
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                self._data.update(loaded)
            except (json.JSONDecodeError, ValueError):
                self._data = dict(DEFAULTS)

    def _save_to_disk(self):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, key):
        return self._data.get(key, DEFAULTS.get(key))

    def set(self, key, value):
        self._data[key] = value
        self._save_to_disk()
