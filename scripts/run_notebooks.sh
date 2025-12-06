#!/bin/bash
# run_notebooks.sh - Execute validation notebooks for annuity-pricing
#
# Usage: ./scripts/run_notebooks.sh [--validation|--all|--specific NOTEBOOK]
#
# Modes:
#   --validation   Run notebooks/validation/**/*.ipynb (default)
#   --all          Run all notebooks
#   --specific     Run a specific notebook
#
# Requires:
#   - jupyter or nbconvert installed
#   - Optional: nbstripout for cleaning output
#
# Exit codes:
#   0 = All notebooks executed successfully
#   1 = One or more notebooks failed

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Parse arguments
MODE="${1:---validation}"
SPECIFIC_NOTEBOOK="${2:-}"

echo "=================================================="
echo "  annuity-pricing Notebook Runner"
echo "  Mode: $MODE"
echo "=================================================="
echo ""

# Check for jupyter/nbconvert
if ! command -v jupyter &> /dev/null; then
    echo -e "${RED}Error: jupyter not found${NC}"
    echo "Install with: pip install jupyter"
    exit 1
fi

run_notebook() {
    local notebook="$1"
    local name=$(basename "$notebook")
    local dir=$(dirname "$notebook")

    echo -e "${BLUE}Running: $name${NC}"
    echo "  Path: $notebook"

    # Execute notebook in place
    if jupyter nbconvert --to notebook --execute --inplace "$notebook" 2>&1; then
        echo -e "${GREEN}✓ $name completed${NC}"
        return 0
    else
        echo -e "${RED}✗ $name FAILED${NC}"
        return 1
    fi
}

count_notebooks() {
    local pattern="$1"
    find "$PROJECT_ROOT" -path "*/$pattern" -name "*.ipynb" ! -path "*/.ipynb_checkpoints/*" | wc -l
}

run_all_matching() {
    local pattern="$1"
    local description="$2"
    local failed=0
    local passed=0

    echo -e "${YELLOW}$description${NC}"
    echo ""

    while IFS= read -r notebook; do
        if [ -n "$notebook" ]; then
            if run_notebook "$notebook"; then
                ((passed++))
            else
                ((failed++))
            fi
            echo ""
        fi
    done < <(find "$PROJECT_ROOT" -path "*/$pattern" -name "*.ipynb" ! -path "*/.ipynb_checkpoints/*" | sort)

    echo "Results: $passed passed, $failed failed"

    if [ $failed -gt 0 ]; then
        return 1
    fi
    return 0
}

case "$MODE" in
    --validation)
        echo "Running validation notebooks..."
        echo ""

        n=$(count_notebooks "notebooks/validation")
        if [ "$n" -eq 0 ]; then
            echo -e "${YELLOW}No validation notebooks found in notebooks/validation/${NC}"
            exit 0
        fi

        run_all_matching "notebooks/validation" "Validation Notebooks ($n found)"
        ;;

    --all)
        echo "Running all notebooks..."
        echo ""

        n=$(count_notebooks "notebooks")
        if [ "$n" -eq 0 ]; then
            echo -e "${YELLOW}No notebooks found${NC}"
            exit 0
        fi

        run_all_matching "notebooks" "All Notebooks ($n found)"
        ;;

    --specific)
        if [ -z "$SPECIFIC_NOTEBOOK" ]; then
            echo -e "${RED}Error: --specific requires a notebook path${NC}"
            echo "Usage: ./scripts/run_notebooks.sh --specific notebooks/path/to/notebook.ipynb"
            exit 1
        fi

        if [ ! -f "$SPECIFIC_NOTEBOOK" ]; then
            echo -e "${RED}Error: Notebook not found: $SPECIFIC_NOTEBOOK${NC}"
            exit 1
        fi

        run_notebook "$SPECIFIC_NOTEBOOK"
        ;;

    --list)
        echo "Available notebooks:"
        echo ""

        echo "Validation notebooks:"
        find "$PROJECT_ROOT/notebooks/validation" -name "*.ipynb" ! -path "*/.ipynb_checkpoints/*" 2>/dev/null | sort | while read f; do
            echo "  $(basename "$f")"
        done
        echo ""

        echo "Other notebooks:"
        find "$PROJECT_ROOT/notebooks" -maxdepth 1 -name "*.ipynb" ! -path "*/.ipynb_checkpoints/*" 2>/dev/null | sort | while read f; do
            echo "  $(basename "$f")"
        done
        ;;

    --help|-h)
        echo "Usage: ./scripts/run_notebooks.sh [--validation|--all|--specific NOTEBOOK|--list]"
        echo ""
        echo "Modes:"
        echo "  --validation   Run validation notebooks only (default)"
        echo "  --all          Run all notebooks"
        echo "  --specific     Run a specific notebook"
        echo "  --list         List available notebooks"
        echo ""
        echo "Examples:"
        echo "  ./scripts/run_notebooks.sh --validation"
        echo "  ./scripts/run_notebooks.sh --specific notebooks/validation/options/black_scholes_vs_financepy.ipynb"
        ;;

    *)
        echo -e "${RED}Unknown mode: $MODE${NC}"
        echo "Use --help for usage information"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}=================================================="
echo "  Notebook execution complete!"
echo "==================================================${NC}"
