from typing import Dict, Optional, List
from datetime import datetime, timedelta, date
from config.settings import settings


class RiskManager:
    def __init__(self, account_balance: float = 10000.0):
        self.account_balance = account_balance
        self.trade_history: List[Dict] = []
        self.open_positions: List[Dict] = []

    def calculate_position_size(self, entry: float, stop_loss: float, risk_percent: float = None) -> Dict:
        risk_pct = risk_percent or settings.risk_per_trade
        dollar_risk = self.account_balance * risk_pct
        price_risk = abs(entry - stop_loss)

        if price_risk == 0:
            return {"position_size": 0, "dollar_risk": 0, "margin_required": 0, "leverage": 1}

        max_leverage = 10
        position_size = dollar_risk / price_risk
        position_value = position_size * entry
        leverage = min(position_value / max(self.account_balance, 1), max_leverage)
        margin_required = position_value / leverage if leverage > 0 else position_value

        if margin_required > self.account_balance * 0.5:
            position_size *= (self.account_balance * 0.5) / margin_required
            margin_required = self.account_balance * 0.5

        return {
            "position_size": round(position_size, 4),
            "dollar_risk": round(dollar_risk, 2),
            "margin_required": round(margin_required, 2),
            "leverage": round(leverage, 1),
        }

    def calculate_risk_reward(self, entry: float, stop_loss: float, take_profit: float, direction: str) -> float:
        if direction == "LONG":
            risk = entry - stop_loss
            reward = take_profit - entry
        else:
            risk = stop_loss - entry
            reward = entry - take_profit

        if risk <= 0:
            return 0

        return round(reward / risk, 2)

    def record_trade(self, trade: Dict):
        self.trade_history.append(trade)
        trade_date = datetime.fromisoformat(trade.get("exit_time", datetime.utcnow().isoformat()))
        trade["_date"] = trade_date

    def get_daily_pnl(self) -> float:
        today = datetime.utcnow().date()
        return sum(
            t.get("pnl", 0) for t in self.trade_history
            if t.get("_date", datetime.utcnow()).date() == today
        )

    def get_weekly_pnl(self) -> float:
        today = datetime.utcnow().date()
        week_start = today - timedelta(days=today.weekday())
        return sum(
            t.get("pnl", 0) for t in self.trade_history
            if t.get("_date", datetime.utcnow()).date() >= week_start
        )

    def check_daily_loss_limit(self) -> bool:
        daily_pnl = self.get_daily_pnl()
        if daily_pnl >= 0:
            return False
        daily_loss_pct = abs(daily_pnl) / max(self.account_balance, 1)
        return daily_loss_pct >= settings.daily_loss_limit

    def check_weekly_loss_limit(self) -> bool:
        weekly_pnl = self.get_weekly_pnl()
        if weekly_pnl >= 0:
            return False
        weekly_loss_pct = abs(weekly_pnl) / max(self.account_balance, 1)
        return weekly_loss_pct >= settings.weekly_loss_limit

    def can_open_position(self) -> bool:
        return len(self.open_positions) < settings.max_open_positions

    def can_trade(self) -> tuple:
        if self.check_daily_loss_limit():
            return False, "Daily loss limit reached"
        if self.check_weekly_loss_limit():
            return False, "Weekly loss limit reached"
        if not self.can_open_position():
            return False, "Max open positions reached"
        return True, "OK"

    def calculate_atr_stop(self, atr: float, multiplier: float = 2.0, direction: str = "LONG", current_price: float = 0) -> float:
        if direction == "LONG":
            return current_price - (atr * multiplier)
        return current_price + (atr * multiplier)

    def get_risk_metrics(self) -> Dict:
        daily_pnl = self.get_daily_pnl()
        weekly_pnl = self.get_weekly_pnl()

        return {
            "daily_pnl": round(daily_pnl, 2),
            "daily_pnl_percent": round(daily_pnl / max(self.account_balance, 1) * 100, 2),
            "weekly_pnl": round(weekly_pnl, 2),
            "weekly_pnl_percent": round(weekly_pnl / max(self.account_balance, 1) * 100, 2),
            "open_positions": len(self.open_positions),
            "max_open_positions": settings.max_open_positions,
            "daily_loss_limit_hit": self.check_daily_loss_limit(),
            "weekly_loss_limit_hit": self.check_weekly_loss_limit(),
            "current_risk_per_trade": settings.risk_per_trade,
            "account_balance": round(self.account_balance, 2),
        }
