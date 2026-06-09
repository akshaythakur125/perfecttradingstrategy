from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database.session import get_db
from services.auth import get_current_user
from models.models import User, Trade, TradeStatus, UserSettings
from schemas.schemas import RiskMetrics
from engines.risk_manager import RiskManager

router = APIRouter(prefix="/api/v1/risk", tags=["risk"])


@router.get("/metrics", response_model=RiskMetrics)
async def get_risk_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    settings_result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    user_settings = settings_result.scalar_one_or_none()

    balance = 10000.0
    max_positions = user_settings.max_open_positions if user_settings else 3
    risk_per_trade = user_settings.risk_per_trade if user_settings else 0.01
    daily_loss_limit = user_settings.daily_loss_limit if user_settings else 0.03
    weekly_loss_limit = user_settings.weekly_loss_limit if user_settings else 0.08

    rm = RiskManager(account_balance=balance)

    today_trades = await db.execute(
        select(Trade).where(
            Trade.user_id == current_user.id,
            Trade.status == TradeStatus.CLOSED,
        )
    )
    for trade in today_trades.scalars().all():
        if trade.exit_time:
            rm.record_trade({
                "pnl": trade.pnl or 0,
                "exit_time": trade.exit_time.isoformat(),
            })

    open_positions_result = await db.execute(
        select(Trade).where(
            Trade.user_id == current_user.id,
            Trade.status == TradeStatus.ACTIVE,
        )
    )
    open_positions = open_positions_result.scalars().all()

    metrics = rm.get_risk_metrics()
    metrics["max_open_positions"] = max_positions
    metrics["current_risk_per_trade"] = risk_per_trade
    return metrics
