from typing import List, Tuple, Optional
import numpy as np
import pandas as pd


def find_swing_highs(high: np.ndarray, window: int = 5) -> np.ndarray:
    swings = np.zeros(len(high), dtype=float)
    for i in range(window, len(high) - window):
        neighborhood = high[i - window:i + window + 1]
        if high[i] >= np.max(neighborhood) and high[i] > np.median(neighborhood) * 1.002:
            left_min = np.min(high[i - window:i])
            right_min = np.min(high[i + 1:i + window + 1])
            if high[i] > left_min * 1.003 and high[i] > right_min * 1.003:
                swings[i] = 1
    return swings


def find_swing_lows(low: np.ndarray, window: int = 5) -> np.ndarray:
    swings = np.zeros(len(low), dtype=float)
    for i in range(window, len(low) - window):
        neighborhood = low[i - window:i + window + 1]
        if low[i] <= np.min(neighborhood) and low[i] < np.median(neighborhood) * 0.998:
            left_max = np.max(low[i - window:i])
            right_max = np.max(low[i + 1:i + window + 1])
            if low[i] < left_max * 0.997 and low[i] < right_max * 0.997:
                swings[i] = 1
    return swings


def detect_bos(high: np.ndarray, low: np.ndarray, swing_highs: np.ndarray, swing_lows: np.ndarray) -> str:
    recent_highs = np.where(swing_highs > 0)[0]
    recent_lows = np.where(swing_lows > 0)[0]

    if len(recent_highs) < 2 or len(recent_lows) < 2:
        return "NEUTRAL"

    last_high_idx = recent_highs[-1]
    prev_high_idx = recent_highs[-2]
    last_low_idx = recent_lows[-1]
    prev_low_idx = recent_lows[-2]

    bullish_bos = low[last_low_idx] > low[prev_low_idx] and high[last_high_idx] > high[prev_high_idx]
    bearish_bos = high[last_high_idx] < high[prev_high_idx] and low[last_low_idx] < low[prev_low_idx]

    if bullish_bos:
        return "BULLISH"
    elif bearish_bos:
        return "BEARISH"
    return "NEUTRAL"


def detect_choch(high: np.ndarray, low: np.ndarray, close: np.ndarray, trend: str) -> str:
    if trend == "BULLISH":
        recent_lows = np.where(
            (low == pd.Series(low).rolling(7, center=True).min().values) &
            (low > 0)
        )[0]
        if len(recent_lows) >= 2:
            if low[recent_lows[-1]] < low[recent_lows[-2]]:
                return "CHOCH_BEARISH"
    elif trend == "BEARISH":
        recent_highs = np.where(
            (high == pd.Series(high).rolling(7, center=True).max().values) &
            (high > 0)
        )[0]
        if len(recent_highs) >= 2:
            if high[recent_highs[-1]] > high[recent_highs[-2]]:
                return "CHOCH_BULLISH"
    return "NO_CHOCH"


def classify_market_regime(high: np.ndarray, low: np.ndarray, close: np.ndarray, ema20: np.ndarray, ema50: np.ndarray, ema200: np.ndarray) -> str:
    latest = -1
    tol = 0.001

    ema_aligned_bull = ema20[latest] > ema50[latest] * (1 + tol) > ema200[latest] * (1 + tol)
    ema_aligned_bear = ema20[latest] < ema50[latest] * (1 - tol) < ema200[latest] * (1 - tol)

    price_above_ema200 = close[latest] > ema200[latest]
    price_below_ema200 = close[latest] < ema200[latest]

    lookback = 20
    recent_high = max(high[-lookback:])
    recent_low = min(low[-lookback:])
    range_size = (recent_high - recent_low) / close[latest]

    is_ranging = range_size < 0.05 or (not ema_aligned_bull and not ema_aligned_bear)

    if is_ranging:
        return "RANGE"

    if ema_aligned_bull and price_above_ema200:
        slope = np.polyfit(range(lookback), close[-lookback:], 1)[0]
        if slope > 0:
            return "STRONG_BULL"
        return "WEAK_BULL"

    if ema_aligned_bear and price_below_ema200:
        slope = np.polyfit(range(lookback), close[-lookback:], 1)[0]
        if slope < 0:
            return "STRONG_BEAR"
        return "WEAK_BEAR"

    return "RANGE"


def detect_trend(high: np.ndarray, low: np.ndarray, close: np.ndarray, ema20: np.ndarray, ema50: np.ndarray) -> str:
    latest = -1

    if close[latest] > ema20[latest] and ema20[latest] > ema50[latest]:
        swing_lows_arr = np.where(
            (low == pd.Series(low).rolling(7, center=True).min().values) &
            (low > 0)
        )[0]
        if len(swing_lows_arr) >= 2:
            if low[swing_lows_arr[-1]] >= low[swing_lows_arr[-2]]:
                return "BULLISH"
        return "BULLISH"

    elif close[latest] < ema20[latest] and ema20[latest] < ema50[latest]:
        swing_highs_arr = np.where(
            (high == pd.Series(high).rolling(7, center=True).max().values) &
            (high > 0)
        )[0]
        if len(swing_highs_arr) >= 2:
            if high[swing_highs_arr[-1]] <= high[swing_highs_arr[-2]]:
                return "BEARISH"
        return "BEARISH"

    return "NEUTRAL"


def detect_consolidation(high: np.ndarray, low: np.ndarray, close: np.ndarray, lookback: int = 20) -> bool:
    high_range = max(high[-lookback:])
    low_range = min(low[-lookback:])
    range_percent = (high_range - low_range) / close[-1]
    atr = np.mean(high[-lookback:] - low[-lookback:])
    return range_percent < atr * 2.0 / close[-1]


def analyze_market_structure(df: pd.DataFrame) -> dict:
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values

    swing_highs = find_swing_highs(high, 5)
    swing_lows = find_swing_lows(low, 5)

    bos = detect_bos(high, low, swing_highs, swing_lows)
    trend = detect_trend(high, low, close, df["ema_20"].values, df["ema_50"].values)
    regime = classify_market_regime(
        high, low, close,
        df["ema_20"].values, df["ema_50"].values, df["ema_200"].values
    )
    choch = detect_choch(high, low, close, trend)
    consolidating = detect_consolidation(high, low, close)

    return {
        "swing_highs": swing_highs.tolist(),
        "swing_lows": swing_lows.tolist(),
        "break_of_structure": bos,
        "change_of_character": choch,
        "trend": trend,
        "regime": regime,
        "consolidating": consolidating,
    }
