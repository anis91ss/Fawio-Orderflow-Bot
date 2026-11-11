# Package layout

Implemented package-root modules:
- `risk_manager.py`: Decimal-based adaptive NQ/MNQ stop selection and contract risk.
- `strategy.py`: FabioScalpEngine risk integration, strict position sizing and daily loss guard.

Planned modules, implemented incrementally:
- `data/`: normalized market events, replay and provider interfaces.
- `indicators/`: Volume Profile, Value Area, LVN and CVD.
- `execution/`: simulated OMS, bracket/OCO and broker adapters.

Tests live in `tests/test_adaptive_stop_loss.py`. Install the project and dev extras before running pytest.

Do not add live broker integration before simulation, risk and test phases are complete.
