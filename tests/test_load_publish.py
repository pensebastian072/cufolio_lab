"""Loader freshness + publish/read fail-safe round-trips (IO, tmp dirs)."""
import json
from datetime import datetime, timedelta, timezone

import pytest

from cufolio_lab import config, load, publish


def _iso(dt):
    return dt.isoformat()


def _write(path, obj):
    path.write_text(json.dumps(obj), encoding="utf-8")


# ── loader ───────────────────────────────────────────────────────


def test_load_missing_returns_none():
    report, status = load.load_daily_returns(config.REPO_ROOT / "does_not_exist.json")
    assert report is None
    assert status == "missing_input"


def test_load_corrupt_returns_none(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    report, status = load.load_daily_returns(p)
    assert report is None
    assert status == "corrupt_input"


def test_load_fresh_ok(tmp_path):
    p = tmp_path / "dr.json"
    _write(p, {"generated_at": _iso(datetime.now(timezone.utc)), "cells": []})
    report, status = load.load_daily_returns(p)
    assert status == "ok"
    assert report["cells"] == []


def test_load_stale_flagged(tmp_path):
    p = tmp_path / "dr.json"
    old = datetime.now(timezone.utc) - timedelta(hours=config.INPUT_STALE_HOURS + 5)
    _write(p, {"generated_at": _iso(old), "cells": []})
    report, status = load.load_daily_returns(p)
    assert status == "stale_input"
    assert report is not None  # stale still returns the data, just flagged


def test_is_stale_bad_ts():
    assert load.is_stale(None) is True
    assert load.is_stale("garbage") is True


# ── publish / read round-trip ────────────────────────────────────


@pytest.fixture
def alloc_file(tmp_path, monkeypatch):
    f = tmp_path / "allocations" / "portfolio_allocation_shadow.json"
    monkeypatch.setattr(config, "ALLOC_FILE", f)
    return f


def test_build_allocation_static_when_missing():
    alloc = publish.build_allocation(None, "missing_input")
    assert alloc["method"] == "static_fallback"
    assert alloc["enforced"] is False
    assert alloc["advisory"] is True
    assert abs(sum(alloc["weights"].values()) + alloc["cash"] - 1.0) < 1e-6


def test_publish_and_read_roundtrip(alloc_file):
    report = {"generated_at": datetime.now(timezone.utc).isoformat(),
              "data_hash": "sha256:abc", "cells": [], "returns": {},
              "per_cell": {}, "dates": []}
    alloc = publish.build_allocation(report, "ok")
    publish.publish(alloc)
    assert alloc_file.exists()
    back = publish.read_allocation()
    assert back["input_data_hash"] == "sha256:abc"
    assert back["enforced"] is False


def test_read_missing_returns_static_fallback(alloc_file):
    # file never written
    back = publish.read_allocation()
    assert back["method"] == "static_fallback"
    assert back["status"] == "missing_input"
    assert back["weights"] == {c: round(w, 6) for c, w in config.STATIC_WEIGHTS.items()}


def test_read_stale_file_returns_static_fallback(alloc_file):
    old = datetime.now(timezone.utc) - timedelta(hours=config.INPUT_STALE_HOURS + 5)
    alloc_file.parent.mkdir(parents=True, exist_ok=True)
    _write(alloc_file, {"generated_at": old.isoformat(), "method": "inverse_variance",
                        "weights": {"a": 1.0}})
    back = publish.read_allocation()
    assert back["method"] == "static_fallback"
    assert back["status"] == "stale_input"


def test_read_corrupt_file_returns_static_fallback(alloc_file):
    alloc_file.parent.mkdir(parents=True, exist_ok=True)
    alloc_file.write_text("{broken", encoding="utf-8")
    back = publish.read_allocation()
    assert back["method"] == "static_fallback"
