from typing import List, Dict, Optional
import asyncio
from datetime import datetime
from engines.signal_engine import SignalEngine
from engines.data_collector import DataCollector
import pandas as pd


class ScannerEngine:
    def __init__(self):
        self.signal_engine = SignalEngine()
        self.data_collector = DataCollector()
        self.signals: List[Dict] = []
        self.scanning = False

    async def scan_symbol(self, symbol: str, exchange: str = "BINANCE") -> Optional[Dict]:
        try:
            df_4h = await self.data_collector.get_klines(
                symbol=symbol,
                exchange=exchange,
                timeframe="4h",
                limit=200,
            )
            df_15m = await self.data_collector.get_klines(
                symbol=symbol,
                exchange=exchange,
                timeframe="15m",
                limit=200,
            )

            if df_4h is None or df_15m is None or len(df_4h) < 50 or len(df_15m) < 50:
                return None

            df_4h["symbol"] = symbol
            df_4h["exchange"] = exchange
            df_15m["symbol"] = symbol
            df_15m["exchange"] = exchange

            try:
                oi_change = await self.data_collector.get_open_interest_change(symbol, exchange)
            except Exception:
                oi_change = None

            try:
                funding_rate = await self.data_collector.get_funding_rate(symbol, exchange)
            except Exception:
                funding_rate = None

            long_signal = self.signal_engine.evaluate_long_setup(
                df_4h, df_15m, oi_change_pct=oi_change, funding_rate=funding_rate
            )
            if long_signal:
                return long_signal

            short_signal = self.signal_engine.evaluate_short_setup(
                df_4h, df_15m, oi_change_pct=oi_change, funding_rate=funding_rate
            )
            if short_signal:
                return short_signal

        except Exception:
            return None

        return None

    async def scan_top_perpetuals(self, exchange: str = "BINGX", top_n: int = 200) -> List[Dict]:
        """Discover the top-N perpetuals by 24h volume on the exchange and scan
        each with the active strategy. Read-only; no API key required."""
        pairs = await self.data_collector.get_top_pairs_by_volume(exchange, top_n)
        return await self.scan_all_pairs(pairs, exchange)

    async def scan_all_pairs(self, pairs: List[str], exchange: str = "BINANCE") -> List[Dict]:
        sem = asyncio.Semaphore(10)
        async def bounded_scan(pair):
            async with sem:
                return await self.scan_symbol(pair, exchange)

        tasks = [bounded_scan(pair) for pair in pairs]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        signals = []
        for result in results:
            if isinstance(result, dict) and result:
                signals.append(result)

        signals.sort(key=lambda x: x["confidence_score"], reverse=True)
        self.signals = signals
        return signals

    def get_top_signals(self, limit: int = 10) -> List[Dict]:
        return self.signals[:limit]

    def filter_signals(self, min_confidence: float = 80, min_rr: float = 3.0,
                       direction: Optional[str] = None, exchange: Optional[str] = None) -> List[Dict]:
        filtered = [s for s in self.signals if s.get("confidence_score", 0) >= min_confidence and s.get("risk_reward", 0) >= min_rr]

        if direction:
            filtered = [s for s in filtered if s.get("direction") == direction]
        if exchange:
            filtered = [s for s in filtered if s.get("exchange", "").upper() == exchange.upper()]

        return filtered
