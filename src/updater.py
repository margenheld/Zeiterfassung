"""Update-Check gegen GitHub-Releases (stdlib-only).

Single Purpose: Netzwerk-Call, Versions-Vergleich, Asset-Match, Throttle.
Keine Tk-Imports; UI-Layer ruft die Funktionen aus einem Worker-Thread.
"""

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
