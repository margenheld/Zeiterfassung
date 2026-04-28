# Update-Check & Banner Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Beim App-Start einmal täglich die GitHub-Releases-API abfragen und bei neuerer Version einen unaufdringlichen Banner unter dem Header anzeigen, der mit einem Klick das richtige Plattform-Asset im Browser öffnet.

**Architecture:** Neues stdlib-only Modul `src/updater.py` (HTTP-Call, Versionsvergleich, Asset-Match, Drosselung). Integration in `src/ui.py::App` über einen Daemon-Worker analog zu `_proactive_token_refresh` — mit dem Unterschied, dass der Worker nur den Netz-Call macht und sämtliche State-Mutationen (Settings + Banner-Aufbau) per `root.after(0, ...)` auf den UI-Thread marshallt, weil `Settings` keinen Lock hat. Banner wird als eigenes Frame zwischen Header und Grid gepackt und ist von `_build_grid` entkoppelt.

**Tech Stack:** Python stdlib (`urllib.request`, `json`, `dataclasses`, `datetime`, `threading`, `webbrowser`), Tkinter, pytest, `unittest.mock`.

**Spec:** `docs/superpowers/specs/2026-04-28-update-check-design.md`

---

## File Structure

| File | Aktion | Zweck |
|---|---|---|
| `src/updater.py` | **Create** | Reine Logik: HTTP-Call, Datenklassen, Versionsvergleich, Asset-Match, Throttle. Keine Tk-Imports, voll testbar. |
| `tests/test_updater.py` | **Create** | Unit-Tests für alle Funktionen in `updater.py`. Netz-Calls per `unittest.mock.patch` auf `urllib.request.urlopen`. |
| `src/settings.py` | **Modify** | Zwei neue Defaults (`last_update_check_at`, `dismissed_version`) im `DEFAULTS`-Dict. |
| `tests/test_settings.py` | **Modify** | Default-Tests für die zwei neuen Felder. |
| `src/ui.py` | **Modify** | Imports erweitern, `__init__` initialisiert `self._update_banner = None` und ruft `_proactive_update_check`, neue Methoden `_proactive_update_check`, `_handle_update_check_result`, `_show_update_banner`, `_open_update_download`, `_dismiss_update_banner`. |

---

## Chunk 1: updater.py — Logik-Modul

### Task 1: `is_newer` und Tuple-Helper

**Files:**
- Create: `src/updater.py`
- Create: `tests/test_updater.py`

- [ ] **Step 1: Failing Tests schreiben**

`tests/test_updater.py` (neu):

```python
from src.updater import is_newer


class TestIsNewer:
    def test_same_version_is_not_newer(self):
        assert is_newer("1.8.3", "1.8.3") is False

    def test_higher_minor_is_newer(self):
        assert is_newer("1.8.3", "1.9.0") is True

    def test_lower_is_not_newer(self):
        assert is_newer("1.9.0", "1.8.3") is False

    def test_two_digit_patch_compares_numerically_not_lex(self):
        assert is_newer("1.8.3", "1.8.10") is True

    def test_higher_major_is_newer(self):
        assert is_newer("1.8.3", "2.0.0") is True
```

- [ ] **Step 2: Tests laufen lassen — sollen failen**

```
pytest tests/test_updater.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.updater'`.

- [ ] **Step 3: Minimale Implementierung**

`src/updater.py` (neu):

```python
"""Update-Check gegen GitHub-Releases (stdlib-only).

Single Purpose: Netzwerk-Call, Versions-Vergleich, Asset-Match, Throttle.
Keine Tk-Imports; UI-Layer ruft die Funktionen aus einem Worker-Thread.
"""


def _to_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def is_newer(current: str, latest: str) -> bool:
    """True, wenn `latest` strikt neuer ist als `current`. Beide ohne v-Prefix."""
    return _to_tuple(latest) > _to_tuple(current)
```

- [ ] **Step 4: Tests laufen — sollen passen**

```
pytest tests/test_updater.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```
git add src/updater.py tests/test_updater.py
git commit -m "feat(updater): add is_newer version comparison"
```

---

### Task 2: `today_iso` und `should_check_today`

**Files:**
- Modify: `src/updater.py`
- Modify: `tests/test_updater.py`

- [ ] **Step 1: Failing Tests schreiben**

In `tests/test_updater.py` ergänzen:

```python
from datetime import date

from src.updater import should_check_today, today_iso


class TestTodayIso:
    def test_returns_iso_date_string(self):
        result = today_iso()
        # Roundtrip-Parse stellt sicher, dass es ein gültiges ISO-Datum ist
        assert date.fromisoformat(result) == date.today()


class TestShouldCheckToday:
    def test_empty_string_returns_true(self):
        assert should_check_today("", today=date(2026, 4, 28)) is True

    def test_none_returns_true(self):
        assert should_check_today(None, today=date(2026, 4, 28)) is True

    def test_yesterday_returns_true(self):
        assert should_check_today("2026-04-27", today=date(2026, 4, 28)) is True

    def test_today_returns_false(self):
        assert should_check_today("2026-04-28", today=date(2026, 4, 28)) is False

    def test_invalid_string_returns_true(self):
        assert should_check_today("not-a-date", today=date(2026, 4, 28)) is True
```

- [ ] **Step 2: Tests laufen — sollen failen**

```
pytest tests/test_updater.py -v
```

Expected: `ImportError: cannot import name 'should_check_today' from 'src.updater'`.

- [ ] **Step 3: Implementierung ergänzen**

In `src/updater.py` am Ende:

```python
from datetime import date


def today_iso() -> str:
    """Heutiges Datum als ISO-Format `YYYY-MM-DD` (lokale Zeitzone)."""
    return date.today().isoformat()


def should_check_today(last_check: str | None, today: date | None = None) -> bool:
    """True, wenn der letzte Check vor dem heutigen Kalendertag lag.

    Drosselung pro Kalendertag (lokale Zeit), nicht pro 24-h-Fenster.
    Bei leerem oder ungültigem `last_check` wird ebenfalls True geliefert,
    damit ein einmal kaputter Wert nicht den Check für immer blockiert.
    """
    if not last_check:
        return True
    today = today or date.today()
    try:
        last = date.fromisoformat(last_check)
    except ValueError:
        return True
    return last < today
```

Den Import `from datetime import date` an den Anfang der Datei verschieben (Stilkonsistenz).

- [ ] **Step 4: Tests laufen**

```
pytest tests/test_updater.py -v
```

Expected: alle bisherigen + 6 neue passed.

- [ ] **Step 5: Commit**

```
git add src/updater.py tests/test_updater.py
git commit -m "feat(updater): add daily check throttling helpers"
```

---

### Task 3: `Release`/`Asset` Datenklassen + `pick_asset_url`

**Files:**
- Modify: `src/updater.py`
- Modify: `tests/test_updater.py`

- [ ] **Step 1: Failing Tests schreiben**

In `tests/test_updater.py` ergänzen:

```python
from src.updater import Asset, pick_asset_url


def _three_assets(version: str) -> list[Asset]:
    return [
        Asset(name="Zeiterfassung_Setup.exe", url="https://example.com/exe"),
        Asset(name=f"Zeiterfassung-{version}-arm64.dmg", url="https://example.com/dmg"),
        Asset(name=f"Zeiterfassung-{version}-x86_64.AppImage", url="https://example.com/appimage"),
    ]


class TestPickAssetUrl:
    def test_windows_picks_exe(self):
        assets = _three_assets("1.9.0")
        assert pick_asset_url(assets, "Windows", "1.9.0") == "https://example.com/exe"

    def test_darwin_picks_arm_dmg(self):
        assets = _three_assets("1.9.0")
        assert pick_asset_url(assets, "Darwin", "1.9.0") == "https://example.com/dmg"

    def test_linux_picks_appimage(self):
        assets = _three_assets("1.9.0")
        assert pick_asset_url(assets, "Linux", "1.9.0") == "https://example.com/appimage"

    def test_unknown_system_returns_none(self):
        assets = _three_assets("1.9.0")
        assert pick_asset_url(assets, "FreeBSD", "1.9.0") is None

    def test_missing_asset_returns_none(self):
        # Nur Linux-Asset vorhanden, Plattform Windows
        assets = [Asset(name="Zeiterfassung-1.9.0-x86_64.AppImage", url="u")]
        assert pick_asset_url(assets, "Windows", "1.9.0") is None

    def test_version_mismatch_in_dmg_name_returns_none(self):
        # Versionsfeld passt nicht — DMG/AppImage tragen die Version im Namen
        assets = [Asset(name="Zeiterfassung-1.8.0-arm64.dmg", url="u")]
        assert pick_asset_url(assets, "Darwin", "1.9.0") is None
```

- [ ] **Step 2: Tests laufen — sollen failen**

```
pytest tests/test_updater.py -v
```

Expected: `ImportError: cannot import name 'Asset' from 'src.updater'`.

- [ ] **Step 3: Implementierung ergänzen**

In `src/updater.py` ergänzen (Imports oben, Code am Ende):

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Asset:
    name: str
    url: str


@dataclass(frozen=True)
class Release:
    version: str        # ohne v-Prefix, z.B. "1.9.0"
    html_url: str       # Release-Page auf GitHub
    assets: tuple[Asset, ...]


def pick_asset_url(assets, system: str, latest_version: str) -> str | None:
    """Liefert die Download-URL für das Plattform-Asset oder None."""
    expected_name = {
        "Windows": "Zeiterfassung_Setup.exe",
        "Darwin": f"Zeiterfassung-{latest_version}-arm64.dmg",
        "Linux": f"Zeiterfassung-{latest_version}-x86_64.AppImage",
    }.get(system)
    if expected_name is None:
        return None
    for asset in assets:
        if asset.name == expected_name:
            return asset.url
    return None
```

`Release.assets` ist ein Tuple statt Liste, weil `frozen=True` keine Mutationen erlaubt — das ist ok, der Caller iteriert nur.

- [ ] **Step 4: Tests laufen**

```
pytest tests/test_updater.py -v
```

Expected: alle bisherigen + 6 neue passed.

- [ ] **Step 5: Commit**

```
git add src/updater.py tests/test_updater.py
git commit -m "feat(updater): add Release/Asset dataclasses and pick_asset_url"
```

---

### Task 4: `check_latest_release` (HTTP-Call, gemockt)

**Files:**
- Modify: `src/updater.py`
- Modify: `tests/test_updater.py`

- [ ] **Step 1: Failing Tests schreiben**

In `tests/test_updater.py` ergänzen:

```python
import json
import socket
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from src.updater import Release, check_latest_release


def _api_response(payload: dict) -> BytesIO:
    return BytesIO(json.dumps(payload).encode("utf-8"))


HAPPY_PAYLOAD = {
    "tag_name": "v1.9.0",
    "html_url": "https://github.com/MargenHeld/Zeiterfassung/releases/tag/v1.9.0",
    "assets": [
        {"name": "Zeiterfassung_Setup.exe", "browser_download_url": "https://example.com/exe"},
        {"name": "Zeiterfassung-1.9.0-arm64.dmg", "browser_download_url": "https://example.com/dmg"},
        {"name": "Zeiterfassung-1.9.0-x86_64.AppImage", "browser_download_url": "https://example.com/appimage"},
    ],
}


class TestCheckLatestRelease:
    def test_happy_path_strips_v_prefix_and_parses_assets(self):
        with patch("src.updater.urlopen", return_value=_api_response(HAPPY_PAYLOAD)):
            release = check_latest_release("MargenHeld/Zeiterfassung")
        assert release is not None
        assert release.version == "1.9.0"
        assert release.html_url.endswith("/v1.9.0")
        assert len(release.assets) == 3
        assert release.assets[0].name == "Zeiterfassung_Setup.exe"
        assert release.assets[0].url == "https://example.com/exe"

    def test_url_error_returns_none(self):
        with patch("src.updater.urlopen", side_effect=URLError("offline")):
            assert check_latest_release("any/repo") is None

    def test_http_404_returns_none(self):
        err = HTTPError(url="x", code=404, msg="Not Found", hdrs=None, fp=None)
        with patch("src.updater.urlopen", side_effect=err):
            assert check_latest_release("any/repo") is None

    def test_socket_timeout_returns_none(self):
        with patch("src.updater.urlopen", side_effect=socket.timeout()):
            assert check_latest_release("any/repo") is None

    def test_invalid_json_returns_none(self):
        with patch("src.updater.urlopen", return_value=BytesIO(b"not json{{")):
            assert check_latest_release("any/repo") is None

    def test_missing_tag_name_returns_none(self):
        payload = {"html_url": "x", "assets": []}
        with patch("src.updater.urlopen", return_value=_api_response(payload)):
            assert check_latest_release("any/repo") is None

    def test_malformed_assets_are_filtered(self):
        # Asset ohne browser_download_url + Asset als String → werden geskippt
        payload = {
            "tag_name": "v1.9.0",
            "html_url": "x",
            "assets": [
                {"name": "ok", "browser_download_url": "u1"},
                {"name": "incomplete"},                       # ohne URL
                "not-a-dict",                                 # falscher Typ
                {"name": "ok2", "browser_download_url": "u2"},
            ],
        }
        with patch("src.updater.urlopen", return_value=_api_response(payload)):
            release = check_latest_release("any/repo")
        assert release is not None
        assert len(release.assets) == 2
        assert {a.name for a in release.assets} == {"ok", "ok2"}

    def test_uppercase_v_prefix_is_stripped(self):
        payload = dict(HAPPY_PAYLOAD, tag_name="V1.9.0")
        with patch("src.updater.urlopen", return_value=_api_response(payload)):
            release = check_latest_release("any/repo")
        assert release is not None
        assert release.version == "1.9.0"
```

- [ ] **Step 2: Tests laufen — sollen failen**

```
pytest tests/test_updater.py::TestCheckLatestRelease -v
```

Expected: `ImportError: cannot import name 'check_latest_release' from 'src.updater'`.

- [ ] **Step 3: Implementierung ergänzen**

Imports oben in `src/updater.py` ergänzen (zusätzlich zum bestehenden `from datetime import date` und `from dataclasses import dataclass`):

```python
import json
from urllib.error import URLError
from urllib.request import Request, urlopen

from src.version import VERSION
```

`src/version.py` bleibt unverändert — wir lesen nur `VERSION` für den User-Agent-Header.

Am Ende der Datei `src/updater.py` ergänzen:

```python
def check_latest_release(repo: str, timeout: float = 5.0) -> Release | None:
    """Fragt die GitHub-API nach dem neuesten Release.

    Liefert `None` bei jedem Fehler (Netzwerk, Timeout, kaputtes JSON,
    fehlendes `tag_name`). Caller darf sich darauf verlassen, dass keine
    Exception bubbled — Update-Hinweis ist nice-to-have.
    """
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"Zeiterfassung/{VERSION}",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        tag = payload.get("tag_name")
        html_url = payload.get("html_url")
        if not tag or not html_url:
            return None
        # Sowohl 'v' als auch 'V' strippen; Tags sind normiert, defensiv ist billig.
        if tag[:1] in ("v", "V"):
            tag = tag[1:]
        raw_assets = payload.get("assets") or []
        assets = tuple(
            Asset(name=a["name"], url=a["browser_download_url"])
            for a in raw_assets
            if isinstance(a, dict) and "name" in a and "browser_download_url" in a
        )
        return Release(version=tag, html_url=html_url, assets=assets)
    except (URLError, OSError, json.JSONDecodeError, TypeError, KeyError, AttributeError):
        # URLError fängt auch HTTPError (4xx/5xx); OSError fängt socket.timeout etc.
        # TypeError/KeyError/AttributeError fangen kaputte Payload-Strukturen ab.
        return None
```

- [ ] **Step 4: Tests laufen — sollen passen**

```
pytest tests/test_updater.py -v
```

Expected: alle Tests passen (Summe aus Tasks 1–4).

- [ ] **Step 5: Commit**

```
git add src/updater.py tests/test_updater.py
git commit -m "feat(updater): add check_latest_release with mocked HTTP tests"
```

---

## Chunk 2: Settings + UI-Integration

### Task 5: Neue Settings-Defaults

**Files:**
- Modify: `src/settings.py:4-18` (DEFAULTS-Dict)
- Modify: `tests/test_settings.py`

- [ ] **Step 1: Failing Tests schreiben**

In `tests/test_settings.py` ergänzen:

```python
def test_last_update_check_at_default(tmp_settings):
    assert tmp_settings.get("last_update_check_at") == ""


def test_dismissed_version_default(tmp_settings):
    assert tmp_settings.get("dismissed_version") == ""
```

- [ ] **Step 2: Tests laufen — sollen failen**

```
pytest tests/test_settings.py -v
```

Expected: 2 neue Tests failen mit `assert None == ""` (Schlüssel nicht in DEFAULTS, `.get()` liefert `None`).

- [ ] **Step 3: DEFAULTS erweitern**

In `src/settings.py` im `DEFAULTS`-Dict zwei Einträge ergänzen (am Ende, vor der schließenden `}`):

```python
    "last_update_check_at": "",
    "dismissed_version": "",
```

- [ ] **Step 4: Tests laufen**

```
pytest tests/test_settings.py -v
```

Expected: alle Tests passen.

- [ ] **Step 5: Commit**

```
git add src/settings.py tests/test_settings.py
git commit -m "feat(settings): add update-check throttle and dismiss fields"
```

---

### Task 6: UI-Integration in `App`

**Files:**
- Modify: `src/ui.py` (Imports am Anfang, `__init__`, neue Methoden)

Hinweis: Tk-Bindings und Banner-Aufbau werden nicht automatisiert getestet — analog zur Arrow-Key-Spec (`docs/superpowers/specs/2026-04-27-arrow-key-navigation-design.md`) liegt der Verifikations-Aufwand bei manuellem Smoke-Test in Task 7. Die Logik darunter (`updater.py`) ist vollständig unit-getestet.

- [ ] **Step 1: Imports erweitern**

In `src/ui.py` direkt nach `import traceback` (aktuell Zeile 10), um den Stdlib-Block alphabetisch zu erhalten:

```python
import webbrowser
```

Und nach den bestehenden `from src...`-Imports (vor dem Block aus `src.dialogs`):

```python
from src.updater import (
    check_latest_release,
    is_newer,
    pick_asset_url,
    should_check_today,
    today_iso,
    Release,
)
```

- [ ] **Step 2: `__init__` erweitern**

In `src/ui.py::App.__init__`, nach Zeile 77 (`self._proactive_token_refresh()`) einfügen:

```python
        self._update_banner = None
        self._proactive_update_check()
```

- [ ] **Step 3: `_proactive_update_check` implementieren**

Direkt unter `_proactive_token_refresh` (also nach Zeile 106) neue Methode anhängen:

```python
    def _proactive_update_check(self):
        """Fragt einmal pro Kalendertag GitHub nach einer neueren Version.

        Der HTTP-Call läuft in einem Daemon-Thread; alle State-Mutationen
        (Settings-Write, Banner-Aufbau) werden via `root.after(0, ...)` auf
        den UI-Thread marshallt, damit `Settings.set` nicht parallel zu
        Schreibvorgängen aus dem Settings-Dialog läuft.

        Fehler werden still verschluckt — Update-Hinweis ist nice-to-have.
        """
        if not should_check_today(self.settings.get("last_update_check_at")):
            return

        def worker():
            try:
                release = check_latest_release("MargenHeld/Zeiterfassung")
                if release is None:
                    return
                newer = is_newer(VERSION, release.version)
            except Exception:
                # Pure Logik, robust gegen exotische Tags. Bei jedem Fehler:
                # nichts persistieren, nichts anzeigen — morgen nochmal probieren.
                return
            self.root.after(
                0, lambda: self._handle_update_check_result(release, newer)
            )

        threading.Thread(target=worker, daemon=True).start()

    def _handle_update_check_result(self, release: "Release", newer: bool):
        """Läuft im UI-Thread. Persistiert den Check-Stand und zeigt ggf. den Banner.

        `is_newer` ist bereits im Worker ausgewertet, damit hier keine ungeschützte
        Logik im Tk-Event-Loop läuft.
        """
        self.settings.set("last_update_check_at", today_iso())
        if not newer:
            return
        if release.version == self.settings.get("dismissed_version"):
            return
        self._show_update_banner(release)
```

- [ ] **Step 4: Banner-Methoden implementieren**

Direkt darunter anhängen. Hinweis zur Theme-Wahl: Die Spec listet `fg=BG` als Beispiel; in der Implementierung verwenden wir `fg="#ffffff"` für Label und Icon, weil der bestehende `primary_button` (in `theme.py`) ebenfalls `bg=ACCENT, fg="#ffffff"` nutzt — so bleibt die Banner-Optik im Kontrast konsistent mit dem Rest der App.

```python
    def _show_update_banner(self, release: "Release"):
        if self._update_banner is not None:
            return
        self._update_banner = tk.Frame(self.root, bg=ACCENT)
        self._update_banner.pack(
            before=self.grid_frame, fill=tk.X, padx=10, pady=(5, 0),
        )

        tk.Label(
            self._update_banner,
            text=f"Version {release.version} verfügbar",
            bg=ACCENT, fg="#ffffff", font=FONT_BOLD,
        ).pack(side=tk.LEFT, padx=10, pady=6)

        icon_button(
            self._update_banner, "✕",
            lambda: self._dismiss_update_banner(release.version),
            fg="#ffffff", hover_fg=TEXT,
        ).pack(side=tk.RIGHT, padx=(0, 6))

        secondary_button(
            self._update_banner, "Download",
            lambda: self._open_update_download(release),
            padx=12,
        ).pack(side=tk.RIGHT, padx=6)

    def _open_update_download(self, release: "Release"):
        url = pick_asset_url(
            release.assets, platform.system(), release.version,
        ) or release.html_url
        webbrowser.open(url)

    def _dismiss_update_banner(self, version: str):
        self.settings.set("dismissed_version", version)
        if self._update_banner is not None:
            self._update_banner.destroy()
            self._update_banner = None
```

Hinweis: `Release` ist als String-Type-Hint annotiert (`"Release"`), damit der Forward-Reference auch funktioniert, falls jemand später die Import-Reihenfolge ändert. `Release` ist sowieso schon konkret importiert — ohne Quotes ginge auch.

- [ ] **Step 5: Smoke-Test (Syntax)**

```
python -m py_compile src/ui.py
```

Expected: kein Output (= ok).

```
pytest tests/ -v
```

Expected: alle Tests passen (kein Test wurde durch UI-Änderung gebrochen).

- [ ] **Step 6: Commit**

```
git add src/ui.py
git commit -m "feat(ui): show update banner when newer GitHub release exists"
```

---

### Task 7: Manuelle End-to-End-Verifikation

**Files:** keine.

Tk-Bindings, Banner-Layout und Browser-Open lassen sich unter pytest nicht sinnvoll testen. Manueller Smoke-Test deckt das ab.

- [ ] **Step 1: App starten und Banner provozieren**

In einer temporären lokalen Änderung in `src/version.py` `VERSION` auf einen Wert setzen, der **kleiner** ist als der aktuelle GitHub-Release-Tag (z.B. `"1.0.0"`):

```python
VERSION = "1.0.0"
```

App starten:

```
python -m src.main
```

Expected:
- Hauptfenster öffnet sich normal.
- Nach kurzer Verzögerung (Netz-Call) erscheint der Streifen unter dem Header: `Version <aktuelle> verfügbar` mit `[Download]` und `✕`.
- In `settings.json` (im Repo-Root) erscheint nach dem Check ein Eintrag `"last_update_check_at": "<heute>"`.

- [ ] **Step 2: Download-Button testen**

Klick auf **Download** → Browser öffnet sich auf der korrekten Plattform-Asset-URL (Windows: `Zeiterfassung_Setup.exe`-Download startet, oder GitHub-Browser-Page für das Asset).

- [ ] **Step 3: Dismiss testen**

App neu starten (Banner ist erst wieder am nächsten Tag fällig — daher `last_update_check_at` in `settings.json` auf gestriges Datum setzen, z.B. `"2026-04-27"`, dann starten).

Banner erscheint wieder. Klick auf **✕** → Banner verschwindet sofort. In `settings.json` steht jetzt `"dismissed_version": "<aktuelle>"`.

App nochmal starten (mit gestrigem `last_update_check_at`). Banner erscheint **nicht** mehr. Manuell `dismissed_version` auf eine ältere Version setzen (z.B. `"0.9.0"`) → Banner kommt wieder.

- [ ] **Step 4: Throttling verifizieren**

`last_update_check_at` in `settings.json` auf heutiges Datum setzen. App starten. Erwartung: kein API-Call, kein Banner (auch wenn neuere Version existiert). Mit `tcpdump` / Network-Monitor optional verifizieren — andernfalls Code-Inspection genügt: `should_check_today` returned False früh.

- [ ] **Step 5: Offline-Verhalten**

Netzwerk trennen (Wi-Fi aus). `last_update_check_at` auf gestriges Datum setzen. App starten.

Expected: keine Messagebox, kein Banner, App bleibt benutzbar. `last_update_check_at` bleibt unverändert (Worker hat keinen erfolgreichen Call gemacht).

- [ ] **Step 6: Negativer Pfad — lokale Version neuer als Release**

`src/version.py` temporär auf `VERSION = "99.0.0"` setzen, `last_update_check_at` in `settings.json` auf gestriges Datum, `dismissed_version` leeren. App starten.

Expected: kein Banner. `last_update_check_at` wird auf heute aktualisiert (Check lief erfolgreich, nur `is_newer` returned False).

- [ ] **Step 7: VERSION zurücksetzen**

`src/version.py` wieder auf den Wirk-Stand setzen (`VERSION = "1.8.3"`). `settings.json` aufräumen oder zurücksetzen (Test-Werte rauslöschen).

- [ ] **Step 8: Final-Check**

```
pytest tests/ -v
```

Expected: alle Tests passen.

```
git status
```

Expected: clean (keine ungewollten Änderungen).

---

## Out of scope für diesen Plan

- Versions-Bump in `src/version.py` und CHANGELOG-Eintrag — bündeln im Release-PR (siehe `CLAUDE.md::Release-Prozess`).
- Opt-out-Toggle in den Settings.
- In-App-Download mit Progress-Bar.
- Tests für die Tk-Bindings / das Banner-Frame.
- Pre-Release-Tracking (`/releases/latest` filtert das bereits raus).
