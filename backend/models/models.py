import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text, Enum, JSON, BigInteger, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base
import enum


class TradeDirection(str, enum.Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class TradeStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class SignalStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXECUTED = "EXECUTED"
    EXPIRED = "EXPIRED"
    IGNORED = "IGNORED"


class Timeframe(str, enum.Enum):
    M15 = "15m"
    H4 = "4h"


class Exchange(str, enum.Enum):
    BINANCE = "BINANCE"
    OKX = "OKX"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    settings = relationship("UserSettings", back_populates="user", uselist=False)

    __table_args__ = (
        Index("idx_users_username", "username"),
        Index("idx_users_email", "email"),
    )


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    risk_per_trade = Column(Float, default=0.01)
    max_open_positions = Column(Integer, default=3)
    daily_loss_limit = Column(Float, default=0.03)
    weekly_loss_limit = Column(Float, default=0.08)
    min_risk_reward = Column(Float, default=3.0)
    preferred_exchanges = Column(JSON, default=["BINANCE", "OKX"])
    excluded_pairs = Column(JSON, default=[])
    min_volume_usd = Column(Float, default=1000000)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="settings")

    __table_args__ = (
        Index("idx_user_settings_user_id", "user_id"),
    )


class Trade(Base):
    __tablename__ = "trades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(10), nullable=False)
    direction = Column(Enum(TradeDirection), nullable=False)
    status = Column(Enum(TradeStatus), default=TradeStatus.PENDING, index=True)
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit_1 = Column(Float)
    take_profit_2 = Column(Float)
    take_profit_3 = Column(Float)
    position_size = Column(Float)
    dollar_risk = Column(Float)
    risk_reward = Column(Float)
    margin_required = Column(Float)
    leverage = Column(Float, default=1.0)
    entry_time = Column(DateTime)
    exit_time = Column(DateTime)
    exit_price = Column(Float)
    pnl = Column(Float)
    pnl_percent = Column(Float)
    confidence_score = Column(Float)
    trend_direction = Column(String(50))
    aoi_used = Column(String(50))
    reasons = Column(JSON)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_trades_user_id", "user_id"),
        Index("idx_trades_symbol", "symbol"),
        Index("idx_trades_status", "status"),
        Index("idx_trades_created_at", "created_at"),
    )


class Signal(Base):
    __tablename__ = "signals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(10), nullable=False)
    timeframe_4h = Column(String(10))
    timeframe_15m = Column(String(10))
    direction = Column(Enum(TradeDirection), nullable=False)
    status = Column(Enum(SignalStatus), default=SignalStatus.ACTIVE, index=True)
    confidence_score = Column(Float, index=True)
    entry_price = Column(Float)
    stop_loss = Column(Float)
    take_profit_1 = Column(Float)
    take_profit_2 = Column(Float)
    take_profit_3 = Column(Float)
    risk_reward = Column(Float)
    trend_direction = Column(String(50))
    market_regime = Column(String(50))
    aoi_type = Column(String(50))
    aoi_price_low = Column(Float)
    aoi_price_high = Column(Float)
    aoi_score = Column(Float)
    structure_score = Column(Float)
    volume_score = Column(Float)
    rsi_score = Column(Float)
    obv_score = Column(Float)
    oi_score = Column(Float)
    funding_score = Column(Float)
    reasons = Column(JSON)
    generated_at = Column(DateTime, default=datetime.utcnow)
    expired_at = Column(DateTime)

    __table_args__ = (
        Index("idx_signals_symbol", "symbol"),
        Index("idx_signals_confidence", "confidence_score"),
        Index("idx_signals_status", "status"),
        Index("idx_signals_generated", "generated_at"),
    )


class Backtest(Base):
    __tablename__ = "backtests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(10), nullable=False)
    timeframe_4h = Column(String(10))
    timeframe_15m = Column(String(10))
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    total_trades = Column(Integer)
    winning_trades = Column(Integer)
    losing_trades = Column(Integer)
    win_rate = Column(Float)
    profit_factor = Column(Float)
    sharpe_ratio = Column(Float)
    sortino_ratio = Column(Float)
    max_drawdown = Column(Float)
    cagr = Column(Float)
    average_rr = Column(Float)
    average_holding_time = Column(Float)
    total_pnl = Column(Float)
    initial_capital = Column(Float)
    final_capital = Column(Float)
    equity_curve = Column(JSON)
    monthly_performance = Column(JSON)
    trades = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_backtests_symbol", "symbol"),
        Index("idx_backtests_created", "created_at"),
    )


class MarketData(Base):
    __tablename__ = "market_data"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    exchange = Column(String(10), nullable=False)
    timeframe = Column(String(10), nullable=False)
    timestamp = Column(BigInteger, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    open_interest = Column(Float)
    funding_rate = Column(Float)
    long_short_ratio = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_market_symbol_tf_ts", "symbol", "timeframe", "timestamp"),
        Index("idx_market_exchange", "exchange"),
        Index("idx_market_timestamp", "timestamp"),
    )


class AOI(Base):
    __tablename__ = "aois"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False)
    exchange = Column(String(10), nullable=False)
    timeframe = Column(String(10), nullable=False)
    aoi_type = Column(String(50), nullable=False)
    direction = Column(String(10))
    price_low = Column(Float)
    price_high = Column(Float)
    strength_score = Column(Float)
    reaction_count = Column(Integer)
    volume_confirmation = Column(Float)
    is_fresh = Column(Boolean, default=True)
    liquidity_present = Column(Boolean, default=False)
    created_at = Column(BigInteger)
    updated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_aois_symbol_type", "symbol", "aoi_type"),
        Index("idx_aois_strength", "strength_score"),
    )


class TradeJournal(Base):
    __tablename__ = "trade_journal"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trade_id = Column(UUID(as_uuid=True), ForeignKey("trades.id"), nullable=False, index=True)
    entry_reasoning = Column(Text)
    exit_reasoning = Column(Text)
    mistakes = Column(Text)
    lessons = Column(Text)
    emotions = Column(String(100))
    setup_quality = Column(Integer)
    execution_quality = Column(Integer)
    screenshot_url = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_journal_trade_id", "trade_id"),
    )
