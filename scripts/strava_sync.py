#!/usr/bin/env python3
"""
Sync Strava activities (and optional streams) into ~/.endurance-coach/coach.db.

Why this exists: intervals.icu API returns only 5 fields for activities whose
`source: STRAVA`. To get the real per-activity detail (sport_type, duration,
HR, power, distance, plus per-second streams) we have to talk to Strava
directly. This script writes activities with `source='strava-direct'` so
they coexist with the intervals.icu rows (which may be 5-field shells for
the same activity — dedupe is by Strava activity id stored in `id`).

Usage:
    # default: backfill 2025-10-07 → today, with streams
    python scripts/strava_sync.py

    # explicit window
    python scripts/strava_sync.py --since 2025-10-07 --until 2026-05-05

    # last N days
    python scripts/strava_sync.py --days 30

    # skip per-second streams (faster, fewer API calls)
    python scripts/strava_sync.py --no-streams

    # only run the schema migration
    python scripts/strava_sync.py --migrate-only

Schema additions (migration 004_strava_columns):
    activities:
        + strava_id     INTEGER  -- canonical Strava id (int)
        + device_name   TEXT
        + external_id   TEXT
        + has_streams   INTEGER  -- 0/1
    streams:
        + latlng_data   TEXT     -- JSON array of [lat, lng] pairs
        + temp_data     TEXT
        + grade_data    TEXT     -- grade_smooth

Rate limits (Strava): 100 req / 15 min, 1000 req / day.
With --streams: each activity costs 2 requests (detail + streams).
Default sleeps: 1.0s between activity-list pages, 9.0s between stream fetches.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.strava_api import (  # noqa: E402
    get_activity_detail,
    get_activity_streams,
    list_all_activities,
)

DB_PATH = Path.home() / ".endurance-coach" / "coach.db"

MIGRATION_NAME = "004_strava_columns"

MIGRATION_SQL = [
    "ALTER TABLE activities ADD COLUMN strava_id INTEGER",
    "ALTER TABLE activities ADD COLUMN device_name TEXT",
    "ALTER TABLE activities ADD COLUMN external_id TEXT",
    "ALTER TABLE activities ADD COLUMN has_streams INTEGER DEFAULT 0",
    "ALTER TABLE streams ADD COLUMN latlng_data TEXT",
    "ALTER TABLE streams ADD COLUMN temp_data TEXT",
    "ALTER TABLE streams ADD COLUMN grade_data TEXT",
    "CREATE INDEX IF NOT EXISTS idx_activities_strava_id ON activities(strava_id)",
    "CREATE INDEX IF NOT EXISTS idx_activities_source ON activities(source)",
    "CREATE INDEX IF NOT EXISTS idx_activities_start_date ON activities(start_date)",
]


UPSERT_ACTIVITY_SQL = """
INSERT INTO activities (
    id, name, sport_type, start_date, elapsed_time, moving_time,
    distance, total_elevation_gain, average_speed, max_speed,
    average_heartrate, max_heartrate, average_watts, max_watts,
    weighted_average_watts, kilojoules, suffer_score, average_cadence,
    calories, description, workout_type, gear_id, raw_json,
    source, strava_id, device_name, external_id, has_streams
) VALUES (
    :id, :name, :sport_type, :start_date, :elapsed_time, :moving_time,
    :distance, :total_elevation_gain, :average_speed, :max_speed,
    :average_heartrate, :max_heartrate, :average_watts, :max_watts,
    :weighted_average_watts, :kilojoules, :suffer_score, :average_cadence,
    :calories, :description, :workout_type, :gear_id, :raw_json,
    'strava-direct', :strava_id, :device_name, :external_id, :has_streams
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
    source='strava-direct',
    strava_id=excluded.strava_id,
    device_name=excluded.device_name,
    external_id=excluded.external_id,
    has_streams=COALESCE(excluded.has_streams, activities.has_streams),
    synced_at=datetime('now')
"""


UPSERT_STREAMS_SQL = """
INSERT INTO streams (
    activity_id, time_data, distance_data, heartrate_data, watts_data,
    cadence_data, altitude_data, velocity_data,
    latlng_data, temp_data, grade_data
) VALUES (
    :activity_id, :time_data, :distance_data, :heartrate_data, :watts_data,
    :cadence_data, :altitude_data, :velocity_data,
    :latlng_data, :temp_data, :grade_data
)
ON CONFLICT(activity_id) DO UPDATE SET
    time_data=excluded.time_data,
    distance_data=excluded.distance_data,
    heartrate_data=excluded.heartrate_data,
    watts_data=excluded.watts_data,
    cadence_data=excluded.cadence_data,
    altitude_data=excluded.altitude_data,
    velocity_data=excluded.velocity_data,
    latlng_data=excluded.latlng_data,
    temp_data=excluded.temp_data,
    grade_data=excluded.grade_data
"""


def _column_exists(cur: sqlite3.Cursor, table: str, col: str) -> bool:
    return any(r[1] == col for r in cur.execute(f"PRAGMA table_info({table})"))


def _streams_has_pk(cur: sqlite3.Cursor) -> bool:
    """Detect if streams.activity_id is already a PRIMARY KEY (needed for UPSERT)."""
    return any(
        r[1] == "activity_id" and r[5] == 1
        for r in cur.execute("PRAGMA table_info(streams)")
    )


def apply_migration(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM schema_migrations WHERE name=?", (MIGRATION_NAME,)
    )
    if cur.fetchone():
        return

    # If streams.activity_id is not a PK, the UPSERT ON CONFLICT(activity_id)
    # won't work. Rebuild the streams table with PK preserved.
    if not _streams_has_pk(cur):
        cur.executescript(
            """
            CREATE TABLE streams_new (
                activity_id INTEGER PRIMARY KEY,
                time_data TEXT,
                distance_data TEXT,
                heartrate_data TEXT,
                watts_data TEXT,
                cadence_data TEXT,
                altitude_data TEXT,
                velocity_data TEXT
            );
            INSERT INTO streams_new
              SELECT activity_id, time_data, distance_data, heartrate_data,
                     watts_data, cadence_data, altitude_data, velocity_data
              FROM streams;
            DROP TABLE streams;
            ALTER TABLE streams_new RENAME TO streams;
            """
        )

    for stmt in MIGRATION_SQL:
        try:
            cur.execute(stmt)
        except sqlite3.OperationalError as e:
            # ALTER ADD COLUMN errors out if the column already exists; that's fine.
            if "duplicate column name" not in str(e).lower():
                raise

    cur.execute(
        "INSERT INTO schema_migrations (name) VALUES (?)", (MIGRATION_NAME,)
    )
    conn.commit()


# ---------------- mappers ----------------

def map_activity(a: dict) -> dict:
    """Map a Strava activity → activities table row."""
    sid = a.get("id")
    workout_type = 0
    sport = a.get("sport_type") or a.get("type") or ""
    if a.get("workout_type") == 1:
        workout_type = 1  # race
    elif sport in ("Run", "Ride", "Swim", "TrailRun", "GravelRide"):
        workout_type = 2  # outdoor

    avg_speed = a.get("average_speed")
    max_speed = a.get("max_speed")

    return {
        "id": str(sid),
        "name": a.get("name"),
        "sport_type": sport or None,
        "start_date": a.get("start_date_local") or a.get("start_date"),
        "elapsed_time": a.get("elapsed_time"),
        "moving_time": a.get("moving_time"),
        "distance": a.get("distance"),
        "total_elevation_gain": a.get("total_elevation_gain"),
        "average_speed": avg_speed,
        "max_speed": max_speed,
        "average_heartrate": a.get("average_heartrate"),
        "max_heartrate": a.get("max_heartrate"),
        "average_watts": a.get("average_watts"),
        "max_watts": a.get("max_watts"),
        "weighted_average_watts": a.get("weighted_average_watts"),
        "kilojoules": a.get("kilojoules"),
        "suffer_score": a.get("suffer_score"),
        "average_cadence": a.get("average_cadence"),
        "calories": a.get("calories"),
        "description": a.get("description"),
        "workout_type": workout_type,
        "gear_id": a.get("gear_id"),
        "raw_json": json.dumps(a, ensure_ascii=False),
        "strava_id": int(sid) if sid is not None else None,
        "device_name": a.get("device_name"),
        "external_id": a.get("external_id"),
        "has_streams": 0,  # set to 1 later if streams fetched
    }


def map_streams(activity_id: int, streams: dict) -> dict:
    """Strava streams response → streams table row.

    Strava returns dict keyed by stream type, each value is
        {"data": [...], "series_type": "...", "original_size": int, ...}
    We store the data array as JSON.
    """
    def _data(key: str) -> str | None:
        s = streams.get(key)
        if not s or "data" not in s:
            return None
        return json.dumps(s["data"], ensure_ascii=False)

    return {
        "activity_id": activity_id,
        "time_data": _data("time"),
        "distance_data": _data("distance"),
        "heartrate_data": _data("heartrate"),
        "watts_data": _data("watts"),
        "cadence_data": _data("cadence"),
        "altitude_data": _data("altitude"),
        "velocity_data": _data("velocity_smooth"),
        "latlng_data": _data("latlng"),
        "temp_data": _data("temp"),
        "grade_data": _data("grade_smooth"),
    }


# ---------------- main ----------------

def parse_args() -> argparse.Namespace:
    today = date.today()
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--since", help="Start date YYYY-MM-DD (default 2025-10-07)")
    p.add_argument("--until", default=str(today), help="End date YYYY-MM-DD (default today)")
    p.add_argument("--days", type=int, help="Last N days (overrides --since)")
    p.add_argument(
        "--streams",
        dest="streams",
        action="store_true",
        default=True,
        help="Fetch per-second streams (default ON)",
    )
    p.add_argument("--no-streams", dest="streams", action="store_false")
    p.add_argument(
        "--detail",
        action="store_true",
        help="Fetch per-activity detail (extra request each, e.g. for description)",
    )
    p.add_argument(
        "--page-sleep",
        type=float,
        default=1.0,
        help="Seconds between activity-list pages (default 1.0)",
    )
    p.add_argument(
        "--stream-sleep",
        type=float,
        default=9.0,
        help="Seconds between stream fetches (default 9.0 → safe for 100 req/15min)",
    )
    p.add_argument("--migrate-only", action="store_true", help="Apply schema migration and exit")
    p.add_argument("--limit", type=int, help="Cap number of activities processed (debug)")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DB_PATH.exists():
        print(f"ERROR: {DB_PATH} not found. Run sync_db.py --init first.", file=sys.stderr)
        return 1

    conn = sqlite3.connect(DB_PATH)
    apply_migration(conn)

    if args.migrate_only:
        print(f"OK — migration {MIGRATION_NAME} applied")
        conn.close()
        return 0

    # Resolve date window
    today = date.today()
    if args.days:
        since = today - timedelta(days=args.days)
    else:
        since = datetime.strptime(args.since or "2025-10-07", "%Y-%m-%d").date()
    until = datetime.strptime(args.until, "%Y-%m-%d").date()

    after_unix = int(datetime(since.year, since.month, since.day, tzinfo=timezone.utc).timestamp())
    before_unix = int(
        datetime(until.year, until.month, until.day, 23, 59, 59, tzinfo=timezone.utc).timestamp()
    )

    cur = conn.cursor()
    started = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    cur.execute(
        "INSERT INTO sync_log (started_at, status) VALUES (?, 'started')",
        (started,),
    )
    sync_id = cur.lastrowid
    conn.commit()

    try:
        print(f"Strava sync window: {since} → {until}  (streams={args.streams})")
        activities = list_all_activities(
            after_unix=after_unix,
            before_unix=before_unix,
            page_sleep=args.page_sleep,
        )
        print(f"Got {len(activities)} activities from Strava")

        if args.limit:
            activities = activities[: args.limit]
            print(f"Limited to first {len(activities)} (--limit)")

        # Optionally enrich with detail (description, gear_id, etc.)
        if args.detail:
            print("Fetching per-activity detail (1 req each, slow)…")
            enriched = []
            for i, a in enumerate(activities, 1):
                try:
                    enriched.append(get_activity_detail(a["id"]))
                except Exception as e:  # noqa: BLE001
                    print(f"  detail fail id={a['id']}: {e}", file=sys.stderr)
                    enriched.append(a)
                if i % 10 == 0:
                    print(f"  {i}/{len(activities)} detailed")
                time.sleep(args.stream_sleep)
            activities = enriched

        # Upsert activities
        n_act = 0
        for a in activities:
            row = map_activity(a)
            cur.execute(UPSERT_ACTIVITY_SQL, row)
            n_act += 1
        conn.commit()
        print(f"Upserted {n_act} activities (source='strava-direct')")

        # Streams
        n_streams = 0
        n_skipped = 0
        if args.streams:
            print(f"Fetching streams ({args.stream_sleep}s/req → ~{len(activities)*args.stream_sleep/60:.1f}min)…")
            for i, a in enumerate(activities, 1):
                aid = a["id"]
                try:
                    s = get_activity_streams(aid)
                    if s:
                        cur.execute(UPSERT_STREAMS_SQL, map_streams(int(aid), s))
                        cur.execute(
                            "UPDATE activities SET has_streams=1 WHERE id=?",
                            (str(aid),),
                        )
                        n_streams += 1
                    else:
                        n_skipped += 1
                except Exception as e:  # noqa: BLE001
                    n_skipped += 1
                    print(f"  stream fail id={aid}: {e}", file=sys.stderr)

                if i % 5 == 0:
                    conn.commit()
                    print(f"  {i}/{len(activities)} streamed (ok={n_streams}, skip={n_skipped})")
                time.sleep(args.stream_sleep)
            conn.commit()
            print(f"Streams: {n_streams} ok, {n_skipped} skipped")

        cur.execute(
            "UPDATE sync_log SET completed_at=?, activities_synced=?, status='success' WHERE id=?",
            (
                datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
                n_act,
                sync_id,
            ),
        )
        conn.commit()
        print(f"OK — {n_act} activities, {n_streams} streams → {DB_PATH}")
        return 0

    except Exception as e:  # noqa: BLE001
        cur.execute(
            "UPDATE sync_log SET completed_at=?, status='failed' WHERE id=?",
            (
                datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
                sync_id,
            ),
        )
        conn.commit()
        print(f"FAIL: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
