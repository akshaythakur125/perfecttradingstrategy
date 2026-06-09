from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from uuid import UUID

from database.session import get_db
from models.models import Signal, TradeDirection, SignalStatus
from schemas.schemas import SignalResponse
from services.auth import get_current_user
from models.models import User

router = APIRouter(prefix="/api/v1/signals", tags=["signals"])


@router.get("/", response_model=List[SignalResponse])
async def get_signals(
    limit: int = 20,
    direction: Optional[str] = None,
    min_confidence: Optional[float] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Signal).order_by(desc(Signal.confidence_score)).limit(limit)

    if direction:
        try:
            dir_enum = TradeDirection(direction.upper())
            query = query.where(Signal.direction == dir_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid direction: {direction}")

    if min_confidence is not None:
        query = query.where(Signal.confidence_score >= min_confidence)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/active", response_model=List[SignalResponse])
async def get_active_signals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Signal)
        .where(Signal.status == SignalStatus.ACTIVE)
        .order_by(desc(Signal.confidence_score))
    )
    return result.scalars().all()


@router.get("/{signal_id}", response_model=SignalResponse)
async def get_signal(
    signal_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Signal).where(Signal.id == signal_id))
    signal = result.scalar_one_or_none()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return signal
