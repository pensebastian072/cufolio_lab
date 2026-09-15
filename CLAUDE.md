# cufolio_lab — agent guide

Shadow **portfolio-allocation sidecar** for `hq-trading-system`. Reads HQ's
calendar-aligned daily-returns artifact and writes **one advisory flag-file**
`journal/allocations/portfolio_allocation_shadow.json`. Same pattern as
`copper_brain` (advisory JSON, off the hot path). cufolio_lab **never sends
orders, never sizes real capital, never sits on any trade path.**

This is a scaffold: the allocator is a stub (inverse-variance + static
fallback). Real Mean-CVaR / cuFOLIO / CVXPY is deferred until the inputs earn
it (see rule 3). NOT installed yet — CPU-only, numpy-only for now.

Skills: load `paper-trading-guardrails` before editing publish/allocate/reader
code, `quant-research-gate` before adding any optimizer/backtest, `win-quant-env`
before installs/git/PS. Before committing, run
`node ~/.claude/hooks/quant-review-scope.js cufolio_lab`; on `DECISION: REVIEW`
run the `quant-reviewer` subagent.

## Data contract

- **Input**: `hq-trading-system/journal/portfolio/daily_returns.json`
  (`schema_version`, `generated_at`, `data_hash`, `dates`, `cells`, `returns`,
  `trade_counts`, `per_cell`, `pairwise`, `combined`). HQ's `journal/` is
  gitignored, so this is a **local filesystem read** across repos, never git.
  Override the path with env `HQ_DAILY_RETURNS`.
- **Output**: `journal/allocations/portfolio_allocation_shadow.json`
  (`method`, `status`, `weights`, `cash`, `input_data_hash`, `input_generated_at`,
  `n_days`, `notes`, `advisory=true`, `enforced=false`). Written atomically
  (tmp + replace).

## Hard rules (non-negotiable — mirror hq-trading-system)

1. **Advisory / shadow only.** Writes a JSON file. `enforced` is always false.
   Never routes an order, never feeds live sizing. No live broker, no keys.
2. **Off the hot path.** Any consumer reads the flag-file via `read_allocation()`,
   which **fail-safes**: missing / corrupt / stale file => static fallback
   weights (HQ's current combo allocation), never raises, never blocks.
3. **Overfit-strict, shadow until the gate clears.** No allocation influences
   even *paper* sizing until it beats equal-weight and the static combo
   out-of-sample under HQ's PBO < 0.5 AND Deflated Sharpe > 0 (purged
   walk-forward). Every risk-aversion / cap / rebalance-frequency variant counts
   as a trial. Today the data is too thin (all HQ pairwise correlations null),
   so the allocator correctly returns `static_fallback / insufficient_data`.
4. **No correlations => no Mean-CVaR.** Covariance-based optimization is disabled
   until HQ emits non-null pairwise correlations (>= its `min_overlap_days`).
   The stub uses variances only (inverse-variance) and gates on per-cell active
   days (`MIN_ACTIVE_DAYS`, default 10).
5. **Isolated.** Never import into HQ's `.venv`; do not add CVXPY/cuML/cuOpt to
   any trading repo's environment. When a real optimizer lands, it lives here.

## Verification

- Tests: `<hq venv or local>\Scripts\python -m pytest` (needs numpy + pytest).
  There is no dedicated `.venv` yet — a follow-up under `win-quant-env` should
  create one (`--native-tls` / truststore behind the TLS proxy). Until then run
  with hq-trading-system's venv:
  `..\hq-trading-system\.venv\Scripts\python -m pytest`
- Run the allocator: `python -m cufolio_lab.cli --print`
  Expected today: `method=static_fallback, status=insufficient_data`.

## Reuse from hq-trading-system (do not reinvent)

- PBO (CSCV) + Deflated Sharpe + walk-forward: `analytics/research_scorecard.py`
- Flag-file + fail-safe reader pattern: `copper_brain/publish.py`,
  hq `analytics/veto_reconcile.py`
- The daily-returns producer: hq `analytics/daily_returns.py`

## Environment

Windows 10, PowerShell 5.1, local-timezone day boundaries, TLS-intercepting
proxy. See `win-quant-env`. Commit with
`git -c user.email='YOUR_GITHUB_NOREPLY_EMAIL' -c user.name='YOUR_GITHUB_USERNAME'`;
retry `git add` if Norton transiently locks `.git/objects`.
