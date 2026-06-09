import hmac
import hashlib
import time
import json
import re
import asyncio
from typing import Optional, Dict, List
import aiohttp
import pandas as pd
from datetime import datetime
from config.settings import settings


class RateLimiter:
    def __init__(self, max_calls: int = 10, period: float = 1.0):
        self.max_calls = max_calls
        self.period = period
        self.calls: List[float] = []

    async def acquire(self):
        now = time.time()
        self.calls = [c for c in self.calls if now - c < self.period]
        if len(self.calls) >= self.max_calls:
            sleep_time = self.calls[0] + self.period - now
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        self.calls.append(time.time())

    def __call__(self, func):
        async def wrapper(*args, **kwargs):
            await self.acquire()
            return await func(*args, **kwargs)
        return wrapper


class BaseExchangeClient:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter = RateLimiter(max_calls=20, period=1.0)

    async def ensure_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def _request(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        await self.rate_limiter.acquire()
        await self.ensure_session()
        for attempt in range(3):
            try:
                async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 429:
                        retry_after = int(resp.headers.get("Retry-After", 2))
                        await asyncio.sleep(retry_after)
                        continue
                    if resp.status != 200:
                        return None
                    return await resp.json()
            except (asyncio.TimeoutError, aiohttp.ClientError):
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                continue
        return None


class BinanceClient(BaseExchangeClient):
    BASE_URL = "https://api.binance.com"
    FUTURES_URL = "https://fapi.binance.com"

    def __init__(self):
        super().__init__()
        self.api_key = settings.binance_api_key
        self.secret_key = settings.binance_secret_key

    async def get_klines(self, symbol: str, interval: str, limit: int = 200) -> Optional[pd.DataFrame]:
        valid_intervals = {"1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "1w", "1M"}
        if interval not in valid_intervals:
            return None

        url = f"{self.FUTURES_URL}/fapi/v1/klines"
        params = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
        data = await self._request(url, params)
        if data is None:
            return None
        return self._parse_klines(data)

    async def get_24hr_ticker(self, symbol: str) -> Optional[Dict]:
        url = f"{self.FUTURES_URL}/fapi/v1/ticker/24hr"
        params = {"symbol": symbol.upper()}
        return await self._request(url, params)

    async def get_exchange_info(self) -> Optional[List[Dict]]:
        url = f"{self.FUTURES_URL}/fapi/v1/exchangeInfo"
        data = await self._request(url)
        if data is None:
            return None
        return data.get("symbols", [])

    async def get_funding_rate(self, symbol: str) -> Optional[float]:
        url = f"{self.FUTURES_URL}/fapi/v1/fundingRate"
        params = {"symbol": symbol.upper(), "limit": 1}
        data = await self._request(url, params)
        if data and len(data) > 0:
            return float(data[0]["fundingRate"])
        return None

    async def get_open_interest(self, symbol: str) -> Optional[float]:
        url = f"{self.FUTURES_URL}/fapi/v1/openInterest"
        params = {"symbol": symbol.upper()}
        data = await self._request(url, params)
        if data:
            return float(data["openInterest"])
        return None

    async def get_open_interest_hist(self, symbol: str, period: str = "15m", limit: int = 2) -> Optional[List[Dict]]:
        url = f"{self.FUTURES_URL}/futures/data/openInterestHist"
        params = {"symbol": symbol.upper(), "period": period, "limit": limit}
        return await self._request(url, params)

    async def get_top_long_short_ratio(self, symbol: str) -> Optional[Dict]:
        url = f"{self.FUTURES_URL}/futures/data/globalLongShortAccountRatio"
        params = {"symbol": symbol.upper(), "period": "15m", "limit": 1}
        data = await self._request(url, params)
        if data and len(data) > 0:
            return data[0]
        return None

    async def get_usdt_pairs(self) -> List[str]:
        info = await self.get_exchange_info()
        if not info:
            return []
        return [
            s["symbol"] for s in info
            if s["symbol"].endswith("USDT") and s["status"] == "TRADING"
        ]

    def _parse_klines(self, data: List) -> pd.DataFrame:
        df = pd.DataFrame(data, columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "count", "taker_buy_volume",
            "taker_buy_quote_volume", "ignore"
        ])
        df["timestamp"] = df["timestamp"].astype("int64")
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        return df[["timestamp", "open", "high", "low", "close", "volume"]]


class OKXClient(BaseExchangeClient):
    BASE_URL = "https://www.okx.com"

    def __init__(self):
        super().__init__()
        self.api_key = settings.okx_api_key
        self.secret_key = settings.okx_secret_key
        self.passphrase = settings.okx_passphrase

    async def get_klines(self, symbol: str, interval: str, limit: int = 200) -> Optional[pd.DataFrame]:
        valid_intervals = {"1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
                           "1h": "1H", "2h": "2H", "4h": "4H", "6h": "6H", "1d": "1D", "1w": "1W"}
        mapped = valid_intervals.get(interval)
        if mapped is None:
            return None

        inst_id = self._to_okx_symbol(symbol)
        url = f"{self.BASE_URL}/api/v5/market/history-candles"
        params = {"instId": inst_id, "bar": mapped, "limit": limit}
        data = await self._request(url, params)
        if data is None:
            return None
        return self._parse_klines(data.get("data", []))

    def _to_okx_symbol(self, symbol: str) -> str:
        match = re.match(r'^(.+?)USDT$', symbol.upper())
        if match:
            base = match.group(1)
            return f"{base}-USDT-SWAP"
        return f"{symbol}-USDT-SWAP"

    def _parse_klines(self, data: List) -> pd.DataFrame:
        df = pd.DataFrame(data, columns=[
            "timestamp", "open", "high", "low", "close", "volume", "vol_ccy", "vol_quote", "confirm"
        ])
        df["timestamp"] = df["timestamp"].astype("int64")
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        return df[["timestamp", "open", "high", "low", "close", "volume"]]

    async def get_usdt_pairs(self) -> List[str]:
        url = f"{self.BASE_URL}/api/v5/public/instruments"
        params = {"instType": "SWAP"}
        data = await self._request(url, params)
        if data is None:
            return []
        pairs = []
        for inst in data.get("data", []):
            if "USDT" in inst.get("instId", "") and inst.get("state") == "live":
                cleaned = inst["instId"].replace("-SWAP", "").replace("-", "")
                pairs.append(cleaned)
        return pairs
