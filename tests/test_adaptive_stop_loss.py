from decimal import Decimal

from fawio_orderflow.risk_manager import AdaptiveStopLossManager, InstrumentSpec, StopType
from fawio_orderflow.strategy import FabioScalpEngine


def nq():
    return InstrumentSpec("NQ", Decimal("0.25"), Decimal("5.00"), Decimal("2.05"))


def mnq():
    return InstrumentSpec("MNQ", Decimal("0.25"), Decimal("0.50"), Decimal("0.62"))


def test_tight_orderflow_stop_nq():
    result = AdaptiveStopLossManager(nq()).calculate_long_stop(
        "21000", "20999.50", None, "21000.50", "20999.00", block_contracts=35
    )
    assert result.is_valid and result.stop_type == StopType.ORDERFLOW_TIGHT
    assert result.stop_price == Decimal("20998.75")
    assert result.ticks_distance == 5
    assert result.risk_dollars == Decimal("27.05")


def test_structural_reference_stop_mnq():
    result = AdaptiveStopLossManager(mnq()).calculate_long_stop(
        "21000", None, None, "21001", "20999.50"
    )
    assert result.is_valid and result.stop_type == StopType.STRUCTURAL_REFERENCE
    assert result.stop_price == Decimal("20998.00")
    assert result.ticks_distance == 8
    assert result.risk_dollars == Decimal("4.62")


def test_volatility_switches_to_structural():
    result = AdaptiveStopLossManager(nq()).calculate_long_stop(
        "21000", "20999.50", None, "21002.50", "20999", block_contracts=40
    )
    assert result.is_valid and result.stop_type == StopType.STRUCTURAL_REFERENCE
    assert result.ticks_distance == 8
    assert "Volatilitätsschutz" in result.reason


def test_excessive_lvn_risk_is_rejected():
    result = AdaptiveStopLossManager(nq(), max_allowed_risk_ticks=10).calculate_long_stop(
        "21000", None, "20995", "21002", "20998"
    )
    assert not result.is_valid
    assert result.stop_type == StopType.REJECTED_RISK_TOO_HIGH
    assert result.ticks_distance == 22


def test_small_block_does_not_enable_tight_stop():
    result = AdaptiveStopLossManager(nq()).calculate_long_stop(
        "21000", "20999.50", None, "21000.50", "20999", block_contracts=29
    )
    assert result.stop_type == StopType.STRUCTURAL_REFERENCE


def test_sizing_never_forces_minimum_contract():
    engine = FabioScalpEngine(AdaptiveStopLossManager(nq()))
    assert engine.calculate_position_size("1000", Decimal("27.05")) == 0
    assert engine.calculate_position_size("20000", Decimal("27.05")) == 1


def test_5000_account_allows_two_mnq_but_zero_nq():
    nq_spec, mnq_spec = nq(), mnq()
    nq_engine = FabioScalpEngine(AdaptiveStopLossManager(nq_spec))
    mnq_engine = FabioScalpEngine(AdaptiveStopLossManager(mnq_spec))
    nq_risk = Decimal("8") * nq_spec.tick_value + nq_spec.commission_per_contract
    mnq_risk = Decimal("8") * mnq_spec.tick_value + mnq_spec.commission_per_contract
    assert nq_engine.calculate_position_size("5000", nq_risk) == 0
    assert mnq_engine.calculate_position_size("5000", mnq_risk) == 2


def test_daily_loss_guard_blocks_new_trades():
    engine = FabioScalpEngine(AdaptiveStopLossManager(nq()))
    engine.record_realized_pnl("-400", "20000")
    assert engine.is_daily_locked
    assert engine.evaluate_long_trigger("21000", "21001", "20999", None, None, "20000") is None
