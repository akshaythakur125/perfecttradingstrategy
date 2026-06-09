from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List
from uuid import UUID
from datetime import datetime

from database.session import get_db
from models.models import Backtest
from schemas.schemas import BacktestResponse, BacktestRequest
from engines.backtest_engine import BacktestEngine
from engines.data_collector import DataCollector
from services.auth import get_current_user
from models.models import User

router = APIRouter(prefix="/api/v1/backtest", tags=["backtest"])


@router.post("/run", response_model=BacktestResponse)
async def run_backtest(
    req: BacktestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    collector = DataCollector()
    df_4h = await collector.get_klines(req.symbol, req.exchange, "4h", 500)
    df_15m = await collector.get_klines(req.symbol, req.exchange, "15m", 2000)

    if df_4h is None or df_15m is None:
        raise HTTPException(status_code=400, detail="Failed to fetch market data")

    engine = BacktestEngine(slippage_pct=0.001, fee_pct=0.0004)
    results = engine.run_backtest(df_4h, df_15m, req.initial_capital)

    start_ts = df_4h.iloc[0].get("timestamp")
    end_ts = df_4h.iloc[-1].get("timestamp")

    backtest = Backtest(
        symbol=req.symbol.upper(),
        exchange=req.exchange.upper(),
        timeframe_4h="4h",
        timeframe_15m="15m",
        start_date=req.start_date or (datetime.fromtimestamp(start_ts / 1000) if isinstance(start_ts, (int, float)) else datetime.utcnow()),
        end_date=req.end_date or (datetime.fromtimestamp(end_ts / 1000) if isinstance(end_ts, (int, float)) else datetime.utcnow()),
        total_trades=results["total_trades"],
        winning_trades=results["winning_trades"],
        losing_trades=results["losing_trades"],
        win_rate=results["win_rate"],
        profit_factor=results["profit_factor"],
        sharpe_ratio=results["sharpe_ratio"],
        sortino_ratio=results["sortino_ratio"],
        max_drawdown=results["max_drawdown"],
        cagr=results["cagr"],
        average_rr=results["average_rr"],
        average_holding_time=results["average_holding_time"],
        total_pnl=results["total_pnl"],
        initial_capital=req.initial_capital,
        final_capital=results["final_capital"],
        equity_curve=results["equity_curve"],
        monthly_performance=results["monthly_performance"],
        trades=results["trades"],
    )
    db.add(backtest)
    await db.commit()
    await db.refresh(backtest)
    return backtest


@router.get("/history", response_model=List[BacktestResponse])
async def get_backtest_history(
    limit: int = 20,
    symbol: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Backtest).order_by(desc(Backtest.created_at)).limit(limit)
    if symbol:
        query = query.where(Backtest.symbol == symbol.upper())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{backtest_id}", response_model=BacktestResponse)
async def get_backtest(
    backtest_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Backtest).where(Backtest.id == backtest_id))
    backtest = result.scalar_one_or_none()
    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return backtest
