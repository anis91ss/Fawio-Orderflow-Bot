# Package layout

Planned modules, implemented incrementally:
- data/: normalized market events, replay and provider interfaces.
- indicators/: Volume Profile, Value Area, LVN and CVD.
- strategy/: market state machine and models A/B.
- risk/: sizing, daily circuit breaker and exit rules.
- execution/: simulated OMS, bracket/OCO and broker adapters.

Do not add live broker integration before simulation, risk and test phases are complete.
