# Implementation Plan

Work through these phases in order. Live execution remains disabled.

## Phase 0 – Specification audit
Read CLAUDE.md and docs; audit codebase; list unresolved strategy decisions.
Acceptance: clean setup, test command, no credentials, live mode off.

## Phase 1 – Domain types and configuration
Create validated config and typed events: Tick, TradeEvent, Level2Snapshot, Bar, ProfileSnapshot, Signal, Position and Order state. Use timezone-aware timestamps and integer ticks/Decimal for price-sensitive calculations.
Acceptance: config/serialization tests; invalid data fails closed.

## Phase 2 – Replayable market data
Provider-neutral interfaces for trades, quotes and depth; deterministic file replay; handle sequence gaps, duplicates, reconnects and timestamps. Never fabricate MBO/Level 2 from OHLCV.
Acceptance: repeated replay yields identical outputs.

## Phase 3 – AMT indicators
Implement rolling/session profile, POC, 70% VAH/VAL, LVNs, prior-session references, CVD, 1-minute slope and configurable divergence. Document KDE/binning choices.
Acceptance: hand-calculated deterministic fixtures and boundary tests.

## Phase 4 – State machine
Implement BALANCED, OUT_OF_BALANCE and ABSORPTION; transitions, reset and invalidation; explicitly track and ignore initial drive. Do not guess unresolved thresholds.
Acceptance: table-driven transition tests.

## Phase 5 – Strategy models
Implement Model A second-drive/retest logic. Implement Model B only after missing parameters are approved. Log accepted/rejected setups. Propose short-side symmetry rather than silently assuming it.
Acceptance: replay fixtures; all thresholds traceable to config.

## Phase 6 – Risk
Daily -2.0% circuit breaker until 00:00 UTC; 0.25%–0.5% fixed-fraction sizing; dynamic stop, 1R and breakeven. Include fees, slippage and contract value. Unknown account/position state blocks new orders.
Acceptance: threshold, reset, sizing, rounding and missing-state tests.

## Phase 7 – Simulated OMS
Order lifecycle, idempotent IDs, OCO/brackets, partial fills, rejects, cancel/replace and restart recovery. Simulated broker first; verify protective stop acknowledgement.
Acceptance: lifecycle tests; no live adapter.

## Phase 8 – Broker/data integration
Only after provider/broker selection: implement documented APIs, verify CME entitlements, depth, limits, order types and calendar. Secrets external to Git; paper trade and reconcile state.
Acceptance: sandbox/paper integration tests.

## Phase 9 – Research and controlled release
Backtest with fees/slippage/realistic assumptions; report drawdown, expectancy, sample size and sensitivity; require human approval for live mode.
Acceptance: signed-off ambiguities, risk review, paper evidence and explicit approval. Otherwise live remains disabled.
