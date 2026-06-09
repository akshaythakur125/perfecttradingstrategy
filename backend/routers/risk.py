from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database.session import get_db
from services.auth import get_current_user
from models.models import User
from schemas.schemas import RiskMetrics
from engines.risk_manager import RiskManager

router = APIRouter(prefix="/api/v1/risk", tags=["risk"])


@router.get("/metrics", response_model=RiskMetrics)
async def get_risk_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rm = RiskManager(account_balance=10000.0)
    return rm.get_risk_metrics()
