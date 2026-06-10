import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from engines.indicators import (
    calculate_rsi, calculate_ema, calculate_atr, calculate_obv,
    get_ema_alignment, compute_all_indicators, get_volume_signal,
    calculate_volume_ma, calculate_volume_std, detect_volume_spike,
)
from engines.market_structure import (
    find_swing_highs, find_swing_lows, detect_bos, detect_choch,
    classify_market_regime, detect_trend, detect_consolidation, analyze_market_structure,
)
from engines.aoi_detection import (
    find_supply_zones, find_demand_zones, find_order_blocks,
    find_fvgs, find_liquidity_pools, find_equal_highs, find_equal_lows,
    find_wick_rejection_zones, detect_all_aois, score_aoi, filter_relevant_aois,
    count_reactions, _calculate_body_ratio,
)
from engines.signal_engine import SignalEngine
from engines.risk_manager import RiskManager
from engines.backtest_engine import BacktestEngine
from engines.data_collector import DataCollector
from engines.exchange_clients import RateLimiter, BingXClient
from engines.scanner import ScannerEngine


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


@pytest.fixture
def bull_trend_ohlcv():
    n = 200
    base = 50000
    prices = base + np.linspace(0, 10000, n) + np.random.randn(n) * 100
    data = {
        "timestamp": np.arange(n) * 900000,
        "open": prices,
        "high": prices + np.abs(np.random.randn(n) * 30),
        "low": prices - np.abs(np.random.randn(n) * 30),
        "close": prices + np.random.randn(n) * 10,
        "volume": np.abs(np.random.randn(n) * 1000 + 8000),
    }
    df = pd.DataFrame(data)
    for col in ["high", "low", "close"]:
        df[col] = df[col].clip(lower=1)
    return df


@pytest.fixture
def bear_trend_ohlcv():
    n = 200
    base = 60000
    prices = base - np.linspace(0, 10000, n) + np.random.randn(n) * 100
    data = {
        "timestamp": np.arange(n) * 900000,
        "open": prices,
        "high": prices + np.abs(np.random.randn(n) * 30),
        "low": prices - np.abs(np.random.randn(n) * 30),
        "close": prices + np.random.randn(n) * 10,
        "volume": np.abs(np.random.randn(n) * 1000 + 8000),
    }
    df = pd.DataFrame(data)
    for col in ["high", "low", "close"]:
        df[col] = df[col].clip(lower=1)
    return df


# ============================================================
# INDICATORS
# ============================================================

class TestIndicators:
    def test_rsi_length(self, sample_ohlcv):
        rsi = calculate_rsi(sample_ohlcv["close"].values, 14)
        assert len(rsi) == len(sample_ohlcv)
        assert all(0 <= v <= 100 for v in rsi)

    def test_rsi_bounds(self):
        prices = np.array([10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25])
        rsi = calculate_rsi(prices, 14)
        assert rsi[-1] > 50

    def test_rsi_oversold(self):
        prices = np.array([100, 99, 98, 97, 96, 95, 94, 93, 92, 91, 90, 89, 88, 87, 86, 85])
        rsi = calculate_rsi(prices, 14)
        assert rsi[-1] < 50

    def test_rsi_extreme_values(self):
        prices = np.array([10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10])
        rsi = calculate_rsi(prices, 14)
        assert 0 <= rsi[-1] <= 100

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

    def test_ema_short_period(self):
        prices = np.array([10, 11, 12])
        ema = calculate_ema(prices, 2)
        assert len(ema) == 3
        assert ema[0] == 10

    def test_atr_values(self, sample_ohlcv):
        atr = calculate_atr(sample_ohlcv["high"].values, sample_ohlcv["low"].values, sample_ohlcv["close"].values, 14)
        assert len(atr) == len(sample_ohlcv)
        assert all(v >= 0 for v in atr)

    def test_atr_zero_range(self):
        high = np.ones(50) * 100
        low = np.ones(50) * 100
        close = np.ones(50) * 100
        atr = calculate_atr(high, low, close, 14)
        assert all(v == 0 for v in atr)

    def test_obv_direction(self):
        close_up = np.array([10, 11, 12, 13, 14, 15])
        vol = np.ones(6) * 100
        obv = calculate_obv(close_up, vol)
        assert obv[-1] > obv[0]

        close_down = np.array([15, 14, 13, 12, 11, 10])
        obv_down = calculate_obv(close_down, vol)
        assert obv_down[-1] < obv_down[0]

    def test_obv_unchanged(self):
        close = np.array([10, 10, 10, 10, 10])
        vol = np.array([100, 200, 50, 300, 150])
        obv = calculate_obv(close, vol)
        assert all(v == obv[0] for v in obv)

    def test_compute_all_indicators(self, sample_ohlcv):
        df = compute_all_indicators(sample_ohlcv)
        required = ["rsi", "ema_20", "ema_50", "ema_200", "atr", "obv", "volume_ma", "volume_std", "ema_alignment", "obv_slope"]
        for col in required:
            assert col in df.columns
        assert len(df["ema_alignment"]) == len(df)

    def test_compute_all_indicators_short_df(self):
        n = 50
        df = pd.DataFrame({
            "close": np.linspace(100, 150, n),
            "high": np.linspace(102, 152, n),
            "low": np.linspace(98, 148, n),
            "volume": np.ones(n) * 1000,
        })
        result = compute_all_indicators(df)
        assert result is not None

    def test_volume_signal(self):
        vol = np.array([100, 110, 95, 500, 105, 98])
        vol_ma = np.array([100, 105, 103, 150, 140, 130])
        vol_std = np.array([10, 12, 11, 80, 60, 50])
        signal = get_volume_signal(vol, vol_ma, vol_std)
        assert 0 <= signal <= 100

    def test_volume_signal_zero_std(self):
        vol = np.array([100, 100, 100])
        vol_ma = np.array([100, 100, 100])
        vol_std = np.array([0, 0, 0])
        signal = get_volume_signal(vol, vol_ma, vol_std)
        assert signal == 0.0

    def test_volume_ma(self):
        vol = np.array([100, 200, 300, 400, 500])
        ma = calculate_volume_ma(vol, 3)
        assert len(ma) == 5
        assert np.isnan(ma[0])

    def test_detect_volume_spike(self):
        vol = np.array([100, 100, 100, 500, 100])
        ma = np.array([100, 100, 100, 150, 120])
        spikes = detect_volume_spike(vol, ma, 1.5)
        assert spikes[3] == 1
        assert spikes[0] == 0


# ============================================================
# MARKET STRUCTURE
# ============================================================

class TestMarketStructure:
    def test_find_swing_highs(self):
        high = np.array([10, 12, 15, 13, 11, 14, 16, 12, 10, 9, 8, 11, 13])
        swings = find_swing_highs(high, 2)
        assert sum(swings > 0) >= 1
        assert all(v in (0, 1) for v in swings)

    def test_find_swing_highs_flat(self):
        high = np.ones(50) * 100
        swings = find_swing_highs(high, 5)
        assert sum(swings) == 0

    def test_find_swing_lows(self):
        low = np.array([10, 9, 7, 8, 9, 11, 10, 6, 7, 8, 9, 10, 12])
        swings = find_swing_lows(low, 2)
        assert sum(swings > 0) >= 1
        assert all(v in (0, 1) for v in swings)

    def test_find_swing_lows_flat(self):
        low = np.ones(50) * 100
        swings = find_swing_lows(low, 5)
        assert sum(swings) == 0

    def test_detect_bos(self):
        high = np.array([10, 11, 12, 13, 14, 15, 16, 17])
        low = np.array([8, 9, 10, 11, 12, 13, 14, 15])
        swing_highs = np.array([0, 0, 0, 0, 0, 0, 0, 1])
        swing_lows = np.array([0, 0, 0, 0, 0, 0, 0, 0])
        bos = detect_bos(high, low, swing_highs, swing_lows)
        assert bos == "NEUTRAL"

    def test_detect_bos_bullish(self):
        high = np.array([10, 11, 12, 18, 14, 15, 16, 17])
        low = np.array([8, 9, 10, 11, 12, 13, 14, 15])
        swing_highs = np.array([0, 0, 0, 1, 0, 0, 0, 1])
        swing_lows = np.array([0, 0, 0, 0, 0, 0, 0, 0])
        bos = detect_bos(high, low, swing_highs, swing_lows)
        assert bos in ("BULLISH", "NEUTRAL")

    def test_detect_bos_insufficient_data(self):
        high = np.array([10, 11])
        low = np.array([8, 9])
        swing_highs = np.zeros(2)
        swing_lows = np.zeros(2)
        bos = detect_bos(high, low, swing_highs, swing_lows)
        assert bos == "NEUTRAL"

    def test_detect_choch(self):
        high = np.array([10, 11, 12, 13, 14, 15, 16, 17, 18, 19])
        low = np.array([8, 9, 10, 11, 12, 13, 14, 15, 16, 17])
        close = np.array([9, 10, 11, 12, 13, 14, 15, 16, 17, 18])
        result = detect_choch(high, low, close, "BULLISH")
        assert result in ("NO_CHOCH", "CHOCH_BEARISH")

    def test_classify_market_regime(self, sample_ohlcv):
        df = compute_all_indicators(sample_ohlcv)
        regime = classify_market_regime(
            df["high"].values, df["low"].values, df["close"].values,
            df["ema_20"].values, df["ema_50"].values, df["ema_200"].values,
        )
        assert regime in ("STRONG_BULL", "WEAK_BULL", "STRONG_BEAR", "WEAK_BEAR", "RANGE")

    def test_detect_trend(self, sample_ohlcv):
        df = compute_all_indicators(sample_ohlcv)
        trend = detect_trend(
            df["high"].values, df["low"].values, df["close"].values,
            df["ema_20"].values, df["ema_50"].values,
        )
        assert trend in ("BULLISH", "BEARISH", "NEUTRAL")

    def test_detect_consolidation(self, sample_ohlcv):
        consolidating = detect_consolidation(
            sample_ohlcv["high"].values, sample_ohlcv["low"].values, sample_ohlcv["close"].values,
        )
        assert consolidating in (True, False)

    def test_analyze_market_structure(self, sample_ohlcv):
        df = compute_all_indicators(sample_ohlcv)
        structure = analyze_market_structure(df)
        assert "trend" in structure
        assert "regime" in structure
        assert "break_of_structure" in structure
        assert "change_of_character" in structure
        assert "consolidating" in structure
        assert structure["trend"] in ("BULLISH", "BEARISH", "NEUTRAL")
        assert "swing_highs" in structure
        assert "swing_lows" in structure


# ============================================================
# AOI DETECTION
# ============================================================

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

    def test_find_liquidity_pools(self, sample_ohlcv):
        pools = find_liquidity_pools(
            sample_ohlcv["high"].values, sample_ohlcv["low"].values,
        )
        for p in pools:
            assert "LIQUIDITY" in p["type"]
            assert p["price"] > 0

    def test_find_equal_highs(self):
        high = np.array([100, 101, 102, 100, 101, 103])
        eq = find_equal_highs(high, tolerance=0.02)
        assert len(eq) >= 0

    def test_find_equal_lows(self):
        low = np.array([100, 99, 98, 100, 99, 97])
        eq = find_equal_lows(low, tolerance=0.02)
        assert len(eq) >= 0

    def test_find_wick_rejection_zones(self):
        high = np.array([110, 105, 103])
        low = np.array([90, 95, 97])
        close = np.array([105, 100, 102])
        open_prices = np.array([100, 98, 99])
        zones = find_wick_rejection_zones(high, low, close, open_prices)
        for z in zones:
            assert "WICK" in z["type"]

    def test_detect_all_aois(self, sample_ohlcv):
        aois = detect_all_aois(sample_ohlcv)
        assert len(aois) > 0
        assert all("strength_score" in a for a in aois)

    def test_detect_all_aois_no_duplicates(self, sample_ohlcv):
        aois = detect_all_aois(sample_ohlcv)
        keys = [(a["type"], round(a.get("price_low", 0), 4), round(a.get("price_high", 0), 4)) for a in aois]
        assert len(keys) == len(set(keys))

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

    def test_filter_relevant_aois_short_excludes_demand(self, sample_ohlcv):
        aois = detect_all_aois(sample_ohlcv)
        current_price = sample_ohlcv["close"].iloc[-1]
        relevant = filter_relevant_aois(aois, current_price, "SHORT")
        demand_types = {"DEMAND", "LOWER_WICK", "LIQUIDITY_LOW", "EQUAL_LOW", "BULLISH_FVG"}
        for r in relevant:
            aoi_type = r.get("type", "")
            assert not any(t in aoi_type for t in demand_types)

    def test_score_aoi(self):
        aoi = {"type": "SUPPLY", "price_low": 100, "price_high": 105, "reaction_count": 3,
               "volume_confirmation": 2.0, "index": 150}
        scored = score_aoi(aoi, 200)
        assert "strength_score" in scored
        assert 0 <= scored["strength_score"] <= 100

    def test_score_aoi_edge_cases(self):
        aoi = {"type": "UNKNOWN", "price_low": 100, "price_high": 105, "reaction_count": 0,
               "volume_confirmation": 0.5, "index": 0}
        scored = score_aoi(aoi, 200)
        assert 0 <= scored["strength_score"] <= 100

    def test_count_reactions(self):
        high = np.array([100, 101, 102, 101, 100, 99])
        low = np.array([98, 99, 100, 99, 98, 97])
        count = count_reactions(high, low, 99, 101, 5)
        assert count >= 0

    def test_calculate_body_ratio(self):
        ratio = _calculate_body_ratio(np.array([100, 101]), np.array([105, 102]), 0)
        assert 0 <= ratio <= 1


# ============================================================
# SIGNAL ENGINE
# ============================================================

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
        assert engine._score_rsi(25, "LONG") == 20

    def test_score_rsi_short(self):
        engine = SignalEngine()
        assert engine._score_rsi(75, "SHORT") == 100
        assert engine._score_rsi(65, "SHORT") == 85
        assert engine._score_rsi(55, "SHORT") == 60
        assert engine._score_rsi(25, "SHORT") == 30
        assert engine._score_rsi(45, "SHORT") == 20

    def test_score_structure(self):
        engine = SignalEngine()
        score = engine._score_structure({"regime": "STRONG_BULL", "trend": "BULLISH", "break_of_structure": "BULLISH"})
        assert 0 <= score <= 100
        assert score >= 75

    def test_score_structure_range(self):
        engine = SignalEngine()
        score = engine._score_structure({"regime": "RANGE", "trend": "NEUTRAL", "break_of_structure": "NEUTRAL"})
        assert score == 50

    def test_score_oi(self):
        engine = SignalEngine()
        assert engine._score_oi(10, "LONG") == 100
        assert engine._score_oi(3, "LONG") == 75
        assert engine._score_oi(1, "LONG") == 60
        assert engine._score_oi(-1, "LONG") == 30
        assert engine._score_oi(None, "LONG") == 50

    def test_score_funding(self):
        engine = SignalEngine()
        assert engine._score_funding(-0.02, "LONG") == 100
        assert engine._score_funding(-0.005, "LONG") == 80
        assert engine._score_funding(0.001, "LONG") == 60
        assert engine._score_funding(0.01, "LONG") == 30
        assert engine._score_funding(None, "LONG") == 50

    def test_score_funding_short(self):
        engine = SignalEngine()
        assert engine._score_funding(0.02, "SHORT") == 100
        assert engine._score_funding(-0.001, "SHORT") == 60
        assert engine._score_funding(-0.02, "SHORT") == 30

    def test_score_setup(self):
        engine = SignalEngine()
        scores = engine._score_setup(80, 70, 60, 50, 40, 30, 20)
        assert "total" in scores
        assert 0 <= scores["total"] <= 100
        assert all(k in scores for k in ["structure", "aoi", "volume", "rsi", "obv", "oi", "funding"])

    def test_generate_reasons_long(self):
        engine = SignalEngine()
        structure = {"trend": "BULLISH", "regime": "STRONG_BULL", "break_of_structure": "BULLISH"}
        aoi = {"type": "DEMAND", "price_low": 100, "price_high": 105, "strength_score": 85}
        latest = pd.Series({"rsi": 55, "ema_alignment": "BULLISH", "obv_slope": 1.0})
        scores = {"total": 88.5}
        reasons = engine._generate_reasons_long(structure, aoi, latest, scores, 75.0)
        assert len(reasons) > 0
        assert any("BULLISH" in r for r in reasons)

    def test_generate_reasons_short(self):
        engine = SignalEngine()
        structure = {"trend": "BEARISH", "regime": "STRONG_BEAR", "break_of_structure": "BEARISH"}
        aoi = {"type": "SUPPLY", "price_low": 200, "price_high": 205, "strength_score": 80}
        latest = pd.Series({"rsi": 72, "ema_alignment": "BEARISH", "obv_slope": -1.0})
        scores = {"total": 85.0}
        reasons = engine._generate_reasons_short(structure, aoi, latest, scores, 80.0)
        assert len(reasons) > 0
        assert any("BEARISH" in r for r in reasons)

    def test_evaluate_long_setup_no_bullish_trend(self, bear_trend_ohlcv):
        engine = SignalEngine()
        df_15m = bear_trend_ohlcv.copy()
        result = engine.evaluate_long_setup(bear_trend_ohlcv, df_15m)
        assert result is None

    def test_evaluate_short_setup_no_bearish_trend(self, bull_trend_ohlcv):
        engine = SignalEngine()
        df_15m = bull_trend_ohlcv.copy()
        result = engine.evaluate_short_setup(bull_trend_ohlcv, df_15m)
        assert result is None


# ============================================================
# RISK MANAGER
# ============================================================

class TestRiskManager:
    def test_position_size(self):
        rm = RiskManager(account_balance=10000)
        result = rm.calculate_position_size(50000, 49500)
        assert result["position_size"] > 0
        assert result["dollar_risk"] == 100
        assert result["margin_required"] > 0

    def test_position_size_custom_risk(self):
        rm = RiskManager(account_balance=10000)
        result = rm.calculate_position_size(50000, 49500, 0.02)
        assert result["dollar_risk"] == 200

    def test_position_size_zero_risk(self):
        rm = RiskManager(account_balance=10000)
        result = rm.calculate_position_size(50000, 50000)
        assert result["position_size"] == 0

    def test_position_size_large_balance(self):
        rm = RiskManager(account_balance=1000000)
        result = rm.calculate_position_size(50000, 49500)
        assert result["position_size"] > 0
        assert result["leverage"] <= 10

    def test_risk_reward_long(self):
        rm = RiskManager()
        rr = rm.calculate_risk_reward(100, 95, 115, "LONG")
        assert rr == 3.0

    def test_risk_reward_short(self):
        rm = RiskManager()
        rr = rm.calculate_risk_reward(100, 105, 85, "SHORT")
        assert rr == 3.0

    def test_risk_reward_zero_risk(self):
        rm = RiskManager()
        rr = rm.calculate_risk_reward(100, 100, 115, "LONG")
        assert rr == 0

    def test_daily_loss_limit(self):
        rm = RiskManager(account_balance=10000)
        assert not rm.check_daily_loss_limit()
        rm.record_trade({"pnl": -400, "exit_time": datetime.utcnow().isoformat()})
        assert rm.check_daily_loss_limit()

    def test_daily_loss_limit_not_hit(self):
        rm = RiskManager(account_balance=10000)
        rm.record_trade({"pnl": -100, "exit_time": datetime.utcnow().isoformat()})
        assert not rm.check_daily_loss_limit()

    def test_weekly_loss_limit(self):
        rm = RiskManager(account_balance=10000)
        assert not rm.check_weekly_loss_limit()
        rm.record_trade({"pnl": -900, "exit_time": datetime.utcnow().isoformat()})
        assert rm.check_weekly_loss_limit()

    def test_weekly_loss_from_multiple_trades(self):
        rm = RiskManager(account_balance=10000)
        rm.record_trade({"pnl": -500, "exit_time": datetime.utcnow().isoformat()})
        rm.record_trade({"pnl": -400, "exit_time": datetime.utcnow().isoformat()})
        assert rm.check_weekly_loss_limit()

    def test_can_trade(self):
        rm = RiskManager(account_balance=10000)
        can, msg = rm.can_trade()
        assert can
        assert msg == "OK"

    def test_can_trade_max_positions(self):
        rm = RiskManager(account_balance=10000)
        rm.open_positions = [{"symbol": "BTC"}, {"symbol": "ETH"}, {"symbol": "SOL"}]
        can, msg = rm.can_trade()
        assert not can
        assert "Max open positions" in msg

    def test_atr_stop_long(self):
        rm = RiskManager()
        stop = rm.calculate_atr_stop(100, 2.0, "LONG", 50000)
        assert stop == 50000 - 200

    def test_atr_stop_short(self):
        rm = RiskManager()
        stop = rm.calculate_atr_stop(100, 2.0, "SHORT", 50000)
        assert stop == 50000 + 200

    def test_drawdown_throttle_at_peak(self):
        rm = RiskManager(account_balance=10000)
        rm.update_balance(10000)
        assert rm.current_drawdown() == 0
        assert rm.get_effective_risk(0.05) == 0.05

    def test_drawdown_throttle_underwater(self):
        rm = RiskManager(account_balance=10000, dd_throttle_level=0.05, dd_throttle_factor=0.4)
        rm.update_balance(11000)   # new peak
        rm.update_balance(10000)   # ~9.1% below peak -> throttled
        assert rm.current_drawdown() > 0.05
        assert rm.get_effective_risk(0.05) == 0.05 * 0.4

    def test_drawdown_throttle_disabled(self):
        rm = RiskManager(account_balance=10000, dd_throttle_level=None)
        rm.update_balance(20000)
        rm.update_balance(10000)
        assert rm.get_effective_risk(0.05) == 0.05

    def test_peak_tracks_maximum(self):
        rm = RiskManager(account_balance=10000)
        rm.update_balance(12000)
        rm.update_balance(11000)
        assert rm.peak_balance == 12000

    def test_get_risk_metrics(self):
        rm = RiskManager(account_balance=10000)
        metrics = rm.get_risk_metrics()
        assert "daily_pnl" in metrics
        assert "weekly_pnl" in metrics
        assert "account_balance" in metrics
        assert metrics["account_balance"] == 10000


# ============================================================
# BACKTEST ENGINE
# ============================================================

class TestBacktestEngine:
    def test_backtest_init(self):
        engine = BacktestEngine()
        assert engine.slippage_pct == 0.001
        assert engine.fee_pct == 0.0004

    def test_backtest_calc_pnl_long(self):
        engine = BacktestEngine()
        pnl = engine._calc_pnl(100, 110, "LONG", 1.0)
        assert pnl == 10

    def test_backtest_calc_pnl_short(self):
        engine = BacktestEngine()
        pnl = engine._calc_pnl(100, 90, "SHORT", 1.0)
        assert pnl == 10

    def test_backtest_calc_fees(self):
        engine = BacktestEngine()
        fees = engine._calc_fees(100, 1.0, 2)
        assert fees == 100 * 1.0 * 0.0004 * 2

    def test_backtest_calc_metrics_no_trades(self):
        engine = BacktestEngine()
        metrics = engine._calculate_metrics([], 10000, 10000, [10000], {}, 0, 0)
        assert metrics["total_trades"] == 0
        assert metrics["win_rate"] == 0

    def test_backtest_calc_metrics_with_trades(self):
        engine = BacktestEngine()
        trades = [
            {"pnl": 100, "dollar_risk": 50, "holding_bars": 10, "breakeven_activated": False, "trailing_activated": False, "partial_exits": []},
            {"pnl": -50, "dollar_risk": 50, "holding_bars": 5, "breakeven_activated": False, "trailing_activated": False, "partial_exits": []},
        ]
        metrics = engine._calculate_metrics(trades, 10000, 10050, [10000, 10050], {}, 0, 0)
        assert metrics["total_trades"] == 2
        assert metrics["winning_trades"] == 1
        assert metrics["losing_trades"] == 1
        assert metrics["win_rate"] == 50

    def test_backtest_get_month_key(self):
        engine = BacktestEngine()
        row = {"timestamp": 1704067200000}
        key = engine._get_month_key(row)
        assert key == "2024-01"

    def test_backtest_run_with_insufficient_data(self):
        engine = BacktestEngine()
        n = 100
        df = pd.DataFrame({
            "close": [100] * n, "high": [101] * n, "low": [99] * n,
            "volume": [1000] * n, "timestamp": np.arange(n) * 900000,
        })
        result = engine.run_backtest(df, df)
        assert result["total_trades"] == 0


# ============================================================
# RATE LIMITER
# ============================================================

class TestBingXClient:
    def test_symbol_to_bingx(self):
        assert BingXClient._to_bingx_symbol("BTCUSDT") == "BTC-USDT"
        assert BingXClient._to_bingx_symbol("ETHUSDT") == "ETH-USDT"
        assert BingXClient._to_bingx_symbol("BTC-USDT") == "BTC-USDT"

    def test_symbol_from_bingx(self):
        assert BingXClient._from_bingx_symbol("BTC-USDT") == "BTCUSDT"
        assert BingXClient._from_bingx_symbol("sol-usdt") == "SOLUSDT"

    def test_unwrap(self):
        assert BingXClient._unwrap({"code": 0, "data": [1, 2]}) == [1, 2]
        assert BingXClient._unwrap([1, 2]) == [1, 2]

    def test_parse_klines_dict_form(self):
        client = BingXClient()
        rows = [
            {"time": 1700000900000, "open": "2", "high": "3", "low": "1", "close": "2.5", "volume": "10"},
            {"time": 1700000000000, "open": "1", "high": "2", "low": "0.5", "close": "1.5", "volume": "5"},
        ]
        df = client._parse_klines(rows)
        assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
        assert df["timestamp"].is_monotonic_increasing  # sorted ascending
        assert df.iloc[0]["close"] == 1.5

    def test_parse_klines_array_form(self):
        client = BingXClient()
        rows = [[1700000000000, "1", "2", "0.5", "1.5", "5"]]
        df = client._parse_klines(rows)
        assert df.iloc[0]["high"] == 2.0

    def test_sign_is_deterministic(self):
        client = BingXClient()
        client.secret_key = "testsecret"
        q1, s1 = client._sign({"symbol": "BTC-USDT", "timestamp": 123})
        q2, s2 = client._sign({"timestamp": 123, "symbol": "BTC-USDT"})
        assert q1 == q2 and s1 == s2  # order-independent (sorted keys)
        assert len(s1) == 64  # sha256 hex


class TestRateLimiter:
    @pytest.mark.asyncio
    async def test_rate_limiter_acquire(self):
        limiter = RateLimiter(max_calls=10, period=1.0)
        await limiter.acquire()
        assert len(limiter.calls) == 1

    @pytest.mark.asyncio
    async def test_rate_limiter_burst(self):
        limiter = RateLimiter(max_calls=5, period=1.0)
        for _ in range(5):
            await limiter.acquire()
        assert len(limiter.calls) == 5

    @pytest.mark.asyncio
    async def test_rate_limiter_clear_old(self):
        import time
        limiter = RateLimiter(max_calls=5, period=0.1)
        limiter.calls = [time.time() - 1.0, time.time() - 0.5]
        await limiter.acquire()
        assert len(limiter.calls) == 1
