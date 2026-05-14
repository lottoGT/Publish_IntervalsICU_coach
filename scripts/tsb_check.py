#!/usr/bin/env python3
"""
Fetch CTL/ATL/TSB from intervals.icu wellness API and print a trend.

Usage:
    python scripts/tsb_check.py                       # last 30 days
    python scripts/tsb_check.py --from 2026-05-01 --to 2026-07-13
    python scripts/tsb_check.py --weekly               # one row per Sunday
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

from lib.intervals_api import get_wellness


def main() -> int:
    today = date.today()
    p = argparse.ArgumentParser()
    p.add_argument("--from", dest="oldest", default=str(today - timedelta(days=30)))
    p.add_argument("--to", dest="newest", default=str(today))
    p.add_argument("--weekly", action="store_true", help="Show only Sundays")
    args = p.parse_args()

    data = get_wellness(args.oldest, args.newest)
    print(f"{'date':<12} {'CTL':>6} {'ATL':>6} {'TSB':>7}  delta")
    prev_ctl = None
    for r in data:
        d = r["id"]
        if args.weekly:
            wd = date.fromisoformat(d).weekday()
            if wd != 6:  # Sunday
                continue
        ctl = r.get("ctl") or 0
        atl = r.get("atl") or 0
        tsb = ctl - atl
        delta = f"{ctl - prev_ctl:+.1f}" if prev_ctl is not None else "    "
        print(f"{d:<12} {ctl:>6.1f} {atl:>6.1f} {tsb:>+7.1f}  {delta}")
        prev_ctl = ctl
    return 0


if __name__ == "__main__":
    sys.exit(main())
