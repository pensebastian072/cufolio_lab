"""CLI: python -m cufolio_lab.cli [--input PATH] [--min-active-days N] [--print]."""
from __future__ import annotations

import argparse
import json

from . import config, publish


def main():
    ap = argparse.ArgumentParser(
        description="Shadow portfolio allocator — reads HQ daily_returns.json, "
                    "writes an advisory allocation flag-file (never orders).")
    ap.add_argument("--input", type=str, default=None,
                    help=f"HQ daily_returns.json (default {config.HQ_DAILY_RETURNS})")
    ap.add_argument("--min-active-days", type=int, default=None,
                    help=f"active-days gate for the data-driven method "
                         f"(default {config.MIN_ACTIVE_DAYS})")
    ap.add_argument("--print", action="store_true", dest="do_print")
    args = ap.parse_args()

    from pathlib import Path
    path = Path(args.input) if args.input else None
    alloc = publish.run(path=path, min_active_days=args.min_active_days)

    if args.do_print:
        print(json.dumps(alloc, indent=2))
    else:
        print(f"wrote {config.ALLOC_FILE} "
              f"(method={alloc['method']}, status={alloc['status']}, "
              f"cells={len(alloc['weights'])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
