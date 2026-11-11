from pathlib import Path

import pytest
from pydantic import ValidationError

from fawio_orderflow.config_loader import AppConfig, load_config


CONFIG_PATH = Path(__file__).parents[1] / "config" / "trading_params.yaml"


def test_load_default_config():
    config = load_config(CONFIG_PATH)
    assert isinstance(config, AppConfig)
    assert {"NQ", "MNQ"}.issubset(config.instruments)


def test_round_trip_commission_calculation():
    config = load_config(CONFIG_PATH)
    nq = config.get_instrument_spec("NQ")
    assert nq.symbol == "NQ"
    assert nq.tick_size == pytest.approx(0.25)
    assert nq.tick_value == pytest.approx(5.00)
    assert nq.commission_per_contract == pytest.approx(4.10)

    mnq = config.get_instrument_spec("MNQ")
    assert mnq.symbol == "MNQ"
    assert mnq.tick_size == pytest.approx(0.25)
    assert mnq.tick_value == pytest.approx(0.50)
    assert mnq.commission_per_contract == pytest.approx(1.24)


def test_missing_instrument_raises_key_error():
    with pytest.raises(KeyError):
        load_config(CONFIG_PATH).get_instrument_spec("ES")


def test_missing_file_raises_error():
    with pytest.raises(FileNotFoundError):
        load_config(CONFIG_PATH.parent / "nicht_existent.yaml")


def test_invalid_config_values_are_rejected():
    with pytest.raises(ValidationError):
        AppConfig.model_validate({
            "instruments": {"NQ": {
                "tick_size": 0, "tick_value": 5, "commission_per_side": 2.05
            }},
            "stop_loss_hypotheses": {},
            "risk_management": {},
        })
