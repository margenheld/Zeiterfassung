"""Update-Check gegen GitHub-Releases (stdlib-only).

Single Purpose: Netzwerk-Call, Versions-Vergleich, Asset-Match, Throttle.
Keine Tk-Imports; UI-Layer ruft die Funktionen aus einem Worker-Thread.
"""

from dataclasses import dataclass
from datetime import date


def _to_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def is_newer(current: str, latest: str) -> bool:
    """True, wenn `latest` strikt neuer ist als `current`. Beide ohne v-Prefix."""
    return _to_tuple(latest) > _to_tuple(current)


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
