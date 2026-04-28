# Codequality-Fixes Runde 1 — Design Spec

## Overview

Bündel-PR mit fünf unabhängigen, aber thematisch verwandten Verbesserungen aus einem Codequality-Review. Jeder Fix landet als eigener Commit im selben PR; Auslieferung als ein Patch-Release. Keine User-facing Feature-Änderungen — alles defensiv, sicherheits- oder robustheitsfokussiert.

Die fünf Punkte:

1. **HTML-Escaping** für alle dynamischen Werte in Mail-Bericht und PDF.
2. **`token.json`-Permissions** auf `0600` setzen (Unix).
3. **`Settings.set_many(...)`** als Batch-API, ersetzt 12 einzelne Disk-Roundtrips beim Settings-Speichern.
4. **Logging + globaler Excepthook** mit Logfile in `<base>/logs/zeiterfassung.log` (rotierend).
5. **Schema-Validation** in `Settings._load`: Type-Casts pro Key gegen `DEFAULTS`, Fallback auf Default bei Cast-Fehler.

## Scope decisions

| # | Decision | Consequence |
|---|----------|-------------|
| 1 | Ein PR, fünf Commits, ein Patch-Release | Schnelles Roll-out, atomares Review |
| 2 | HTML-Escape **alles** (Variante A aus Brainstorming) — Templates und Werte werden vor der Inline-Interpolation escaped, `\n → <br>` als zweiter Pass | Schließt Mojibake-/Injection-Klasse vollständig; bewusstes HTML in Templates ist nicht (mehr) möglich, dafür sind die Settings-Felder reine Text-Widgets |
| 3 | `set_many(dict)` als einzige Batch-API, kein Context-Manager | YAGNI; Settings-Dialog ist die einzige Stelle mit mehreren Writes |
| 4 | Kein Threading-Lock auf `Settings._save_to_disk` | Lost-Update-Risiko wird durch `set_many` drastisch verkleinert; weiterführende Locks erst wenn ein konkreter Bug auftaucht |
| 5 | Logfile in `<base>/logs/zeiterfassung.log` mit `RotatingFileHandler`, 1 MB, 3 Backups | Subdir hält das Datenverzeichnis aufgeräumt; Rotation verhindert Disk-Overflow bei langer Nutzung |
| 6 | Globaler Excepthook + `Tk.report_callback_exception`-Override loggen Tracebacks und zeigen kurze Messagebox | Bei `--noconsole` keine Spur sonst; UI-Crashes werden sichtbar, ohne den User mit Tracebacks zu erschlagen |
| 7 | Bestehende `messagebox.showerror(...)`-Stellen mit `traceback.format_exc()` behalten ihren Fehlertext, aber zusätzlich wandert der Traceback ins Logfile | Logfile als Single Source of Truth für Debugging; Messagebox bleibt aus historischen Gründen unverändert (siehe CLAUDE.md "UI-Fehler sichtbar machen") |
| 8 | Schema-Validation leitet Casts aus `type(DEFAULTS[key])` ab | DRY; `DEFAULTS` ist die einzige Stelle, an der Typen deklariert werden |
| 9 | Unbekannte Keys aus `settings.json` werden ignoriert (nicht in `_data` übernommen) | Verhindert Bloat durch alte/fremde Felder; Default-Schreibung beim nächsten Save überschreibt sie nicht — sie sind dann verloren, was OK ist |
| 10 | Fehlerhafte Casts werden ins Logfile geschrieben und still durch Default ersetzt | Variante A aus Brainstorming — keine Messagebox, kein Backup-File; Logfile reicht für Diagnose |
| 11 | `token.json`-Chmod nur auf nicht-Windows-Plattformen (no-op via try/except) | Windows hat kein POSIX-Permission-Modell; `os.chmod` ist dort funktional bedeutungslos |
| 12 | Versions-Bump auf `1.9.2`, CHANGELOG-Eintrag, `release:patch`-Label | Keine User-facing Feature-Änderungen, eine kleine Behavior-Änderung (HTML in Mail-Templates wird escaped) — wird im CHANGELOG explizit erwähnt |

## 1) HTML-Escaping in Bericht und PDF

### Problem

`src/report.py` interpoliert `greeting`, `content`, `closing`, `name` und Platzhalterwerte (`label`, `total`) **unescaped** in HTML-Strings. Beispiel `report.py:175`:

```python
greeting_html = f'<p style="{text_style}">{greeting_filled}</p>' if greeting_filled else ""
```

Ein `&`, `<`, `>` im Namen oder Gruß zerschießt das Rendering. `mail_subject` in `send_dialog.py:172–176` wird ebenfalls unescaped in den Mail-Header geschrieben — hier weniger kritisch, weil `Header(...)` auf RFC-Header-Encoding setzt, aber konsistent absichern.

### Lösung

**Single Choke-Point** in `src/report.py`: Alle Werte, die ins HTML gehen, laufen vorher durch `html.escape(..., quote=True)`. Reihenfolge ist wichtig:

1. **Erst escapen**, dann Platzhalter ersetzen — die Platzhalterwerte (`{zeitraum}`, `{gesamt}`) sind selbst sicher (Datum + Float), aber wir escapen sie trotzdem, damit `_apply_placeholders` keine Sonderbehandlung braucht.
2. **`\n → <br>` als zweiter Pass** — nach dem Escaping, damit `<br>` nicht wieder zu `&lt;br&gt;` wird.

Konkret:

```python
import html

def _esc(text: str) -> str:
    return html.escape(text or "", quote=True)

def _esc_multiline(text: str) -> str:
    return _esc(text).replace("\n", "<br>")

def _apply_placeholders(text, label, total):
    # text ist bereits escaped; label und total sind sicher (Datum + Float)
    return text.replace("{zeitraum}", _esc(label)).replace("{gesamt}", _esc(f"{total}h"))
```

In `generate_report`:

```python
greeting_filled = _apply_placeholders(_esc_multiline(greeting), label, total)
content_filled  = _apply_placeholders(_esc_multiline(content),  label, total)
closing_filled  = _apply_placeholders(_esc_multiline(closing),  label, total)
```

In `generate_pdf` analog für `name`:

```python
name_html = (
    f"<p style='...'>{_esc(name)}</p>"
    if name else ""
)
```

`_week_block` und `_build_table` rendern Werte aus dem Storage (`entry["start"]`, `entry["end"]`, `weekday`, `day_fmt`, `iso_week`). Diese sind durch `validate_entry` bzw. `datetime`-Formatter strukturell auf `[0-9:.-]` beschränkt und brauchen kein Escape. Im Code wird ein einzeiliger Kommentar an der entsprechenden Stelle hinterlegt, damit ein zukünftiger Reviewer nicht denkt, das sei vergessen worden.

### `mail_subject` (`src/dialogs/send_dialog.py`)

`mail_subject` enthält ebenfalls Platzhalter (`{zeitraum}`, `{gesamt}`) und wird in `send_dialog.py:172–176` mit `.replace(...)` befüllt. **Kein HTML-Escape nötig**, weil:

1. Subject ist kein HTML, sondern ein RFC-822-Mail-Header.
2. `Header(subject, "utf-8")` macht RFC-2047-Encoding (Quoted-Printable / Base64), das Sonderzeichen sicher kodiert.

Hier bleibt der Code unverändert — die Spec erwähnt das explizit, damit es nicht später als "vergessen" erscheint.

### Behavior-Change (User-sichtbar)

Vor diesem Fix konnte ein Power-User HTML-Tags (`<b>`, `<br>`, `<a href="...">`) in den Mail-Templates verwenden. Nach dem Fix werden diese als Klartext angezeigt. Das gilt für `mail_greeting`, `mail_content`, `mail_closing` und `name`. Der CHANGELOG-Eintrag erwähnt das ausdrücklich.

### Test-Anpassungen

`tests/test_report.py` hat aktuell Test-Fixtures wie `greeting="Sehr geehrte Damen & Herren"`. Diese erwartet im aktuellen HTML-Output ein rohes `&`. Nach dem Fix steht dort `&amp;` — die Assertions müssen angepasst werden.

Neue Test-Cases:

- Greeting mit `&` → Output enthält `&amp;`, nicht `&`.
- Greeting mit `<script>` → Output enthält `&lt;script&gt;`.
- Content mit Zeilenumbruch → Output enthält `<br>`.
- Closing mit Zeilenumbruch und `<` → Output enthält `&lt;` und `<br>` (nicht `&lt;br&gt;`).
- `name` mit Sonderzeichen im PDF-HTML-String enthält escaped Form. **CI-Hinweis:** `generate_pdf` lazy-importiert `xhtml2pdf`, das in CI nicht installiert ist. Der Test mockt `xhtml2pdf.pisa.CreatePDF` (oder verwendet `monkeypatch.setattr` auf das lazy-importierte Modul) und prüft, dass der an `CreatePDF` übergebene HTML-String die escaped Form enthält. Damit läuft der Test auch ohne installiertes `xhtml2pdf`.
- Platzhalter `{zeitraum}` ist Datum (sicher), Platzhalter wird korrekt ersetzt nach Escape.

## 2) `token.json`-Permissions

### Problem

`src/mail.py:32, 96` schreibt `token.json` mit Default-Permissions (typisch `0644`). Auf Multi-User-Linux/macOS-Systemen ist die Datei für andere User lesbar — der Refresh-Token mit `gmail.send`-Scope sollte das nicht sein.

### Lösung

Helper-Funktion in `src/mail.py`, die nach jedem Write die Permissions setzt:

```python
import stat

def _write_token(creds, token_path: str) -> None:
    """Persistiere Credentials und setze restriktive Permissions (Unix only)."""
    with open(token_path, "w") as f:
        f.write(creds.to_json())
    try:
        os.chmod(token_path, stat.S_IRUSR | stat.S_IWUSR)  # 0600
    except OSError:
        # Windows oder Filesystem ohne POSIX-Permissions: best-effort
        pass
```

Beide Aufrufer (`_refresh_and_persist` und `get_gmail_service`) verwenden den Helper.

### Test-Anpassungen

`tests/test_mail.py` deckt aktuell `_refresh_and_persist` und `refresh_token_if_needed` ab. Neuer Test:

- Auf POSIX-Systemen (`platform.system() != "Windows"`): nach `_write_token(creds, path)` ist `os.stat(path).st_mode & 0o777 == 0o600`. Test übersprungen via `pytest.mark.skipif(platform.system() == "Windows", ...)`.

## 3) `Settings.set_many` — Batch-Write

### Problem

`src/dialogs/settings_dialog.py:179–199` macht 12 einzelne `settings.set(key, value)`-Calls = 12 Disk-Roundtrips inkl. atomarem Replace. Im Worst Case (Banner-Worker schreibt parallel `last_update_check_at`) führt das zu Lost Updates.

### Lösung

Neue Methode in `src/settings.py`:

```python
def set_many(self, updates: dict) -> None:
    """Mehrere Werte setzen, einmal auf Platte schreiben.

    Leeres Dict ist No-op (kein Disk-Roundtrip).
    """
    if not updates:
        return
    self._data.update(updates)
    self._save_to_disk()
```

`set(key, value)` bleibt erhalten und ist nun ein dünner Wrapper:

```python
def set(self, key, value) -> None:
    self.set_many({key: value})
```

### Aufrufer-Anpassung

`save_settings` in `settings_dialog.py` wird zu einem einzelnen `set_many`-Call:

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

### Test-Anpassungen

`tests/test_settings.py` erweitern um:

- `set_many({"a": 1, "b": 2})` schreibt einmal auf Platte (mockbar via `unittest.mock.patch.object(s, "_save_to_disk")` — Anzahl der Calls = 1).
- `set_many` aktualisiert `_data` korrekt.
- `set(key, value)` ist weiterhin idempotent (wrapper-Test).
- `set_many({})` ist **No-op**: kein `_save_to_disk`-Call. Begründung: vermeidet einen nutzlosen Disk-Write, wenn ein Caller versehentlich ein leeres Dict übergibt. Implementierung: `if not updates: return` als erste Zeile in `set_many`.

## 4) Logging + globaler Excepthook

### Architektur

Neues Modul **`src/logging_setup.py`** — single-purpose, wird einmal in `src/main.py` aufgerufen, bevor `App` gebaut wird.

### Logfile-Pfad

`<base>/logs/zeiterfassung.log` — Subdir wird beim Setup angelegt, falls nicht vorhanden. `base` ist das Ergebnis von `get_base_path()`.

### Setup

```python
# src/logging_setup.py
import logging
import os
import sys
import tkinter as tk
from logging.handlers import RotatingFileHandler


LOGFILE_NAME = "zeiterfassung.log"
LOG_SUBDIR = "logs"
MAX_BYTES = 1_000_000      # ~4 MB max. Logvolumen (1 MB × (1 + 3 Backups))
BACKUP_COUNT = 3
DEFAULT_LEVEL = logging.INFO   # Begründung: Start-Logs und Settings-Cast-Warnungen
                               # sollen sichtbar sein. Crash-Loops sind in einem
                               # Desktop-Tool selten und Rotation deckt das ab.


def get_log_path(base_path: str) -> str:
    return os.path.join(base_path, LOG_SUBDIR, LOGFILE_NAME)


def setup_logging(base_path: str) -> str:
    """Konfiguriert Root-Logger und Excepthooks. Returns Logfile-Pfad."""
    log_dir = os.path.join(base_path, LOG_SUBDIR)
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, LOGFILE_NAME)

    handler = RotatingFileHandler(
        log_path, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    ))

    root = logging.getLogger()
    root.setLevel(DEFAULT_LEVEL)
    # Idempotent: doppelter setup_logging-Call (z.B. in Tests) verdoppelt keine Handler.
    if not any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        root.addHandler(handler)

    _install_excepthooks()
    return log_path


def _install_excepthooks() -> None:
    log = logging.getLogger("zeiterfassung.uncaught")

    def _hook(exc_type, exc, tb):
        log.error(
            "Uncaught exception",
            exc_info=(exc_type, exc, tb),
        )

    sys.excepthook = _hook

    # Tk-Callback-Exceptions (Event-Handler-Crashes im Mainloop)
    def _tk_hook(self, exc_type, exc, tb):
        log.error(
            "Tk callback exception",
            exc_info=(exc_type, exc, tb),
        )
        # Kurze Messagebox, damit der User merkt dass etwas passiert ist,
        # ohne den vollen Traceback zu zeigen.
        try:
            from tkinter import messagebox
            messagebox.showerror(
                "Unerwarteter Fehler",
                f"{exc_type.__name__}: {exc}\n\n"
                f"Details im Logfile.",
            )
        except Exception:
            log.exception("Messagebox für uncaught Tk exception konnte nicht angezeigt werden")

    tk.Tk.report_callback_exception = _tk_hook
```

### `src/main.py`-Anpassung

```python
def main():
    base = get_base_path()
    try:
        setup_logging(base)
        logging.getLogger(__name__).info("Zeiterfassung v%s gestartet", VERSION)
    except Exception:
        # Logging-Setup-Fehler (Permission-Denied auf logs/, exotisches FS):
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
```

### Bestehende Messagebox-Stellen

Die existierenden `messagebox.showerror(... f"{traceback.format_exc()}")`-Stellen (in `ui.py`, `send_dialog.py`, `settings_dialog.py`) bleiben **inhaltlich** unverändert — die Traceback-im-Dialog-Convention ist im Projekt-CLAUDE.md explizit als "muss" festgehalten ("UI-Fehler sichtbar machen"). Wir ergänzen aber an jeder Stelle einen `logging.exception(...)`-Call, damit das Logfile die volle Spur unabhängig von der Messagebox kriegt:

```python
except Exception as e:
    logging.getLogger(__name__).exception("Senden fehlgeschlagen")
    messagebox.showerror(
        "Senden fehlgeschlagen",
        f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}",
        parent=dialog,
    )
```

**Scope dieses Commits:** Diese `logging.exception`-Anpassungen in `src/ui.py`, `src/dialogs/send_dialog.py` und `src/dialogs/settings_dialog.py` sind **Teil des Logging-Commits (Commit 1)** — nicht ein separater Commit. Begründung: Sie hängen funktional am neuen Logging-Setup; ohne den Setup-Code haben sie keine Wirkung. Trennung wäre künstlich.

### Test-Anpassungen

Neue Datei `tests/test_logging_setup.py`:

- `setup_logging(tmp_path)` legt `<tmp_path>/logs/zeiterfassung.log` an.
- Loggen von `logging.getLogger("test").info("foo")` schreibt nach Logfile.
- Doppelter `setup_logging`-Call addiert keinen zweiten `RotatingFileHandler` (Idempotenz).
- `sys.excepthook` ist nach Setup nicht mehr der Default.
- `tk.Tk.report_callback_exception` ist nach Setup gesetzt (kein Aufruf, nur Identitäts-Check).

**Test-Isolation:** Jeder Test verwendet eine `pytest`-Fixture, die nach dem Lauf alle `RotatingFileHandler`-Instanzen aus dem Root-Logger entfernt und `sys.excepthook` sowie `tk.Tk.report_callback_exception` auf die Originale zurücksetzt. Sonst leaken Handler in andere Tests (z.B. die später laufenden Settings-Tests, die selbst `caplog` nutzen).

Skizze:

```python
@pytest.fixture
def isolated_logging():
    import logging, sys, tkinter as tk
    root = logging.getLogger()
    saved_handlers = root.handlers[:]
    saved_level = root.level
    saved_excepthook = sys.excepthook
    saved_tk_hook = tk.Tk.report_callback_exception
    yield
    root.handlers = saved_handlers
    root.setLevel(saved_level)
    sys.excepthook = saved_excepthook
    tk.Tk.report_callback_exception = saved_tk_hook
```

Bestehende Tests laufen unverändert — `setup_logging` wird in Tests nur in `test_logging_setup.py` aufgerufen, also keine Side-Effects auf andere Test-Module.

## 5) Schema-Validation in `Settings._load`

### Problem

`Settings._load` macht aktuell `self._data.update(loaded)`. Wenn `settings.json` einen Wert mit falschem Typ hat (z.B. `"default_pause": "30"` statt `30`, oder ein altes Schema mit anderem Typ), schmiert ein späterer Aufrufer ab — z.B. `int(pause_var.get())` in `entry_dialog.py:74`.

### Lösung

Validate-Layer in `_load`, der pro Key versucht, den Loaded-Value in den Default-Typ zu casten. Bei Erfolg: übernehmen. Bei Fehler: Default behalten und einmal warnen.

```python
import logging  # neuer Import in src/settings.py

def _load(self) -> None:
    if not os.path.exists(self.filepath):
        return
    try:
        with open(self.filepath, "r", encoding="utf-8") as f:
            loaded = json.load(f)
    except (json.JSONDecodeError, ValueError):
        self._data = dict(DEFAULTS)
        return

    if not isinstance(loaded, dict):
        # Komplett kaputtes JSON-Toplevel (z.B. eine Liste): zurück auf Defaults.
        logging.getLogger(__name__).warning(
            "settings.json hat unerwartetes Toplevel-Format, verwerfe Inhalt",
        )
        self._data = dict(DEFAULTS)
        return

    for key, default_value in DEFAULTS.items():
        if key not in loaded:
            continue
        coerced = _coerce(loaded[key], default_value)
        if coerced is _COERCE_FAILED:
            logging.getLogger(__name__).warning(
                "settings.json: Wert für %r (%r) ist nicht in Typ %s castbar — "
                "verwende Default %r",
                key, loaded[key], type(default_value).__name__, default_value,
            )
            continue
        self._data[key] = coerced

    # Unbekannte Keys aus loaded: ignoriert (nicht übernommen).
```

Cast-Logik:

```python
_COERCE_FAILED = object()  # Sentinel

def _coerce(value, default):
    """Versuche value in den Typ von default zu casten. Bei Erfolg: cast-Wert,
    bei Fehler: _COERCE_FAILED."""
    target_type = type(default)
    if isinstance(value, target_type) and not (target_type is int and isinstance(value, bool)):
        # bool ist Subklasse von int — verhindere, dass True als 1 durchgewunken wird,
        # wenn der Default ein int ist.
        return value
    try:
        if target_type is bool:
            # JSON kennt true/false; sonstige Werte (z.B. "true") sind verdächtig.
            if isinstance(value, bool):
                return value
            return _COERCE_FAILED
        if target_type is int:
            return int(value)
        if target_type is float:
            return float(value)
        if target_type is str:
            return str(value)
    except (TypeError, ValueError):
        return _COERCE_FAILED
    return _COERCE_FAILED
```

### Edge-Cases

| Szenario | Verhalten |
|---|---|
| `"default_pause": "30"` (String statt Int) | Cast zu `int(30)`, übernommen |
| `"default_pause": "abc"` | Cast schlägt fehl, Default `30` bleibt, Logfile-Warnung |
| `"autostart": "true"` (String statt Bool) | Cast schlägt fehl (bool-Strenge), Default `False` bleibt |
| `"autostart": 1` (Int statt Bool) | Cast schlägt fehl (bool-Strenge), Default bleibt |
| `"hourly_rate": 25` (Int für Float-Default) | Cast zu `float(25.0)`, übernommen |
| Unbekannter Key `"old_field": "x"` | Ignoriert, nicht in `_data` |
| Toplevel ist Liste statt Dict | `_data = dict(DEFAULTS)`, Logfile-Warnung |

### Test-Anpassungen

`tests/test_settings.py` erweitern:

- String-int castet: `'{"default_pause": "30"}'` → `s.get("default_pause") == 30`.
- Kaputter Cast lässt Default: `'{"default_pause": "abc"}'` → `s.get("default_pause") == 30`.
- Bool-Strenge: `'{"autostart": "true"}'` → `s.get("autostart") is False`.
- Bool-Strenge: `'{"autostart": 1}'` → `s.get("autostart") is False`.
- Int-für-Float: `'{"hourly_rate": 25}'` → `s.get("hourly_rate") == 25.0` (float).
- Unbekannter Key wird ignoriert: `'{"old_field": "x"}'` → `s.get("old_field") is None`.
- Kaputtes JSON-Toplevel (`'[1,2,3]'`) → alle Defaults werden zurückgesetzt.
- **Warning-Logging via `caplog`:** Bei `'{"default_pause": "abc"}'` enthält `caplog.records` mindestens einen Eintrag mit `levelname == "WARNING"` und `"default_pause"` in der Message. Analog für Bool-Strenge und Toplevel-Mismatch. Damit ist garantiert, dass Cast-Failures in Production sichtbar werden.

## Reihenfolge der Commits im PR

Reihenfolge so gewählt, dass jeder Commit für sich grün ist und Logging früh verfügbar wird (Punkt #4 zuerst, damit alle nachfolgenden Punkte sofort ins Logfile schreiben können):

1. **Logging-Setup + `logging.exception`-Calls in den Dialog-Modulen** (`logging_setup.py`, `main.py`-Hookup, ergänzte `logging.exception(...)`-Calls in `ui.py`, `dialogs/send_dialog.py`, `dialogs/settings_dialog.py`, `tests/test_logging_setup.py`).
2. **`Settings.set_many` + Schema-Validation** (`settings.py`, `settings_dialog.py`-Refactor auf `set_many`, `tests/test_settings.py`-Erweiterung). Beide hängen am gleichen Modul, ein gemeinsamer Commit ist sauberer als zwei.
3. **HTML-Escaping in Bericht/PDF** (`report.py`, `tests/test_report.py`-Anpassung).
4. **`token.json`-Permissions** (`mail.py`, `tests/test_mail.py`-Erweiterung).
5. **Versions-Bump auf `1.9.2` + CHANGELOG-Eintrag** (`src/version.py`, `CHANGELOG.md`).

Letzter Commit: das `release:patch`-Label kommt am PR, nicht im Code.

## CHANGELOG-Eintrag

Konkreter Text für den `## v1.9.2`-Block (oben in `CHANGELOG.md` einzufügen):

```markdown
## v1.9.2
- Mail-Templates (Anrede, Inhalt, Gruß, Name) und der Bericht escapen Sonderzeichen jetzt korrekt — `&`, `<`, `>` werden im Mail-HTML und PDF nicht mehr roh ausgegeben. **Behavior-Change:** wer bisher bewusst HTML-Tags wie `<b>` oder `<br>` in den Mail-Templates verwendet hat, sieht diese jetzt als Klartext. Zeilenumbrüche im Inhalt/Gruß werden weiterhin korrekt umgebrochen
- `token.json` wird auf macOS/Linux mit `0600`-Permissions geschrieben — der Refresh-Token mit Gmail-Send-Scope ist auf Multi-User-Systemen nicht mehr für andere User lesbar (Windows ignoriert Unix-Permissions)
- Settings-Speichern macht statt 12 separater Disk-Roundtrips nur noch einen einzigen — minimiert das Risiko verlorener Updates, wenn der Update-Banner-Worker parallel zum Settings-Dialog schreibt
- Neues Logfile unter `<Datenordner>/logs/zeiterfassung.log` (rotierend, max. 4 MB Gesamtvolumen). App-Start, uncaught Exceptions im Tk-Mainloop und alle Sendepfad-Fehler landen dort — bei `--noconsole`-Builds (Windows-Release) gab es bisher keine Spur von Crashes
- `settings.json` wird beim Laden gegen die erwarteten Typen validiert. Ein manuell verändertes Feld mit falschem Typ (z.B. String statt Int) lässt die App nicht mehr abstürzen, sondern fällt auf den Default zurück und schreibt eine Warnung ins Logfile
```


## Risiken / Abwägungen

| Risiko | Mitigation |
|---|---|
| HTML-Escape-Test-Anpassungen übersehen | Lokal `pytest tests/test_report.py -v` vor PR; CI fängt Rest |
| `chmod` schlägt auf exotischem Filesystem fehl (sshfs etc.) | `try/except OSError: pass` — nicht-kritisch |
| `chmod`-Race nach `open` (Datei kurzzeitig `0644`) | Im Single-User-Desktop-Workflow vernachlässigbar. Robust wäre `os.open(..., 0o600)`, aber YAGNI. Erwähnt für Awareness. |
| Schema-Validation kostet Settings-Read-Latenz | Vernachlässigbar (16 Keys, einfache Casts); kein I/O |
| `RotatingFileHandler` blockt UI-Thread bei Rotate | 1 MB Files, Rotate ist Sekundenbruchteil; alternativ `QueueHandler`, aber YAGNI |
| Logfile-Pfad fehlt im Backup-Plan des Users | Out of scope; `<base>/logs/` ist offensichtlich genug |
| `bool` ist `int`-Subklasse, Cast-Logik subtil | Expliziter Test deckt das ab; Sentinel-Wert macht Failure deutlich |
| Settings-Tests laufen vor Logging-Setup; `caplog` muss ohne `setup_logging` funktionieren | `caplog` von pytest hängt sich an den Root-Logger und funktioniert unabhängig von handlers — `_load`-Warnings kommen unverändert durch |
| Test-Handler leaken in andere Tests (s. Logging-Test-Isolation) | `isolated_logging`-Fixture in `test_logging_setup.py` räumt auf |

## Out of scope

- Andere Punkte aus dem ursprünglichen Review (#2 VBS-Injection, #6 Tempfile-Cleanup, #7 Storage-Read-Performance, #8 SemVer-Library, #10/#11 weitere Excepthook-Aspekte über das hier hinaus, #12 Refresh-Flicker, #13 Threading-Race, #14 CI-Test-Coverage, #15 Linter, #16 Inno-Setup-Audit, #17 Test-Coverage, #18 Settings-Lock, #19 `ui.py`-Split, #20 `build.py`-Version-Check) — Folge-PR.
- Manuelle Migration alter `settings.json`-Dateien (`Settings._load` macht das implizit beim nächsten Save).
- Externes Reporting für Logfile (Sentry o.ä.).
- "Logfile öffnen"-Button im Settings-Dialog (war Teil von Logging-Variante C, abgewählt).
- Settings-Dialog: visuelle Anzeige, dass Schema-Korrekturen stattfanden (Variante B aus Brainstorming, abgewählt).
- Performance-Test, dass `set_many` wirklich nur einmal `_save_to_disk` triggert — durch Code-Inspektion offensichtlich, einfacher Mock-Test reicht.
