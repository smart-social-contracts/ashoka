#!/bin/bash

set -e
set -x

source /workspace/venv/bin/activate

# Deploy a local realm with demo data for testing
echo "🏛️ Deploying local realm for testing..."
cd /workspace/realms
dfx start --background --clean || true
sleep 5

# Create and deploy realm with demo data
realms realm create --deploy --name "test_realm"

# Get the realm folder path and export it for the test runner
REALM_FOLDER=$(realms realm current --path 2>/dev/null || echo ".realms/test_realm")
export REALM_FOLDER
export REALM_NETWORK="local"

echo "✅ Realm deployed at: $REALM_FOLDER"

# Run the tests
cd /workspace
python test_runner.py --use-tools