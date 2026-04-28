from datetime import date

from src.updater import Asset, is_newer, pick_asset_url, should_check_today, today_iso


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


def _three_assets(version: str) -> list[Asset]:
    return [
        Asset(name="Zeiterfassung_Setup.exe", url="https://example.com/exe"),
        Asset(name=f"Zeiterfassung-{version}-arm64.dmg", url="https://example.com/dmg"),
        Asset(name=f"Zeiterfassung-{version}-x86_64.AppImage", url="https://example.com/appimage"),
    ]


class TestPickAssetUrl:
    def test_windows_picks_exe(self):
        assets = _three_assets("1.9.0")
        assert pick_asset_url(assets, "Windows", "1.9.0") == "https://example.com/exe"

    def test_darwin_picks_arm_dmg(self):
        assets = _three_assets("1.9.0")
        assert pick_asset_url(assets, "Darwin", "1.9.0") == "https://example.com/dmg"

    def test_linux_picks_appimage(self):
        assets = _three_assets("1.9.0")
        assert pick_asset_url(assets, "Linux", "1.9.0") == "https://example.com/appimage"

    def test_unknown_system_returns_none(self):
        assets = _three_assets("1.9.0")
        assert pick_asset_url(assets, "FreeBSD", "1.9.0") is None

    def test_missing_asset_returns_none(self):
        assets = [Asset(name="Zeiterfassung-1.9.0-x86_64.AppImage", url="u")]
        assert pick_asset_url(assets, "Windows", "1.9.0") is None

    def test_version_mismatch_in_dmg_name_returns_none(self):
        assets = [Asset(name="Zeiterfassung-1.8.0-arm64.dmg", url="u")]
        assert pick_asset_url(assets, "Darwin", "1.9.0") is None
