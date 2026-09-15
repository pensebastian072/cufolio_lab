"""Build, atomically write, and fail-safe read the shadow allocation flag-file.

The artifact is ADVISORY: `enforced` is always False, `advisory` always True.
A consumer (HQ UI / daily report) that ever wires this in must treat a missing,
stale, or corrupt file as "use existing static weights" — read_allocation()
returns exactly that fallback and never raises.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from . import allocate, config
from .load import load_daily_returns


def build_allocation(report, status, min_active_days=None):
    """Assemble the allocation dict from an HQ report + load status."""
    method, out_status, weights, notes = allocate.allocate(
        report, status, min_active_days=min_active_days)
    report = report or {}
    return {
        "schema_version": config.SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": method,
        "status": out_status,
        "weights": {c: round(w, 6) for c, w in weights.items()},
        "cash": round(1.0 - sum(weights.values()), 6),
        "input_data_hash": report.get("data_hash"),
        "input_generated_at": report.get("generated_at"),
        "n_days": len(report.get("dates", [])),
        "notes": notes,
        "advisory": True,
        "enforced": False,
    }


def run(path=None, min_active_days=None):
    """Load HQ artifact -> allocate -> publish. Returns the allocation dict."""
    report, status = load_daily_returns(path)
    alloc = build_allocation(report, status, min_active_days=min_active_days)
    publish(alloc)
    return alloc


def publish(alloc):
    """Atomically write the allocation to the flag-file (tmp + replace)."""
    config.ALLOC_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = config.ALLOC_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(alloc, indent=2), encoding="utf-8")
    tmp.replace(config.ALLOC_FILE)
    return str(config.ALLOC_FILE)


def _static_fallback_dict():
    return {
        "schema_version": config.SCHEMA_VERSION,
        "generated_at": None,
        "method": "static_fallback",
        "status": "missing_input",
        "weights": {c: round(w, 6) for c, w in config.STATIC_WEIGHTS.items()},
        "cash": 0.0,
        "input_data_hash": None,
        "input_generated_at": None,
        "n_days": 0,
        "notes": ["allocation file missing/corrupt/stale -> static fallback"],
        "advisory": True,
        "enforced": False,
    }


def read_allocation():
    """Fail-safe reader for any consumer. Returns the published allocation, or
    the static fallback if the file is missing, unparseable, or older than the
    input-stale window. Never raises."""
    try:
        raw = json.loads(config.ALLOC_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — missing/corrupt -> static fallback
        return _static_fallback_dict()

    gen = raw.get("generated_at")
    try:
        ts = datetime.fromisoformat(str(gen).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age_h = (datetime.now(timezone.utc) - ts).total_seconds() / 3600.0
        if age_h > config.INPUT_STALE_HOURS:
            fb = _static_fallback_dict()
            fb["status"] = "stale_input"
            fb["notes"] = ["allocation file stale -> static fallback"]
            return fb
    except Exception:  # noqa: BLE001
        return _static_fallback_dict()
    return raw
