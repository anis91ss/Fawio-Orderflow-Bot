from decimal import Decimal

import pytest

from fawio_orderflow.risk.adaptive_stop import (
    AdaptiveStopLossManager,
    InstrumentSpec,
    StopType,
)
from fawio_orderflow.strategy.fabio_strategy import FabioScalpEngine


@pytest.fixture
def nq_spec():
    return InstrumentSpec("NQ", Decimal("0.25"), Decimal("5.00"), Decimal("2.05"))


@pytest.fixture
def mnq_spec():
    return InstrumentSpec("MNQ", Decimal("0.25"), Decimal("0.50"), Decimal("0.62"))


def test_case_a_tight_orderflow_stop_nq(nq_spec):
    manager = AdaptiveStopLossManager(nq_spec)
    result = manager.calculate_long_stop(
        entry_price="21000.00", block_low="20999.50", lvn_level=None,
        bar_high="21000.50", bar_low="20999.00", block_contracts=35,
    )
    assert result.is_valid
    assert result.stop_type == StopType.ORDERFLOW_TIGHT
    assert result.stop_price == Decimal("20998.75")
    assert result.ticks_distance == 5
    assert result.risk_dollars == Decimal("27.05")


def test_case_b_structural_ref_stop_mnq(mnq_spec):
    manager = AdaptiveStopLossManager(mnq_spec)
    result = manager.calculate_long_stop(
        entry_price="21000.00", block_low=None, lvn_level=None,
        bar_high="21001.00", bar_low="20999.50",
    )
    assert result.is_valid
    assert result.stop_type == StopType.STRUCTURAL_REFERENCE
    assert result.stop_price == Decimal("20998.00")
    assert result.ticks_distance == 8
    assert result.risk_dollars == Decimal("4.62")


def test_case_c1_volatility_switches_to_structural(nq_spec):
    manager = AdaptiveStopLossManager(nq_spec, volatility_threshold_ticks=12)
    result = manager.calculate_long_stop(
        entry_price="21000.00", block_low="20999.50", lvn_level=None,
        bar_high="21002.50", bar_low="20999.00", block_contracts=40,
    )
    assert result.is_valid
    assert result.stop_type == StopType.STRUCTURAL_REFERENCE
    assert result.ticks_distance == 8
    assert "Volatilitätsschutz" in result.reason


def test_case_c2_rejects_excessive_lvn_risk(nq_spec):
    manager = AdaptiveStopLossManager(nq_spec, max_allowed_risk_ticks=10)
    result = manager.calculate_long_stop(
        entry_price="21000.00", block_low=None, lvn_level="20995.00",
        bar_high="21002.00", bar_low="20998.00",
    )
    assert not result.is_valid
    assert result.stop_type == StopType.REJECTED_RISK_TOO_HIGH
    assert result.ticks_distance == 22


def test_block_below_threshold_cannot_activate_tight_stop(nq_spec):
    manager = AdaptiveStopLossManager(nq_spec, block_threshold_contracts=30)
    result = manager.calculate_long_stop(
        entry_price="21000.00", block_low="20999.50", lvn_level=None,
        bar_high="21000.50", bar_low="20999.00", block_contracts=29,
    )
    assert result.stop_type == StopType.STRUCTURAL_REFERENCE


def test_position_size_never_forces_one_contract(nq_spec):
    manager = AdaptiveStopLossManager(nq_spec)
    engine = FabioScalpEngine(manager)
    assert engine.calculate_position_size("1000", Decimal("27.05")) == 0
    assert engine.calculate_position_size("20000", Decimal("27.05")) == 1


def test_daily_loss_guard_locks_at_threshold(nq_spec):
    engine = FabioScalpEngine(AdaptiveStopLossManager(nq_spec))
    engine.record_realized_pnl("-400", "20000")
    assert engine.is_daily_locked
    assert engine.evaluate_long_trigger(
        "21000", "21001", "20999", None, None, "20000"
    ) is None
