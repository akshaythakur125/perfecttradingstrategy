import pytest
from services.auth import hash_password, verify_password, create_access_token
from jose import jwt
from config.settings import settings
from uuid import UUID
from utils.security import sanitize_symbol, validate_exchange, validate_timeframe, validate_limit, mask_api_key
from fastapi import HTTPException


class TestAuthService:
    def test_hash_password(self):
        pw = "testPass123"
        hashed = hash_password(pw)
        assert hashed != pw
        assert hashed.startswith("$2b$")

    def test_verify_password_correct(self):
        pw = "testPass123"
        hashed = hash_password(pw)
        assert verify_password(pw, hashed)

    def test_verify_password_incorrect(self):
        pw = "testPass123"
        hashed = hash_password(pw)
        assert not verify_password("wrong", hashed)

    def test_create_access_token(self):
        token = create_access_token({"sub": "test-user-id"})
        assert isinstance(token, str)
        assert len(token.split(".")) == 3

    def test_token_decodable(self):
        token = create_access_token({"sub": "test-user-id"})
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        assert payload["sub"] == "test-user-id"
        assert "exp" in payload

    def test_token_with_expiry(self):
        from datetime import timedelta
        token = create_access_token({"sub": "test"}, expires_delta=timedelta(hours=1))
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        assert payload["sub"] == "test"


class TestSecurityUtils:
    def test_sanitize_symbol(self):
        assert sanitize_symbol("btcusdt") == "BTCUSDT"
        assert sanitize_symbol(" eth / usdt ") == "ETHUSDT"

    def test_sanitize_symbol_empty(self):
        with pytest.raises(HTTPException):
            sanitize_symbol("")

    def test_validate_exchange(self):
        assert validate_exchange("binance") == "BINANCE"
        assert validate_exchange("okx") == "OKX"

    def test_validate_exchange_invalid(self):
        with pytest.raises(HTTPException):
            validate_exchange("coinbase")

    def test_validate_timeframe(self):
        assert validate_timeframe("15m") == "15m"
        assert validate_timeframe("4h") == "4h"

    def test_validate_timeframe_invalid(self):
        with pytest.raises(HTTPException):
            validate_timeframe("13m")

    def test_validate_limit(self):
        assert validate_limit(50) == 50
        assert validate_limit(1) == 1

    def test_validate_limit_too_low(self):
        with pytest.raises(HTTPException):
            validate_limit(0)

    def test_validate_limit_too_high(self):
        with pytest.raises(HTTPException):
            validate_limit(1000)

    def test_mask_api_key(self):
        assert mask_api_key("abc123def456") == "abc1****f456"

    def test_mask_api_key_none(self):
        assert mask_api_key(None) == "not_set"

    def test_mask_api_key_short(self):
        assert mask_api_key("abc") == "****"
