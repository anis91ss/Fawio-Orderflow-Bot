# Fawio Orderflow Bot

Claude Code implementation workspace for the supplied Fabio Valentino-inspired Auction Market Theory (AMT) and orderflow strategy.

**Markets:** CME E-mini / Micro E-mini Nasdaq 100 futures (NQ / MNQ)  
**Target:** Python 3.11+, event-driven architecture.

> Research and simulation specification only. It is not a validated or profitable trading system. Historical replay and paper trading first; live execution stays disabled by default.

## Claude Code
Open this repository in your development environment and run Claude Code from the project root. It should read `CLAUDE.md`.

Suggested first prompt:
```text
Read CLAUDE.md and docs/. Audit the repository, then implement Phase 1
from docs/implementation_plan.md. Preserve the strategy thresholds, add
deterministic tests, document ambiguities, and do not implement live trading.
```

## Layout
- `CLAUDE.md`: agent rules and safety constraints.
- `docs/strategy_blueprint.md`: complete structured strategy specification.
- `docs/implementation_plan.md`: phased roadmap and acceptance criteria.
- `config/trading_params.yaml`: configurable source parameters.
- `src/fawio_orderflow/`: Python package.
- `tests/`: deterministic tests.
- `.env.example`: variable names only; never commit secrets.

## Setup
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
pytest
```

## Safety defaults
Simulation/replay first. Source risk rules: daily circuit breaker at -2.0% until 00:00 UTC; per-trade risk 0.25%–0.5%. Unknown market/account/position state must block new orders. Protective orders must be acknowledged and verified.

Source ambiguities (including stop distance 2–4 ticks vs. sample 8 ticks) are recorded in the strategy specification and must not be silently resolved.