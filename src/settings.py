import json
import logging
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

_COERCE_FAILED = object()


def _coerce(value, default):
    """Versuche `value` in den Typ von `default` zu casten.

    Liefert den gecasteten Wert oder `_COERCE_FAILED`. bool ist Subklasse
    von int — wir verlangen für bool-Defaults strikt einen bool, sonst
    wäre `1` versehentlich `True`.
    """
    target_type = type(default)
    if target_type is bool:
        return value if isinstance(value, bool) else _COERCE_FAILED
    if isinstance(value, target_type) and not isinstance(value, bool):
        return value
    try:
        if target_type is int:
            return int(value)
        if target_type is float:
            return float(value)
        if target_type is str:
            return str(value)
    except (TypeError, ValueError):
        return _COERCE_FAILED
    return _COERCE_FAILED


class Settings:
    def __init__(self, filepath="settings.json"):
        self.filepath = filepath
        self._data = dict(DEFAULTS)
        self._load()

    def _load(self):
        if not os.path.exists(self.filepath):
            return
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                loaded = json.load(f)
        except (json.JSONDecodeError, ValueError):
            self._data = dict(DEFAULTS)
            return

        log = logging.getLogger(__name__)
        if not isinstance(loaded, dict):
            log.warning(
                "settings.json hat unerwartetes Toplevel-Format (%s), "
                "verwerfe Inhalt und verwende Defaults",
                type(loaded).__name__,
            )
            self._data = dict(DEFAULTS)
            return

        for key, default_value in DEFAULTS.items():
            if key not in loaded:
                continue
            coerced = _coerce(loaded[key], default_value)
            if coerced is _COERCE_FAILED:
                log.warning(
                    "settings.json: Wert für %r (%r, Typ %s) ist nicht in Typ %s "
                    "castbar — verwende Default %r",
                    key, loaded[key], type(loaded[key]).__name__,
                    type(default_value).__name__, default_value,
                )
                continue
            self._data[key] = coerced
        # Unbekannte Keys aus loaded werden ignoriert (nicht in _data übernommen).

    def _save_to_disk(self):
        # Atomic write: temp file + replace, damit ein Crash mid-write
        # kein halb geschriebenes settings.json hinterlässt. Relevant, weil
        # der Update-Banner den Settings-Write aus einem Worker-Thread
        # via root.after auf den UI-Thread schiebt und parallel zum Settings-
        # Dialog schreiben kann.
        tmp = self.filepath + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
        try:
            os.replace(tmp, self.filepath)
        except OSError:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise

    def get(self, key):
        return self._data.get(key, DEFAULTS.get(key))

    def set(self, key, value):
        self.set_many({key: value})

    def set_many(self, updates):
        """Mehrere Werte setzen, einmal auf Platte schreiben.

        Leeres Dict ist No-op (kein Disk-Roundtrip).
        """
        if not updates:
            return
        self._data.update(updates)
        self._save_to_disk()
