# Codequality-Fixes Runde 1 — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fünf Codequality-Fixes (HTML-Escape im Bericht, `token.json`-Permissions, `Settings.set_many`, Logging+Excepthook, Settings-Schema-Validation) als ein PR mit fünf Commits ausliefern, ein Patch-Release `v1.9.2`.

**Architecture:** Defensive Fixes ohne neue User-Features. Jeder Commit ist für sich grün und unabhängig revertierbar; Reihenfolge so gewählt, dass das neue Logging-Modul zuerst landet (alle nachfolgenden Commits können dann `logging.exception(...)`-Aufrufe nutzen, falls nötig). Spec: `docs/superpowers/specs/2026-04-28-codequality-fixes-runde-1-design.md`.

**Tech Stack:** Python 3, Tkinter, pytest, stdlib `logging` mit `RotatingFileHandler`, stdlib `html.escape`. Keine neuen Dependencies.

---

## File Structure

**Neue Dateien:**
| Pfad | Zweck |
|---|---|
| `src/logging_setup.py` | Single-purpose: konfiguriert Root-Logger mit `RotatingFileHandler`, installiert `sys.excepthook` und `tk.Tk.report_callback_exception`. |
| `tests/test_logging_setup.py` | Tests für `setup_logging`: Logfile-Anlage, Idempotenz, Excepthook-Installation, Cleanup-Fixture. |

**Geänderte Dateien:**
| Pfad | Änderung |
|---|---|
| `src/main.py` | `setup_logging(base)` aufrufen, in `try/except` gewrappt. |
| `src/ui.py` | `logging.exception(...)` in den Worker-`except`-Blöcken (Token-Refresh, Update-Check). |
| `src/dialogs/send_dialog.py` | `logging.exception(...)` neben den bestehenden `messagebox.showerror`-Calls. |
| `src/dialogs/settings_dialog.py` | `logging.exception(...)` neben `messagebox.showerror` + `save_settings` auf `set_many` refactoren. |
| `src/settings.py` | `set_many(updates)` neu, `set` als Wrapper, `_load` mit Schema-Validation und Cast-Logik. |
| `src/report.py` | `_esc`/`_esc_multiline`-Helper, alle dynamischen User-Strings escapen. |
| `src/mail.py` | `_write_token`-Helper mit `os.chmod 0o600` (best-effort). |
| `tests/test_settings.py` | Tests für `set_many`, `set_many({})` no-op, Schema-Validation inkl. `caplog`. |
| `tests/test_report.py` | Neue Tests für Sonderzeichen-Escape und `\n → <br>`. Bestehende Tests bleiben grün. |
| `tests/test_mail.py` | Test, dass `token.json` nach Write `0o600` hat (skip auf Windows). |
| `src/version.py` | `1.9.1` → `1.9.2`. |
| `CHANGELOG.md` | Neuer Block `## v1.9.2` oben. |

---

## Chunk 1: Branch-Setup und Verification der Ausgangslage

### Task 0: Branch anlegen und Ausgangs-Tests laufen lassen

**Files:** keine — nur Git und Test-Run.

- [ ] **Step 0.1: Branch anlegen**

```bash
git checkout master
git pull origin master
git checkout -b fix/codequality-runde-1
```

Erwartung: neuer Branch, ausgehend von `master`.

- [ ] **Step 0.2: Bestehende Tests laufen lassen**

```bash
pytest -q
```

Erwartung: alles grün. Wenn nicht: vor diesem Plan klären, sonst Verwechslung mit eigenen Regressionen unmöglich.

- [ ] **Step 0.3: Notiere Test-Anzahl**

Schreibe die Zahl der pytest-collected Tests in das Plan-Tracking (für Vergleich am Ende). Aktuell laut Repo-Stand: 13 Test-Dateien, ca. 60–70 Tests.

---

## Chunk 2: Commit 1 — Logging-Setup + logging.exception in den Dialog-Modulen

### Task 1.1: `tests/test_logging_setup.py` anlegen mit failing tests

**Files:**
- Create: `tests/test_logging_setup.py`

- [ ] **Step 1.1.1: Test-File schreiben**

```python
# tests/test_logging_setup.py
import logging
import sys
import tkinter as tk
from logging.handlers import RotatingFileHandler

import pytest

from src.logging_setup import setup_logging, get_log_path, LOG_SUBDIR, LOGFILE_NAME


@pytest.fixture
def isolated_logging():
    """Fixture: Speichert + restored Root-Logger und Excepthooks pro Test."""
    root = logging.getLogger()
    saved_handlers = root.handlers[:]
    saved_level = root.level
    saved_excepthook = sys.excepthook
    saved_tk_hook = tk.Tk.report_callback_exception
    yield
    # Cleanup: Handler schließen, damit das Logfile nicht von Windows gelockt bleibt.
    for handler in root.handlers:
        if handler not in saved_handlers:
            handler.close()
    root.handlers = saved_handlers
    root.setLevel(saved_level)
    sys.excepthook = saved_excepthook
    tk.Tk.report_callback_exception = saved_tk_hook


def test_setup_logging_creates_subdir_and_logfile(tmp_path, isolated_logging):
    log_path = setup_logging(str(tmp_path))
    assert log_path == str(tmp_path / LOG_SUBDIR / LOGFILE_NAME)
    assert (tmp_path / LOG_SUBDIR).is_dir()


def test_setup_logging_writes_log_records(tmp_path, isolated_logging):
    log_path = setup_logging(str(tmp_path))
    logging.getLogger("test").info("hallo welt")
    # Force flush
    for h in logging.getLogger().handlers:
        h.flush()
    with open(log_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "hallo welt" in content
    assert "INFO" in content


def test_setup_logging_is_idempotent(tmp_path, isolated_logging):
    setup_logging(str(tmp_path))
    setup_logging(str(tmp_path))
    handlers = [
        h for h in logging.getLogger().handlers
        if isinstance(h, RotatingFileHandler)
    ]
    assert len(handlers) == 1


def test_setup_logging_installs_sys_excepthook(tmp_path, isolated_logging):
    original = sys.excepthook
    setup_logging(str(tmp_path))
    assert sys.excepthook is not original


def test_setup_logging_installs_tk_callback_excepthook(tmp_path, isolated_logging):
    original = tk.Tk.report_callback_exception
    setup_logging(str(tmp_path))
    assert tk.Tk.report_callback_exception is not original


def test_get_log_path_does_not_create_dir(tmp_path):
    path = get_log_path(str(tmp_path))
    assert path == str(tmp_path / LOG_SUBDIR / LOGFILE_NAME)
    # get_log_path darf das Verzeichnis NICHT anlegen — das ist Job von setup_logging.
    assert not (tmp_path / LOG_SUBDIR).exists()
```

- [ ] **Step 1.1.2: Test laufen lassen**

```bash
pytest tests/test_logging_setup.py -v
```

Erwartung: **FAIL** mit `ModuleNotFoundError: No module named 'src.logging_setup'`.

### Task 1.2: `src/logging_setup.py` implementieren

**Files:**
- Create: `src/logging_setup.py`

- [ ] **Step 1.2.1: Modul anlegen**

```python
# src/logging_setup.py
"""Logging-Setup mit Logfile + globalem Excepthook.

Single Purpose: einmal in main() aufrufen, danach landen alle uncaught
Exceptions und alle expliziten log.*-Calls im Logfile. Tkinter-Callback-
Crashes bekommen zusätzlich eine kurze Messagebox; der volle Traceback
geht ins Log.
"""

import logging
import os
import sys
import tkinter as tk
from logging.handlers import RotatingFileHandler


LOGFILE_NAME = "zeiterfassung.log"
LOG_SUBDIR = "logs"
MAX_BYTES = 1_000_000        # ~4 MB max. Logvolumen (1 MB × (1 + 3 Backups))
BACKUP_COUNT = 3
DEFAULT_LEVEL = logging.INFO  # Begründung: Start-Logs und Settings-Cast-Warnungen
                              # sollen sichtbar sein. Crash-Loops sind in einem
                              # Desktop-Tool selten und Rotation deckt das ab.


def get_log_path(base_path: str) -> str:
    """Pfad zum Logfile, ohne das Verzeichnis anzulegen."""
    return os.path.join(base_path, LOG_SUBDIR, LOGFILE_NAME)


def setup_logging(base_path: str) -> str:
    """Konfiguriert Root-Logger und Excepthooks. Returns Logfile-Pfad.

    Idempotent: ein zweiter Aufruf addiert keinen weiteren Handler.
    """
    log_dir = os.path.join(base_path, LOG_SUBDIR)
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, LOGFILE_NAME)

    root = logging.getLogger()
    root.setLevel(DEFAULT_LEVEL)
    if not any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        handler = RotatingFileHandler(
            log_path,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        ))
        root.addHandler(handler)

    _install_excepthooks()
    return log_path


def _install_excepthooks() -> None:
    log = logging.getLogger("zeiterfassung.uncaught")

    def _hook(exc_type, exc, tb):
        log.error("Uncaught exception", exc_info=(exc_type, exc, tb))

    sys.excepthook = _hook

    def _tk_hook(self, exc_type, exc, tb):
        log.error("Tk callback exception", exc_info=(exc_type, exc, tb))
        try:
            from tkinter import messagebox
            messagebox.showerror(
                "Unerwarteter Fehler",
                f"{exc_type.__name__}: {exc}\n\nDetails im Logfile.",
            )
        except Exception:
            log.exception(
                "Messagebox für uncaught Tk exception konnte nicht angezeigt werden",
            )

    tk.Tk.report_callback_exception = _tk_hook
```

- [ ] **Step 1.2.2: Tests laufen lassen**

```bash
pytest tests/test_logging_setup.py -v
```

Erwartung: alle 6 Tests **PASS**.

### Task 1.3: `src/main.py` an Logging-Setup hängen

**Files:**
- Modify: `src/main.py`

- [ ] **Step 1.3.1: `main.py` anpassen**

Vollständige neue Datei (ersetzt die bestehenden 26 Zeilen):

```python
# src/main.py
import logging
import os
import sys
import tkinter as tk

from src.logging_setup import setup_logging
from src.paths import get_base_path
from src.settings import Settings
from src.storage import Storage
from src.ui import App
from src.version import VERSION


def main():
    base = get_base_path()
    try:
        setup_logging(base)
        logging.getLogger(__name__).info("Zeiterfassung v%s gestartet", VERSION)
    except Exception:
        # Logging-Setup-Fehler (z.B. Permission-Denied auf logs/, exotisches FS):
        # die App soll trotzdem starten. Ohne Logfile haben wir kein
        # File-Logging, aber der globale Excepthook ist nicht installiert —
        # uncaught Exceptions schreiben auf stderr (im Repo-Mode sichtbar,
        # im Frozen-Mode mit --noconsole verschluckt). Akzeptabler Fallback.
        pass

    storage = Storage(os.path.join(base, "zeiterfassung.json"))
    settings = Settings(os.path.join(base, "settings.json"))

    root = tk.Tk()
    app = App(root, storage, settings, base_path=base)

    if "--minimized" in sys.argv:
        root.iconify()

    root.mainloop()


if __name__ == "__main__":
    main()
```

- [ ] **Step 1.3.2: App manuell starten**

```bash
python -m src.main
```

Erwartung: App startet wie vorher. Beim Schließen liegt `<base>/logs/zeiterfassung.log` mit einem `Zeiterfassung v1.9.1 gestartet`-Eintrag drin.

Im Repo-Modus ist `<base>` das Repo-Root. Logfile finden via:

```bash
ls logs/
cat logs/zeiterfassung.log
```

### Task 1.4: `logging.exception` in den Dialog-Modulen ergänzen

**Files:**
- Modify: `src/ui.py:107-110`, `src/ui.py:128-137`
- Modify: `src/dialogs/send_dialog.py:38-46`, `src/dialogs/send_dialog.py:186-193`
- Modify: `src/dialogs/settings_dialog.py:50-57`, `src/dialogs/settings_dialog.py:171-177`

- [ ] **Step 1.4.1: `src/ui.py` — Token-Refresh-Worker**

In `_proactive_token_refresh.worker` (`ui.py:94-111`), unter `except Exception as e:` (Zeile 107) **vor** dem `messagebox.showerror`-Call eine `logging.exception(...)`-Zeile einfügen.

Aktueller Code:

```python
            except Exception as e:
                err = f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}"
                self.root.after(0, lambda: messagebox.showerror(
                    "Token-Refresh fehlgeschlagen", err
                ))
```

Neu:

```python
            except Exception as e:
                logging.getLogger(__name__).exception("Token-Refresh fehlgeschlagen")
                err = f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}"
                self.root.after(0, lambda: messagebox.showerror(
                    "Token-Refresh fehlgeschlagen", err
                ))
```

Außerdem oben in `src/ui.py` einmalig `import logging` ergänzen (alphabetisch zwischen den anderen Stdlib-Imports).

- [ ] **Step 1.4.2: `src/ui.py` — Update-Check-Worker**

In `_proactive_update_check.worker` (`ui.py:128-137`), unter `except Exception:` (Zeile 134) ein `logging.getLogger(__name__).exception("Update-Check fehlgeschlagen")` ergänzen — der bestehende stille Fallback bleibt (kein Banner, kein User-Dialog), aber das Logfile bekommt die Spur. Begründung: silent für UI, aber der Maintainer soll im Logfile sehen, ob die Throttle-Logik immer scheitert.

Aktueller Code:

```python
            except Exception:
                # Pure Logik, robust gegen exotische Tags. Bei jedem Fehler:
                # nichts persistieren, nichts anzeigen — morgen nochmal probieren.
                return
```

Neu:

```python
            except Exception:
                # Pure Logik, robust gegen exotische Tags. Bei jedem Fehler:
                # nichts persistieren, nichts anzeigen — morgen nochmal probieren.
                # Trace landet im Logfile, falls jemand den Fehler diagnostizieren will.
                logging.getLogger(__name__).exception("Update-Check fehlgeschlagen")
                return
```

- [ ] **Step 1.4.3: `src/dialogs/send_dialog.py` — `open_and_close`**

In `show_missing_credentials_dialog.open_and_close` (`send_dialog.py:38-46`), unter `except Exception as e:` (Zeile 40) `logging.getLogger(__name__).exception(...)` ergänzen.

Aktueller Code:

```python
        except Exception as e:
            messagebox.showerror(
                "Ordner konnte nicht geöffnet werden",
                f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}",
                parent=dialog,
            )
            return
```

Neu:

```python
        except Exception as e:
            logging.getLogger(__name__).exception("Datenordner konnte nicht geöffnet werden")
            messagebox.showerror(
                "Ordner konnte nicht geöffnet werden",
                f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}",
                parent=dialog,
            )
            return
```

`import logging` oben in `send_dialog.py` ergänzen.

- [ ] **Step 1.4.4: `src/dialogs/send_dialog.py` — `do_send`**

In `do_send` (`send_dialog.py:188-193`), unter dem zweiten `except Exception as e:` `logging.getLogger(__name__).exception("Senden fehlgeschlagen")` ergänzen.

Aktueller Code:

```python
        except Exception as e:
            messagebox.showerror(
                "Senden fehlgeschlagen",
                f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}",
                parent=dialog,
            )
```

Neu:

```python
        except Exception as e:
            logging.getLogger(__name__).exception("Senden fehlgeschlagen")
            messagebox.showerror(
                "Senden fehlgeschlagen",
                f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}",
                parent=dialog,
            )
```

- [ ] **Step 1.4.5: `src/dialogs/settings_dialog.py` — `open_data_folder`**

In `open_data_folder` (`settings_dialog.py:50-57`), unter `except Exception as e:` `logging.getLogger(__name__).exception(...)` ergänzen.

Aktueller Code:

```python
        except Exception as e:
            messagebox.showerror(
                "Ordner konnte nicht geöffnet werden",
                f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}",
                parent=dialog,
            )
```

Neu:

```python
        except Exception as e:
            logging.getLogger(__name__).exception("Datenordner konnte nicht geöffnet werden")
            messagebox.showerror(
                "Ordner konnte nicht geöffnet werden",
                f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}",
                parent=dialog,
            )
```

`import logging` oben in `settings_dialog.py` ergänzen.

Hinweis: Der `Autostart-Fehler`-Catch (`settings_dialog.py:171-177`) bleibt **ohne** `logging.exception` — die Exception-Message vom `enable_autostart`/`disable_autostart` ist meistens trivial (`PermissionError`) und im Dialog-Kontext irrelevant fürs Logfile. Wenn das später gewünscht wird, ein-Zeilen-Add. Für YAGNI hier weglassen.

### Task 1.5: Tests laufen lassen und committen

- [ ] **Step 1.5.1: Alle Tests grün?**

```bash
pytest -q
```

Erwartung: alle bisherigen Tests + die neuen 6 in `test_logging_setup.py` **PASS**.

- [ ] **Step 1.5.2: App manuell starten und Sendepfad triggern**

Manueller Smoketest: App starten, Settings öffnen, schließen. Logfile unter `<base>/logs/zeiterfassung.log` sollte:

- Eine `Zeiterfassung v1.9.1 gestartet`-Zeile haben.

Optional (wenn ohne Internet): `_proactive_update_check` schreibt eine Exception-Trace ins Log — verifiziert, dass der Hook funktioniert.

- [ ] **Step 1.5.3: Commit 1**

```bash
git add src/logging_setup.py src/main.py src/ui.py src/dialogs/send_dialog.py src/dialogs/settings_dialog.py tests/test_logging_setup.py
git commit -m "$(cat <<'EOF'
feat: logfile + globaler excepthook

- Neues Modul src/logging_setup.py mit RotatingFileHandler
  (<base>/logs/zeiterfassung.log, 1 MB × 4 Backups, INFO-Level)
- sys.excepthook und tk.Tk.report_callback_exception werden global
  installiert — uncaught Exceptions im Mainloop landen im Logfile,
  Tk-Callback-Crashes zeigen zusätzlich eine kurze Messagebox
- src/main.py ruft setup_logging() defensiv (try/except), damit ein
  Permission-Denied auf logs/ nicht den App-Start verhindert
- logging.exception(...) in den bestehenden except-Blöcken in ui.py,
  send_dialog.py, settings_dialog.py — Tracebacks landen unabhängig
  von der Messagebox im Logfile

Spec: docs/superpowers/specs/2026-04-28-codequality-fixes-runde-1-design.md
EOF
)"
```

---

## Chunk 3: Commit 2 — `Settings.set_many` + Schema-Validation

### Task 2.1: Tests in `tests/test_settings.py` ergänzen (failing)

**Files:**
- Modify: `tests/test_settings.py`

- [ ] **Step 2.1.1: Neue Test-Funktionen anhängen**

Folgende Tests am Ende von `tests/test_settings.py` ergänzen (nach `test_dismissed_version_default`):

```python
import json  # ergänzen falls nicht oben vorhanden
from unittest.mock import patch


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
```

- [ ] **Step 2.1.2: Tests laufen lassen**

```bash
pytest tests/test_settings.py -v
```

Erwartung: die neuen Tests **FAIL** (set_many existiert nicht; Schema-Validation greift nicht).

### Task 2.2: `src/settings.py` mit `set_many` und Schema-Validation

**Files:**
- Modify: `src/settings.py`

- [ ] **Step 2.2.1: Vollständige Datei ersetzen**

```python
# src/settings.py
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
```

- [ ] **Step 2.2.2: Tests laufen lassen**

```bash
pytest tests/test_settings.py -v
```

Erwartung: alle Tests (alte + neue ~10) **PASS**.

### Task 2.3: `settings_dialog.py` auf `set_many` refactoren

**Files:**
- Modify: `src/dialogs/settings_dialog.py:154-201`

- [ ] **Step 2.3.1: `save_settings` ersetzen**

Bestehende Funktion (`settings_dialog.py:154-201`) komplett ersetzen durch:

```python
    def save_settings():
        ok, msg = validate_entry(start_var.get(), end_var.get())
        if not ok:
            messagebox.showerror("Standard-Arbeitszeit ungültig", msg, parent=dialog)
            return

        new_autostart = autostart_var.get()
        old_autostart = settings.get("autostart")

        # Autostart-Toggle muss vor dem Settings-Write passieren, weil
        # er failen kann und dann nichts persistiert werden soll.
        if new_autostart != old_autostart:
            try:
                if new_autostart:
                    target, arguments = resolve_autostart_target(base_path)
                    enable_autostart(target, arguments)
                else:
                    disable_autostart()
            except Exception as e:
                messagebox.showerror(
                    "Autostart-Fehler",
                    f"Autostart konnte nicht geändert werden:\n{e}",
                    parent=dialog,
                )
                return

        rate_str = rate_var.get().strip()
        try:
            hourly_rate = float(rate_str) if rate_str else 0.0
        except ValueError:
            hourly_rate = 0.0

        selected_label = state_var.get()
        selected_code = next(
            (code for code, lbl in STATES if lbl == selected_label),
            "",
        )

        settings.set_many({
            "autostart": new_autostart,
            "email": email_var.get(),
            "default_start": start_var.get(),
            "default_end": end_var.get(),
            "default_pause": int(pause_var.get()),
            "recipient": recipient_var.get(),
            "name": name_var.get(),
            "mail_subject": subject_var.get(),
            "mail_greeting": greeting_var.get(),
            "mail_content": content_text.get("1.0", "end-1c"),
            "mail_closing": closing_text.get("1.0", "end-1c"),
            "hourly_rate": hourly_rate,
            "state": selected_code,
        })
        on_change()
        dialog.destroy()
```

- [ ] **Step 2.3.2: Manueller Smoketest**

```bash
python -m src.main
```

App starten, Einstellungen öffnen, Werte ändern, speichern. Verifizieren:

- Werte werden korrekt persistiert (App neu starten, Werte sind noch da).
- `settings.json` enthält alle 13 Keys einmal, kein doppelter Write sichtbar (kein Test, nur Sanity-Check).

- [ ] **Step 2.3.3: Tests laufen lassen**

```bash
pytest -q
```

Erwartung: alle grün.

- [ ] **Step 2.3.4: Commit 2**

```bash
git add src/settings.py src/dialogs/settings_dialog.py tests/test_settings.py
git commit -m "$(cat <<'EOF'
feat(settings): set_many batch-API + schema-validation

- Settings.set_many(updates) als Batch-API; Settings.set ist nun ein
  Wrapper, der 1-Element-Dicts an set_many delegiert
- save_settings() im Settings-Dialog macht statt 12 separater
  set()-Calls einen einzigen set_many-Call → ein Disk-Write statt 12,
  reduziert Lost-Update-Risiko mit dem Update-Banner-Worker
- Settings._load validiert Werte gegen DEFAULTS und castet, wo
  möglich (String→int, int→float). Bool-Strenge: weder "true" noch 1
  werden als True akzeptiert. Cast-Failures landen mit Warnung im
  Logfile, der Default bleibt
- Unbekannte Keys aus settings.json werden ignoriert
- set_many({}) ist No-op (kein Disk-Roundtrip)

Spec: docs/superpowers/specs/2026-04-28-codequality-fixes-runde-1-design.md
EOF
)"
```

---

## Chunk 4: Commit 3 — HTML-Escaping in Bericht/PDF

### Task 3.1: Test-Erweiterungen in `tests/test_report.py` (failing)

**Files:**
- Modify: `tests/test_report.py`

- [ ] **Step 3.1.1: Neue Tests anhängen**

Am Ende von `tests/test_report.py` ergänzen (nach `test_iso_week_across_year_boundary`):

```python
from unittest.mock import patch, MagicMock


# --- HTML-Escaping ---

def test_greeting_with_ampersand_is_escaped():
    entries = {"2026-03-23": {"start": "08:00", "end": "16:00", "pause": 0}}
    html, _ = generate_report(
        datetime.date(2026, 3, 1), datetime.date(2026, 3, 31), entries,
        greeting="Mayer & Söhne,",
    )
    assert "Mayer &amp; Söhne," in html
    assert "Mayer & Söhne" not in html


def test_greeting_with_html_tag_is_escaped():
    entries = {"2026-03-23": {"start": "08:00", "end": "16:00", "pause": 0}}
    html, _ = generate_report(
        datetime.date(2026, 3, 1), datetime.date(2026, 3, 31), entries,
        greeting="<script>alert(1)</script>",
    )
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>alert(1)</script>" not in html


def test_content_newline_becomes_br():
    entries = {"2026-03-23": {"start": "08:00", "end": "16:00", "pause": 0}}
    html, _ = generate_report(
        datetime.date(2026, 3, 1), datetime.date(2026, 3, 31), entries,
        content="Zeile1\nZeile2",
    )
    assert "Zeile1<br>Zeile2" in html


def test_closing_with_lt_and_newline_escaped_with_br():
    entries = {"2026-03-23": {"start": "08:00", "end": "16:00", "pause": 0}}
    html, _ = generate_report(
        datetime.date(2026, 3, 1), datetime.date(2026, 3, 31), entries,
        closing="A < B\nFreundlich",
    )
    # `<` muss escaped sein, `<br>` darf NICHT escaped sein
    assert "A &lt; B<br>Freundlich" in html
    assert "&lt;br&gt;" not in html


def test_placeholder_zeitraum_replaced_after_escape():
    entries = {"2026-03-23": {"start": "08:00", "end": "16:00", "pause": 0}}
    html, _ = generate_report(
        datetime.date(2026, 3, 1), datetime.date(2026, 3, 31), entries,
        content="Zeitraum: {zeitraum}",
    )
    # Das Datum enthält keine HTML-Specials; Replacement findet statt.
    assert "Zeitraum: 01.03.2026 – 31.03.2026" in html


def test_pdf_name_is_escaped():
    """generate_pdf escaped name vor der HTML-Generierung. xhtml2pdf wird
    gemockt, damit der Test ohne installierte Lib läuft (CI-kompatibel)."""
    from src import report as report_mod
    entries = {"2026-03-23": {"start": "08:00", "end": "16:00", "pause": 0}}

    captured_html = {}

    class FakePisa:
        @staticmethod
        def CreatePDF(html_str, dest):
            captured_html["html"] = html_str
            return MagicMock(err=0)

    fake_xhtml2pdf = MagicMock()
    fake_xhtml2pdf.pisa = FakePisa

    with patch.dict("sys.modules", {"xhtml2pdf": fake_xhtml2pdf}):
        report_mod.generate_pdf(
            datetime.date(2026, 3, 1), datetime.date(2026, 3, 31), entries,
            name="Müller & Co",
        )

    assert "Müller &amp; Co" in captured_html["html"]
    assert "Müller & Co" not in captured_html["html"]
```

- [ ] **Step 3.1.2: Tests laufen lassen**

```bash
pytest tests/test_report.py -v
```

Erwartung: die neuen 6 Tests **FAIL**, alte 14 Tests **PASS**.

### Task 3.2: `src/report.py` mit Escape-Logik

**Files:**
- Modify: `src/report.py`

- [ ] **Step 3.2.1: Helper hinzufügen + `_apply_placeholders`/`generate_report`/`generate_pdf` anpassen**

Folgende Änderungen in `src/report.py`:

1. **Import** an den Anfang ergänzen:
   ```python
   import html
   ```

2. **Helper** unterhalb der Imports und über `COLUMN_LABELS` einfügen:
   ```python
   def _esc(text):
       return html.escape(text or "", quote=True)


   def _esc_multiline(text):
       return _esc(text).replace("\n", "<br>")
   ```

3. **`_apply_placeholders` anpassen** — Werte selbst escapen (defensive — Datum/Float sind sicher, aber konsistent):
   ```python
   def _apply_placeholders(text, label, total):
       # text ist bereits escaped; label und total sind strukturell sicher
       # (Datum + Float), werden aber für Konsistenz ebenfalls escaped.
       return text.replace("{zeitraum}", _esc(label)).replace("{gesamt}", _esc(f"{total}h"))
   ```

4. **`generate_report` anpassen** — Greeting/Content/Closing escapen vor Placeholder:
   ```python
   def generate_report(date_from, date_to, all_entries, greeting="", content="", closing=""):
       """Generate an HTML email report with greeting, content, table, and closing.

       Returns (html, total) tuple, or (None, 0) if no entries.
       """
       range_entries = _filter_entries(date_from, date_to, all_entries)
       if not range_entries:
           return None, 0

       label = f"{date_from.strftime('%d.%m.%Y')} – {date_to.strftime('%d.%m.%Y')}"
       groups = _group_by_week(range_entries)
       table, total = _build_table(groups, HTML_STYLE)

       greeting_filled = _apply_placeholders(_esc_multiline(greeting), label, total)
       content_filled = _apply_placeholders(_esc_multiline(content), label, total)
       closing_filled = _apply_placeholders(_esc_multiline(closing), label, total)

       text_style = "color:#cbd5e1;font-size:14px;line-height:1.6;margin:0 0 16px 0;"
       greeting_html = f'<p style="{text_style}">{greeting_filled}</p>' if greeting_filled else ""
       content_html = f'<p style="{text_style}">{content_filled}</p>' if content_filled else ""
       closing_html = f'<p style="{text_style}margin-top:24px;white-space:pre-line;">{closing_filled}</p>' if closing_filled else ""

       html_out = f"""<html><head><meta charset="utf-8"><meta http-equiv="Content-Type" content="text/html; charset=utf-8"></head>
   <body style="margin:0;padding:0;background:#0f172a;font-family:'Segoe UI',Arial,sans-serif;">
   <div style="max-width:640px;margin:0 auto;padding:32px 24px;">
   {greeting_html}
   {content_html}
   {table}
   {closing_html}
   </div>
   </body></html>"""

       return html_out, total
   ```
   **Wichtig:** lokale Variable umbenennen von `html` auf `html_out`, weil `html` jetzt das importierte Modul shadowed wäre.

5. **`generate_pdf` anpassen**:
   ```python
   def generate_pdf(date_from, date_to, all_entries, name=""):
       """Generate a PDF of the time tracking table. Returns PDF bytes, or None if no entries."""
       from xhtml2pdf import pisa

       range_entries = _filter_entries(date_from, date_to, all_entries)
       if not range_entries:
           return None

       label = f"{date_from.strftime('%d.%m.%Y')} – {date_to.strftime('%d.%m.%Y')}"
       groups = _group_by_week(range_entries)
       table, _ = _build_table(groups, PDF_STYLE)

       name_html = (
           f"<p style='color:#111827;font-size:13px;margin:0 0 2px 0;font-weight:600;'>{_esc(name)}</p>"
           if name else ""
       )

       pdf_html = f"""<html><head><meta charset="utf-8"></head>
   <body style="margin:0;padding:20px;font-family:Arial,sans-serif;font-size:12px;color:#111827;">
   <h2 style="font-size:18px;margin:0 0 4px 0;color:#111827;">Zeiterfassung</h2>
   {name_html}
   <p style="color:#4b5563;font-size:12px;margin:0 0 16px 0;">{_esc(label)}</p>
   {table}
   </body></html>"""

       buffer = io.BytesIO()
       pisa.CreatePDF(pdf_html, dest=buffer)
       return buffer.getvalue()
   ```

6. **Code-Kommentar für unescaped Storage-Werte** — über `_week_block` einfügen (vor der Funktionsdefinition):
   ```python
   # _week_block und _build_table rendern Werte aus dem Storage (entry["start"],
   # entry["end"], weekday, day_fmt, iso_week). Diese sind durch validate_entry
   # bzw. datetime-Formatter strukturell auf [0-9:.-] beschränkt — kein Escape
   # nötig. Wenn diese Quelle sich mal ändert (z.B. freie Eingabe), Escape ergänzen.
   ```

7. **`mail_subject` bleibt unverändert** — `src/dialogs/send_dialog.py:172-176` ruft `.replace(...)` auf dem Subject auf und übergibt ihn an `Header(subject, "utf-8")`. Subject ist kein HTML, sondern ein RFC-822-Mail-Header; `Header()` macht RFC-2047-Encoding. Kein HTML-Escape nötig, nicht in diesem Commit angefasst. Spec-Begründung siehe Abschnitt „mail_subject (`src/dialogs/send_dialog.py`)" im Design-Dokument.

- [ ] **Step 3.2.2: Tests laufen lassen**

```bash
pytest tests/test_report.py -v
```

Erwartung: alle Tests **PASS** (20 Tests: 14 alte + 6 neue).

### Task 3.3: Manueller Sanity-Check + Commit

- [ ] **Step 3.3.1: App starten, Einstellungen mit Sonderzeichen befüllen, Mail (an sich selbst) senden**

```bash
python -m src.main
```

In Settings: `mail_greeting = "Hallo & Welt,"`, speichern. Eine Test-Mail an die eigene Adresse senden. In der empfangenen Mail muss das `&` korrekt erscheinen (nicht `&amp;` und auch nicht zerschossenes Rendering).

Wenn keine credentials.json zur Hand: diesen Schritt überspringen, die Tests decken den HTML-Output ab.

- [ ] **Step 3.3.2: Commit 3**

```bash
git add src/report.py tests/test_report.py
git commit -m "$(cat <<'EOF'
fix(report): html-escape user-strings in mail report and pdf

Mail-Templates (greeting, content, closing) und der Name im PDF werden
vor der HTML-Interpolation durch html.escape() geschickt. Zeilen-
umbrüche (\n) werden anschließend zu <br> konvertiert.

Behavior-Change: wer bisher bewusst <b>, <a> oder andere HTML-Tags in
seinen Mail-Templates verwendet hat, sieht diese jetzt als Klartext.
Zeilenumbrüche funktionieren weiterhin.

Werte aus dem Storage (entry-Zeiten, Wochentag, ISO-Woche) sind
strukturell sicher und werden nicht escaped — Code-Kommentar erklärt
warum.

Spec: docs/superpowers/specs/2026-04-28-codequality-fixes-runde-1-design.md
EOF
)"
```

---

## Chunk 5: Commit 4 — `token.json`-Permissions

### Task 4.1: Test in `tests/test_mail.py` (failing)

**Files:**
- Modify: `tests/test_mail.py`

- [ ] **Step 4.1.1: Test-Funktion anhängen**

Am Ende von `tests/test_mail.py` ergänzen:

```python
import platform  # falls nicht oben vorhanden
import stat


@pytest.mark.skipif(
    platform.system() == "Windows",
    reason="Windows hat kein POSIX-Permission-Modell",
)
def test_refresh_writes_token_with_0600_permissions(tmp_path):
    """Nach erfolgreichem Refresh hat token.json Mode 0o600."""
    path = str(tmp_path / "token.json")
    open(path, "w").close()

    fake_creds = MagicMock()
    fake_creds.valid = False
    fake_creds.expired = True
    fake_creds.refresh_token = "rt"
    fake_creds.to_json.return_value = '{"fresh": true}'

    with patch("google.oauth2.credentials.Credentials.from_authorized_user_file",
               return_value=fake_creds):
        refresh_token_if_needed(path)

    mode = os.stat(path).st_mode & 0o777
    assert mode == 0o600, f"Erwartete 0o600, ist {oct(mode)}"
```

- [ ] **Step 4.1.2: Tests laufen lassen**

Auf Windows:

```bash
pytest tests/test_mail.py -v
```

Erwartung: der neue Test wird **SKIPPED** auf Windows. Keine Failures.

Auf Linux/macOS:

```bash
pytest tests/test_mail.py -v
```

Erwartung: der neue Test **FAILT** (chmod wird noch nicht aufgerufen, Default-Mode ist meist `0o644`).

(Für die Praxis: Wenn nur Windows zur Verfügung steht, dieser Test wird im CI auf Linux/macOS scharf — `release.yml` baut auf allen drei. Der Test-CI ist Linux: `test.yml`. Dort wird der Test scharf laufen.)

### Task 4.2: `src/mail.py` mit `_write_token`

**Files:**
- Modify: `src/mail.py:32-33, 96-97`

- [ ] **Step 4.2.1: Helper anlegen + Aufrufer anpassen**

Folgende Änderungen in `src/mail.py`:

1. **Imports oben** ergänzen:
   ```python
   import stat
   ```

2. **Neue Helper-Funktion** über `_refresh_and_persist` einfügen:
   ```python
   def _write_token(creds, token_path):
       """Persistiere Credentials und setze restriktive Permissions (Unix only).

       Auf Windows bleibt das chmod ein No-op — POSIX-Permissions gibt es
       dort nicht. `try/except OSError` deckt zusätzlich exotische Filesystems
       (sshfs, FAT32 auf USB-Stick) ab, wo chmod fehlschlagen kann.
       """
       with open(token_path, "w") as f:
           f.write(creds.to_json())
       try:
           os.chmod(token_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
       except OSError:
           pass
   ```

3. **`_refresh_and_persist` anpassen** — den `with open(...) as f: f.write(creds.to_json())`-Block ersetzen durch `_write_token(creds, token_path)`:
   ```python
   def _refresh_and_persist(creds, token_path):
       """Refresh credentials and write them back. Translates Google exceptions."""
       from google.auth.exceptions import RefreshError, TransportError
       from google.auth.transport.requests import Request

       try:
           creds.refresh(Request())
       except RefreshError as e:
           raise TokenAuthError(str(e)) from e
       except TransportError as e:
           raise TokenNetworkError(str(e)) from e

       _write_token(creds, token_path)
   ```

4. **`get_gmail_service` anpassen** — die Stelle nach `flow.run_local_server(...)` (`mail.py:96-97`):
   ```python
       if not creds or not creds.valid:
           if not os.path.exists(credentials_path):
               raise FileNotFoundError(
                   f"credentials.json nicht gefunden unter:\n{credentials_path}\n\n"
                   "Bitte erstelle ein Google Cloud Projekt mit Gmail API "
                   "und lade die OAuth2 Client-ID dort ab."
               )
           flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
           creds = flow.run_local_server(port=0)
           _write_token(creds, token_path)
   ```

- [ ] **Step 4.2.2: Tests laufen lassen**

```bash
pytest tests/test_mail.py -v
```

Erwartung: Auf Windows skipt der neue Test, alle anderen **PASS**. Auf Linux/macOS: alle Tests **PASS**.

### Task 4.3: Commit 4

- [ ] **Step 4.3.1: Commit**

```bash
git add src/mail.py tests/test_mail.py
git commit -m "$(cat <<'EOF'
fix(mail): chmod 0600 on token.json (unix-only, best-effort)

Der Refresh-Token (Gmail-Send-Scope) wird auf macOS/Linux mit
0o600-Permissions geschrieben — vorher 0o644 (typisch via umask).
Auf Multi-User-Systemen ist die Datei jetzt nicht mehr für andere
User lesbar.

Auf Windows ist os.chmod ein No-op (kein POSIX-Permission-Modell);
auf exotischen Filesystems (sshfs etc.) fängt try/except OSError
einen Fehlschlag still ab — Token-Schreibvorgang darf nicht durch
chmod-Fehler scheitern.

Spec: docs/superpowers/specs/2026-04-28-codequality-fixes-runde-1-design.md
EOF
)"
```

---

## Chunk 6: Commit 5 — Versions-Bump und CHANGELOG

### Task 5.1: `src/version.py` und `CHANGELOG.md`

**Files:**
- Modify: `src/version.py`
- Modify: `CHANGELOG.md`

- [ ] **Step 5.1.1: `src/version.py` anpassen**

Aktueller Inhalt: `VERSION = "1.9.1"`. Neuer Inhalt:

```python
VERSION = "1.9.2"
```

- [ ] **Step 5.1.2: CHANGELOG.md aktualisieren**

In `CHANGELOG.md` direkt unter der ersten Zeile (`# Changelog`) und vor `## v1.9.1` folgenden Block einfügen:

```markdown
## v1.9.2
- Mail-Templates (Anrede, Inhalt, Gruß, Name) und der Bericht escapen Sonderzeichen jetzt korrekt — `&`, `<`, `>` werden im Mail-HTML und PDF nicht mehr roh ausgegeben. **Behavior-Change:** wer bisher bewusst HTML-Tags wie `<b>` oder `<br>` in den Mail-Templates verwendet hat, sieht diese jetzt als Klartext. Zeilenumbrüche im Inhalt/Gruß werden weiterhin korrekt umgebrochen
- `token.json` wird auf macOS/Linux mit `0600`-Permissions geschrieben — der Refresh-Token mit Gmail-Send-Scope ist auf Multi-User-Systemen nicht mehr für andere User lesbar (Windows ignoriert Unix-Permissions)
- Settings-Speichern macht statt 12 separater Disk-Roundtrips nur noch einen einzigen — minimiert das Risiko verlorener Updates, wenn der Update-Banner-Worker parallel zum Settings-Dialog schreibt
- Neues Logfile unter `<Datenordner>/logs/zeiterfassung.log` (rotierend, max. 4 MB Gesamtvolumen). App-Start, uncaught Exceptions im Tk-Mainloop und alle Sendepfad-Fehler landen dort — bei `--noconsole`-Builds (Windows-Release) gab es bisher keine Spur von Crashes
- `settings.json` wird beim Laden gegen die erwarteten Typen validiert. Ein manuell verändertes Feld mit falschem Typ (z.B. String statt Int) lässt die App nicht mehr abstürzen, sondern fällt auf den Default zurück und schreibt eine Warnung ins Logfile
```

- [ ] **Step 5.1.3: Tests final laufen lassen**

```bash
pytest -q
```

Erwartung: alle Tests grün. Anzahl ≥ Schritt 0.3-Notiz + ~17 neue Tests (6 Logging + ~10 Settings + 6 Report + 1 Mail = 23, evtl. ein paar weniger je nachdem wie genau).

- [ ] **Step 5.1.4: Commit 5**

```bash
git add src/version.py CHANGELOG.md
git commit -m "$(cat <<'EOF'
release: v1.9.2 (codequality runde 1)

Bündel-Patch-Release mit fünf defensiven Fixes:
- HTML-Escape im Mail-Bericht und PDF
- token.json mit 0600-Permissions (unix-only)
- Settings.set_many als Batch-API
- Logfile + globaler Excepthook
- Settings-Schema-Validation

Spec: docs/superpowers/specs/2026-04-28-codequality-fixes-runde-1-design.md
Plan: docs/superpowers/plans/2026-04-28-codequality-fixes-runde-1.md
EOF
)"
```

---

## Chunk 7: PR öffnen

### Task 6.1: Push und PR erstellen

- [ ] **Step 6.1.1: Branch pushen**

```bash
git push -u origin fix/codequality-runde-1
```

- [ ] **Step 6.1.2: PR via gh CLI öffnen**

```bash
gh pr create --label "release:patch" --title "Codequality-Fixes Runde 1 (v1.9.2)" --body "$(cat <<'EOF'
## Summary
Fünf defensive Fixes als ein Bündel-PR, ausgeliefert als Patch-Release `v1.9.2`.

- **HTML-Escape** im Mail-Bericht und PDF (`src/report.py`) — Sonderzeichen in Mail-Templates werden korrekt encoded. Behavior-Change: bewusst genutztes HTML in Templates erscheint nun als Klartext.
- **`token.json`-Permissions** auf `0600` (Unix only) — Refresh-Token nicht mehr für andere User lesbar.
- **`Settings.set_many`** als Batch-API — Settings-Dialog macht jetzt einen statt 12 Disk-Writes.
- **Logfile + globaler Excepthook** unter `<Datenordner>/logs/zeiterfassung.log` (rotierend, ~4 MB max). uncaught Exceptions werden geloggt, bei `--noconsole`-Builds gab es bisher keine Spur.
- **Settings-Schema-Validation** in `Settings._load` — kaputte/migrierte `settings.json` lässt App nicht mehr crashen, sondern fällt auf Defaults zurück und warnt im Logfile.

Spec: `docs/superpowers/specs/2026-04-28-codequality-fixes-runde-1-design.md`
Plan: `docs/superpowers/plans/2026-04-28-codequality-fixes-runde-1.md`

## Test plan
- [ ] `pytest -q` grün (lokal verifiziert)
- [ ] CI-Workflow `test.yml` grün
- [ ] Manueller Smoketest: App starten, Settings ändern + speichern, Mail mit `&` im Greeting senden, prüfen dass Mail korrekt rendert
- [ ] Logfile prüfen: `<base>/logs/zeiterfassung.log` enthält Start-Eintrag
- [ ] Auf macOS/Linux: `stat` auf `token.json` zeigt `0600` nach erstem Refresh

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 6.1.3: PR-URL notieren**

PR-URL aus der `gh`-Ausgabe an den User reporten. Nach dem Merge erzeugt `release.yml` automatisch das `v1.9.2`-Release.

---

## Verification matrix

Nach allen Tasks vor dem Mergen:

| Check | Erwartung |
|---|---|
| `pytest -q` lokal | alles grün |
| CI `test.yml` (auf PR) | alles grün |
| App startet (`python -m src.main`) | wie vorher, keine Regressionen |
| `<base>/logs/zeiterfassung.log` existiert nach Start | mit `Zeiterfassung v1.9.2 gestartet` |
| Settings speichern | UI weiterhin funktional, ein einzelner JSON-Write sichtbar |
| Settings öffnen mit `{"default_pause": "abc"}` in der JSON | App startet, `default_pause` zurück auf 30, Logfile-Warnung |
| Mail-Greeting mit `&` rendert korrekt in der Email | (manuell, optional) |
| `token.json` auf macOS nach Refresh | Mode `0600` (`stat` prüfen) |

## Risk register

| Risiko | Mitigation |
|---|---|
| Manueller Smoketest in Step 1.3.2 / 2.3.2 / 3.3.1 wird im Auto-Mode übersprungen | Spätestens vor PR-Merge nachholen — App-Start und Settings-Save sind die kritischsten Pfade |
| `xhtml2pdf`-Mock-Test (Step 3.1.1, `test_pdf_name_is_escaped`) zerschießt andere Tests durch `sys.modules`-Manipulation | `patch.dict(..., {...})` ist Context-bound; nach Block ist `sys.modules` restored. Aber: `xhtml2pdf` ist in CI nicht installiert, daher gar nicht in `sys.modules` — Mock setzt es während des Tests ein, danach wird es wieder entfernt. Sollte sicher sein |
| `chmod`-Test failt auf Linux-CI, weil `os.chmod` Erfolg meldet, aber auf manchen Mounts (tmpfs?) keine Wirkung hat | Unwahrscheinlich auf GitHub-runner-Standard-Filesystems. Bei Failure: Test als `xfail` markieren oder Mount-Type prüfen |
| Branch-Setup (Step 0.1) übersieht uncommitted Changes | `git status` vor `git checkout -b` prüfen; falls dirty, klären (eventuell Stash) |
