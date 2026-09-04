#!/usr/bin/env bash
# =============================================================================
# RegimeX — Repository Quality Gate Script
# scripts/quality-check.sh
# =============================================================================
#
# Runs the full quality gate in order:
#   1. Backend: Ruff format check
#   2. Backend: Ruff lint
#   3. Backend: mypy type check
#   4. Backend: pytest
#   5. Frontend: ESLint
#   6. Frontend: TypeScript check
#
# Usage:
#   bash scripts/quality-check.sh
#
# Prerequisites:
#   Backend:  pip install -e ".[dev]"  (in apps/api/)
#   Frontend: npm install              (in apps/web/)
#
# Exit codes:
#   0 — all checks passed
#   1 — one or more checks failed
#
# Note: This script intentionally does NOT run `next build` because it is
# slow and should be reserved for CI or explicit invocation. Run
# `npm run build` in apps/web/ to validate the production build.
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$REPO_ROOT/apps/api"
WEB_DIR="$REPO_ROOT/apps/web"

# Colours
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

FAILED_CHECKS=()

run_check() {
    local name="$1"
    shift
    echo ""
    echo -e "${BLUE}▶  ${name}${NC}"
    if "$@"; then
        echo -e "${GREEN}   ✅  ${name} passed${NC}"
    else
        echo -e "${RED}   ❌  ${name} FAILED${NC}"
        FAILED_CHECKS+=("$name")
    fi
}

echo ""
echo "═══════════════════════════════════════════════════"
echo "  RegimeX Quality Gate"
echo "═══════════════════════════════════════════════════"

# ---------------------------------------------------------------------------
# 1. Backend: Ruff format check
# ---------------------------------------------------------------------------
run_check "Backend: Ruff format check" \
    bash -c "cd '$API_DIR' && ruff format --check app/ tests/"

# ---------------------------------------------------------------------------
# 2. Backend: Ruff lint
# ---------------------------------------------------------------------------
run_check "Backend: Ruff lint" \
    bash -c "cd '$API_DIR' && ruff check app/ tests/"

# ---------------------------------------------------------------------------
# 3. Backend: mypy type check
# ---------------------------------------------------------------------------
run_check "Backend: mypy type check" \
    bash -c "cd '$API_DIR' && mypy app tests"

# ---------------------------------------------------------------------------
# 4. Backend: pytest
# ---------------------------------------------------------------------------
run_check "Backend: pytest" \
    bash -c "cd '$API_DIR' && python -m pytest tests/ -v --tb=short"

# ---------------------------------------------------------------------------
# 5. Frontend: ESLint
# ---------------------------------------------------------------------------
run_check "Frontend: ESLint" \
    bash -c "cd '$WEB_DIR' && npm run lint"

# ---------------------------------------------------------------------------
# 6. Frontend: TypeScript check
# ---------------------------------------------------------------------------
run_check "Frontend: TypeScript check" \
    bash -c "cd '$WEB_DIR' && npm run type-check"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "═══════════════════════════════════════════════════"
if [ ${#FAILED_CHECKS[@]} -eq 0 ]; then
    echo -e "${GREEN}  ✅  All quality gates passed.${NC}"
    echo "═══════════════════════════════════════════════════"
    echo ""
    exit 0
else
    echo -e "${RED}  ❌  ${#FAILED_CHECKS[@]} check(s) failed:${NC}"
    for check in "${FAILED_CHECKS[@]}"; do
        echo -e "${RED}     • ${check}${NC}"
    done
    echo "═══════════════════════════════════════════════════"
    echo ""
    exit 1
fi
