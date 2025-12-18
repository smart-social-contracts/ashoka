#!/bin/bash

set -e
set -x

source /workspace/venv/bin/activate

# Run tests from the app directory
cd /app/ashoka

# Check if realms CLI is available for tool-based testing
if command -v realms &> /dev/null; then
    echo "🏛️ Realms CLI found, deploying local realm for testing..."
    
    # Start dfx if not running
    dfx start --background --clean || true
    sleep 5
    
    # Create and deploy realm with demo data
    realms realm create --deploy --realm-name "test_realm" || true
    
    # Get the realm folder path
    REALM_FOLDER=$(realms realm current --path 2>/dev/null || echo ".realms/test_realm")
    export REALM_FOLDER
    export REALM_NETWORK="local"
    
    echo "✅ Realm deployed at: $REALM_FOLDER"
    python test_runner.py --use-tools
else
    echo "⚠️ Realms CLI not found, running tests without tool calling"
    python test_runner.py
fi