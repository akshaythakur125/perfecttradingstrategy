from pydantic_settings import BaseSettings
from pydantic import field_validator, Field
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "PerfectTradingStrategy"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/perfecttrading"
    redis_url: str = "redis://localhost:6379/0"

    binance_api_key: Optional[str] = None
    binance_secret_key: Optional[str] = None
    binance_testnet: bool = True

    okx_api_key: Optional[str] = None
    okx_secret_key: Optional[str] = None
    okx_passphrase: Optional[str] = None
    okx_testnet: bool = True

    # BingX: only needed for private/order endpoints. Public market-data
    # scanning (klines/tickers) requires no credentials.
    bingx_api_key: Optional[str] = None
    bingx_secret_key: Optional[str] = None

    jwt_secret: str = "super-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=60, ge=15, le=1440)

    max_open_positions: int = Field(default=3, ge=1, le=50)
    risk_per_trade: float = Field(default=0.01, ge=0.001, le=0.1)
    daily_loss_limit: float = Field(default=0.03, ge=0.01, le=0.5)
    weekly_loss_limit: float = Field(default=0.08, ge=0.02, le=1.0)
    min_risk_reward: float = Field(default=3.0, ge=1.0, le=10.0)

    scanner_scan_interval: int = Field(default=60, ge=10, le=3600)
    websocket_port: int = 8001

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if v in ("super-secret-key-change-in-production", "change-me", "secret"):
            import warnings
            warnings.warn("JWT_SECRET is set to a default value. Change it in production!")
        if len(v) < 16:
            raise ValueError("JWT_SECRET must be at least 16 characters long")
        return v

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if v.startswith("sqlite"):
            return v
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must use asyncpg driver")
        return v

    @field_validator("binance_api_key")
    @classmethod
    def validate_binance_key(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v) < 10:
            raise ValueError("BINANCE_API_KEY appears to be invalid (too short)")
        return v

    @field_validator("okx_api_key")
    @classmethod
    def validate_okx_key(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v) < 10:
            raise ValueError("OKX_API_KEY appears to be invalid (too short)")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
