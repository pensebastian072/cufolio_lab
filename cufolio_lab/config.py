"""Paths + constants for the shadow allocator.

Cross-repo: reads HQ's journal artifact by local filesystem path (HQ's journal/
is gitignored, so this is a local read, never via git). Everything here is
advisory/reporting — no capital, no execution, no network.
"""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PARENT_DIR = REPO_ROOT.parent  # C:\Users\<your-user>

# HQ daily-returns artifact (produced by hq-trading-system/analytics/daily_returns.py).
HQ_DAILY_RETURNS = Path(os.environ.get(
    "HQ_DAILY_RETURNS",
    PARENT_DIR / "hq-trading-system" / "journal" / "portfolio" / "daily_returns.json",
))

# The one artifact this repo writes.
ALLOC_FILE = REPO_ROOT / "journal" / "allocations" / "portfolio_allocation_shadow.json"

SCHEMA_VERSION = 1

# Input freshness: the HQ artifact regenerates on demand (roughly daily). Older
# than this -> fall back to static weights and mark stale.
INPUT_STALE_HOURS = float(os.environ.get("CUFOLIO_INPUT_STALE_HOURS", "36"))

# An "active" data-driven method (inverse-variance today, Mean-CVaR later) needs
# at least this many active trading days per eligible cell. Below it, the honest
# answer is the static fallback, not an optimized allocation on noise.
MIN_ACTIVE_DAYS = int(os.environ.get("CUFOLIO_MIN_ACTIVE_DAYS", "10"))

# Static fallback = HQ's current combo_all5 sleeve allocation. This is the
# fail-safe the sidecar returns whenever the data is missing, stale, or too thin
# to optimize. Mirrors hq-trading-system analytics/config.py _SLEEVE_WEIGHTS
# (sums to 1.0; BASKET_v2_2 0.35 split equally across its 4 cells).
STATIC_WEIGHTS = {
    "schwartz_v2_spy_d":        0.30,
    "schwartz_v2_qqq_d":        0.15,
    "regimeswitch_v2_usdjpy_d": 0.10,
    "regimeswitch_v2_gbpusd_d": 0.10,
    "basket_v2_2_usdjpy_30m":   0.0875,
    "basket_v2_2_eurusd_15m":   0.0875,
    "basket_v2_2_gbpusd_30m":   0.0875,
    "basket_v2_2_usdcad_30m":   0.0875,
}
