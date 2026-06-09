import pytest
from config.settings import settings


class TestSettings:
    def test_settings_have_defaults(self):
        assert settings.app_name == "PerfectTradingStrategy"
        assert settings.max_open_positions >= 1
        assert settings.risk_per_trade > 0

    def test_settings_jwt_values(self):
        assert settings.jwt_algorithm == "HS256"
        assert settings.access_token_expire_minutes >= 15

    def test_settings_risk_values(self):
        assert 0.001 <= settings.risk_per_trade <= 0.1
        assert 0.01 <= settings.daily_loss_limit <= 0.5
        assert 0.02 <= settings.weekly_loss_limit <= 1.0
        assert 1.0 <= settings.min_risk_reward <= 10.0

    def test_settings_scanner(self):
        assert 10 <= settings.scanner_scan_interval <= 3600
