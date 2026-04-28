from datetime import date

from src.updater import is_newer, should_check_today, today_iso


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
