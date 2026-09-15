"""Fail-safe loader for HQ's daily-returns artifact.

Never raises: a missing/corrupt file returns None so the allocator falls back to
static weights. Freshness is judged on the artifact's own generated_at.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from . import config


def load_daily_returns(path=None):
    """Return (report_dict | None, status). status in {ok, missing_input,
    corrupt_input, stale_input}. Never raises."""
    path = path or config.HQ_DAILY_RETURNS
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, "missing_input"
    except (json.JSONDecodeError, OSError):
        return None, "corrupt_input"

    if is_stale(raw.get("generated_at")):
        return raw, "stale_input"
    return raw, "ok"


def is_stale(generated_at):
    """True if the artifact is older than INPUT_STALE_HOURS (or has no/bad ts)."""
    if not generated_at:
        return True
    try:
        ts = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return True
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    age_h = (datetime.now(timezone.utc) - ts).total_seconds() / 3600.0
    return age_h > config.INPUT_STALE_HOURS
