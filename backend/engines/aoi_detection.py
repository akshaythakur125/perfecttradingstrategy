from typing import List, Dict, Optional, Tuple
import numpy as np
import pandas as pd


def _calculate_body_ratio(open_prices: np.ndarray, close: np.ndarray, i: int) -> float:
    body = abs(close[i] - open_prices[i])
    total_range = max(close[i], open_prices[i]) - min(close[i], open_prices[i])
    if total_range == 0:
        return 0.0
    return body / total_range


def find_supply_zones(high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray, open_prices: np.ndarray) -> List[Dict]:
    zones = []
    window = 5
    vol_ma = pd.Series(volume).rolling(20).mean().values
    vol_std = pd.Series(volume).rolling(20).std().values

    for i in range(window, len(high) - window):
        if high[i] == max(high[i - window:i + window + 1]):
            zone_high = high[i]
            zone_low = min(close[i], open_prices[i])
            zone_range = zone_high - zone_low
            
            if zone_range / zone_high < 0.001:
                continue
            
            reactions = count_reactions(high, low, zone_low, zone_high, i)
            
            vol_z = (volume[i] - vol_ma[i]) / max(vol_std[i], 1)
            if vol_z < 0.5:
                continue
            
            body_ratio = _calculate_body_ratio(open_prices, close, i)
            wick_ratio = (high[i] - max(close[i], open_prices[i])) / max(zone_range, 0.001)
            
            if wick_ratio < 0.3:
                continue
                
            vol_conf = float(np.mean(volume[max(0, i - 3):i + 1]) / max(np.mean(volume[:i + 1]), 1))
            zones.append({
                "type": "SUPPLY",
                "price_low": float(zone_low),
                "price_high": float(zone_high),
                "reaction_count": reactions,
                "volume_confirmation": float(vol_conf),
                "index": i,
            })
    return zones


def find_demand_zones(high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray, open_prices: np.ndarray) -> List[Dict]:
    zones = []
    window = 5
    vol_ma = pd.Series(volume).rolling(20).mean().values
    vol_std = pd.Series(volume).rolling(20).std().values

    for i in range(window, len(high) - window):
        if low[i] == min(low[i - window:i + window + 1]):
            zone_low = low[i]
            zone_high = max(close[i], open_prices[i])
            zone_range = zone_high - zone_low
            
            if zone_range / max(zone_high, 1) < 0.001:
                continue
            
            reactions = count_reactions(high, low, zone_low, zone_high, i)
            
            vol_z = (volume[i] - vol_ma[i]) / max(vol_std[i], 1)
            if vol_z < 0.5:
                continue
            
            body_ratio = _calculate_body_ratio(open_prices, close, i)
            wick_ratio = (min(close[i], open_prices[i]) - low[i]) / max(zone_range, 0.001)
            
            if wick_ratio < 0.3:
                continue
                
            vol_conf = float(np.mean(volume[max(0, i - 3):i + 1]) / max(np.mean(volume[:i + 1]), 1))
            zones.append({
                "type": "DEMAND",
                "price_low": float(zone_low),
                "price_high": float(zone_high),
                "reaction_count": reactions,
                "volume_confirmation": float(vol_conf),
                "index": i,
            })
    return zones


def find_order_blocks(df: pd.DataFrame) -> List[Dict]:
    blocks = []
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values
    volume = df["volume"].values
    open_prices = df["open"].values
    
    avg_range = pd.Series(high - low).rolling(20).mean().values

    for i in range(2, len(df) - 3):
        body_i = abs(close[i] - open_prices[i])
        range_i = high[i] - low[i]
        
        if range_i == 0:
            continue
            
        body_ratio = body_i / range_i
        
        if body_ratio < 0.3:
            continue
        
        impulse_mult = 2.0
        
        bullish_ob = (
            close[i] > open_prices[i] and
            close[i + 1] > high[i] and
            high[i + 1] - low[i + 1] > avg_range[i] * impulse_mult
        )
        
        if bullish_ob:
            vol_ratio = volume[i] / max(np.mean(volume[max(0, i - 10):i]), 0.1)
            if vol_ratio > 1.2:
                blocks.append({
                    "type": "DEMAND_OB",
                    "price_low": float(low[i]),
                    "price_high": float(high[i]),
                    "volume_confirmation": float(min(vol_ratio, 5.0)),
                    "index": i,
                })
                continue
        
        bearish_ob = (
            close[i] < open_prices[i] and
            close[i + 1] < low[i] and
            high[i + 1] - low[i + 1] > avg_range[i] * impulse_mult
        )
        
        if bearish_ob:
            vol_ratio = volume[i] / max(np.mean(volume[max(0, i - 10):i]), 0.1)
            if vol_ratio > 1.2:
                blocks.append({
                    "type": "SUPPLY_OB",
                    "price_low": float(low[i]),
                    "price_high": float(high[i]),
                    "volume_confirmation": float(min(vol_ratio, 5.0)),
                    "index": i,
                })
    return blocks


def find_fvgs(df: pd.DataFrame) -> List[Dict]:
    fvgs = []
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values
    
    avg_candle_range = pd.Series(high - low).rolling(20).mean().values

    for i in range(1, len(df) - 1):
        if low[i + 1] > high[i - 1]:
            gap_size = low[i + 1] - high[i - 1]
            if gap_size > avg_candle_range[i] * 0.3:
                fvgs.append({
                    "type": "BULLISH_FVG",
                    "price_low": float(high[i - 1]),
                    "price_high": float(low[i + 1]),
                    "gap_size": float(gap_size),
                    "index": i + 1,
                })
        elif high[i + 1] < low[i - 1]:
            gap_size = low[i - 1] - high[i + 1]
            if gap_size > avg_candle_range[i] * 0.3:
                fvgs.append({
                    "type": "BEARISH_FVG",
                    "price_low": float(high[i + 1]),
                    "price_high": float(low[i - 1]),
                    "gap_size": float(gap_size),
                    "index": i + 1,
                })

    return fvgs


def find_liquidity_pools(high: np.ndarray, low: np.ndarray) -> List[Dict]:
    pools = []
    for i in range(3, len(high) - 3):
        is_high = True
        is_low = True
        for j in range(1, 4):
            if high[i] <= high[i - j] or high[i] <= high[i + j]:
                is_high = False
            if low[i] >= low[i - j] or low[i] >= low[i + j]:
                is_low = False
        if is_high:
            pools.append({
                "type": "LIQUIDITY_HIGH",
                "price": float(high[i]),
                "index": i,
            })
        if is_low:
            pools.append({
                "type": "LIQUIDITY_LOW",
                "price": float(low[i]),
                "index": i,
            })
    return pools


def find_equal_highs(high: np.ndarray, tolerance: float = 0.002) -> List[Dict]:
    eq_highs = []
    for i in range(len(high)):
        for j in range(i + 1, min(i + 50, len(high))):
            if abs(high[i] - high[j]) / max(high[i], 0.001) < tolerance:
                eq_highs.append({
                    "type": "EQUAL_HIGH",
                    "price": float((high[i] + high[j]) / 2),
                    "index": j,
                })
    return eq_highs


def find_equal_lows(low: np.ndarray, tolerance: float = 0.002) -> List[Dict]:
    eq_lows = []
    for i in range(len(low)):
        for j in range(i + 1, min(i + 50, len(low))):
            if abs(low[i] - low[j]) / max(low[i], 0.001) < tolerance:
                eq_lows.append({
                    "type": "EQUAL_LOW",
                    "price": float((low[i] + low[j]) / 2),
                    "index": j,
                })
    return eq_lows


def find_wick_rejection_zones(high: np.ndarray, low: np.ndarray, close: np.ndarray, open_prices: np.ndarray) -> List[Dict]:
    zones = []
    for i in range(len(high)):
        upper_wick = high[i] - max(close[i], open_prices[i])
        lower_wick = min(close[i], open_prices[i]) - low[i]
        body = abs(close[i] - open_prices[i])
        total_range = high[i] - low[i]

        if total_range == 0 or body == 0:
            continue

        upper_ratio = upper_wick / total_range
        lower_ratio = lower_wick / total_range

        if upper_ratio > 0.6:
            zones.append({
                "type": "UPPER_WICK_REJECTION",
                "price_high": float(high[i]),
                "price_low": float(max(close[i], open_prices[i])),
                "index": i,
            })
        if lower_ratio > 0.6:
            zones.append({
                "type": "LOWER_WICK_REJECTION",
                "price_low": float(low[i]),
                "price_high": float(min(close[i], open_prices[i])),
                "index": i,
            })
    return zones


def count_reactions(high: np.ndarray, low: np.ndarray, zone_low: float, zone_high: float, current_idx: int) -> int:
    count = 0
    for idx in range(current_idx - 1, max(0, current_idx - 50), -1):
        if zone_low * 0.995 <= low[idx] <= zone_high * 1.005 or zone_low * 0.995 <= high[idx] <= zone_high * 1.005:
            count += 1
    return count


def score_aoi(aoi: Dict, total_candles: int) -> Dict:
    recency = aoi.get("index", 0) / max(total_candles, 1)
    
    reaction_count = aoi.get("reaction_count", 0)
    if reaction_count >= 3:
        reaction_score = 1.0
    elif reaction_count == 2:
        reaction_score = 0.8
    elif reaction_count == 1:
        reaction_score = 0.5
    else:
        reaction_score = 0.3
    
    vol_conf = aoi.get("volume_confirmation", 1.0)
    volume_score = min(vol_conf / 2.0, 1.0)
    
    aoi_type = aoi.get("type", "")
    if "LIQUIDITY" in aoi_type:
        liquidity_score = 0.8
    elif "OB" in aoi_type:
        liquidity_score = 0.7
    elif "FVG" in aoi_type:
        liquidity_score = 0.6
    elif "SUPPLY" in aoi_type or "DEMAND" in aoi_type:
        liquidity_score = 0.5
    else:
        liquidity_score = 0.3

    score = (reaction_score * 0.35 + volume_score * 0.25 + recency * 0.20 + liquidity_score * 0.20) * 100

    aoi["strength_score"] = round(min(score, 100), 2)
    aoi["recency_score"] = round(recency * 100, 2)

    return aoi


def detect_all_aois(df: pd.DataFrame) -> List[Dict]:
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values
    volume = df["volume"].values
    open_prices = df["open"].values
    total = len(df)

    zones = []
    zones.extend(find_supply_zones(high, low, close, volume, open_prices))
    zones.extend(find_demand_zones(high, low, close, volume, open_prices))
    zones.extend(find_order_blocks(df))
    zones.extend(find_fvgs(df))
    zones.extend(find_liquidity_pools(high, low))
    zones.extend(find_equal_highs(high))
    zones.extend(find_equal_lows(low))
    zones.extend(find_wick_rejection_zones(high, low, close, open_prices))

    zones = [score_aoi(z, total) for z in zones]
    zones.sort(key=lambda x: x["strength_score"], reverse=True)

    seen = set()
    deduped = []
    for z in zones:
        key = (z["type"], round(z.get("price_low", 0), 4), round(z.get("price_high", 0), 4))
        if key not in seen:
            seen.add(key)
            deduped.append(z)
        elif z["strength_score"] > 0:
            pass

    return deduped


def filter_relevant_aois(aois: List[Dict], current_price: float, direction: str, max_distance_pct: float = 0.05) -> List[Dict]:
    relevant = []
    for aoi in aois:
        aoi_type = aoi.get("type", "")
        price_low = aoi.get("price_low", current_price)
        price_high = aoi.get("price_high", current_price)
        avg_price = (price_low + price_high) / 2

        if direction == "LONG":
            is_demand_type = any(t in aoi_type for t in ["DEMAND", "LOWER_WICK", "LIQUIDITY_LOW", "EQUAL_LOW", "BULLISH_FVG"])
            is_supply_type = any(t in aoi_type for t in ["SUPPLY", "UPPER_WICK", "LIQUIDITY_HIGH", "EQUAL_HIGH", "BEARISH_FVG"])
            
            if is_supply_type:
                continue
            
            if avg_price > current_price:
                continue
            
            dist = abs(current_price - avg_price) / current_price
            if dist <= max_distance_pct:
                relevant.append(aoi)

        elif direction == "SHORT":
            is_supply_type = any(t in aoi_type for t in ["SUPPLY", "UPPER_WICK", "LIQUIDITY_HIGH", "EQUAL_HIGH", "BEARISH_FVG"])
            is_demand_type = any(t in aoi_type for t in ["DEMAND", "LOWER_WICK", "LIQUIDITY_LOW", "EQUAL_LOW", "BULLISH_FVG"])
            
            if is_demand_type:
                continue
            
            if avg_price < current_price:
                continue
            
            dist = abs(avg_price - current_price) / current_price
            if dist <= max_distance_pct:
                relevant.append(aoi)

    relevant.sort(key=lambda x: x.get("strength_score", 0), reverse=True)
    return relevant
