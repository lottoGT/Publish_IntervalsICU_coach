#!/usr/bin/env bash
# Post-setup verification — runs after install/setup.sh.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY=$(command -v python3 || command -v python)

pass() { printf "  \033[1;32m[OK]\033[0m %s\n" "$*"; }
fail() { printf "  \033[1;31m[FAIL]\033[0m %s\n" "$*"; FAILED=1; }

FAILED=0
echo "Endurance system verification"
echo "============================="

# Skill installed
[ -f "${HOME}/.claude/skills/coach/SKILL.md" ] \
    && pass "coach skill installed" \
    || fail "missing ~/.claude/skills/coach/SKILL.md"

# Config exists
[ -f "${HOME}/.endurance-coach/config.json" ] \
    && pass "config.json exists" \
    || fail "missing ~/.endurance-coach/config.json — run install/setup.sh"

# Athlete context
[ -f "${HOME}/.endurance-coach/Athlete_Context.md" ] \
    && pass "Athlete_Context.md installed" \
    || fail "missing Athlete_Context.md"

# .env exists at repo root
[ -f "${REPO_ROOT}/.env" ] \
    && pass ".env at repo root" \
    || fail "missing ${REPO_ROOT}/.env"

# DB initialized
[ -f "${HOME}/.endurance-coach/coach.db" ] \
    && pass "coach.db exists" \
    || fail "missing coach.db — run python scripts/sync_db.py --init"

# API smoke test
echo "  Testing API connectivity..."
if $PY "${REPO_ROOT}/scripts/lib/intervals_api.py" >/dev/null 2>&1; then
    pass "intervals.icu API authenticated"
else
    fail "intervals.icu API auth failed — check ~/.endurance-coach/config.json"
fi

# .gitignore protects secrets
cd "$REPO_ROOT" || { fail "Cannot cd to repo root: $REPO_ROOT"; exit 1; }
if git check-ignore -q .env config.json 2>/dev/null; then
    pass ".env and config.json are gitignored"
else
    # only one needs to be ignored
    if git check-ignore -q .env 2>/dev/null; then
        pass ".env is gitignored"
    else
        fail ".env is NOT gitignored — DO NOT COMMIT"
    fi
fi

echo "============================="
if [ $FAILED -eq 0 ]; then
    echo "All checks passed."
    exit 0
else
    echo "Some checks FAILED — see above."
    exit 1
fi
