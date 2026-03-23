import datetime
import pytest
from src.report import generate_report

def test_empty_entries():
    html = generate_report(datetime.date(2026, 3, 1), datetime.date(2026, 3, 31), {})
    assert html is None

def test_single_entry():
    entries = {
        "2026-03-23": {"start": "08:00", "end": "16:30", "pause": 30}
    }
    html = generate_report(datetime.date(2026, 3, 1), datetime.date(2026, 3, 31), entries)
    assert "01.03.2026 – 31.03.2026" in html
    assert "23.03.2026" in html
    assert "Mo" in html
    assert "08:00" in html
    assert "16:30" in html
    assert "8.0h" in html
    assert "<table" in html
    # Dark mode styling
    assert "#0f172a" in html
    assert "#00D8A7" in html

def test_multiple_entries_sorted():
    entries = {
        "2026-03-25": {"start": "09:00", "end": "17:00", "pause": 30},
        "2026-03-23": {"start": "08:00", "end": "16:30", "pause": 30},
    }
    html = generate_report(datetime.date(2026, 3, 1), datetime.date(2026, 3, 31), entries)
    pos_23 = html.index("23.03.2026")
    pos_25 = html.index("25.03.2026")
    assert pos_23 < pos_25

def test_total_hours():
    entries = {
        "2026-03-23": {"start": "08:00", "end": "16:30", "pause": 30},
        "2026-03-24": {"start": "09:00", "end": "17:00", "pause": 60},
    }
    html = generate_report(datetime.date(2026, 3, 1), datetime.date(2026, 3, 31), entries)
    assert "15.0h" in html

def test_filters_outside_range():
    entries = {
        "2026-03-23": {"start": "08:00", "end": "16:30", "pause": 0},
        "2026-04-01": {"start": "09:00", "end": "17:00", "pause": 0},
    }
    html = generate_report(datetime.date(2026, 3, 1), datetime.date(2026, 3, 31), entries)
    assert "23.03.2026" in html
    assert "01.04.2026" not in html

def test_legacy_entry_no_pause():
    entries = {
        "2026-03-23": {"start": "08:00", "end": "16:30"}
    }
    html = generate_report(datetime.date(2026, 3, 1), datetime.date(2026, 3, 31), entries)
    assert "8.5h" in html

def test_cross_month_range():
    entries = {
        "2026-02-20": {"start": "08:00", "end": "16:00", "pause": 0},
        "2026-03-05": {"start": "09:00", "end": "17:00", "pause": 0},
        "2026-03-20": {"start": "08:00", "end": "16:00", "pause": 0},
    }
    html = generate_report(datetime.date(2026, 2, 15), datetime.date(2026, 3, 14), entries)
    assert "20.02.2026" in html
    assert "05.03.2026" in html
    assert "20.03.2026" not in html

def test_inclusive_boundaries():
    entries = {
        "2026-03-01": {"start": "08:00", "end": "16:00", "pause": 0},
        "2026-03-15": {"start": "08:00", "end": "16:00", "pause": 0},
        "2026-03-16": {"start": "08:00", "end": "16:00", "pause": 0},
    }
    html = generate_report(datetime.date(2026, 3, 1), datetime.date(2026, 3, 15), entries)
    assert "01.03.2026" in html
    assert "15.03.2026" in html
    assert "16.03.2026" not in html

def test_alternating_row_colors():
    entries = {
        "2026-03-23": {"start": "08:00", "end": "16:00", "pause": 0},
        "2026-03-24": {"start": "08:00", "end": "16:00", "pause": 0},
    }
    html = generate_report(datetime.date(2026, 3, 1), datetime.date(2026, 3, 31), entries)
    assert "#1e293b" in html
    assert "#243347" in html
