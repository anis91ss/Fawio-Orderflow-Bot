# Tests

Use deterministic fixtures only; no live network/broker connections.
Cover POC, VAH/VAL, LVN, CVD, state transitions, Model A initial-drive rejection and second-drive retest, Model B after its rules are approved, sizing, stop distance, +1R breakeven, -2% daily lockout, partial fills, rejects, OCO cancellation and recovery.

Tests must never submit live orders or require API credentials.
