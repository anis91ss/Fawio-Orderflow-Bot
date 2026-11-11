# Fabio Valentino Orderflow & AMT – Strategy Blueprint

## 1. Scope and source
Structured transcription of the user's supplied three-page PDF, *Fabio Valentino Orderflow System – Claude Code Blueprint*. The source attributes the approach to a Chart Fanatics YouTube feature with Fabio Valentino.
- Instruments: CME E-mini Nasdaq 100 (NQ) and Micro E-mini Nasdaq 100 (MNQ).
- Architecture: event-driven Tick/MBO ingestion, Volume Profile engine, Delta Aggregator and state-machine OMS.
- Target stack: Claude Code CLI, Python 3.11+, NautilusTrader or custom async engine.
- Theory: Auction Market Theory (AMT), associated in the source with J. Peter Steidlmayer.

This is a transcription/engineering specification, not independent verification of the method or its profitability.

## 2. AMT foundations
Markets are treated as two-sided auctions seeking fair value through aggregated liquidity.

### Balance / imbalance
Balance: approximately Gaussian volume distribution around POC; price within the 70% Value Area (VAL–VAH). Imbalance: directional exploration outside balance; source threshold is breakout volume greater than 1.5 × sigma. The source does not define the sigma population, baseline or window.

### POC
Price with the highest aggregated transaction volume; algorithmically the absolute maximum of the Volume Profile V(P) over the selected lookback.

### LVN
Low-activity profile zones described as rejection/barrier areas with low dwell time. A level P* is a local minimum in [P*−δ, P*+δ] and V(P*) < α × median(V), with α = 0.30. The source does not specify δ, bin size, smoothing or KDE bandwidth.

### Aggression / sweeps
Market orders consume passive limit liquidity. Source threshold: Ask-Sweep ≥30 NQ contracts within ≤200 ms. It also describes directional block orders ≥30 lots. Aggressor classification and MNQ scaling are not defined.

### Absorption / failed auction
Aggressive market flow is absorbed by passive liquidity. Source description: CVD rises strongly while price remains within ≤2 ticks. No numerical CVD magnitude or observation window is supplied.

## 3. Trading models

### Model A – Trend-following momentum breakout
Intended around NY cash open, stated by source as 15:30–17:30 CET / 09:30–11:30 EST.
1. Consolidation: Value Area established for at least 30–60 minutes.
2. Initial drive: explicitly ignore the first impulsive breakout; no FOMO entry.
3. Second drive/retracement: price returns to a structural LVN or VAH/VAL edge.
4. Aggression trigger: on 1-minute chart or footprint, block orders ≥30 lots in trend direction.
5. Targets: unfinished auctions, prior-day Virgin POCs, or reward/risk 1:2–1:3.

The source reference template shows a long example: reject when daily drawdown limit reached; require price above VAH and second-drive flag; require price within 3 ticks of an LVN; sum recent BUY block volume and require threshold; require positive 1-minute CVD slope. Example stop is 8 ticks below entry and target 24 ticks above (1:3). No short-side algorithm is supplied.

### Model B – Mean-reversion / Failure to Auction
Context: London sessions or low-volatility periods, including summer months.
1. Market attempts breakout from balance.
2. Price meets substantial passive liquidity and aggressive flow is absorbed.
3. Breakout fails and price closes back inside Value Area.
4. Entry is against the failed breakout.
5. Target is Value Area POC.

Exact entry timing, stop, minimum absorption magnitude, observation window and invalidation are not supplied.

## 4. Risk and exits
- Daily circuit breaker: strict at -2.0% total account drawdown; block order submissions until 00:00 UTC.
- Per-trade risk: 0.25%–0.5% of account capital.
- Narrative stop: 2–4 ticks behind triggering orderflow block.
- Breakeven: at +1.0R OR when CVD slope abruptly flattens, move stop to breakeven (+1 tick).
- General target: 1:2–1:3, unfinished auction or prior-day Virgin POC; Model B target is POC.

Implementation must define account-equity baseline, realized/unrealized P&L, fees, resets, and measurable CVD flattening. Never allow stop changes to increase risk.

## 5. Mathematical definitions
CVD for trades t_i=(P_i,V_i,S_i), S_i=+1 Ask and −1 Bid:
`CVD(t) = CVD(t−1) + (V_i × S_i)`

LVN: local minimum V(P*) within the configured neighborhood, with:
`V(P*) < α × median(V)`, α=0.30.

Value Area is 70% of profile volume around POC, but the exact expansion algorithm is not specified. Imbalance uses >1.5 × sigma, but sigma's meaning and sampling window are not specified.

## 6. Architecture from source
- `config/trading_params.yaml`: thresholds such as block size 30, risk 0.5%, sessions.
- `src/data/market_feed.py`: async WebSocket/FIX ingestion (source examples: CME/Rithmic/IBKR).
- `src/data/order_book_types.py`: Tick, TradeEvent, Level2Snapshot.
- `src/indicators/volume_profile.py`: VAH, VAL, POC, LVN using KDE or ticks.
- `src/indicators/cvd_aggregator.py`: CVD and divergence engine.
- `src/execution/risk_manager.py`: circuit breaker and fixed-fraction sizing.
- `src/execution/order_manager.py`: bracket orders, trailing and breakeven.
- `src/strategy/state_machine.py`: BALANCED, OUT_OF_BALANCE, ABSORPTION.
- `src/strategy/valentino_engine.py`: signal orchestration.
- `tests/test_orderflow_logic.py`: deterministic LVN/CVD tests.

## 7. Reference long signal logic
1. Reject if drawdown reaches daily limit.
2. Require current price above VAH and second-drive flag true.
3. Require price within 3 ticks of an LVN.
4. Sum recent BUY block volumes; require at least configured 30 lots.
5. Require positive 1-minute CVD slope.
6. Example stop = entry −8 ticks; target = entry +24 ticks.
7. Emit BUY with reason `AMT_OUT_OF_BALANCE_LVN_BOUNCE`; otherwise no signal.

This is not a complete executable system: no ingestion, short side, realistic sizing, OMS, or full Model B.

## 8. Source implementation sequence
1. Initialize Python project with numpy, pandas, pydantic, scipy (KDE) and asyncio. Note: asyncio is in the Python standard library.
2. Implement rolling 60-minute and session Volume Profile: POC, VAH, VAL, LVN.
3. Implement CVD aggregator and price/CVD divergence.
4. Connect state machine to OMS with OCO bracket orders.

## 9. Unresolved source ambiguities – do not guess
1. Stop narrative 2–4 ticks versus reference 8 ticks.
2. Risk/reward range 1:2–1:3 versus sample 1:3.
3. 30-lot NQ block threshold; MNQ conversion not specified.
4. Ask-Sweep ≥30 NQ contracts within ≤200 ms versus generic block rule.
5. Aggressor-side source, CVD windows and divergence rules.
6. Absorption CVD magnitude and time window.
7. Profile bin size, KDE bandwidth, VA algorithm, LVN δ and sparse-level handling.
8. Sigma definition and baseline/window for 1.5× imbalance.
9. Explicit timezone, daylight saving and exchange holiday calendar for the stated NY session.
10. Model B entry, stop, risk/reward and invalidation.
11. Definitions/lookback for Virgin POC and unfinished auction.
12. Numeric CVD flattening threshold.
13. Market-data vendor, licensing, depth level, broker, reconnect and sequence-gap behavior.
14. Fees, slippage, queue position, latency and futures roll assumptions in backtests.

## 10. Validation
Before paper trading, test profile/CVD/state/strategy/risk/exit rules with deterministic fixtures. Replay tick and depth data; test missing, duplicated, delayed and out-of-order events, disconnects, partial fills, rejects, cancel/replace races and restart recovery. Include fees, slippage, realistic execution, out-of-sample periods and manually reviewed signal logs. No live trading without explicit approval of provider, broker, unresolved rules and separate live-mode procedure.
