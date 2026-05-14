#!/usr/bin/env python3
"""
Update an intervals.icu event.

Usage:
    python scripts/update_event.py <event_id> --name "New Name" --desc "<workout builder>" --time 1800

The workout_doc field is deleted before PUT (so the server re-parses description).
"""
from __future__ import annotations

import argparse
import sys

from lib.intervals_api import update_event_description, get_event


def main() -> int:
    p = argparse.ArgumentParser(description="Update an intervals.icu event")
    p.add_argument("event_id", type=int, help="intervals.icu event ID")
    p.add_argument("--name", help="New event name")
    p.add_argument("--desc", help="New description (workout builder syntax)")
    p.add_argument("--time", type=int, help="New moving_time in seconds")
    p.add_argument("--show", action="store_true", help="Just GET and print the event")
    args = p.parse_args()

    if args.show:
        ev = get_event(args.event_id)
        print(
            f"id={ev['id']}\nname={ev.get('name')}\ntype={ev.get('type')}\n"
            f"date={ev.get('start_date_local')}\nmoving_time={ev.get('moving_time')}\n"
            f"steps={len(ev.get('workout_doc', {}).get('steps', []))}\n"
            f"description:\n{ev.get('description', '')}"
        )
        return 0

    changes: dict = {}
    if args.name:
        changes["name"] = args.name
    if args.desc:
        changes["description"] = args.desc
    if args.time:
        changes["moving_time"] = args.time

    if not changes:
        p.error("No changes specified — use --name, --desc, or --time")

    result = update_event_description(args.event_id, **changes)
    steps = len(result.get("workout_doc", {}).get("steps", []))
    print(
        f"OK — name={result.get('name')} steps={steps} "
        f"moving_time={result.get('moving_time')}"
    )
    if steps == 0 and result.get("type") not in ("WeightTraining", "Other"):
        print("WARNING: steps=0 — Garmin/Zwift sync will not work", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
