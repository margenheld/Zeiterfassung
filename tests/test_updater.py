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
