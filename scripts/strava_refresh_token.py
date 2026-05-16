"""
Strava token auto-refresh utility.

Usage:
    python scripts/strava_refresh_token.py

Exit codes:
    0 — token valid or successfully refreshed
    1 — refresh failed (missing credentials or API error)

Called automatically by coach skill before any Strava-dependent query.
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

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / ".env"
TOKEN_CACHE = Path.home() / ".endurance-coach" / "strava_tokens.json"
TOKEN_URL = "https://www.strava.com/api/v3/oauth/token"
REFRESH_BUFFER = 300  # refresh if expires within 5 minutes


def _load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


def main() -> int:
    env = _load_env()

    client_id = env.get("STRAVA_CLIENT_ID") or os.environ.get("STRAVA_CLIENT_ID")
    client_secret = env.get("STRAVA_CLIENT_SECRET") or os.environ.get("STRAVA_CLIENT_SECRET")
    refresh_token = env.get("STRAVA_REFRESH_TOKEN") or os.environ.get("STRAVA_REFRESH_TOKEN")

    # Override refresh_token with cached value if available
    if TOKEN_CACHE.exists():
        try:
            cached = json.loads(TOKEN_CACHE.read_text(encoding="utf-8"))
            refresh_token = cached.get("refresh_token", refresh_token)

            # Check if current token is still valid
            expires_at = cached.get("expires_at", 0)
            if time.time() < expires_at - REFRESH_BUFFER:
                print(f"Strava token valid until {time.strftime('%Y-%m-%d %H:%M', time.localtime(expires_at))}")
                return 0
        except (json.JSONDecodeError, KeyError):
            pass

    if not all([client_id, client_secret, refresh_token]):
        print("ERROR: Missing Strava credentials (client_id / client_secret / refresh_token)", file=sys.stderr)
        print(f"Expected in: {ENV_FILE}", file=sys.stderr)
        return 1

    # Refresh
    body = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }).encode("utf-8")

    try:
        req = urllib.request.Request(TOKEN_URL, data=body, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            payload = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        print(f"ERROR: Strava token refresh failed: {e.code} {detail}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    tokens = {
        "access_token": payload["access_token"],
        "refresh_token": payload["refresh_token"],
        "expires_at": int(payload["expires_at"]),
        "scope": payload.get("scope", ""),
    }

    TOKEN_CACHE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_CACHE.write_text(json.dumps(tokens, indent=2), encoding="utf-8")
    TOKEN_CACHE.chmod(0o600)

    exp_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(tokens["expires_at"]))
    print(f"Strava token refreshed — valid until {exp_str}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
