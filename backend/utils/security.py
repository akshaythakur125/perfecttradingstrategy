import re
from typing import Optional
from fastapi import HTTPException, status


def sanitize_symbol(symbol: str) -> str:
    cleaned = re.sub(r'[^A-Z0-9]', '', symbol.upper())
    if not cleaned:
        raise HTTPException(status_code=400, detail="Invalid symbol")
    return cleaned


def validate_exchange(exchange: str) -> str:
    exchange = exchange.upper()
    if exchange not in ("BINANCE", "OKX"):
        raise HTTPException(status_code=400, detail=f"Unsupported exchange: {exchange}")
    return exchange


def validate_timeframe(timeframe: str) -> str:
    valid = {"1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "1w", "1M"}
    if timeframe not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid timeframe: {timeframe}")
    return timeframe


def validate_limit(limit: int, max_limit: int = 500) -> int:
    if limit < 1 or limit > max_limit:
        raise HTTPException(status_code=400, detail=f"Limit must be between 1 and {max_limit}")
    return limit


def mask_api_key(key: Optional[str]) -> str:
    if not key:
        return "not_set"
    if len(key) <= 8:
        return "****"
    return key[:4] + "****" + key[-4:]
