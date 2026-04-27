from datetime import date
from functools import lru_cache

# Code-Label-Paare. Reihenfolge alphabetisch nach Klartext-Label.
STATES: list[tuple[str, str]] = [
    ("", "— kein Bundesland —"),
    ("BW", "Baden-Württemberg"),
    ("BY", "Bayern"),
    ("BE", "Berlin"),
    ("BB", "Brandenburg"),
    ("HB", "Bremen"),
    ("HH", "Hamburg"),
    ("HE", "Hessen"),
    ("MV", "Mecklenburg-Vorpommern"),
    ("NI", "Niedersachsen"),
    ("NW", "Nordrhein-Westfalen"),
    ("RP", "Rheinland-Pfalz"),
    ("SL", "Saarland"),
    ("SN", "Sachsen"),
    ("ST", "Sachsen-Anhalt"),
    ("SH", "Schleswig-Holstein"),
    ("TH", "Thüringen"),
]

_VALID_CODES = {code for code, _ in STATES if code}


@lru_cache(maxsize=64)
def get_holidays(state_code: str, year: int) -> dict[date, str]:
    """Liefert {date: name} für gewähltes Bundesland und Jahr.

    Leerer oder ungültiger Code → leeres Dict (silent fallback,
    damit ein versehentlich falsch gespeicherter Code keinen Crash auslöst).
    """
    if state_code not in _VALID_CODES:
        return {}
    import holidays
    return dict(holidays.Germany(subdiv=state_code, years=year))
