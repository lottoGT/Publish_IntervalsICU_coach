#!/usr/bin/env python3
"""
POST a new event to intervals.icu.

Usage:
    python scripts/post_event.py --date 2026-07-14 --type VirtualRide \\
        --name "FTP Test 20min" --desc "- Warm up 15m Z2..." --time 3600
"""
from __future__ import annotations

import argparse
import sys

from lib.intervals_api import post_event, event_payload

VALID_TYPES = (
    "Run", "Ride", "VirtualRide", "Swim",
    "WeightTraining", "Other", "Workout",
)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--date", required=True, help="YYYY-MM-DD")
    p.add_argument("--type", required=True, choices=VALID_TYPES)
    p.add_argument("--name", required=True)
    p.add_argument("--desc", required=True, help="Workout builder syntax")
    p.add_argument("--time", type=int, required=True, help="Moving time seconds")
    args = p.parse_args()

    payload = event_payload(args.date, args.type, args.name, args.desc, args.time)
    result = post_event(payload)
    steps = len(result.get("workout_doc", {}).get("steps", []))
    print(
        f"OK — id={result.get('id')} {result.get('type')} "
        f"[{result.get('name')}] steps={steps}"
    )
    if steps == 0 and args.type not in ("WeightTraining", "Other"):
        print("WARNING: steps=0 — workout builder syntax may have errors", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
