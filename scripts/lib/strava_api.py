"""
Strava API helper with OAuth refresh.

Reads credentials from (in priority order):
  1. ~/.endurance-coach/strava_tokens.json   (token cache, rotated)
  2. .env at repo root                       (bootstrap creds)
  3. Environment variables                   (fallback)

Auto-refreshes access_token before expiry. Persists rotated refresh_token
to the cache file (chmod 600).

Strava is not behind Cloudflare-style WAF, so we use stdlib urllib here
(unlike intervals.icu which requires curl subprocess).

Rate limits (per Strava docs):
- 100 requests / 15 min
- 1000 requests / day
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

CFG_DIR = Path.home() / ".endurance-coach"
TOKEN_CACHE = CFG_DIR / "strava_tokens.json"
REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = REPO_ROOT / ".env"

API_BASE = "https://www.strava.com/api/v3"
TOKEN_URL = "https://www.strava.com/api/v3/oauth/token"

DEFAULT_STREAM_KEYS = [
    "time", "distance", "heartrate", "watts", "cadence",
    "altitude", "velocity_smooth", "latlng", "temp", "grade_smooth",
]


# ---------------- credential loading ----------------

def _load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _load_token_cache() -> dict[str, Any]:
    if not TOKEN_CACHE.exists():
        return {}
    try:
        return json.loads(TOKEN_CACHE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_token_cache(tokens: dict[str, Any]) -> None:
    CFG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_CACHE.write_text(json.dumps(tokens, indent=2), encoding="utf-8")
    try:
        os.chmod(TOKEN_CACHE, 0o600)
    except OSError:
        pass


def _load_credentials() -> dict[str, Any]:
    env = _load_env_file(ENV_FILE)
    cache = _load_token_cache()

    client_id = (
        os.environ.get("STRAVA_CLIENT_ID")
        or env.get("STRAVA_CLIENT_ID")
    )
    client_secret = (
        os.environ.get("STRAVA_CLIENT_SECRET")
        or env.get("STRAVA_CLIENT_SECRET")
    )
    # cache wins because refresh_token may have rotated
    refresh_token = (
        cache.get("refresh_token")
        or os.environ.get("STRAVA_REFRESH_TOKEN")
        or env.get("STRAVA_REFRESH_TOKEN")
    )

    if not client_id or not client_secret or not refresh_token:
        sys.stderr.write(
            "ERROR: Strava credentials not found.\n"
            "Add the following to .env at repo root:\n"
            "  STRAVA_CLIENT_ID=...\n"
            "  STRAVA_CLIENT_SECRET=...\n"
            "  STRAVA_REFRESH_TOKEN=...\n"
            "  STRAVA_ATHLETE_ID=...\n"
            "Get these via the OAuth flow described in docs/strava-api.md.\n"
        )
        sys.exit(1)

    return {
        "client_id": str(client_id),
        "client_secret": str(client_secret),
        "refresh_token": str(refresh_token),
        "access_token": cache.get("access_token"),
        "expires_at": int(cache.get("expires_at", 0) or 0),
    }


# ---------------- token refresh ----------------

def _refresh_access_token(creds: dict[str, Any]) -> dict[str, Any]:
    body = urllib.parse.urlencode({
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
        "refresh_token": creds["refresh_token"],
        "grant_type": "refresh_token",
    }).encode("utf-8")

    req = urllib.request.Request(TOKEN_URL, data=body, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            payload = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Strava token refresh failed: {e.code} {detail}") from e

    tokens = {
        "access_token": payload["access_token"],
        "refresh_token": payload["refresh_token"],
        "expires_at": int(payload["expires_at"]),
        "scope": payload.get("scope", ""),
    }
    _save_token_cache(tokens)
    return tokens


# module-level state — lazy
_creds: dict[str, Any] | None = None


def _ensure_token() -> str:
    global _creds
    if _creds is None:
        _creds = _load_credentials()

    # Use cached access_token if still valid (>60s buffer)
    if _creds.get("access_token") and time.time() < _creds["expires_at"] - 60:
        return str(_creds["access_token"])

    # Refresh
    tokens = _refresh_access_token(_creds)
    _creds["access_token"] = tokens["access_token"]
    _creds["refresh_token"] = tokens["refresh_token"]
    _creds["expires_at"] = tokens["expires_at"]
    return str(_creds["access_token"])


# ---------------- HTTP helper ----------------

def _request(path: str, params: dict | None = None,
             retry_on_401: bool = True) -> Any:
    token = _ensure_token()
    url = API_BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {token}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        if e.code == 401 and retry_on_401:
            # Token may have been revoked — clear cache and retry once
            global _creds
            if TOKEN_CACHE.exists():
                try:
                    TOKEN_CACHE.unlink()
                except OSError:
                    pass
            _creds = None
            return _request(path, params, retry_on_401=False)
        raise RuntimeError(f"Strava API {path} failed: {e.code} {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Strava API {path} network error: {e}") from e


# ---------------- public API ----------------

def get_athlete() -> dict:
    return _request("/athlete")


def list_activities(after: int | None = None, before: int | None = None,
                    page: int = 1, per_page: int = 200) -> list[dict]:
    """Fetch one page of activities.

    after / before are unix timestamps (seconds).
    """
    params: dict[str, Any] = {"page": page, "per_page": per_page}
    if after is not None:
        params["after"] = after
    if before is not None:
        params["before"] = before
    return _request("/athlete/activities", params)


def list_all_activities(after_unix: int, before_unix: int | None = None,
                         page_sleep: float = 1.0) -> list[dict]:
    """Paginate all activities in a date range (unix timestamps)."""
    if before_unix is None:
        before_unix = int(time.time())
    out: list[dict] = []
    page = 1
    while True:
        batch = list_activities(after=after_unix, before=before_unix,
                                page=page, per_page=200)
        if not batch:
            break
        out.extend(batch)
        if len(batch) < 200:
            break
        page += 1
        time.sleep(page_sleep)
    return out


def get_activity_detail(activity_id: int | str) -> dict:
    return _request(f"/activities/{activity_id}")


def get_activity_streams(activity_id: int | str,
                         keys: list[str] | None = None) -> dict:
    """Fetch activity streams. Returns dict keyed by stream type."""
    if keys is None:
        keys = DEFAULT_STREAM_KEYS
    return _request(
        f"/activities/{activity_id}/streams",
        {"keys": ",".join(keys), "key_by_type": "true"},
    )


# ---------------- smoke test ----------------

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--test", action="store_true",
                   help="Verify auth + fetch athlete profile")
    p.add_argument("--whoami", action="store_true",
                   help="Same as --test")
    args = p.parse_args()

    a = get_athlete()
    print(f"OK — Strava authenticated")
    print(f"     athlete_id: {a.get('id')}")
    print(f"     name:       {a.get('firstname')} {a.get('lastname')}")
    print(f"     premium:    {a.get('premium')}")
    print(f"     weight:     {a.get('weight')} kg")
    if _creds:
        exp = _creds.get("expires_at", 0)
        if exp:
            from datetime import datetime
            print(f"     token exp:  {datetime.fromtimestamp(exp)}")
