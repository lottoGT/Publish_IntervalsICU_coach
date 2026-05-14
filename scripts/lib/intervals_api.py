"""
intervals.icu API helper.

Reads credentials from (in priority order):
  1. Environment variables: INTERVALS_API_KEY, INTERVALS_ATHLETE_ID
  2. .env file at repo root
  3. ~/.endurance-coach/config.json

Uses curl subprocess + file-based JSON because:
- Cloudflare blocks Python urllib (returns 403)
- Windows curl with -d "<chinese-text>" causes JSON parse errors,
  so we always write to a UTF-8 file and use --data-binary @file
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

BASE = "https://intervals.icu/api/v1/athlete"


def _load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _load_credentials() -> tuple[str, str]:
    # 1. env vars
    api_key = os.environ.get("INTERVALS_API_KEY")
    athlete_id = os.environ.get("INTERVALS_ATHLETE_ID")
    if api_key and athlete_id:
        return api_key, athlete_id

    # 2. .env at repo root (script's grandparent)
    repo_root = Path(__file__).resolve().parents[2]
    env = _load_env_file(repo_root / ".env")
    api_key = api_key or env.get("INTERVALS_API_KEY")
    athlete_id = athlete_id or env.get("INTERVALS_ATHLETE_ID")
    if api_key and athlete_id:
        return api_key, athlete_id

    # 3. ~/.endurance-coach/config.json
    cfg_path = Path.home() / ".endurance-coach" / "config.json"
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        api_key = api_key or cfg.get("intervals", {}).get("api_key")
        athlete_id = athlete_id or cfg.get("intervals", {}).get("athlete_id")

    if not api_key or not athlete_id:
        sys.stderr.write(
            "ERROR: intervals.icu credentials not found.\n"
            "Set INTERVALS_API_KEY and INTERVALS_ATHLETE_ID via:\n"
            "  - Environment variables, or\n"
            "  - .env file at repo root, or\n"
            "  - ~/.endurance-coach/config.json\n"
            "Run install/setup.sh to configure.\n"
        )
        sys.exit(1)

    return api_key, athlete_id


API_KEY, ATHLETE_ID = _load_credentials()
AUTH = f"API_KEY:{API_KEY}"
ATHLETE_URL = f"{BASE}/{ATHLETE_ID}"


def _curl(method: str, url: str, body: dict | None = None) -> dict | list:
    args = ["curl", "-s", "-u", AUTH, "-X", method]
    tmp = None
    if body is not None:
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        json.dump(body, tmp, ensure_ascii=False)
        tmp.close()
        args += ["-H", "Content-Type: application/json", "--data-binary", f"@{tmp.name}"]
    args.append(url)

    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
    if tmp:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    if r.returncode != 0:
        raise RuntimeError(f"curl failed: {r.stderr}")
    if not r.stdout:
        return {}
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"non-JSON response: {r.stdout[:300]}")


# ---------- public API ----------

def get_event(event_id: int | str) -> dict:
    return _curl("GET", f"{ATHLETE_URL}/events/{event_id}")  # type: ignore[return-value]


def list_events(oldest: str, newest: str) -> list[dict]:
    return _curl("GET", f"{ATHLETE_URL}/events?oldest={oldest}&newest={newest}")  # type: ignore[return-value]


def post_event(payload: dict) -> dict:
    return _curl("POST", f"{ATHLETE_URL}/events", payload)  # type: ignore[return-value]


def put_event(event_id: int | str, payload: dict) -> dict:
    return _curl("PUT", f"{ATHLETE_URL}/events/{event_id}", payload)  # type: ignore[return-value]


def delete_event(event_id: int | str) -> dict:
    return _curl("DELETE", f"{ATHLETE_URL}/events/{event_id}")  # type: ignore[return-value]


def list_activities(oldest: str, newest: str) -> list[dict]:
    return _curl(
        "GET", f"{ATHLETE_URL}/activities?oldest={oldest}&newest={newest}"
    )  # type: ignore[return-value]


def get_wellness(oldest: str, newest: str) -> list[dict]:
    return _curl(
        "GET", f"{ATHLETE_URL}/wellness?oldest={oldest}&newest={newest}"
    )  # type: ignore[return-value]


def update_event_description(event_id: int | str, **changes: Any) -> dict:
    """
    PUT helper that handles the workout_doc deletion gotcha.

    intervals.icu silently drops workout_doc.steps if you PUT the JSON directly.
    Correct method: GET event, mutate fields, DELETE workout_doc, PUT back —
    server then re-parses description as workout builder syntax.
    """
    event = get_event(event_id)
    event.update(changes)
    if "workout_doc" in event:
        del event["workout_doc"]
    return put_event(event_id, event)


def event_payload(date: str, etype: str, name: str, description: str, secs: int) -> dict:
    """Build a workout-builder event payload for POST."""
    return {
        "start_date_local": f"{date}T08:00:00",
        "type": etype,
        "name": name,
        "description": description,
        "moving_time": secs,
        "category": "WORKOUT",
    }


if __name__ == "__main__":
    # Smoke test: verify auth works
    import sys

    print(f"athlete_id: {ATHLETE_ID}")
    print(f"api_key: {API_KEY[:6]}...{API_KEY[-4:]}")
    try:
        events = list_events("2026-05-01", "2026-05-07")
        print(f"OK — fetched {len(events)} events in 2026-05-01..05-07")
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
