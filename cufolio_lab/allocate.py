"""Stub allocators — the shadow decision logic.

NO CVXPY / cuFOLIO yet. Mean-CVaR / mean-variance need a usable covariance,
which needs pairwise correlations — and HQ suppresses those until cells share
>= min_overlap_days. Until then the only defensible data-driven method is
inverse-variance (variances only, no correlations), and even that is gated on
per-cell active days; below the gate the honest output is the static fallback.

All functions are pure (dicts in, dicts out) so they test without any IO.
"""
from __future__ import annotations

import numpy as np

from . import config


def static_weights():
    """HQ's current combo sleeve allocation — the fail-safe."""
    return dict(config.STATIC_WEIGHTS)


def equal_weights(cells):
    if not cells:
        return {}
    w = 1.0 / len(cells)
    return {c: w for c in cells}


def inverse_variance_weights(returns, cells):
    """w_i proportional to 1/var(returns_i), normalized over `cells`. Cells with
    zero variance are dropped (undefined risk contribution)."""
    inv = {}
    for c in cells:
        v = float(np.var(np.array(returns[c]))) if returns.get(c) else 0.0
        if v > 0:
            inv[c] = 1.0 / v
    total = sum(inv.values())
    if total <= 0:
        return {}
    return {c: iv / total for c, iv in inv.items()}


def eligible_cells(report, min_active_days):
    """Cells with enough active days AND non-zero return variance."""
    out = []
    per_cell = report.get("per_cell", {})
    returns = report.get("returns", {})
    for c in report.get("cells", []):
        stats = per_cell.get(c, {})
        if stats.get("n_active_days", 0) < min_active_days:
            continue
        if float(np.var(np.array(returns.get(c, [0.0])))) <= 0:
            continue
        out.append(c)
    return out


def allocate(report, status, min_active_days=None):
    """Decide the shadow allocation.

    Returns (method, out_status, weights, notes). out_status is one of
    ok / insufficient_data / stale_input / missing_input / corrupt_input.
    Any non-ok path returns the static fallback weights (fail-safe)."""
    min_active_days = config.MIN_ACTIVE_DAYS if min_active_days is None else min_active_days
    notes = []

    if report is None or status in ("missing_input", "corrupt_input"):
        notes.append(f"input {status}; using static fallback")
        return "static_fallback", status, static_weights(), notes

    if status == "stale_input":
        notes.append("input stale; using static fallback")
        return "static_fallback", "stale_input", static_weights(), notes

    elig = eligible_cells(report, min_active_days)
    if len(elig) < 2:
        notes.append(f"only {len(elig)} cell(s) with >= {min_active_days} active "
                     "days and non-zero variance; using static fallback")
        return "static_fallback", "insufficient_data", static_weights(), notes

    weights = inverse_variance_weights(report.get("returns", {}), elig)
    notes.append(f"inverse-variance over {len(elig)} eligible cells "
                 "(no correlations yet -> Mean-CVaR deferred)")
    return "inverse_variance", "ok", weights, notes
