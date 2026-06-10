from typing import Optional, List, Dict
import pandas as pd
from engines.exchange_clients import BinanceClient, OKXClient, BingXClient


class DataCollector:
    def __init__(self):
        self.binance = BinanceClient()
        self.okx = OKXClient()
        self.bingx = BingXClient()
        self.clients = {
            "BINANCE": self.binance,
            "OKX": self.okx,
            "BINGX": self.bingx,
        }

    async def get_klines(self, symbol: str, exchange: str = "BINANCE",
                         timeframe: str = "15m", limit: int = 200) -> Optional[pd.DataFrame]:
        client = self.clients.get(exchange.upper())
        if not client:
            return None
        return await client.get_klines(symbol, timeframe, limit)

    async def get_usdt_pairs(self, exchange: str = "BINANCE") -> List[str]:
        client = self.clients.get(exchange.upper())
        if not client:
            return []
        return await client.get_usdt_pairs()

    async def get_funding_rate(self, symbol: str, exchange: str = "BINANCE") -> Optional[float]:
        client = self.clients.get(exchange.upper())
        if not client or not hasattr(client, "get_funding_rate"):
            return None
        return await client.get_funding_rate(symbol)

    async def get_open_interest_change(self, symbol: str, exchange: str = "BINANCE") -> Optional[float]:
        client = self.clients.get(exchange.upper())
        if not client or not hasattr(client, "get_open_interest_hist"):
            return None
        hist = await client.get_open_interest_hist(symbol, period="15m", limit=2)
        if hist and len(hist) >= 2:
            current = float(hist[0]["sumOpenInterest"])
            previous = float(hist[1]["sumOpenInterest"])
            if previous > 0:
                return ((current - previous) / previous) * 100
        return None

    async def get_open_interest(self, symbol: str, exchange: str = "BINANCE") -> Optional[float]:
        client = self.clients.get(exchange.upper())
        if not client or not hasattr(client, "get_open_interest"):
            return None
        return await client.get_open_interest(symbol)

    async def get_market_snapshot(self, symbol: str, exchange: str = "BINANCE") -> Dict:
        client = self.clients.get(exchange.upper())
        if not client:
            return {}

        data = {"symbol": symbol, "exchange": exchange}

        if hasattr(client, "get_funding_rate"):
            data["funding_rate"] = await client.get_funding_rate(symbol)

        if hasattr(client, "get_open_interest"):
            data["open_interest"] = await client.get_open_interest(symbol)

        if hasattr(client, "get_open_interest_hist"):
            data["oi_change_pct"] = await self.get_open_interest_change(symbol, exchange)

        if hasattr(client, "get_24hr_ticker"):
            ticker = await client.get_24hr_ticker(symbol)
            if ticker:
                data["volume_24h"] = float(ticker.get("volume", 0))
                data["price_change_24h"] = float(ticker.get("priceChangePercent", 0))

        return data

    async def get_top_pairs_by_volume(self, exchange: str = "BINANCE", top_n: int = 50) -> List[str]:
        client = self.clients.get(exchange.upper())
        if client and hasattr(client, "get_top_pairs_by_volume"):
            return await client.get_top_pairs_by_volume(top_n)
        pairs = await self.get_usdt_pairs(exchange)
        return pairs[:top_n]
