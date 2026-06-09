import numpy as np
import pandas as pd
from typing import Optional


def calculate_rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
    prices = prices.astype(float)
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.zeros_like(prices, dtype=float)
    avg_loss = np.zeros_like(prices, dtype=float)

    avg_gain[period] = np.mean(gains[:period])
    avg_loss[period] = np.mean(losses[:period])

    for i in range(period + 1, len(prices)):
        avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gains[i - 1]) / period
        avg_loss[i] = (avg_loss[i - 1] * (period - 1) + losses[i - 1]) / period

    rs = np.zeros_like(avg_gain, dtype=float)
    normal = avg_loss > 0
    very_bullish = (avg_gain > 0) & (avg_loss == 0)
    very_bearish = (avg_gain == 0) & (avg_loss == 0)

    rs[normal] = avg_gain[normal] / avg_loss[normal]
    rs[very_bullish] = 999.0
    rs[very_bearish] = 0.0

    rsi = 100 - (100 / (1 + rs))
    rsi[:period] = 50
    rsi[rsi > 100] = 100
    rsi[rsi < 0] = 0

    return rsi


def calculate_ema(prices: np.ndarray, period: int) -> np.ndarray:
    alpha = 2 / (period + 1)
    ema = np.zeros_like(prices)
    ema[0] = prices[0]
    for i in range(1, len(prices)):
        ema[i] = alpha * prices[i] + (1 - alpha) * ema[i - 1]
    return ema


def calculate_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    high_low = high - low
    high_close = np.abs(high - np.roll(close, 1))
    low_close = np.abs(low - np.roll(close, 1))
    tr = np.maximum(high_low, np.maximum(high_close, low_close))
    tr[0] = high_low[0]

    atr = np.zeros_like(close)
    atr[period - 1] = np.mean(tr[:period])
    for i in range(period, len(close)):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    atr[:period - 1] = atr[period - 1]

    return atr


def calculate_obv(close: np.ndarray, volume: np.ndarray) -> np.ndarray:
    obv = np.zeros_like(volume)
    obv[0] = volume[0]
    for i in range(1, len(close)):
        if close[i] > close[i - 1]:
            obv[i] = obv[i - 1] + volume[i]
        elif close[i] < close[i - 1]:
            obv[i] = obv[i - 1] - volume[i]
        else:
            obv[i] = obv[i - 1]
    return obv


def calculate_volume_ma(volume: np.ndarray, period: int = 20) -> np.ndarray:
    return pd.Series(volume).rolling(window=period).mean().to_numpy()


def detect_volume_spike(volume: np.ndarray, volume_ma: np.ndarray, multiplier: float = 1.5) -> np.ndarray:
    return (volume > volume_ma * multiplier).astype(int)


def get_ema_alignment(ema20: np.ndarray, ema50: np.ndarray, ema200: np.ndarray, i: int) -> str:
    tol = 0.001
    if ema20[i] > ema50[i] * (1 + tol) and ema50[i] > ema200[i] * (1 + tol):
        return "BULLISH"
    elif ema20[i] < ema50[i] * (1 - tol) and ema50[i] < ema200[i] * (1 - tol):
        return "BEARISH"
    return "NEUTRAL"


def calculate_volume_std(volume: np.ndarray, period: int = 20) -> np.ndarray:
    return pd.Series(volume).rolling(window=period).std().to_numpy()


def get_volume_signal(volume: np.ndarray, volume_ma: np.ndarray, volume_std: np.ndarray) -> float:
    if volume_std[-1] == 0:
        return 0.0
    z = (volume[-1] - volume_ma[-1]) / volume_std[-1]
    return min(max(z / 2.0, 0.0), 1.0) * 100


def compute_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    volume = df["volume"].values

    df["rsi"] = calculate_rsi(close, 14)
    df["ema_20"] = calculate_ema(close, 20)
    df["ema_50"] = calculate_ema(close, 50)
    df["ema_200"] = calculate_ema(close, 200)
    df["atr"] = calculate_atr(high, low, close, 14)
    df["obv"] = calculate_obv(close, volume)
    df["volume_ma"] = calculate_volume_ma(volume, 20)
    df["volume_std"] = calculate_volume_std(volume, 20)
    df["volume_spike"] = detect_volume_spike(volume, df["volume_ma"].values, 1.5)

    ema_align = []
    for i in range(len(df)):
        ema_align.append(get_ema_alignment(
            df["ema_20"].values, df["ema_50"].values, df["ema_200"].values, i
        ))
    df["ema_alignment"] = ema_align

    df["obv_slope"] = np.gradient(df["obv"].values)

    return df
