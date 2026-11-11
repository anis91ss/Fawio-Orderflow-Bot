"""Strategy-side risk integration; signal generation remains separate."""
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from fawio_orderflow.risk.adaptive_stop import (
    AdaptiveStopLossManager,
    StopLossResult,
)


@dataclass
class FabioScalpEngine:
    stop_manager: AdaptiveStopLossManager
    risk_per_trade_pct: Decimal = Decimal("0.0025")
    daily_drawdown_limit_pct: Decimal = Decimal("0.02")

    def __post_init__(self) -> None:
        if not (Decimal("0") < self.risk_per_trade_pct <= Decimal("0.01")):
            raise ValueError("risk_per_trade_pct must be in (0, 1%]")
        if not (Decimal("0") < self.daily_drawdown_limit_pct <= Decimal("0.10")):
            raise ValueError("daily_drawdown_limit_pct must be in (0, 10%]")
        self.daily_realized_pnl = Decimal("0")
        self.is_daily_locked = False

    def record_realized_pnl(self, pnl: Decimal | str | int | float,
                            account_equity_at_day_start: Decimal | str | int | float) -> None:
        self.daily_realized_pnl += Decimal(str(pnl))
        day_start_equity = Decimal(str(account_equity_at_day_start))
        if day_start_equity <= 0:
            self.is_daily_locked = True
            return
        if self.daily_realized_pnl <= -(day_start_equity * self.daily_drawdown_limit_pct):
            self.is_daily_locked = True

    def reset_daily_guard(self) -> None:
        """Call only from the scheduler after the configured UTC session reset."""
        self.daily_realized_pnl = Decimal("0")
        self.is_daily_locked = False

    def calculate_position_size(self, account_equity: Decimal | str | int | float,
                                 risk_per_contract: Decimal) -> int:
        equity = Decimal(str(account_equity))
        if equity <= 0 or risk_per_contract <= 0:
            return 0
        risk_budget = equity * self.risk_per_trade_pct
        # Never force one contract when it exceeds the risk budget.
        return int(risk_budget // risk_per_contract)

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
            entry_price=entry_price,
            block_low=block_low,
            lvn_level=lvn_level,
            bar_high=bar_high,
            bar_low=bar_low,
            block_contracts=block_contracts,
        )
        if not stop.is_valid:
            return None
        contracts = self.calculate_position_size(account_equity, stop.risk_dollars)
        if contracts == 0:
            return None

        entry = Decimal(str(entry_price))
        risk_points = entry - stop.stop_price
        target = entry + reward_risk * risk_points
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
