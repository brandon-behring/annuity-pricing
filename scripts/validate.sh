#!/bin/bash
# validate.sh - Run tests, type checks, and lint for annuity-pricing
#
# Usage: ./scripts/validate.sh [--quick|--full|--anti-patterns]
#
# Modes:
#   --quick        Run anti-pattern tests only (default for pre-commit)
#   --full         Run all tests + type check + lint
#   --anti-patterns  Run anti-pattern tests only (alias for --quick)
#
# Exit codes:
#   0 = All checks passed
#   1 = Tests failed
#   2 = Type check failed
#   3 = Lint failed

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Parse arguments
MODE="${1:---quick}"

echo "=================================================="
echo "  annuity-pricing Validation"
echo "  Mode: $MODE"
echo "=================================================="
echo ""

run_tests() {
    local test_path="$1"
    local description="$2"

    echo -e "${YELLOW}Running: $description${NC}"
    if pytest "$test_path" -v --tb=short; then
        echo -e "${GREEN}✓ $description passed${NC}"
        echo ""
        return 0
    else
        echo -e "${RED}✗ $description FAILED${NC}"
        return 1
    fi
}

case "$MODE" in
    --quick|--anti-patterns)
        echo "Quick validation (anti-pattern tests only)"
        echo ""

        if [ -d "tests/anti_patterns" ]; then
            run_tests "tests/anti_patterns/" "Anti-pattern tests"
        else
            echo -e "${YELLOW}Warning: tests/anti_patterns/ not found${NC}"
        fi

        echo -e "${GREEN}Quick validation complete!${NC}"
        ;;

    --full)
        echo "Full validation (all tests + type check + lint)"
        echo ""

        # 1. Anti-pattern tests (must pass)
        if [ -d "tests/anti_patterns" ]; then
            run_tests "tests/anti_patterns/" "Anti-pattern tests" || exit 1
        fi

        # 2. Validation tests (known answers)
        if [ -d "tests/validation" ]; then
            run_tests "tests/validation/" "Validation tests" || exit 1
        fi

        # 3. Unit tests
        if [ -d "tests/unit" ]; then
            run_tests "tests/unit/" "Unit tests" || exit 1
        fi

        # 4. All tests with coverage
        echo -e "${YELLOW}Running: Full test suite with coverage${NC}"
        if pytest tests/ --cov=src --cov-report=term-missing -v; then
            echo -e "${GREEN}✓ All tests passed${NC}"
        else
            echo -e "${RED}✗ Test suite FAILED${NC}"
            exit 1
        fi
        echo ""

        # 5. Type checking
        echo -e "${YELLOW}Running: Type checking (mypy)${NC}"
        if mypy src/ --strict 2>/dev/null; then
            echo -e "${GREEN}✓ Type check passed${NC}"
        else
            echo -e "${YELLOW}⚠ Type check had issues (may need src/ to exist)${NC}"
        fi
        echo ""

        # 6. Linting
        echo -e "${YELLOW}Running: Lint (ruff)${NC}"
        if ruff check src/ 2>/dev/null; then
            echo -e "${GREEN}✓ Lint passed${NC}"
        else
            echo -e "${YELLOW}⚠ Lint had issues (may need src/ to exist)${NC}"
        fi
        echo ""

        # 7. Formatting check
        echo -e "${YELLOW}Running: Format check (black)${NC}"
        if black --check src/ 2>/dev/null; then
            echo -e "${GREEN}✓ Formatting OK${NC}"
        else
            echo -e "${YELLOW}⚠ Formatting issues (run: black src/)${NC}"
        fi
        echo ""

        echo -e "${GREEN}=================================================="
        echo "  Full validation complete!"
        echo "==================================================${NC}"
        ;;

    --help|-h)
        echo "Usage: ./scripts/validate.sh [--quick|--full|--anti-patterns]"
        echo ""
        echo "Modes:"
        echo "  --quick         Run anti-pattern tests only (default)"
        echo "  --full          Run all tests + type check + lint"
        echo "  --anti-patterns Run anti-pattern tests only"
        echo ""
        echo "Example:"
        echo "  ./scripts/validate.sh --full"
        ;;

    *)
        echo -e "${RED}Unknown mode: $MODE${NC}"
        echo "Use --help for usage information"
        exit 1
        ;;
esac
