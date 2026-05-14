#!/usr/bin/env python3
"""
Sync intervals.icu activities into local SQLite at ~/.endurance-coach/coach.db.

Replacement for the broken TypeScript CLI `coach sync` referenced in
SKILL.md. Fetches recent activities, upserts into the existing schema.

Usage:
    python scripts/sync_db.py                # last 90 days
    python scripts/sync_db.py --days 365     # last year
    python scripts/sync_db.py --from 2024-01-01 --to 2026-05-04
    python scripts/sync_db.py --init         # create schema if missing
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.intervals_api import list_activities, ATHLETE_ID  # noqa: E402

DB_PATH = Path.home() / ".endurance-coach" / "coach.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS activities (
  id TEXT PRIMARY KEY,
  name TEXT,
  sport_type TEXT,
  start_date TEXT,
  elapsed_time INTEGER,
  moving_time INTEGER,
  distance REAL,
  total_elevation_gain REAL,
  average_speed REAL,
  max_speed REAL,
  average_heartrate REAL,
  max_heartrate REAL,
  average_watts REAL,
  max_watts REAL,
  weighted_average_watts REAL,
  kilojoules REAL,
  suffer_score INTEGER,
  average_cadence REAL,
  calories REAL,
  description TEXT,
  workout_type INTEGER,
  gear_id TEXT,
  raw_json TEXT,
  synced_at TEXT DEFAULT (datetime('now')),
  source TEXT NOT NULL DEFAULT 'intervals.icu'
);

CREATE TABLE IF NOT EXISTS athlete (
  id TEXT PRIMARY KEY,
  firstname TEXT,
  lastname TEXT,
  weight REAL,
  ftp INTEGER,
  max_heartrate INTEGER,
  raw_json TEXT,
  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sync_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at TEXT,
  completed_at TEXT,
  activities_synced INTEGER,
  status TEXT
);
"""

UPSERT_SQL = """
INSERT INTO activities (
  id, name, sport_type, start_date, elapsed_time, moving_time,
  distance, total_elevation_gain, average_speed, max_speed,
  average_heartrate, max_heartrate, average_watts, max_watts,
  weighted_average_watts, kilojoules, suffer_score, average_cadence,
  calories, description, workout_type, gear_id, raw_json, source
) VALUES (
  :id, :name, :sport_type, :start_date, :elapsed_time, :moving_time,
  :distance, :total_elevation_gain, :average_speed, :max_speed,
  :average_heartrate, :max_heartrate, :average_watts, :max_watts,
  :weighted_average_watts, :kilojoules, :suffer_score, :average_cadence,
  :calories, :description, :workout_type, :gear_id, :raw_json, 'intervals.icu'
)
ON CONFLICT(id) DO UPDATE SET
  name=excluded.name,
  sport_type=excluded.sport_type,
  start_date=excluded.start_date,
  elapsed_time=excluded.elapsed_time,
  moving_time=excluded.moving_time,
  distance=excluded.distance,
  total_elevation_gain=excluded.total_elevation_gain,
  average_speed=excluded.average_speed,
  max_speed=excluded.max_speed,
  average_heartrate=excluded.average_heartrate,
  max_heartrate=excluded.max_heartrate,
  average_watts=excluded.average_watts,
  max_watts=excluded.max_watts,
  weighted_average_watts=excluded.weighted_average_watts,
  kilojoules=excluded.kilojoules,
  suffer_score=excluded.suffer_score,
  average_cadence=excluded.average_cadence,
  calories=excluded.calories,
  description=excluded.description,
  workout_type=excluded.workout_type,
  gear_id=excluded.gear_id,
  raw_json=excluded.raw_json,
  synced_at=datetime('now')
"""


def map_activity(a: dict) -> dict:
    """Map intervals.icu activity object → activities table row."""
    workout_type = 0
    if a.get("race"):
        workout_type = 1
    elif a.get("type", "").startswith(("Run", "Ride", "Swim")) and not a.get("trainer"):
        workout_type = 2

    return {
        "id": str(a.get("id")),
        "name": a.get("name"),
        "sport_type": a.get("type"),
        "start_date": a.get("start_date_local") or a.get("start_date"),
        "elapsed_time": a.get("elapsed_time"),
        "moving_time": a.get("moving_time"),
        "distance": a.get("distance") or a.get("icu_distance"),
        "total_elevation_gain": a.get("total_elevation_gain"),
        "average_speed": a.get("average_speed"),
        "max_speed": a.get("max_speed"),
        "average_heartrate": a.get("average_heartrate"),
        "max_heartrate": a.get("max_heartrate"),
        "average_watts": a.get("icu_average_watts") or a.get("average_watts"),
        "max_watts": a.get("p_max"),
        "weighted_average_watts": a.get("icu_weighted_avg_watts"),
        "kilojoules": a.get("icu_joules"),
        "suffer_score": a.get("strain_score") or a.get("icu_training_load"),
        "average_cadence": a.get("average_cadence"),
        "calories": a.get("calories"),
        "description": a.get("description"),
        "workout_type": workout_type,
        "gear_id": (a.get("gear") or {}).get("id") if isinstance(a.get("gear"), dict) else None,
        "raw_json": json.dumps(a, ensure_ascii=False),
    }


def init_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn


def main() -> int:
    today = date.today()
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=90)
    p.add_argument("--from", dest="oldest")
    p.add_argument("--to", dest="newest", default=str(today))
    p.add_argument("--init", action="store_true", help="Create schema and exit")
    args = p.parse_args()

    if args.init and not DB_PATH.exists():
        init_db()
        print(f"Initialized {DB_PATH}")
        return 0

    conn = init_db()
    cur = conn.cursor()

    started = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    cur.execute(
        "INSERT INTO sync_log (started_at, status) VALUES (?, 'started')",
        (started,),
    )
    sync_id = cur.lastrowid
    conn.commit()

    try:
        oldest = args.oldest or str(today - timedelta(days=args.days))
        print(f"Fetching activities {oldest} .. {args.newest} for athlete {ATHLETE_ID}")
        activities = list_activities(oldest, args.newest)
        print(f"Got {len(activities)} activities")

        n = 0
        for a in activities:
            cur.execute(UPSERT_SQL, map_activity(a))
            n += 1
        conn.commit()

        cur.execute(
            "UPDATE sync_log SET completed_at=?, activities_synced=?, status='success' WHERE id=?",
            (datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"), n, sync_id),
        )
        conn.commit()
        print(f"OK — synced {n} activities → {DB_PATH}")
        return 0

    except Exception as e:
        cur.execute(
            "UPDATE sync_log SET completed_at=?, status='failed' WHERE id=?",
            (datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"), sync_id),
        )
        conn.commit()
        print(f"FAIL: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
