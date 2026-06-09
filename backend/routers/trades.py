from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from uuid import UUID

from database.session import get_db
from models.models import Trade, TradeStatus
from schemas.schemas import TradeResponse
from services.auth import get_current_user
from models.models import User

router = APIRouter(prefix="/api/v1/trades", tags=["trades"])


@router.get("/", response_model=List[TradeResponse])
async def get_trades(
    limit: int = 50,
    status: Optional[str] = None,
    symbol: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Trade).order_by(desc(Trade.created_at)).limit(limit)
    if status:
        try:
            status_enum = TradeStatus(status.upper())
            query = query.where(Trade.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    if symbol:
        query = query.where(Trade.symbol == symbol.upper())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/open", response_model=List[TradeResponse])
async def get_open_trades(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Trade)
        .where(Trade.status == TradeStatus.ACTIVE)
        .order_by(desc(Trade.created_at))
    )
    return result.scalars().all()


@router.get("/{trade_id}", response_model=TradeResponse)
async def get_trade(
    trade_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Trade).where(Trade.id == trade_id))
    trade = result.scalar_one_or_none()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade
