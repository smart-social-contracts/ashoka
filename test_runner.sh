#!/bin/bash

set -e
set -x

source /workspace/venv/bin/activate

# Run tests from the app directory
cd /app/ashoka

# For now, run tests without tool calling (local dfx/PocketIC setup is unreliable in container)
# TODO: Enable tool-based testing when local replica environment is stable
echo "📋 Running semantic similarity tests..."
python test_runner.py