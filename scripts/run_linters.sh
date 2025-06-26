#!/bin/bash
# Simple script to run all linters from CI workflow locally
# Usage: ./run_linters.sh [--fix]
#   --fix    Apply fixes automatically when possible (black, isort)

# Exit on first error
set -e

# Check if we should fix issues or just check
FIX_MODE=false
if [ "$1" == "--fix" ]; then
    FIX_MODE=true
    echo "Running linters in FIX mode..."
else
    echo "Running linters in CHECK mode (use --fix to auto-format)..."
fi

# Check/fix formatting with black
echo "Running black..."
if [ "$FIX_MODE" = true ]; then
    black ashoka cli tests
else
    black ashoka cli tests --check
fi

# Check/fix imports with isort
echo "Running isort..."
if [ "$FIX_MODE" = true ]; then
    isort ashoka cli tests
else
    isort ashoka cli tests --check-only
fi

# Lint with flake8 (no auto-fix available)
echo "Running flake8..."
# Using configuration from .flake8
flake8 ashoka cli tests --extend-ignore=F401,W291,F841 --config=.flake8

echo "All linters completed successfully!"
