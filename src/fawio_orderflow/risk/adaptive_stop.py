"""Adaptive stop selection for NQ/MNQ research and simulation.

All price calculations use Decimal. Commission is treated as the configured
per-contract cost estimate; confirm whether that estimate is round-trip before
using it in a production risk budget.
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Optional


def _d(value: Decimal | str | int | float) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


class StopType(str, Enum):
    ORDERFLOW_TIGHT = "ORDERFLOW_TIGHT"
    STRUCTURAL_REFERENCE = "STRUCTURAL_REFERENCE"
    REJECTED_RISK_TOO_HIGH = "REJECTED_RISK_TOO_HIGH"


@dataclass(frozen=True)
class InstrumentSpec:
    symbol: str
    tick_size: Decimal
    tick_value: Decimal
    commission_per_contract: Decimal

    def __post_init__(self) -> None:
        if self.tick_size <= 0 or self.tick_value <= 0:
            raise ValueError("tick_size and tick_value must be positive")
        if self.commission_per_contract < 0:
            raise ValueError("commission_per_contract cannot be negative")


@dataclass(frozen=True)
class StopLossResult:
    stop_price: Decimal
    ticks_distance: int
    risk_dollars: Decimal
    stop_type: StopType
    is_valid: bool
    reason: str


class AdaptiveStopLossManager:
    def __init__(
        self,
        instrument: InstrumentSpec,
        tight_buffer_ticks: int = 3,
        structural_ref_ticks: int = 8,
        max_tight_distance_ticks: int = 6,
        volatility_threshold_ticks: int = 12,
        max_allowed_risk_ticks: int = 16,
        lvn_buffer_ticks: int = 2,
        block_threshold_contracts: int = 30,
    ) -> None:
        if min(
            tight_buffer_ticks,
            structural_ref_ticks,
            max_tight_distance_ticks,
            volatility_threshold_ticks,
            max_allowed_risk_ticks,
            lvn_buffer_ticks,
            block_threshold_contracts,
        ) < 1:
            raise ValueError("Stop and block thresholds must be positive")
        self.spec = instrument
        self.tight_buffer_ticks = tight_buffer_ticks
        self.structural_ref_ticks = structural_ref_ticks
        self.max_tight_distance_ticks = max_tight_distance_ticks
        self.volatility_threshold_ticks = volatility_threshold_ticks
        self.max_allowed_risk_ticks = max_allowed_risk_ticks
        self.lvn_buffer_ticks = lvn_buffer_ticks
        self.block_threshold_contracts = block_threshold_contracts

    def _ticks(self, price_distance: Decimal) -> int:
        ticks = price_distance / self.spec.tick_size
        integral = ticks.to_integral_value()
        if ticks != integral:
            raise ValueError("Price distance is not aligned to instrument tick size")
        return int(integral)

    def _result(
        self, entry: Decimal, stop: Decimal, stop_type: StopType,
        valid: bool, reason: str,
    ) -> StopLossResult:
        distance = self._ticks(entry - stop)
        risk = Decimal(distance) * self.spec.tick_value + self.spec.commission_per_contract
        return StopLossResult(
            stop_price=stop,
            ticks_distance=distance,
            risk_dollars=risk.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            stop_type=stop_type,
            is_valid=valid,
            reason=reason,
        )

    def calculate_long_stop(
        self,
        entry_price: Decimal | str | int | float,
        block_low: Optional[Decimal | str | int | float],
        lvn_level: Optional[Decimal | str | int | float],
        bar_high: Decimal | str | int | float,
        bar_low: Decimal | str | int | float,
        block_contracts: int = 0,
    ) -> StopLossResult:
        entry, high, low = _d(entry_price), _d(bar_high), _d(bar_low)
        if high < low or entry <= 0:
            raise ValueError("Invalid bar range or entry price")
        bar_range_ticks = self._ticks(high - low)

        # Tight stop is eligible only for a threshold-qualified block and
        # ordinary volatility. Presence of a price alone is not proof of a block.
        if (
            block_low is not None
            and block_contracts >= self.block_threshold_contracts
            and bar_range_ticks <= self.volatility_threshold_ticks
        ):
            block_price = _d(block_low)
            candidate = block_price - Decimal(self.tight_buffer_ticks) * self.spec.tick_size
            distance = self._ticks(entry - candidate)
            if 0 < distance <= self.max_tight_distance_ticks:
                return self._result(
                    entry, candidate, StopType.ORDERFLOW_TIGHT, True,
                    f"Qualifizierter Orderflow-Block ({block_contracts} Kontrakte): "
                    f"{self.tight_buffer_ticks} Ticks Puffer unter Block-Tief",
                )

        # Structural reference: retain the 8-tick baseline; if an LVN is
        # supplied, place the stop beyond its lower edge (the farther stop).
        structural = entry - Decimal(self.structural_ref_ticks) * self.spec.tick_size
        if lvn_level is not None:
            lvn = _d(lvn_level)
            if lvn < entry:
                structural = min(
                    structural,
                    lvn - Decimal(self.lvn_buffer_ticks) * self.spec.tick_size,
                )

        distance = self._ticks(entry - structural)
        if distance <= 0:
            raise ValueError("Calculated long stop must be below entry")
        if distance > self.max_allowed_risk_ticks:
            return self._result(
                entry, structural, StopType.REJECTED_RISK_TOO_HIGH, False,
                f"Abgelehnt: {distance} Ticks überschreiten das Maximum "
                f"von {self.max_allowed_risk_ticks} Ticks",
            )

        reason = "Struktureller Referenz-Stop"
        if bar_range_ticks > self.volatility_threshold_ticks:
            reason = (
                f"Volatilitätsschutz: Bar-Spanne {bar_range_ticks} Ticks; "
                "enger Orderflow-Stop deaktiviert"
            )
        elif block_low is not None and block_contracts < self.block_threshold_contracts:
            reason = (
                f"Block nicht qualifiziert ({block_contracts}/"
                f"{self.block_threshold_contracts} Kontrakte); Struktur-Stop"
            )
        return self._result(
            entry, structural, StopType.STRUCTURAL_REFERENCE, True, reason
        )
