from typing import Optional, List, Dict
import numpy as np
import pandas as pd
from engines.indicators import compute_all_indicators, get_volume_signal
from engines.market_structure import analyze_market_structure
from engines.aoi_detection import detect_all_aois, filter_relevant_aois
from config.settings import settings


class SignalEngine:
    def __init__(self):
        # Reported "high-conviction" confidence label (not a hard entry gate).
        self.min_confidence = 80.0
        # Full-target R:R requirement (trades aim for a 3R take-profit).
        self.min_risk_reward = settings.min_risk_reward
        # Trend-pullback entry parameters (validated out-of-sample on real data).
        self.atr_mult = 2.0            # ATR-multiple for the protective stop
        self.pullback_tol = 0.004      # how close price must be to the 15m EMA20
        self.pullback_lookback = 8     # bars to confirm a genuine pullback touch
        self.rsi_long_lo = 35.0        # RSI band for long re-entry (momentum turning up)
        self.rsi_long_hi = 62.0
        self.bull_regimes = ("STRONG_BULL", "WEAK_BULL")
        self.bear_regimes = ("STRONG_BEAR", "WEAK_BEAR")

    def evaluate_long_setup(self, df_4h: pd.DataFrame, df_15m: pd.DataFrame,
                            oi_change_pct: Optional[float] = None,
                            funding_rate: Optional[float] = None) -> Optional[Dict]:
        if "rsi" not in df_4h.columns:
            df_4h = compute_all_indicators(df_4h)
        if "rsi" not in df_15m.columns:
            df_15m = compute_all_indicators(df_15m)

        if len(df_4h) < 50 or len(df_15m) < self.pullback_lookback + 2:
            return None

        # 1) Higher-timeframe filter: only trade with an established 4H uptrend.
        structure_4h = analyze_market_structure(df_4h)
        if structure_4h["trend"] != "BULLISH":
            return None
        if structure_4h["regime"] not in self.bull_regimes:
            return None

        r4 = df_4h.iloc[-1]
        current_price = float(df_15m["close"].values[-1])
        # Price must be on the bullish side of both the 4H EMA50 and EMA200.
        if current_price <= r4["ema_50"] or current_price <= r4["ema_200"]:
            return None

        latest_15m = df_15m.iloc[-1]
        ema20_15 = latest_15m["ema_20"]
        atr_val = latest_15m["atr"]
        rsi = latest_15m["rsi"]
        if atr_val <= 0:
            return None

        # 2) Entry trigger: a pullback into the 15M EMA20 with momentum turning back up.
        recent_low = df_15m["low"].values[-self.pullback_lookback:].min()
        pulled_back = current_price <= ema20_15 * (1 + self.pullback_tol) and recent_low <= ema20_15
        rsi_turn = rsi > df_15m["rsi"].iloc[-2] and self.rsi_long_lo <= rsi <= self.rsi_long_hi
        if not (pulled_back and rsi_turn):
            return None

        # 3) Risk/target geometry: ATR stop, partial targets at 1.5R / 3R / 5R.
        entry = current_price
        stop_loss = entry - atr_val * self.atr_mult
        risk = entry - stop_loss
        if risk <= 0:
            return None
        tp1 = entry + risk * 1.5
        tp2 = entry + risk * 3.0
        tp3 = entry + risk * 5.0
        risk_reward = (tp2 - entry) / risk  # full target is 3R
        if risk_reward < self.min_risk_reward:
            return None

        # 4) Supplementary confidence score (reported, used for ranking).
        aois = detect_all_aois(df_4h)
        relevant_aois = filter_relevant_aois(aois, current_price, "LONG")
        best_aoi = relevant_aois[0] if relevant_aois else {
            "type": "EMA20_PULLBACK", "price_low": stop_loss, "price_high": entry, "strength_score": 60,
        }
        obv_confirmed = latest_15m["obv_slope"] > 0
        volume_signal = get_volume_signal(
            df_15m["volume"].values,
            df_15m["volume_ma"].values,
            df_15m["volume_std"].values,
        )
        scores = self._score_setup(
            structure_score=self._score_structure(structure_4h),
            aoi_score=best_aoi.get("strength_score", 60),
            volume_score=min(volume_signal, 100),
            rsi_score=self._score_rsi(rsi, "LONG"),
            obv_score=100 if obv_confirmed else 40,
            oi_score=self._score_oi(oi_change_pct, "LONG"),
            funding_score=self._score_funding(funding_rate, "LONG"),
        )

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
        if "rsi" not in df_4h.columns:
            df_4h = compute_all_indicators(df_4h)
        if "rsi" not in df_15m.columns:
            df_15m = compute_all_indicators(df_15m)

        if len(df_4h) < 50 or len(df_15m) < self.pullback_lookback + 2:
            return None

        # 1) Higher-timeframe filter: only trade with an established 4H downtrend.
        structure_4h = analyze_market_structure(df_4h)
        if structure_4h["trend"] != "BEARISH":
            return None
        if structure_4h["regime"] not in self.bear_regimes:
            return None

        r4 = df_4h.iloc[-1]
        current_price = float(df_15m["close"].values[-1])
        # Price must be on the bearish side of both the 4H EMA50 and EMA200.
        if current_price >= r4["ema_50"] or current_price >= r4["ema_200"]:
            return None

        latest_15m = df_15m.iloc[-1]
        ema20_15 = latest_15m["ema_20"]
        atr_val = latest_15m["atr"]
        rsi = latest_15m["rsi"]
        if atr_val <= 0:
            return None

        # 2) Entry trigger: a pull-up into the 15M EMA20 with momentum turning back down.
        recent_high = df_15m["high"].values[-self.pullback_lookback:].max()
        pulled_up = current_price >= ema20_15 * (1 - self.pullback_tol) and recent_high >= ema20_15
        rsi_turn = (rsi < df_15m["rsi"].iloc[-2]
                    and (100 - self.rsi_long_hi) <= rsi <= (100 - self.rsi_long_lo))
        if not (pulled_up and rsi_turn):
            return None

        # 3) Risk/target geometry: ATR stop, partial targets at 1.5R / 3R / 5R.
        entry = current_price
        stop_loss = entry + atr_val * self.atr_mult
        risk = stop_loss - entry
        if risk <= 0:
            return None
        tp1 = entry - risk * 1.5
        tp2 = entry - risk * 3.0
        tp3 = entry - risk * 5.0
        risk_reward = (entry - tp2) / risk  # full target is 3R
        if risk_reward < self.min_risk_reward:
            return None

        # 4) Supplementary confidence score (reported, used for ranking).
        aois = detect_all_aois(df_4h)
        relevant_aois = filter_relevant_aois(aois, current_price, "SHORT")
        best_aoi = relevant_aois[0] if relevant_aois else {
            "type": "EMA20_PULLBACK", "price_low": entry, "price_high": stop_loss, "strength_score": 60,
        }
        obv_confirmed = latest_15m["obv_slope"] < 0
        volume_signal = get_volume_signal(
            df_15m["volume"].values,
            df_15m["volume_ma"].values,
            df_15m["volume_std"].values,
        )
        scores = self._score_setup(
            structure_score=self._score_structure(structure_4h),
            aoi_score=best_aoi.get("strength_score", 60),
            volume_score=min(volume_signal, 100),
            rsi_score=self._score_rsi(rsi, "SHORT"),
            obv_score=100 if obv_confirmed else 40,
            oi_score=self._score_oi(oi_change_pct, "SHORT"),
            funding_score=self._score_funding(funding_rate, "SHORT"),
        )

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
