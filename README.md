# cufolio_lab

Shadow portfolio-allocation sidecar for **hq-trading-system**. Reads HQ's
calendar-aligned daily per-cell returns and publishes one **advisory** allocation
flag-file. It never routes orders, never sizes real capital, and never sits on a
trade hot path.

```
hq-trading-system/journal/portfolio/daily_returns.json   (per-cell daily returns)
        │  local read (HQ journal is gitignored)
        ▼
cufolio_lab  ──►  journal/allocations/portfolio_allocation_shadow.json
        │              (method, weights, cash, provenance, advisory=true)
        └── consumers: HQ UI / daily report only.  enforced=false, always.
```

## Status: scaffold + stub

The allocator is a stub — **inverse-variance** when there is enough data, else
the **static fallback** (HQ's current combo_all5 sleeve weights). Real Mean-CVaR
/ cuFOLIO / CVXPY is deferred: it needs a usable covariance, and HQ suppresses
pairwise correlations until cells share enough overlapping trading days. With
today's ~8 live days the sidecar correctly returns
`static_fallback / insufficient_data`.

## Run

```
python -m cufolio_lab.cli --print          # load HQ artifact, publish, show it
python -m cufolio_lab.cli --min-active-days 10
```

## Test

No dedicated venv yet (numpy + pytest only). Until one exists, use HQ's:

```
..\hq-trading-system\.venv\Scripts\python -m pytest
```

See `CLAUDE.md` for the data contract and the hard shadow/paper rules.
