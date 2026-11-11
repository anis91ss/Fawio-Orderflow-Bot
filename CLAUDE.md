# Claude Code – Fawio Orderflow Bot

## Mission
Implement the strategy documented in `docs/strategy_blueprint.md` as a testable, event-driven Python trading research system for CME E-mini / Micro E-mini Nasdaq 100 futures (NQ / MNQ). The source specification is authoritative. Do not silently change its thresholds or invent missing trading rules.

## Read first
1. `README.md`
2. `docs/strategy_blueprint.md`
3. `docs/implementation_plan.md`
4. `config/trading_params.yaml`

## Non-negotiable safety rules
- Default to research, replay, simulation and paper trading. Live order execution must remain disabled unless a human explicitly configures and confirms it.
- Never place a live order as part of tests, examples, startup, backtests or development.
- Enforce the daily loss circuit breaker and per-trade risk checks before any order can be submitted.
- Fail closed on stale, missing, malformed or out-of-order market data; unknown position state; disconnected broker; or risk-state uncertainty.
- Use broker-side protective orders where supported, and verify acknowledgements and current position before managing exits.
- Never hardcode credentials. Read secrets from environment variables or a secrets manager; commit only `.env.example`.
- Do not claim profitability or imply that the thresholds are validated. Require realistic fees, slippage and market-data assumptions in research.
- Add deterministic unit tests for every signal, state transition, risk rule and order lifecycle.
- Do not enable live trading without an explicit, separate approval step and documented broker-specific validation.

## Engineering conventions
- Python 3.11+; type hints on public interfaces; dataclasses or Pydantic models for validated event/config types.
- Keep data ingestion, normalization, indicators, strategy, risk, execution and persistence separate.
- Prefer small pure functions for calculations. Keep exchange/broker I/O behind interfaces.
- Use Decimal or integer ticks for prices and money-sensitive calculations; avoid binary-float price comparisons.
- All timestamps must be timezone-aware. Store UTC internally and convert session schedules using an explicit exchange timezone and calendar.
- Make session boundaries, holidays, daylight-saving changes, tick size, contract multiplier and fees configurable and tested.
- Log decisions with timestamp, market context, state, trigger and rejection reason. Never log secrets.
- Do not fabricate Level 2 / MBO data from ordinary OHLCV bars. Clearly label data fidelity.
- Keep strategy parameters in `config/trading_params.yaml`; validate them at startup.

## Required workflow
1. Inspect the existing code and tests before editing.
2. State a short plan for multi-file changes.
3. Implement in small increments.
4. Run formatting, static checks and tests; report commands and outcomes accurately.
5. Update docs when behavior or configuration changes.
6. Do not remove a risk guard or weaken a test merely to make a test pass.

## Strategy fidelity and unresolved items
The blueprint includes thresholds and a reference snippet, but also leaves implementation details unresolved. Preserve all source values and list conflicts explicitly in `docs/strategy_blueprint.md`. Do not decide these silently:
- It specifies a 2–4 tick stop behind the triggering orderflow block, while the reference code uses 8 ticks.
- It describes 1:2 to 1:3 reward/risk, while the sample returns 1:3.
- It defines a 30-lot NQ block threshold; MNQ scaling is not specified.
- It describes ask sweeps of at least 30 NQ contracts within at most 200 ms, while the sample code sums BUY blocks without a time-window implementation.
- The CVD trade-side classification, exact absorption threshold, profile binning/KDE parameters, and session calendar need precise definitions.
- The stated 15:30–17:30 CET and 09:30–11:30 EST session labels need an explicit timezone/calendar implementation for daylight-saving transitions.

When a decision is required, create a documented proposal and ask the user rather than silently changing the strategy.
