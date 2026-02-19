#!/bin/bash
# Code Formatting Script
# Automatically fixes formatting issues

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "Running Code Formatting"
echo "=========================================="
echo ""

# Format with Black
echo "1. Formatting code with Black..."
uv run black backend/*.py backend/tests/*.py main.py
echo "   Code formatted"
echo ""

# Fix imports with isort
echo "2. Organizing imports with isort..."
uv run isort backend/*.py backend/tests/*.py main.py
echo "   Imports organized"
echo ""

# Fix ruff issues
echo "3. Fixing ruff issues..."
uv run ruff check --fix backend/*.py backend/tests/*.py main.py || echo "   Note: Some issues may require manual attention"
echo "   Auto-fixable issues resolved"
echo ""

echo "=========================================="
echo "Formatting complete!"
echo "Run './scripts/check-quality.sh' to verify all checks pass."
echo "=========================================="
