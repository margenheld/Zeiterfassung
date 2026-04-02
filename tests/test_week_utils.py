import datetime
from src.time_utils import get_week_dates, get_week_label, week_spans_months


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


def test_get_week_label_spans_months():
    """KW 14 of 2026 spans March/April"""
    assert get_week_label(2026, 14) == "KW 14 · 30.03. – 05.04.2026"


def test_get_week_label_same_month():
    """KW 15 of 2026 is fully within April"""
    assert get_week_label(2026, 15) == "KW 15 · 06.04. – 12.04.2026"


def test_get_week_label_year_boundary():
    """KW 1 of 2026 spans Dec 2025 / Jan 2026"""
    assert get_week_label(2026, 1) == "KW 1 · 29.12.2025 – 04.01.2026"


def test_week_spans_months_true():
    assert week_spans_months(2026, 14) is True  # Mar/Apr


def test_week_spans_months_false():
    assert week_spans_months(2026, 15) is False  # fully in April
