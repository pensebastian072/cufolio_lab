"""Allocator logic — pure functions, no IO."""
from cufolio_lab import allocate, config


def _report(cells, returns, active_days):
    return {
        "cells": cells,
        "returns": returns,
        "per_cell": {c: {"n_active_days": active_days[c]} for c in cells},
        "dates": list(range(max(len(v) for v in returns.values()))),
    }


def test_static_weights_sum_to_one():
    w = allocate.static_weights()
    assert abs(sum(w.values()) - 1.0) < 1e-9
    assert w == config.STATIC_WEIGHTS


def test_equal_weights():
    w = allocate.equal_weights(["a", "b", "c", "d"])
    assert w == {"a": 0.25, "b": 0.25, "c": 0.25, "d": 0.25}
    assert allocate.equal_weights([]) == {}


def test_inverse_variance_lower_var_gets_more_weight():
    returns = {"lo": [0.001, -0.001, 0.001, -0.001],   # small variance
               "hi": [0.05, -0.05, 0.05, -0.05]}       # large variance
    w = allocate.inverse_variance_weights(returns, ["lo", "hi"])
    assert w["lo"] > w["hi"]
    assert abs(sum(w.values()) - 1.0) < 1e-9


def test_inverse_variance_drops_zero_variance():
    returns = {"flat": [0.01, 0.01, 0.01], "vary": [0.0, 0.02, -0.01]}
    w = allocate.inverse_variance_weights(returns, ["flat", "vary"])
    assert "flat" not in w
    assert w["vary"] == 1.0


def test_eligible_requires_active_days_and_variance():
    report = _report(
        cells=["ok", "thin", "flat"],
        returns={"ok": [0.01, -0.02, 0.03, -0.01, 0.02],
                 "thin": [0.01, -0.02, 0.03, -0.01, 0.02],
                 "flat": [0.0, 0.0, 0.0, 0.0, 0.0]},
        active_days={"ok": 12, "thin": 3, "flat": 12},
    )
    elig = allocate.eligible_cells(report, min_active_days=10)
    assert elig == ["ok"]  # thin fails days, flat fails variance


def test_allocate_falls_back_when_insufficient():
    # mirrors today's real data: cells present but < min_active_days
    report = _report(
        cells=["schwartz_v2_spy_d", "basket_v2_2_usdjpy_30m"],
        returns={"schwartz_v2_spy_d": [0.01, -0.02, 0.03],
                 "basket_v2_2_usdjpy_30m": [0.001, -0.001, 0.002]},
        active_days={"schwartz_v2_spy_d": 4, "basket_v2_2_usdjpy_30m": 4},
    )
    method, status, weights, notes = allocate.allocate(report, "ok", min_active_days=10)
    assert method == "static_fallback"
    assert status == "insufficient_data"
    assert weights == config.STATIC_WEIGHTS


def test_allocate_active_when_data_sufficient():
    report = _report(
        cells=["a", "b"],
        returns={"a": [0.01, -0.02, 0.03, -0.01, 0.02, -0.03, 0.01, -0.02, 0.03, -0.01, 0.02],
                 "b": [0.001, -0.001, 0.002, -0.001, 0.001, -0.002, 0.001, -0.001, 0.002, -0.001, 0.001]},
        active_days={"a": 11, "b": 11},
    )
    method, status, weights, notes = allocate.allocate(report, "ok", min_active_days=10)
    assert method == "inverse_variance"
    assert status == "ok"
    assert set(weights) == {"a", "b"}
    assert weights["b"] > weights["a"]  # b lower variance -> more weight


def test_allocate_fallback_on_stale_and_missing():
    for status in ("stale_input", "missing_input", "corrupt_input"):
        report = None if status != "stale_input" else {"cells": [], "returns": {}}
        method, out_status, weights, _ = allocate.allocate(report, status)
        assert method == "static_fallback"
        assert weights == config.STATIC_WEIGHTS
