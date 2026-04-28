# Update-Check & Banner — Design Spec

## Overview

Die App soll beim Start prüfen, ob auf GitHub eine neuere Release-Version verfügbar ist, und bei Treffer einen unaufdringlichen Banner unter dem Header anzeigen. Klick auf **Download** öffnet das passende Plattform-Asset im Browser; Klick auf **✕** dismissed die jeweilige Version dauerhaft. Der Check ist auf 1×/Tag gedrosselt und scheitert still bei Netzwerk-/API-Problemen — er darf die Zeiterfassung nicht stören.

Repo wird hartcodiert auf `MargenHeld/Zeiterfassung`. Public GitHub-API genügt (60 Requests/h pro IP, kein Auth nötig). Keine neue Dependency: `urllib.request` aus der Stdlib reicht.

## Scope decisions

| # | Decision | Consequence |
|---|----------|-------------|
| 1 | Throttling auf 1×/Tag, persistiert in `settings.json` als ISO-Datum | Schont Rate-Limit auch bei Power-Usern, die die App häufig öffnen |
| 2 | Dismiss pro Version (`dismissed_version` in Settings) | Banner verschwindet bis zur nächsten neueren Version — übliches Pattern |
| 3 | Kein Opt-out-Toggle in Settings | YAGNI; falls jemand das später braucht, ist ein Bool-Flag trivial nachzuziehen |
| 4 | Download-Button öffnet plattformspezifisches Asset (Browser), Fallback auf Release-Page | Ein Klick weniger als „Release-Seite → richtiges Asset finden" |
| 5 | Kein In-App-Download / Auto-Update | Auf 3 Plattformen mit jeweils eigenem Installer-Pfad zu komplex; Browser-Download + manuelle Installation reicht |
| 6 | Update-Check und Token-Refresh laufen parallel als getrennte Daemon-Threads | Keine Abhängigkeit, bestehender Pattern bleibt unverändert |
| 7 | Bei Netzwerk-/API-Fehler **still scheitern** (kein Dialog, keine Logzeile) | Update-Hinweis ist Nice-to-have; analog zu `TokenNetworkError` |
| 8 | Repo-Slug hartcodiert | Kein Settings-Feld, keine Form-UI — wenn der Slug sich mal ändert, ist das ein Code-Edit |
| 9 | Versions-Vergleich via Tuple-Split nach `.` | `tag_name` ist immer `vX.Y.Z` (Workflow erzwungen); kein semver-Lib nötig |
| 10 | Versions-Bump und CHANGELOG nicht Teil dieser Spec | Wird im Release-PR gebündelt |

## Architecture

Neues Modul **`src/updater.py`** — single-purpose, gut testbar, keine Tk-Imports.

### Public API

```python
@dataclass
class Release:
    version: str        # ohne v-Prefix, z.B. "1.9.0"
    html_url: str       # Release-Page auf GitHub
    assets: list[Asset] # [(name, browser_download_url), ...]

@dataclass
class Asset:
    name: str
    url: str

def check_latest_release(repo: str, timeout: float = 5.0) -> Release | None
def is_newer(current: str, latest: str) -> bool
def pick_asset_url(assets: list[Asset], system: str, latest_version: str) -> str | None
def should_check_today(last_check: str | None, today: date | None = None) -> bool
def today_iso() -> str
```

### `check_latest_release`

- GET `https://api.github.com/repos/{repo}/releases/latest` mit Header `Accept: application/vnd.github+json` und `User-Agent: Zeiterfassung/{VERSION}` (GitHub erfordert UA).
- Timeout 5s.
- Erfolg: JSON parsen, `tag_name` (mit Strip von `v`-Prefix), `html_url`, `assets[].name` und `assets[].browser_download_url` extrahieren → `Release`.
- Fehlschlag (URLError, HTTPError, Timeout, JSONDecodeError, KeyError, fehlendes `tag_name`): `None`.

### `is_newer`

```python
def is_newer(current: str, latest: str) -> bool:
    return _to_tuple(latest) > _to_tuple(current)

def _to_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(part) for part in v.split("."))
```

`tag_name` aus dem GitHub-API kommt mit `v`-Prefix; `check_latest_release` strippt das vorher. `VERSION` aus `src/version.py` ist bereits prefixlos. Edge: nicht-numerische Komponenten (z.B. `1.9.0-rc1`) sind durch den Workflow ausgeschlossen — `pre-check` validiert nicht explizit, aber der Tag-Name wird vom Workflow selbst aus `VERSION` gebildet, und `VERSION` ist im Repo immer pure SemVer. Falls doch mal: `int(...)` raised `ValueError`, der Caller in `_proactive_update_check` fängt mit breitem `except` und der Banner erscheint einfach nicht.

### `pick_asset_url`

Plattform-Pattern (Asset-Namen aus `release.yml`):

| `system` (`platform.system()`) | Asset-Name-Pattern |
|---|---|
| `"Windows"` | `Zeiterfassung_Setup.exe` |
| `"Darwin"` | `Zeiterfassung-{version}-arm64.dmg` |
| `"Linux"` | `Zeiterfassung-{version}-x86_64.AppImage` |

Match strikt per Name-Equality, nicht via `in`/regex — die Workflow-Asset-Namen sind stabil. Bei Mismatch (Intel-Mac, exotisches Linux, Asset im Release fehlt): `None` → Caller fällt auf `release.html_url` zurück, Banner funktioniert weiterhin.

### `should_check_today` / `today_iso`

```python
def today_iso() -> str:
    return date.today().isoformat()  # "YYYY-MM-DD"

def should_check_today(last_check: str | None, today: date | None = None) -> bool:
    if not last_check:
        return True
    today = today or date.today()
    try:
        last = date.fromisoformat(last_check)
    except ValueError:
        return True   # kaputter Wert → einfach prüfen, überschreibt sich gleich
    return last < today
```

Lokales Datum, nicht UTC — Drosselung pro Kalendertag des Users ist intuitiver als ein UTC-Cutoff um 01:00 lokaler Zeit.

## Settings-Schema

Erweitere `DEFAULTS` in `src/settings.py`:

```python
"last_update_check_at": "",   # ISO-Datum "YYYY-MM-DD"
"dismissed_version": "",      # ohne v-Prefix, z.B. "1.9.0"
```

`Settings._load` mergt mit `DEFAULTS` (`self._data.update(loaded)`), bestehende `settings.json` bekommen die Felder beim ersten `set(...)` automatisch geschrieben. Keine Migration.

## Integration in `App` (`src/ui.py`)

Neue Methode `_proactive_update_check`, parallel zu `_proactive_token_refresh` aufgerufen am Ende von `__init__`:

```python
def _proactive_update_check(self):
    if not should_check_today(self.settings.get("last_update_check_at")):
        return

    def worker():
        try:
            release = check_latest_release("MargenHeld/Zeiterfassung")
        except Exception:
            return
        if release is None:
            return
        self.root.after(0, lambda: self._handle_update_check_result(release))

    threading.Thread(target=worker, daemon=True).start()

def _handle_update_check_result(self, release: Release):
    self.settings.set("last_update_check_at", today_iso())
    if not is_newer(VERSION, release.version):
        return
    if release.version == self.settings.get("dismissed_version"):
        return
    self._show_update_banner(release)
```

Begründung Marshal: `Settings.set` ist nicht thread-safe (kein Lock in `src/settings.py`). Der UI-Thread kann jederzeit über den Settings-Dialog schreiben — gleichzeitiger Worker-Write könnte die JSON-Datei korrumpieren. `root.after(0, ...)` schiebt die Settings-Mutation und den Banner-Aufbau zusammen auf den UI-Thread, der den State-Mutationen serialisiert. Der HTTP-Call selbst bleibt im Worker, damit der UI-Thread nicht blockiert.

Reihenfolge in `__init__` (analog zur bestehenden Struktur):

```python
self._build_header()
self._build_grid()
self._build_footer()
self.root.bind("<Left>",  lambda e: self._prev())
self.root.bind("<Right>", lambda e: self._next())
self._refresh()
self._proactive_token_refresh()
self._proactive_update_check()
```

`last_update_check_at` wird nur bei erfolgreichem API-Call geschrieben — schlägt der Check still fehl (Offline-Start), wird beim nächsten Start erneut probiert, statt einen ganzen Tag zu warten.

## UI: Update-Banner

Neuer Frame zwischen Header und Grid. Wird **nicht** in `_build_grid` oder `_build_header` integriert, sondern dynamisch via `pack(before=self.grid_frame, fill=tk.X, padx=10, pady=(5, 0))` eingehängt — so bleibt der Initial-Build unverändert und der Banner erscheint nur, wenn er gebraucht wird.

```
┌────────────────────────────────────────────────────────────┐
│  Version 1.9.0 verfügbar       [ Download ]    ✕            │
└────────────────────────────────────────────────────────────┘
```

### Methoden

```python
def _show_update_banner(self, release: Release):
    self._update_banner = tk.Frame(self.root, bg=ACCENT)
    self._update_banner.pack(before=self.grid_frame, fill=tk.X, padx=10, pady=(5, 0))

    tk.Label(
        self._update_banner,
        text=f"Version {release.version} verfügbar",
        bg=ACCENT, fg=BG, font=FONT_BOLD,
    ).pack(side=tk.LEFT, padx=10, pady=6)

    icon_button(
        self._update_banner, "✕",
        lambda: self._dismiss_update_banner(release.version),
        fg=BG, hover_fg=TEXT,
    ).pack(side=tk.RIGHT, padx=(0, 6))

    secondary_button(
        self._update_banner, "Download",
        lambda: self._open_update_download(release),
        padx=12,
    ).pack(side=tk.RIGHT, padx=6)

def _open_update_download(self, release: Release):
    url = pick_asset_url(release.assets, platform.system(), release.version) or release.html_url
    webbrowser.open(url)

def _dismiss_update_banner(self, version: str):
    self.settings.set("dismissed_version", version)
    if self._update_banner is not None:
        self._update_banner.destroy()
        self._update_banner = None
```

### Theme-Anbindung

Der Banner verwendet das bestehende Theme-Vokabular (`ACCENT`, `BG`, `TEXT`, `FONT_BOLD`, `icon_button`, `secondary_button` aus `src/theme.py`). Keine neuen Theme-Konstanten nötig. Falls der `ACCENT`-Hintergrund mit dem schwarzen `BG`-Text bei der Implementierung als zu schreiend empfunden wird, ist ein Wechsel auf einen gedämpfteren Ton ein Ein-Zeilen-Edit — nicht hier festgenagelt.

### Lifecycle

`self._update_banner = None` in `__init__` (vor `_proactive_update_check`). Erst `_show_update_banner` legt das Frame an. Nach Dismiss → `destroy()` und zurück auf `None`. Ein zweiter Call sollte nicht passieren (jeder App-Start prüft genau einmal), aber `_show_update_banner` schützt sich defensiv als erste Zeile:

```python
def _show_update_banner(self, release: Release):
    if self._update_banner is not None:
        return
    self._update_banner = tk.Frame(self.root, bg=ACCENT)
    # ... Aufbau wie oben
```

## Fehlerbehandlung

Konsequent **still scheitern** für Update-bezogene Probleme — der User darf nichts merken, wenn der Check schief geht.

| Szenario | Verhalten |
|---|---|
| Offline / DNS / Timeout | `check_latest_release` → `None`, Banner erscheint nicht, `last_update_check_at` bleibt leer (nächster Start prüft wieder) |
| 403 Rate-Limit | gleich wie oben |
| 404 (Repo umbenannt o.ä.) | gleich wie oben |
| 5xx | gleich wie oben |
| Kaputtes JSON / fehlendes `tag_name` | `None` |
| Asset-Match fehlgeschlagen | `pick_asset_url` → `None`, Banner zeigt sich, Button öffnet Release-Page |
| `is_newer` raised (z.B. exotischer Tag) | Worker `except Exception: return`, Banner erscheint nicht |

Keine Logzeile, keine Messagebox. Begründung: ein User, der das Tool dreimal pro Tag öffnet, soll nicht beim Offline-Start eine Fehlermeldung sehen.

## Tests

Neue Datei `tests/test_updater.py`. Keine echten Netzwerk-Calls — alle HTTP-Aufrufe gemockt via `unittest.mock.patch` auf `urllib.request.urlopen`.

### Test-Cases

**`is_newer`:**
- gleich (`1.8.3` vs `1.8.3`) → `False`
- höher (`1.8.3` vs `1.9.0`) → `True`
- niedriger (`1.9.0` vs `1.8.3`) → `False`
- Patch-Sprung (`1.8.3` vs `1.8.10`) → `True` (kein Lex-Vergleich)
- Major (`1.8.3` vs `2.0.0`) → `True`

**`pick_asset_url`:**
- Windows + passendes Asset → korrekte URL
- Darwin + passendes Asset → korrekte URL (mit Version im Namen)
- Linux + passendes Asset → korrekte URL
- Unbekanntes System (`"FreeBSD"`) → `None`
- Plattform passt, Asset fehlt → `None`
- Plattform passt, Version im Asset-Namen mismatcht → `None`

**`should_check_today`:**
- leerer String → `True`
- gestriges Datum → `True`
- heutiges Datum → `False`
- kaputter Wert (`"abc"`) → `True`

**`check_latest_release`:**
- Happy Path: JSON mit `tag_name="v1.9.0"` und 3 Assets → `Release(version="1.9.0", ...)`, v-Prefix gestrippt
- `URLError` → `None`
- `HTTPError(404)` → `None`
- `socket.timeout` → `None`
- Kaputtes JSON → `None`
- JSON ohne `tag_name` → `None`

CI-Workflow `test.yml` muss nichts dazu installieren — alles stdlib. Run lokal: `pytest tests/test_updater.py`.

## Out of scope

- In-App-Download mit Progress-Bar oder Auto-Update.
- Pre-Release-Tracking (`/releases/latest` filtert Pre-Releases bereits raus).
- Update-Check via Settings-Dialog manuell auslösbar machen.
- Opt-out-Checkbox.
- Telemetrie / Logging.
- Intel-Mac- oder ARM-Linux-Asset-Matching (gibt es nicht im Release).
- Versions-Bump und CHANGELOG für dieses Feature — wird im Release-PR gebündelt.
