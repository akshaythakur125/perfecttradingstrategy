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


class BingXClient(BaseExchangeClient):
    """BingX USDT-M perpetual swap client.

    Market-data endpoints used for scanning are PUBLIC and need no API key.
    Credentials (settings.bingx_*) are only required for private/account or
    order-placement endpoints (signing helper provided for future use).

    Note: built to BingX's documented swap API; exact JSON field names should
    be confirmed against a live response, as this environment cannot reach the
    exchange. Parsing is defensive about dict-vs-list response shapes.
    """
    BASE_URL = "https://open-api.bingx.com"
    VALID_INTERVALS = {"1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h",
                       "6h", "8h", "12h", "1d", "3d", "1w", "1M"}

    def __init__(self):
        super().__init__()
        self.api_key = settings.bingx_api_key
        self.secret_key = settings.bingx_secret_key

    @staticmethod
    def _to_bingx_symbol(symbol: str) -> str:
        """Internal 'BTCUSDT' -> BingX 'BTC-USDT'."""
        s = symbol.upper()
        if "-" in s:
            return s
        if s.endswith("USDT"):
            return f"{s[:-4]}-USDT"
        return s

    @staticmethod
    def _from_bingx_symbol(symbol: str) -> str:
        """BingX 'BTC-USDT' -> internal 'BTCUSDT'."""
        return symbol.upper().replace("-", "")

    @staticmethod
    def _unwrap(data):
        """BingX wraps payloads as {code, msg, data: ...}; return the data part."""
        if isinstance(data, dict):
            return data.get("data", data)
        return data

    async def get_klines(self, symbol: str, interval: str, limit: int = 200,
                         start_time: Optional[int] = None,
                         end_time: Optional[int] = None) -> Optional[pd.DataFrame]:
        if interval not in self.VALID_INTERVALS:
            return None
        url = f"{self.BASE_URL}/openApi/swap/v3/quote/klines"
        params = {"symbol": self._to_bingx_symbol(symbol), "interval": interval, "limit": min(limit, 1440)}
        if start_time is not None:
            params["startTime"] = int(start_time)
        if end_time is not None:
            params["endTime"] = int(end_time)
        data = await self._request(url, params)
        rows = self._unwrap(data)
        if not rows:
            return None
        return self._parse_klines(rows)

    def _parse_klines(self, rows: List) -> pd.DataFrame:
        recs = []
        for k in rows:
            if isinstance(k, dict):
                ts = k.get("time", k.get("T", k.get("t")))
                recs.append({
                    "timestamp": int(ts),
                    "open": float(k["open"]), "high": float(k["high"]),
                    "low": float(k["low"]), "close": float(k["close"]),
                    "volume": float(k["volume"]),
                })
            else:  # array form [time, open, high, low, close, volume]
                recs.append({
                    "timestamp": int(k[0]), "open": float(k[1]), "high": float(k[2]),
                    "low": float(k[3]), "close": float(k[4]), "volume": float(k[5]),
                })
        df = pd.DataFrame(recs)
        if df.empty:
            return df
        return df.sort_values("timestamp").reset_index(drop=True)[
            ["timestamp", "open", "high", "low", "close", "volume"]
        ]

    async def get_contracts(self) -> List[Dict]:
        url = f"{self.BASE_URL}/openApi/swap/v2/quote/contracts"
        return self._unwrap(await self._request(url)) or []

    async def get_usdt_pairs(self) -> List[str]:
        pairs = []
        for c in await self.get_contracts():
            sym = c.get("symbol", "")
            if sym.endswith("-USDT") and c.get("status", 1) in (1, "1", True):
                pairs.append(self._from_bingx_symbol(sym))
        return pairs

    async def get_24hr_ticker(self, symbol: Optional[str] = None):
        url = f"{self.BASE_URL}/openApi/swap/v2/quote/ticker"
        params = {"symbol": self._to_bingx_symbol(symbol)} if symbol else None
        return await self._request(url, params)

    async def get_top_pairs_by_volume(self, top_n: int = 200) -> List[str]:
        rows = self._unwrap(await self.get_24hr_ticker()) or []
        ranked = []
        for t in rows:
            sym = t.get("symbol", "")
            if not sym.endswith("-USDT"):
                continue
            qv = float(t.get("quoteVolume") or t.get("volume") or 0)
            ranked.append((self._from_bingx_symbol(sym), qv))
        ranked.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in ranked[:top_n]]

    async def get_funding_rate(self, symbol: str) -> Optional[float]:
        url = f"{self.BASE_URL}/openApi/swap/v2/quote/premiumIndex"
        d = self._unwrap(await self._request(url, {"symbol": self._to_bingx_symbol(symbol)}))
        if isinstance(d, list) and d:
            d = d[0]
        try:
            return float(d["lastFundingRate"])
        except (TypeError, KeyError, ValueError):
            return None

    async def get_open_interest(self, symbol: str) -> Optional[float]:
        url = f"{self.BASE_URL}/openApi/swap/v2/quote/openInterest"
        d = self._unwrap(await self._request(url, {"symbol": self._to_bingx_symbol(symbol)}))
        if isinstance(d, list) and d:
            d = d[0]
        try:
            return float(d["openInterest"])
        except (TypeError, KeyError, ValueError):
            return None

    def _sign(self, params: Dict) -> tuple:
        """HMAC-SHA256 signing for private endpoints (orders/account)."""
        query = "&".join(f"{k}={params[k]}" for k in sorted(params))
        signature = hmac.new(
            (self.secret_key or "").encode(), query.encode(), hashlib.sha256
        ).hexdigest()
        return query, signature
