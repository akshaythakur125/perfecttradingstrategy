from datetime import datetime
from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from services.auth import get_current_user
from models.models import User
from engines.scanner import ScannerEngine
from engines.data_collector import DataCollector

router = APIRouter(prefix="/api/v1/scanner", tags=["scanner"])


@router.get("/scan")
async def scan_market(
    exchange: str = "BINANCE",
    limit: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    collector = DataCollector()
    pairs = await collector.get_top_pairs_by_volume(exchange, limit)

    scanner = ScannerEngine()
    signals = await scanner.scan_all_pairs(pairs, exchange)

    return {
        "scanned_pairs": len(pairs),
        "signals_found": len(signals),
        "signals": signals,
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.get("/pairs")
async def get_available_pairs(
    exchange: str = "BINANCE",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    collector = DataCollector()
    pairs = await collector.get_usdt_pairs(exchange)
    return {"pairs": pairs, "count": len(pairs), "exchange": exchange}
