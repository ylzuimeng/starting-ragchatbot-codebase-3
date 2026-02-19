#!/bin/bash
# Code Quality Check Script
# Runs all quality checks without modifying files

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "Running Code Quality Checks"
echo "=========================================="
echo ""

# Check formatting with Black
echo "1. Checking code formatting with Black..."
uv run black --check backend/*.py backend/tests/*.py main.py
echo "   Code formatting check passed"
echo ""

# Check import ordering with isort
echo "2. Checking import ordering with isort..."
uv run isort --check-only backend/*.py backend/tests/*.py main.py
echo "   Import ordering check passed"
echo ""

# Run ruff linter
echo "3. Running ruff linter..."
uv run ruff check backend/*.py backend/tests/*.py main.py
echo "   Lint check passed"
echo ""

# Run tests
echo "4. Running tests..."
uv run pytest backend/tests/ -v
echo "   Tests passed"
echo ""

echo "=========================================="
echo "All quality checks passed!"
echo "=========================================="
