from pydantic_settings import BaseSettings
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

    jwt_secret: str = "super-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    max_open_positions: int = 3
    risk_per_trade: float = 0.01
    daily_loss_limit: float = 0.03
    weekly_loss_limit: float = 0.08
    min_risk_reward: float = 3.0

    scanner_scan_interval: int = 60
    websocket_port: int = 8001

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
