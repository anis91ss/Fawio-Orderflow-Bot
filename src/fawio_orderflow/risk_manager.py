"""Adaptive NQ/MNQ stop selection for research and simulation."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from fawio_orderflow.config_loader import AppConfig


def _decimal(value: Decimal | str | int | float) -> Decimal:
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
            raise ValueError("commission cannot be negative")


@dataclass(frozen=True)
class StopLossResult:
    stop_price: Decimal
    ticks_distance: int
    risk_dollars: Decimal
    stop_type: StopType
    is_valid: bool
    reason: str


class AdaptiveStopLossManager:
    @classmethod
    def from_config(cls, config: "AppConfig", symbol: str) -> "AdaptiveStopLossManager":
        hypotheses = config.stop_loss_hypotheses
        return cls(instrument=config.get_instrument_spec(symbol),
                   tight_buffer_ticks=hypotheses.tight_buffer_ticks,
                   structural_ref_ticks=hypotheses.structural_ref_ticks,
                   max_tight_distance_ticks=hypotheses.max_tight_distance_ticks,
                   volatility_threshold_ticks=hypotheses.volatility_threshold_ticks,
                   max_allowed_risk_ticks=hypotheses.max_allowed_risk_ticks,
                   lvn_buffer_ticks=hypotheses.lvn_buffer_ticks)

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
        values = (tight_buffer_ticks, structural_ref_ticks, max_tight_distance_ticks,
                  volatility_threshold_ticks, max_allowed_risk_ticks,
                  lvn_buffer_ticks, block_threshold_contracts)
        if min(values) < 1:
            raise ValueError("All thresholds must be positive")
        self.instrument = instrument
        self.tight_buffer_ticks = tight_buffer_ticks
        self.structural_ref_ticks = structural_ref_ticks
        self.max_tight_distance_ticks = max_tight_distance_ticks
        self.volatility_threshold_ticks = volatility_threshold_ticks
        self.max_allowed_risk_ticks = max_allowed_risk_ticks
        self.lvn_buffer_ticks = lvn_buffer_ticks
        self.block_threshold_contracts = block_threshold_contracts

    def _ticks(self, distance: Decimal) -> int:
        ticks = distance / self.instrument.tick_size
        if ticks != ticks.to_integral_value():
            raise ValueError("Price is not aligned to tick size")
        return int(ticks)

    def _result(self, entry: Decimal, stop: Decimal, kind: StopType,
                valid: bool, reason: str) -> StopLossResult:
        distance = self._ticks(entry - stop)
        risk = (Decimal(distance) * self.instrument.tick_value
                + self.instrument.commission_per_contract)
        return StopLossResult(
            stop, distance, risk.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            kind, valid, reason,
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
        entry, high, low = map(_decimal, (entry_price, bar_high, bar_low))
        if entry <= 0 or high < low:
            raise ValueError("Invalid entry price or bar range")
        bar_range = self._ticks(high - low)

        # Tight orderflow stop requires a qualifying block AND normal volatility.
        if (block_low is not None
                and block_contracts >= self.block_threshold_contracts
                and bar_range <= self.volatility_threshold_ticks):
            block = _decimal(block_low)
            stop = block - Decimal(self.tight_buffer_ticks) * self.instrument.tick_size
            distance = self._ticks(entry - stop)
            if 0 < distance <= self.max_tight_distance_ticks:
                return self._result(
                    entry, stop, StopType.ORDERFLOW_TIGHT, True,
                    f"Qualifizierter Block ({block_contracts} Kontrakte), "
                    f"{self.tight_buffer_ticks} Ticks Puffer",
                )

        # Keep 8-tick reference; an LVN requires a stop beyond its lower edge.
        stop = entry - Decimal(self.structural_ref_ticks) * self.instrument.tick_size
        if lvn_level is not None:
            lvn = _decimal(lvn_level)
            if lvn < entry:
                stop = min(
                    stop,
                    lvn - Decimal(self.lvn_buffer_ticks) * self.instrument.tick_size,
                )
        distance = self._ticks(entry - stop)
        if distance <= 0:
            raise ValueError("Long stop must be below entry")
        if distance > self.max_allowed_risk_ticks:
            return self._result(
                entry, stop, StopType.REJECTED_RISK_TOO_HIGH, False,
                f"Abgelehnt: {distance} Ticks über Maximum "
                f"{self.max_allowed_risk_ticks}",
            )
        reason = "Struktureller Referenz-Stop"
        if bar_range > self.volatility_threshold_ticks:
            reason = f"Volatilitätsschutz: {bar_range} Ticks; enger Stop deaktiviert"
        elif block_low is not None and block_contracts < self.block_threshold_contracts:
            reason = f"Block nicht qualifiziert ({block_contracts} Kontrakte)"
        return self._result(entry, stop, StopType.STRUCTURAL_REFERENCE, True, reason)
