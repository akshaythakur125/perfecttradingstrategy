from typing import Optional, List, Dict
import numpy as np
import pandas as pd
from engines.indicators import compute_all_indicators, get_volume_signal
from engines.market_structure import analyze_market_structure
from engines.aoi_detection import detect_all_aois, filter_relevant_aois
from config.settings import settings


class SignalEngine:
    def __init__(self):
        self.min_confidence = 80.0
        self.min_risk_reward = settings.min_risk_reward

    def evaluate_long_setup(self, df_4h: pd.DataFrame, df_15m: pd.DataFrame,
                            oi_change_pct: Optional[float] = None,
                            funding_rate: Optional[float] = None) -> Optional[Dict]:
        df_4h = compute_all_indicators(df_4h)
        df_15m = compute_all_indicators(df_15m)

        structure_4h = analyze_market_structure(df_4h)
        structure_15m = analyze_market_structure(df_15m)

        if structure_4h["trend"] != "BULLISH":
            return None

        current_price = df_15m["close"].values[-1]
        aois = detect_all_aois(df_4h)
        relevant_aois = filter_relevant_aois(aois, current_price, "LONG")

        if not relevant_aois:
            return None

        best_aoi = relevant_aois[0]

        latest_15m = df_15m.iloc[-1]
        rsi_rising = latest_15m["rsi"] > df_15m["rsi"].iloc[-5]
        rsi_range_ok = 30 <= latest_15m["rsi"] <= 65
        rsi_bullish = rsi_range_ok and rsi_rising

        obv_rising = len(df_15m) >= 3 and df_15m["obv"].iloc[-1] > df_15m["obv"].iloc[-3]
        obv_slope_positive = latest_15m["obv_slope"] > 0
        obv_confirmed = obv_rising or obv_slope_positive

        volume_signal = get_volume_signal(
            df_15m["volume"].values,
            df_15m["volume_ma"].values,
            df_15m["volume_std"].values,
        )
        ema_bullish = latest_15m["ema_alignment"] == "BULLISH"

        if not all([rsi_bullish, obv_confirmed, volume_signal > 30, ema_bullish]):
            return None

        atr_val = latest_15m["atr"]
        aoi_low = best_aoi.get("price_low", current_price * 0.99)
        atr_stop = current_price - (atr_val * 2.0)
        stop_loss = min(aoi_low, atr_stop) * 0.995

        entry = current_price
        tp1 = entry + (entry - stop_loss) * 1.5
        tp2 = entry + (entry - stop_loss) * 3.0
        tp3 = entry + (entry - stop_loss) * 5.0
        risk_reward = (tp1 - entry) / (entry - stop_loss)

        if risk_reward < self.min_risk_reward:
            return None

        oi_score_val = self._score_oi(oi_change_pct, "LONG")
        funding_score_val = self._score_funding(funding_rate, "LONG")

        scores = self._score_setup(
            structure_score=self._score_structure(structure_4h),
            aoi_score=best_aoi.get("strength_score", 50),
            volume_score=min(volume_signal, 100),
            rsi_score=self._score_rsi(latest_15m["rsi"], "LONG"),
            obv_score=100 if obv_confirmed else 0,
            oi_score=oi_score_val,
            funding_score=funding_score_val,
        )

        if scores["total"] < self.min_confidence:
            return None

        return {
            "symbol": df_4h.get("symbol", df_15m.get("symbol", "UNKNOWN")),
            "exchange": df_4h.get("exchange", df_15m.get("exchange", "BINANCE")),
            "direction": "LONG",
            "confidence_score": round(scores["total"], 2),
            "entry_price": round(entry, 2),
            "stop_loss": round(stop_loss, 2),
            "take_profit_1": round(tp1, 2),
            "take_profit_2": round(tp2, 2),
            "take_profit_3": round(tp3, 2),
            "risk_reward": round(risk_reward, 2),
            "trend_direction": structure_4h["trend"],
            "market_regime": structure_4h["regime"],
            "aoi_type": best_aoi.get("type", ""),
            "aoi_price_low": best_aoi.get("price_low", 0),
            "aoi_price_high": best_aoi.get("price_high", 0),
            "aoi_score": best_aoi.get("strength_score", 0),
            "structure_score": scores["structure"],
            "volume_score": scores["volume"],
            "rsi_score": scores["rsi"],
            "obv_score": scores["obv"],
            "oi_score": scores["oi"],
            "funding_score": scores["funding"],
            "reasons": self._generate_reasons_long(structure_4h, best_aoi, latest_15m, scores, volume_signal),
        }

    def evaluate_short_setup(self, df_4h: pd.DataFrame, df_15m: pd.DataFrame,
                             oi_change_pct: Optional[float] = None,
                             funding_rate: Optional[float] = None) -> Optional[Dict]:
        df_4h = compute_all_indicators(df_4h)
        df_15m = compute_all_indicators(df_15m)

        structure_4h = analyze_market_structure(df_4h)
        structure_15m = analyze_market_structure(df_15m)

        if structure_4h["trend"] != "BEARISH":
            return None

        current_price = df_15m["close"].values[-1]
        aois = detect_all_aois(df_4h)
        relevant_aois = filter_relevant_aois(aois, current_price, "SHORT")

        if not relevant_aois:
            return None

        best_aoi = relevant_aois[0]

        latest_15m = df_15m.iloc[-1]
        rsi_overbought = latest_15m["rsi"] >= 70
        rsi_falling = latest_15m["rsi"] < df_15m["rsi"].iloc[-5]
        rsi_weak = 50 <= latest_15m["rsi"] <= 70 and rsi_falling
        rsi_bearish = rsi_overbought or rsi_weak

        obv_falling = len(df_15m) >= 3 and df_15m["obv"].iloc[-1] < df_15m["obv"].iloc[-3]
        obv_slope_negative = latest_15m["obv_slope"] < 0
        obv_confirmed = obv_falling or obv_slope_negative

        volume_signal = get_volume_signal(
            df_15m["volume"].values,
            df_15m["volume_ma"].values,
            df_15m["volume_std"].values,
        )
        ema_bearish = latest_15m["ema_alignment"] == "BEARISH"

        if not all([rsi_bearish, obv_confirmed, volume_signal > 30, ema_bearish]):
            return None

        atr_val = latest_15m["atr"]
        aoi_high = best_aoi.get("price_high", current_price * 1.01)
        atr_stop = current_price + (atr_val * 2.0)
        stop_loss = max(aoi_high, atr_stop) * 1.005

        entry = current_price
        tp1 = entry - (stop_loss - entry) * 1.5
        tp2 = entry - (stop_loss - entry) * 3.0
        tp3 = entry - (stop_loss - entry) * 5.0
        risk_reward = (entry - tp1) / (stop_loss - entry)

        if risk_reward < self.min_risk_reward:
            return None

        oi_score_val = self._score_oi(oi_change_pct, "SHORT")
        funding_score_val = self._score_funding(funding_rate, "SHORT")

        scores = self._score_setup(
            structure_score=self._score_structure(structure_4h),
            aoi_score=best_aoi.get("strength_score", 50),
            volume_score=min(volume_signal, 100),
            rsi_score=self._score_rsi(latest_15m["rsi"], "SHORT"),
            obv_score=100 if obv_confirmed else 0,
            oi_score=oi_score_val,
            funding_score=funding_score_val,
        )

        if scores["total"] < self.min_confidence:
            return None

        return {
            "symbol": df_4h.get("symbol", df_15m.get("symbol", "UNKNOWN")),
            "exchange": df_4h.get("exchange", df_15m.get("exchange", "BINANCE")),
            "direction": "SHORT",
            "confidence_score": round(scores["total"], 2),
            "entry_price": round(entry, 2),
            "stop_loss": round(stop_loss, 2),
            "take_profit_1": round(tp1, 2),
            "take_profit_2": round(tp2, 2),
            "take_profit_3": round(tp3, 2),
            "risk_reward": round(risk_reward, 2),
            "trend_direction": structure_4h["trend"],
            "market_regime": structure_4h["regime"],
            "aoi_type": best_aoi.get("type", ""),
            "aoi_price_low": best_aoi.get("price_low", 0),
            "aoi_price_high": best_aoi.get("price_high", 0),
            "aoi_score": best_aoi.get("strength_score", 0),
            "structure_score": scores["structure"],
            "volume_score": scores["volume"],
            "rsi_score": scores["rsi"],
            "obv_score": scores["obv"],
            "oi_score": scores["oi"],
            "funding_score": scores["funding"],
            "reasons": self._generate_reasons_short(structure_4h, best_aoi, latest_15m, scores, volume_signal),
        }

    def _score_structure(self, structure: Dict) -> float:
        regime = structure.get("regime", "RANGE")
        trend = structure.get("trend", "NEUTRAL")
        bos = structure.get("break_of_structure", "NEUTRAL")

        score = 50.0
        if regime in ("STRONG_BULL", "STRONG_BEAR"):
            score += 25
        elif regime in ("WEAK_BULL", "WEAK_BEAR"):
            score += 10

        if trend != "NEUTRAL":
            score += 15

        if bos != "NEUTRAL":
            score += 10

        return min(score, 100)

    def _score_rsi(self, rsi: float, direction: str) -> float:
        if direction == "LONG":
            if 30 <= rsi <= 45:
                return 100
            elif 45 < rsi <= 55:
                return 80
            elif 55 < rsi <= 65:
                return 60
            elif rsi > 65:
                return 30
            else:
                return 20
        else:
            if rsi >= 70:
                return 100
            elif 60 <= rsi < 70:
                return 85
            elif 50 <= rsi < 60:
                return 60
            elif rsi < 30:
                return 30
            else:
                return 20

    def _score_oi(self, oi_change_pct: Optional[float], direction: str) -> float:
        if oi_change_pct is None:
            return 50
        if direction == "LONG":
            if oi_change_pct > 5:
                return 100
            elif oi_change_pct > 2:
                return 75
            elif oi_change_pct > 0:
                return 60
            else:
                return 30
        else:
            if oi_change_pct > 5:
                return 100
            elif oi_change_pct > 2:
                return 75
            elif oi_change_pct > 0:
                return 60
            else:
                return 30

    def _score_funding(self, funding_rate: Optional[float], direction: str) -> float:
        if funding_rate is None:
            return 50
        if direction == "LONG":
            if funding_rate < 0:
                return 100 if funding_rate < -0.01 else 80
            elif funding_rate < 0.005:
                return 60
            else:
                return 30
        else:
            if funding_rate > 0:
                return 100 if funding_rate > 0.01 else 80
            elif funding_rate > -0.005:
                return 60
            else:
                return 30

    def _score_setup(self, structure_score: float, aoi_score: float,
                     volume_score: float, rsi_score: float,
                     obv_score: float, oi_score: float,
                     funding_score: float) -> Dict:
        total = (
            structure_score * 0.25 +
            aoi_score * 0.25 +
            volume_score * 0.15 +
            rsi_score * 0.10 +
            obv_score * 0.10 +
            oi_score * 0.10 +
            funding_score * 0.05
        )

        return {
            "structure": round(structure_score, 2),
            "aoi": round(aoi_score, 2),
            "volume": round(volume_score, 2),
            "rsi": round(rsi_score, 2),
            "obv": round(obv_score, 2),
            "oi": round(oi_score, 2),
            "funding": round(funding_score, 2),
            "total": round(total, 2),
        }

    def _generate_reasons_long(self, structure: Dict, aoi: Dict, latest: pd.Series, scores: Dict, vol_signal: float) -> List[str]:
        return [
            f"4H Trend: {structure['trend']}",
            f"Market Regime: {structure['regime']}",
            f"BOS: {structure['break_of_structure']}",
            f"AOI: {aoi.get('type', '')} at ${aoi.get('price_low', 0):.2f}-${aoi.get('price_high', 0):.2f}",
            f"AOI Score: {aoi.get('strength_score', 0)}/100",
            f"RSI: {latest['rsi']:.2f} ({'Rising' if latest['rsi'] > 50 else 'Neutral'})",
            f"EMA: {latest['ema_alignment']}",
            f"Volume Signal: {vol_signal:.1f}/100",
            f"OBV: {'Rising' if latest['obv_slope'] > 0 else 'Flat'}",
            f"Confidence: {scores['total']}/100",
        ]

    def _generate_reasons_short(self, structure: Dict, aoi: Dict, latest: pd.Series, scores: Dict, vol_signal: float) -> List[str]:
        return [
            f"4H Trend: {structure['trend']}",
            f"Market Regime: {structure['regime']}",
            f"BOS: {structure['break_of_structure']}",
            f"AOI: {aoi.get('type', '')} at ${aoi.get('price_low', 0):.2f}-${aoi.get('price_high', 0):.2f}",
            f"AOI Score: {aoi.get('strength_score', 0)}/100",
            f"RSI: {latest['rsi']:.2f} ({'Overbought' if latest['rsi'] >= 70 else 'Falling'})",
            f"EMA: {latest['ema_alignment']}",
            f"Volume Signal: {vol_signal:.1f}/100",
            f"OBV: {'Falling' if latest['obv_slope'] < 0 else 'Flat'}",
            f"Confidence: {scores['total']}/100",
        ]
