"""Risk-aware strategy wrapper; signal generation is intentionally separate."""
from decimal import Decimal
from typing import Optional

from fawio_orderflow.risk_manager import AdaptiveStopLossManager, StopLossResult


class FabioScalpEngine:
    def __init__(
        self,
        stop_manager: AdaptiveStopLossManager,
        risk_per_trade_pct: Decimal = Decimal("0.0025"),
        daily_drawdown_limit_pct: Decimal = Decimal("0.02"),
    ) -> None:
        if not (Decimal("0") < risk_per_trade_pct <= Decimal("0.01")):
            raise ValueError("risk_per_trade_pct must be in (0, 1%]")
        if not (Decimal("0") < daily_drawdown_limit_pct <= Decimal("0.10")):
            raise ValueError("daily_drawdown_limit_pct must be in (0, 10%]")
        self.stop_manager = stop_manager
        self.risk_per_trade_pct = risk_per_trade_pct
        self.daily_drawdown_limit_pct = daily_drawdown_limit_pct
        self.daily_realized_pnl = Decimal("0")
        self.is_daily_locked = False

    def calculate_position_size(
        self, account_equity: Decimal | str | int | float,
        risk_dollars_per_contract: Decimal,
    ) -> int:
        equity = Decimal(str(account_equity))
        if equity <= 0 or risk_dollars_per_contract <= 0:
            return 0
        allowed_risk = equity * self.risk_per_trade_pct
        # Strict sizing: zero contracts means NO_TRADE_RISK_EXCEEDED.
        return int(allowed_risk // risk_dollars_per_contract)

    def record_realized_pnl(
        self, pnl: Decimal | str | int | float,
        day_start_equity: Decimal | str | int | float,
    ) -> None:
        equity = Decimal(str(day_start_equity))
        self.daily_realized_pnl += Decimal(str(pnl))
        if equity <= 0 or self.daily_realized_pnl <= -(equity * self.daily_drawdown_limit_pct):
            self.is_daily_locked = True

    def reset_daily_guard(self) -> None:
        """Scheduler must call at the configured UTC reset boundary."""
        self.daily_realized_pnl = Decimal("0")
        self.is_daily_locked = False

    def evaluate_long_trigger(
        self,
        entry_price: Decimal | str | int | float,
        bar_high: Decimal | str | int | float,
        bar_low: Decimal | str | int | float,
        block_low: Optional[Decimal | str | int | float],
        lvn_level: Optional[Decimal | str | int | float],
        account_equity: Decimal | str | int | float,
        block_contracts: int = 0,
        reward_risk: Decimal = Decimal("3.0"),
    ) -> Optional[dict[str, object]]:
        if self.is_daily_locked:
            return None
        stop: StopLossResult = self.stop_manager.calculate_long_stop(
            entry_price, block_low, lvn_level, bar_high, bar_low, block_contracts
        )
        if not stop.is_valid:
            return None
        contracts = self.calculate_position_size(account_equity, stop.risk_dollars)
        if contracts == 0:
            return {
                "action": "NO_TRADE_RISK_EXCEEDED",
                "contracts": 0,
                "risk_per_contract": stop.risk_dollars,
                "reason": "Erlaubtes Kontorisiko reicht nicht für einen Kontrakt",
            }
        entry = Decimal(str(entry_price))
        target = entry + reward_risk * (entry - stop.stop_price)
        return {
            "action": "BUY",
            "entry_price": entry,
            "stop_price": stop.stop_price,
            "take_profit": target,
            "ticks_risk": stop.ticks_distance,
            "risk_per_contract": stop.risk_dollars,
            "total_planned_risk": stop.risk_dollars * contracts,
            "contracts": contracts,
            "stop_type": stop.stop_type.value,
            "reason": stop.reason,
        }
