import pytest
import numpy as np
import pandas as pd
from datetime import datetime
from engines.indicators import (
    calculate_rsi, calculate_ema, calculate_atr, calculate_obv,
    get_ema_alignment, compute_all_indicators, get_volume_signal
)
from engines.market_structure import (
    find_swing_highs, find_swing_lows, detect_bos, detect_trend,
    classify_market_regime, analyze_market_structure
)
from engines.aoi_detection import (
    find_supply_zones, find_demand_zones, find_order_blocks,
    find_fvgs, detect_all_aois, score_aoi, filter_relevant_aois
)
from engines.signal_engine import SignalEngine
from engines.risk_manager import RiskManager


@pytest.fixture
def sample_ohlcv():
    np.random.seed(42)
    n = 200
    base = 50000
    prices = base + np.cumsum(np.random.randn(n) * 50)
    data = {
        "timestamp": np.arange(n) * 900000,
        "open": prices,
        "high": prices + np.abs(np.random.randn(n) * 20),
        "low": prices - np.abs(np.random.randn(n) * 20),
        "close": prices + np.random.randn(n) * 5,
        "volume": np.abs(np.random.randn(n) * 1000 + 5000),
    }
    df = pd.DataFrame(data)
    for col in ["high", "low", "close"]:
        df[col] = df[col].clip(lower=1)
    return df


class TestIndicators:
    def test_rsi_length(self, sample_ohlcv):
        rsi = calculate_rsi(sample_ohlcv["close"].values, 14)
        assert len(rsi) == len(sample_ohlcv)
        assert all(0 <= v <= 100 for v in rsi)

    def test_rsi_bounds(self):
        prices = np.array([10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25])
        rsi = calculate_rsi(prices, 14)
        assert rsi[-1] > 50

    def test_ema_length(self, sample_ohlcv):
        ema = calculate_ema(sample_ohlcv["close"].values, 20)
        assert len(ema) == len(sample_ohlcv)

    def test_ema_order(self):
        prices = np.array([10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])
        ema20 = calculate_ema(prices, 20)
        ema50 = calculate_ema(prices, 50)
        ema200 = calculate_ema(prices, 200)
        align = get_ema_alignment(ema20, ema50, ema200, -1)
        assert align in ("BULLISH", "BEARISH", "NEUTRAL")

    def test_ema_alignment_tolerance(self):
        prices = np.array([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110])
        ema20 = calculate_ema(prices, 3)
        ema50 = calculate_ema(prices, 5)
        ema200 = calculate_ema(prices, 7)
        align = get_ema_alignment(ema20, ema50, ema200, -1)
        assert isinstance(align, str)

    def test_atr_values(self, sample_ohlcv):
        atr = calculate_atr(sample_ohlcv["high"].values, sample_ohlcv["low"].values, sample_ohlcv["close"].values, 14)
        assert len(atr) == len(sample_ohlcv)
        assert all(v >= 0 for v in atr)

    def test_obv_direction(self):
        close_up = np.array([10, 11, 12, 13, 14, 15])
        vol = np.ones(6) * 100
        obv = calculate_obv(close_up, vol)
        assert obv[-1] > obv[0]

        close_down = np.array([15, 14, 13, 12, 11, 10])
        obv_down = calculate_obv(close_down, vol)
        assert obv_down[-1] < obv_down[0]

    def test_compute_all_indicators(self, sample_ohlcv):
        df = compute_all_indicators(sample_ohlcv)
        assert "rsi" in df.columns
        assert "ema_20" in df.columns
        assert "ema_50" in df.columns
        assert "ema_200" in df.columns
        assert "atr" in df.columns
        assert "obv" in df.columns
        assert "volume_ma" in df.columns
        assert "volume_std" in df.columns
        assert "ema_alignment" in df.columns
        assert "obv_slope" in df.columns

    def test_volume_signal(self):
        vol = np.array([100, 110, 95, 500, 105, 98])
        vol_ma = np.array([100, 105, 103, 150, 140, 130])
        vol_std = np.array([10, 12, 11, 80, 60, 50])
        signal = get_volume_signal(vol, vol_ma, vol_std)
        assert 0 <= signal <= 100


class TestMarketStructure:
    def test_find_swing_highs(self):
        high = np.array([10, 12, 15, 13, 11, 14, 16, 12, 10, 9, 8, 11, 13])
        swings = find_swing_highs(high, 2)
        assert sum(swings > 0) >= 1
        assert all(v in (0, 1) for v in swings)

    def test_find_swing_lows(self):
        low = np.array([10, 9, 7, 8, 9, 11, 10, 6, 7, 8, 9, 10, 12])
        swings = find_swing_lows(low, 2)
        assert sum(swings > 0) >= 1
        assert all(v in (0, 1) for v in swings)

    def test_detect_bos(self):
        high = np.array([10, 11, 12, 13, 14, 15, 16, 17])
        low = np.array([8, 9, 10, 11, 12, 13, 14, 15])
        swing_highs = np.array([0, 0, 0, 0, 0, 0, 0, 1])
        swing_lows = np.array([0, 0, 0, 0, 0, 0, 0, 0])
        bos = detect_bos(high, low, swing_highs, swing_lows)
        assert bos == "NEUTRAL"

    def test_analyze_market_structure(self, sample_ohlcv):
        df = compute_all_indicators(sample_ohlcv)
        structure = analyze_market_structure(df)
        assert "trend" in structure
        assert "regime" in structure
        assert "break_of_structure" in structure
        assert "change_of_character" in structure
        assert "consolidating" in structure
        assert structure["trend"] in ("BULLISH", "BEARISH", "NEUTRAL")


class TestAOIDetection:
    def test_find_supply_zones(self, sample_ohlcv):
        zones = find_supply_zones(
            sample_ohlcv["high"].values,
            sample_ohlcv["low"].values,
            sample_ohlcv["close"].values,
            sample_ohlcv["volume"].values,
            sample_ohlcv["open"].values,
        )
        for z in zones:
            assert z["type"] == "SUPPLY"
            assert z["price_low"] < z["price_high"]
            assert z["strength_score"] <= 100 if "strength_score" in z else True

    def test_find_demand_zones(self, sample_ohlcv):
        zones = find_demand_zones(
            sample_ohlcv["high"].values,
            sample_ohlcv["low"].values,
            sample_ohlcv["close"].values,
            sample_ohlcv["volume"].values,
            sample_ohlcv["open"].values,
        )
        for z in zones:
            assert z["type"] == "DEMAND"
            assert z["price_low"] < z["price_high"]

    def test_find_fvgs(self, sample_ohlcv):
        fvgs = find_fvgs(sample_ohlcv)
        for f in fvgs:
            assert "FVG" in f["type"]
            assert f["gap_size"] > 0

    def test_find_order_blocks(self, sample_ohlcv):
        blocks = find_order_blocks(sample_ohlcv)
        for b in blocks:
            assert "OB" in b["type"]
            assert b["price_low"] < b["price_high"]

    def test_detect_all_aois(self, sample_ohlcv):
        aois = detect_all_aois(sample_ohlcv)
        assert len(aois) > 0
        assert all("strength_score" in a for a in aois)

    def test_filter_relevant_aois_long(self, sample_ohlcv):
        aois = detect_all_aois(sample_ohlcv)
        current_price = sample_ohlcv["close"].iloc[-1]
        relevant = filter_relevant_aois(aois, current_price, "LONG")
        for r in relevant:
            avg_price = (r.get("price_low", current_price) + r.get("price_high", current_price)) / 2
            assert avg_price <= current_price * 1.05

    def test_filter_relevant_aois_short(self, sample_ohlcv):
        aois = detect_all_aois(sample_ohlcv)
        current_price = sample_ohlcv["close"].iloc[-1]
        relevant = filter_relevant_aois(aois, current_price, "SHORT")
        for r in relevant:
            avg_price = (r.get("price_low", current_price) + r.get("price_high", current_price)) / 2
            assert avg_price >= current_price * 0.95

    def test_score_aoi(self):
        aoi = {"type": "SUPPLY", "price_low": 100, "price_high": 105, "reaction_count": 3,
               "volume_confirmation": 2.0, "index": 150}
        scored = score_aoi(aoi, 200)
        assert "strength_score" in scored
        assert 0 <= scored["strength_score"] <= 100


class TestSignalEngine:
    def test_signal_engine_init(self):
        engine = SignalEngine()
        assert engine.min_confidence == 80.0
        assert engine.min_risk_reward >= 3.0

    def test_score_rsi_long(self):
        engine = SignalEngine()
        assert engine._score_rsi(40, "LONG") == 100
        assert engine._score_rsi(50, "LONG") == 80
        assert engine._score_rsi(60, "LONG") == 60
        assert engine._score_rsi(80, "LONG") == 30

    def test_score_rsi_short(self):
        engine = SignalEngine()
        assert engine._score_rsi(75, "SHORT") == 100
        assert engine._score_rsi(65, "SHORT") == 85
        assert engine._score_rsi(55, "SHORT") == 60
        assert engine._score_rsi(25, "SHORT") == 30


class TestRiskManager:
    def test_position_size(self):
        rm = RiskManager(account_balance=10000)
        result = rm.calculate_position_size(50000, 49500)
        assert result["position_size"] > 0
        assert result["dollar_risk"] == 100
        assert result["margin_required"] > 0

    def test_position_size_zero_risk(self):
        rm = RiskManager(account_balance=10000)
        result = rm.calculate_position_size(50000, 50000)
        assert result["position_size"] == 0

    def test_risk_reward_long(self):
        rm = RiskManager()
        rr = rm.calculate_risk_reward(100, 95, 115, "LONG")
        assert rr == 3.0

    def test_risk_reward_short(self):
        rm = RiskManager()
        rr = rm.calculate_risk_reward(100, 105, 85, "SHORT")
        assert rr == 3.0

    def test_daily_loss_limit(self):
        rm = RiskManager(account_balance=10000)
        assert not rm.check_daily_loss_limit()
        rm.record_trade({"pnl": -400, "exit_time": datetime.utcnow().isoformat()})
        assert rm.check_daily_loss_limit()

    def test_weekly_loss_limit(self):
        rm = RiskManager(account_balance=10000)
        assert not rm.check_weekly_loss_limit()
        rm.record_trade({"pnl": -900, "exit_time": datetime.utcnow().isoformat()})
        assert rm.check_weekly_loss_limit()

    def test_can_trade(self):
        rm = RiskManager(account_balance=10000)
        can, msg = rm.can_trade()
        assert can
        assert msg == "OK"

    def test_atr_stop_long(self):
        rm = RiskManager()
        stop = rm.calculate_atr_stop(100, 2.0, "LONG", 50000)
        assert stop == 50000 - 200

    def test_atr_stop_short(self):
        rm = RiskManager()
        stop = rm.calculate_atr_stop(100, 2.0, "SHORT", 50000)
        assert stop == 50000 + 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
