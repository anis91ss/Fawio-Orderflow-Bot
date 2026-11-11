"""Validated application configuration loaded from trading_params.yaml."""
from pathlib import Path
from typing import Dict

import yaml
from pydantic import BaseModel, ConfigDict, Field

from fawio_orderflow.risk_manager import InstrumentSpec


class InstrumentYAML(BaseModel):
    model_config = ConfigDict(extra="ignore")
    tick_size: float = Field(gt=0)
    tick_value: float = Field(gt=0)
    commission_per_side: float = Field(ge=0)

    @property
    def round_trip_commission(self) -> float:
        return round(self.commission_per_side * 2.0, 4)


class StopLossHypothesesYAML(BaseModel):
    model_config = ConfigDict(extra="ignore")
    tight_buffer_ticks: int = Field(default=3, ge=1)
    structural_ref_ticks: int = Field(default=8, ge=1)
    max_tight_distance_ticks: int = Field(default=6, ge=1)
    volatility_threshold_ticks: int = Field(default=12, ge=1)
    max_allowed_risk_ticks: int = Field(default=16, ge=1)
    lvn_buffer_ticks: int = Field(default=2, ge=1)


class RiskManagementYAML(BaseModel):
    model_config = ConfigDict(extra="ignore")
    account_risk_pct: float = Field(default=0.0025, gt=0, le=0.05)
    daily_max_loss_pct: float = Field(default=0.02, gt=0, le=0.10)


class AppConfig(BaseModel):
    # The YAML also contains session, profile, strategy and execution settings;
    # this loader validates the subset currently consumed by the risk engine.
    model_config = ConfigDict(extra="ignore")
    instruments: Dict[str, InstrumentYAML]
    stop_loss_hypotheses: StopLossHypothesesYAML
    risk_management: RiskManagementYAML

    def get_instrument_spec(self, symbol: str) -> InstrumentSpec:
        sym = symbol.upper()
        if sym not in self.instruments:
            raise KeyError(f"Instrument '{symbol}' ist nicht in der Konfiguration definiert.")
        inst = self.instruments[sym]
        return InstrumentSpec(
            symbol=sym,
            tick_size=inst.tick_size,
            tick_value=inst.tick_value,
            commission_per_contract=inst.round_trip_commission,
        )


def load_config(config_path: str | Path = "config/trading_params.yaml") -> AppConfig:
    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"Konfigurationsdatei nicht gefunden unter: {path.resolve()}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError("Die YAML-Konfiguration muss ein YAML-Objekt enthalten.")
    return AppConfig.model_validate(data)
