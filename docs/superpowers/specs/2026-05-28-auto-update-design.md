# Auto-Update: Direkter Download + Installation

**Datum:** 2026-05-28
**Status:** Design freigegeben, Implementierung ausstehend
**Scope:** Windows + Linux. macOS bleibt beim aktuellen Verhalten (`webbrowser.open(release.html_url)`).

## Ziel

Klick auf den Download-Button im Update-Banner soll die neue Version direkt herunterladen und installieren, statt nur die GitHub-Release-Seite im Browser zu öffnen.

## Nicht-Ziele

- Hintergrund-Downloads ohne Nutzerinteraktion
- Auto-Update auf macOS (erfordert Code-Signing / Notarisierung)
- Delta-Updates
- Eigene Update-Server-Infrastruktur (GitHub-Releases-API genügt)
- Rollback-Mechanismus (Installer bzw. AppImage liefern dies bereits implizit über Reinstall des alten Assets)

## UX-Flow

1. Nutzer klickt im Banner auf "Download".
2. Modaler Dialog öffnet sich mit:
   - Versionsnummer
   - Changelog (Release-Body von GitHub als reiner Text in scrollbarem `tk.Text`, readonly)
   - Buttons: "Abbrechen" / "Jetzt installieren"
3. Klick "Jetzt installieren" → Dialog wechselt in Download-State: Progressbar, Byte-Anzeige, "Abbrechen"-Button.
4. Bei Erfolg: App schließt sich, Installer läuft, neue Version startet automatisch.
5. Bei Fehler: `messagebox.showerror` mit kurzer Message. Dialog kehrt in State 1 zurück, ergänzt um "Im Browser öffnen"-Button als Fallback.
6. Auf Plattformen ohne Auto-Install-Pfad (macOS, Linux-Repo-Modus): Dialog wird gar nicht erst geöffnet, `webbrowser.open(release.html_url)` wie bisher.

## Architektur

Trennung in pure Logik (testbar, ohne Tk) und UI-Schicht.

| Pfad | Verantwortung | Tk-Abhängigkeit |
|------|---------------|-----------------|
| `src/update/__init__.py` | Re-exports der öffentlichen API | Keine |
| `src/update/release.py` | GitHub-API-Layer: `check_latest_release`, `is_newer`, `should_check_today`, `today_iso`, `pick_asset`, Dataclasses `Asset` und `Release`. Migriert aus `src/updater.py`. | Keine |
| `src/update/installer.py` | Download mit Progress-Callback, SHA256-Verifikation, Plattform-Dispatch | Keine |
| `src/dialogs/update_dialog.py` | Modaler Tk-Dialog: Changelog, Progressbar, Fehlerbehandlung, Worker-Thread-Spawn | Tk |
| `src/ui.py` | `_open_update_download` ruft `show_update_dialog` statt `webbrowser.open` | Tk |
| `installer.iss` | Zweite `[Run]`-Zeile für Restart nach Silent-Install, `CloseApplications=force` | — |

### Migration des bestehenden `src/updater.py`

- `git mv src/updater.py src/update/release.py`
- Neues `src/update/__init__.py` mit Re-exports
- Importpfade in `src/ui.py` und `tests/test_updater.py` (umbenannt in `tests/test_release.py`) auf `src.update` umstellen
- Vor Beginn der Implementierung: `grep -rn "from src.updater\|from src import updater\|src\.updater" src/ tests/` ausführen, um vollständige Caller-Liste zu erhalten (gemäß CLAUDE.md "Refactor-Caller-Grep")
- Kein Kompat-Shim — App startet immer als Modul, alle Imports sind absolut

## Datenmodell

**`Asset`** (erweitert):

```python
@dataclass(frozen=True)
class Asset:
    name: str
    url: str
    digest: str | None      # NEU: "sha256:<hex>" oder None bei alten Releases
    size: int               # NEU: für Progressbar-Anzeige
```

**`Release`** (erweitert):

```python
@dataclass(frozen=True)
class Release:
    version: str
    html_url: str
    body: str               # NEU: Changelog-Markdown von GitHub
    assets: tuple[Asset, ...]
```

GitHub-Releases-API liefert `digest` seit ca. 2024 als Top-Level-Feld pro Asset im Format `"sha256:<hex>"`. Fehlt das Feld → `None`, kein Fehler (alte Releases bleiben kompatibel).

**`pick_asset`** (Umbenennung):
- Ersetzt das bisherige `pick_asset_url`.
- Liefert das `Asset`-Objekt statt nur die URL, damit der Caller Zugriff auf `digest` und `size` hat.
- Einziger Call-Site (`ui.py:308`) wird mitmigriert. Kein Wrapper für Backwards-Compat.

## Datenfluss: Klick → Restart

```
[Banner: "Download"-Klick]
        │
        ▼
ui._open_update_download(release)
        │  prüft installer.can_auto_install(); wenn nein → webbrowser.open(release.html_url)
        ▼
dialogs.update_dialog.show_update_dialog(parent, release)
        │  modaler Dialog, State 1
        ▼
[Klick "Jetzt installieren"]
        │  Dialog wechselt in State 2 (Progressbar)
        │  Worker-Thread spawn (daemon)
        ▼
installer.download_and_install(release, on_progress, cancel_event)
        │
        ├─ 1. asset = pick_asset(release.assets, system, version)
        │     → None: InstallError("Für diese Plattform ist kein Installer im Release.")
        │
        ├─ 2. _download(asset.url, tmp_path, asset.size, on_progress, cancel_event)
        │     → urllib.request.urlopen + Chunk-Loop (8 KiB)
        │     → on_progress(bytes_done, bytes_total) pro Chunk, im UI-Thread via root.after
        │     → cancel_event.is_set() → InstallError("abgebrochen"), tmp gelöscht
        │     → URLError/OSError/HTTPError → InstallError mit lesbarer Message, tmp gelöscht
        │
        ├─ 3. _verify_sha256(tmp_path, asset.digest)
        │     → digest None: Log-Warning, weitermachen
        │     → digest-Format ungültig (kein "sha256:"-Prefix): InstallError
        │     → Hash mismatch: tmp gelöscht, InstallError("Sicherheitsprüfung fehlgeschlagen ...")
        │
        ├─ 4. Plattform-Dispatch:
        │     Windows: _install_windows(tmp_path)
        │       subprocess.Popen([tmp, "/VERYSILENT", "/SUPPRESSMSGBOXES",
        │                         "/CLOSEAPPLICATIONS", "/FORCECLOSEAPPLICATIONS",
        │                         "/NORESTART"],
        │                        creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
        │                        close_fds=True)
        │       → Inno Setup wartet auf File-Lock-Freigabe, ersetzt Exe,
        │         startet neue Instanz via [Run] in installer.iss
        │
        │     Linux:   _install_linux(tmp_path)
        │       appimage = os.environ.get("APPIMAGE")
        │       if not appimage or not os.access(dirname(appimage), os.W_OK):
        │           raise InstallError("...")
        │       shutil.move(tmp_path, appimage + ".new")
        │       os.chmod(appimage + ".new", 0o755)
        │       os.replace(appimage + ".new", appimage)
        │       subprocess.Popen([appimage], start_new_session=True, close_fds=True)
        │
        ▼
Dialog erhält on_complete(error=None|InstallError) via root.after(0, ...)
        │
        ├─ error is None:
        │     root.destroy() — App beendet sich, Installer übernimmt
        │
        └─ error:
              messagebox.showerror mit error.message
              State 1 + "Im Browser öffnen"-Button (öffnet release.html_url)
              Hash-Mismatch-Spezialfall: nur "Schließen", kein Browser-Fallback
              (Nutzer nicht auf potenziell kompromittierten Pfad lenken)
```

**Threading-Regel** (analog zu `ui._proactive_update_check` heute): Netzwerk und `subprocess.Popen` im Worker-Thread, alle Tk-Aufrufe über `root.after(0, ...)`. Worker ist Daemon, damit App-Beenden nicht durch hängende Sockets blockiert wird.

**Cancel-Pfad**: Während Download setzt der Dialog ein `threading.Event`; der Download-Loop prüft pro Chunk. Nach Hash-Check ist Abbrechen nicht mehr sinnvoll — der Installer läuft als separater Prozess.

## API-Konturen

### `src/update/release.py`

```python
@dataclass(frozen=True)
class Asset:
    name: str
    url: str
    digest: str | None
    size: int

@dataclass(frozen=True)
class Release:
    version: str
    html_url: str
    body: str
    assets: tuple[Asset, ...]

def is_newer(current: str, latest: str) -> bool: ...
def today_iso() -> str: ...
def should_check_today(last_check: str | None, today: date | None = None) -> bool: ...
def pick_asset(assets, system: str, latest_version: str) -> Asset | None: ...
def check_latest_release(repo: str, timeout: float = 5.0) -> Release | None: ...
```

### `src/update/installer.py`

```python
class InstallError(Exception):
    """Nutzerlesbare deutsche Message in args[0]."""

def can_auto_install() -> bool:
    """True, wenn die laufende App Auto-Install unterstützt.
    Windows: immer True.
    Linux: True wenn $APPIMAGE gesetzt und schreibbar.
    macOS: immer False.
    Repo-Modus (nicht frozen): immer False — Auto-Install ergibt nur
    Sinn im gebauten Artefakt."""

def download_and_install(
    release: Release,
    on_progress: Callable[[int, int], None],
    cancel_event: threading.Event,
) -> None:
    """Blockierend. Wirft InstallError bei jedem Fehler.
    Bei Erfolg: subprocess.Popen ist gestartet, Caller muss App beenden."""

# Private, aber per Modul-Pfad testbar:
def _download(url, dest, expected_size, on_progress, cancel_event) -> None: ...
def _verify_sha256(path, expected_digest) -> None: ...
def _install_windows(setup_exe) -> None: ...
def _install_linux(appimage_path) -> None: ...
```

### `src/dialogs/update_dialog.py`

```python
def show_update_dialog(parent, release: Release) -> None:
    """Modaler Dialog. Kümmert sich um:
    - Worker-Thread-Spawn für Download
    - Progress-Updates via root.after
    - Fehlerbehandlung mit Browser-Fallback
    - App-Beendigung bei Erfolg (root.destroy)"""
```

## Anpassung `installer.iss`

```ini
[Setup]
...
CloseApplications=force        ; NEU: ohne Dialog die Exe killen, falls noch Locks bestehen
RestartApplications=no         ; NEU: wir kontrollieren Restart selbst

[Run]
Filename: "{app}\Zeiterfassung.exe"; Description: "Zeiterfassung jetzt starten"; Flags: nowait postinstall skipifsilent
Filename: "{app}\Zeiterfassung.exe"; Flags: nowait runasoriginaluser    ; NEU: Restart bei Silent-Install
```

Begründung der zweiten Zeile: Die erste `[Run]`-Zeile mit `Flags: postinstall skipifsilent` greift im interaktiven Setup-Modus (Checkbox am Ende des Wizards). Bei `/VERYSILENT` wird sie übersprungen — wir brauchen daher eine zweite Zeile, die im Silent-Modus aktiv wird, damit die App nach Installation automatisch wieder startet.

`runasoriginaluser` stellt sicher, dass die neue Instanz mit den Rechten des ursprünglichen Nutzers läuft (relevant falls der Installer durch UAC eskaliert wäre — bei unserem `PrivilegesRequired=lowest`-Setup normalerweise nicht der Fall, aber defensiv).

## Fehlerbehandlung

Alle Fehler werden als `InstallError` mit deutscher, nutzerlesbarer Message gewrappt. Worker übergibt sie an den Dialog via `root.after(0, ...)`.

| Fehler | Quelle | Message | Recovery |
|--------|--------|---------|----------|
| Kein Plattform-Asset | `pick_asset() is None` | "Für diese Plattform ist kein Installer im Release." | Browser-Fallback |
| Netzwerk / Timeout | `URLError`, `OSError` in `_download` | "Download fehlgeschlagen: Netzwerkproblem." | Browser-Fallback |
| HTTP-Fehler (4xx/5xx) | `HTTPError` | "Download fehlgeschlagen: Server-Fehler (HTTP {code})." | Browser-Fallback |
| Disk voll / Permission | `OSError` beim Schreiben | "Download fehlgeschlagen: Datei konnte nicht gespeichert werden." | Browser-Fallback |
| Hash-Mismatch | `_verify_sha256` | "Sicherheitsprüfung fehlgeschlagen — Datei wurde unterwegs verändert." | **Kein** Browser-Fallback (nicht auf kompromittierten Pfad lenken) |
| Hash fehlt im API-Response | `asset.digest is None` | Kein Fehler — Log-Warning, weitermachen | — |
| AppImage-Pfad nicht beschreibbar | `_install_linux` | "AppImage liegt in einem schreibgeschützten Verzeichnis ({path})." | Browser-Fallback |
| `$APPIMAGE` nicht gesetzt | `_install_linux` | "Auto-Update funktioniert nur in der gepackten AppImage." | Browser-Fallback |
| `subprocess.Popen` schlägt fehl | Setup.exe nicht startbar | "Installer konnte nicht gestartet werden." | Browser-Fallback |
| Cancel durch Nutzer | `cancel_event.is_set()` | Kein Fehler — Dialog kehrt in State 1 zurück, Temp gelöscht | — |

**Logging**: Jeder `InstallError`-Pfad loggt zusätzlich via `logging.getLogger(__name__).exception(...)`, sodass Detail-Trace im File-Log (`logs/`) landet. Im UI bleibt die kurze deutsche Message sichtbar.

**Worker während App-Schließen**: Daemon-Thread → wird mit dem Prozess beendet. Temp-Datei bleibt liegen, wird vom OS aufgeräumt (`%TEMP%` / `/tmp`).

## Tests

### Migration: `tests/test_updater.py` → `tests/test_release.py`

Bestehende Tests inhaltlich erhalten, nur Imports auf `src.update.release` umstellen.

Neue Tests im selben File:
- `check_latest_release` parsed `digest` und `size` aus dem Asset-Payload
- `check_latest_release` toleriert fehlendes `digest`-Feld → `Asset.digest is None`
- `check_latest_release` parsed `body` aus dem Release-Payload
- `pick_asset` liefert `Asset`-Objekt (nicht nur URL), respektiert Plattform-Mapping

### Neu: `tests/test_installer.py`

- `_verify_sha256` mit korrektem Hash → kein Fehler
- `_verify_sha256` mit falschem Hash → `InstallError`
- `_verify_sha256` mit `digest=None` → kein Fehler, Log-Warning (caplog assert)
- `_verify_sha256` mit ungültigem Digest-Format → `InstallError`
- `_download` mit gemocktem `urlopen`: schreibt Chunks, ruft `on_progress` mit kumulierten Bytes
- `_download` mit `cancel_event.set()` mitten im Loop: bricht ab, Temp gelöscht, `InstallError("abgebrochen")`
- `_download` mit `URLError`: `InstallError`, Temp gelöscht
- `_install_windows` Smoke: `subprocess.Popen` mit erwarteten Args aufgerufen (mock)
- `_install_linux` Smoke: gleiche Logik
- `_install_linux` ohne `$APPIMAGE` → `InstallError`
- `_install_linux` mit read-only Parent-Dir → `InstallError` (skip auf Windows)
- `can_auto_install` Matrix: Windows/Linux+APPIMAGE/Linux ohne APPIMAGE/Darwin/non-frozen

### Bewusst nicht getestet

`src/dialogs/update_dialog.py` — Tk-Dialoge unit-testen rentiert sich nicht. Manuelle Verifikation per Checkliste im PR.

### CI-Kompatibilität

Alle neuen Tests sind pure Python ohne Plattform-Abhängigkeit (`subprocess.Popen` gemockt, `urlopen` gemockt, `tempfile` portabel). Läuft auf bestehendem Ubuntu-CI ohne zusätzliche Dependencies. Keine Änderungen an `.github/workflows/test.yml` nötig.

## Manuelle Verifikation vor Merge

PR-Body als Checkliste:

- [ ] Windows: Installer baut (`python build.py`), Banner erscheint nach simuliertem alten `version.py`, "Jetzt installieren" → App schließt → neue Version startet
- [ ] Windows: Kein UAC-Prompt während Silent-Install
- [ ] Linux: Gleiche Probe in einer gepackten AppImage (nicht Repo-Modus)
- [ ] Beide: Hash-Mismatch (per Hand Temp-Datei korrumpieren) → Sicherheitsdialog ohne Browser-Fallback
- [ ] Beide: Netzwerk-Abbruch (Wifi aus während Download) → Fehlerdialog mit Browser-Fallback
- [ ] Linux Repo-Modus: Klick auf "Download" öffnet weiterhin Browser (kein Dialog)
- [ ] macOS: Verhalten unverändert (Browser öffnet sich)

## Security-Erwägungen

- **SHA256-Verifikation** des Downloads gegen den `digest` aus der GitHub-API. Schutz gegen Korruption und gegen Cache-Vergiftung auf dem Übertragungsweg.
- **Hash-Mismatch hat keinen Browser-Fallback**: wenn der Hash falsch ist, könnte ein Angreifer im Netzwerk auch die Release-Seite manipulieren. Wir leiten den Nutzer nicht weiter, sondern lassen ihn bewusst neu starten.
- **Keine eigene Signatur-Infrastruktur**: GitHub-Compromise würde uns ohnehin erwischen (der Key müsste über GitHub verteilt werden). Vermeidet Key-Management-Overhead ohne realen Sicherheitsgewinn.
- **Code-Signing der Binaries** ist außerhalb des Scopes dieses Specs — wäre eine separate Initiative für alle drei Plattformen.

## Offene Punkte (außerhalb Scope)

- macOS-Auto-Update erfordert Code-Signing + Notarisierung → eigener Spec
- Windows-Code-Signing-Zertifikat würde SmartScreen-Warnungen reduzieren → eigener Spec
- Delta-Updates → nur sinnvoll wenn Installer-Größe ein echtes Problem wird (aktuell ~30 MB)
