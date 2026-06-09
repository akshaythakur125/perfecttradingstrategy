from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class SignalResponse(BaseModel):
    id: UUID
    symbol: str
    exchange: str
    direction: str
    confidence_score: float
    entry_price: float
    stop_loss: float
    take_profit_1: Optional[float] = None
    take_profit_2: Optional[float] = None
    take_profit_3: Optional[float] = None
    risk_reward: Optional[float] = None
    trend_direction: str
    market_regime: Optional[str] = None
    aoi_type: Optional[str] = None
    aoi_price_low: Optional[float] = None
    aoi_price_high: Optional[float] = None
    reasons: Optional[List[str]] = None
    generated_at: datetime

    class Config:
        from_attributes = True


class TradeResponse(BaseModel):
    id: UUID
    symbol: str
    exchange: str
    direction: str
    status: str
    entry_price: float
    stop_loss: float
    take_profit_1: Optional[float] = None
    take_profit_2: Optional[float] = None
    take_profit_3: Optional[float] = None
    position_size: Optional[float] = None
    dollar_risk: Optional[float] = None
    risk_reward: Optional[float] = None
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
    confidence_score: Optional[float] = None
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BacktestResponse(BaseModel):
    id: UUID
    symbol: str
    exchange: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    total_trades: Optional[int] = None
    win_rate: Optional[float] = None
    profit_factor: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    cagr: Optional[float] = None
    average_rr: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ScannerFilter(BaseModel):
    exchanges: Optional[List[str]] = None
    min_volume_usd: Optional[float] = None
    trend_filter: Optional[str] = None
    min_confidence: Optional[float] = 80.0
    max_results: Optional[int] = 50


class BacktestRequest(BaseModel):
    symbol: str = Field(..., description="Trading pair symbol")
    exchange: str = "BINANCE"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    initial_capital: float = 10000.0


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=8, max_length=64)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RiskMetrics(BaseModel):
    daily_pnl: float
    daily_pnl_percent: float
    weekly_pnl: float
    weekly_pnl_percent: float
    open_positions: int
    max_open_positions: int
    daily_loss_limit_hit: bool
    weekly_loss_limit_hit: bool
    current_risk_per_trade: float
    account_balance: Optional[float] = None
