import datetime
from src.time_utils import get_week_dates, get_week_label


def test_get_week_dates_regular():
    """KW 14 of 2026: Mon Mar 30 - Sun Apr 5"""
    dates = get_week_dates(2026, 14)
    assert len(dates) == 7
    assert dates[0] == datetime.date(2026, 3, 30)  # Monday
    assert dates[6] == datetime.date(2026, 4, 5)    # Sunday


def test_get_week_dates_year_boundary():
    """KW 1 of 2026 starts on Mon Dec 29, 2025"""
    dates = get_week_dates(2026, 1)
    assert dates[0] == datetime.date(2025, 12, 29)
    assert dates[6] == datetime.date(2026, 1, 4)


def test_get_week_dates_kw53():
    """2020 has KW 53"""
    dates = get_week_dates(2020, 53)
    assert dates[0] == datetime.date(2020, 12, 28)
    assert dates[6] == datetime.date(2021, 1, 3)


def test_get_week_label():
    assert get_week_label(2026, 14) == "KW 14 · 2026"
    assert get_week_label(2020, 53) == "KW 53 · 2020"
