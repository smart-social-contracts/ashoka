#!/bin/bash

# Health check script that polls a URL for success response
# Usage: ./health_check.sh <BOOTUP_TIMEOUT_SEC> <POD_URL>

set -e

# Check if correct number of arguments provided
if [ $# -ne 2 ]; then
    echo "Usage: $0 <BOOTUP_TIMEOUT_SEC> <POD_URL>"
    echo "Example: $0 45 https://example.com"
    exit 1
fi

BOOTUP_TIMEOUT_SEC=$1
POD_URL=$2
SLEEP_INTERVAL=10

echo "🔍 Health checking $POD_URL for up to $BOOTUP_TIMEOUT_SEC seconds..."

# Start time
start_time=$(date +%s)
end_time=$((start_time + BOOTUP_TIMEOUT_SEC))

# Poll every second
while [ $(date +%s) -lt $end_time ]; do
    current_time=$(date +%s)
    elapsed=$((current_time - start_time))
    
    echo "⏱️  Attempt at ${elapsed}s: checking $POD_URL"
    
    # Try health endpoint first, then fallback to root
    if curl -f --max-time 15 --silent "$POD_URL/health" >/dev/null 2>&1; then
        echo "✅ Health check successful at $POD_URL/health after ${elapsed}s"
        exit 0
    elif curl -f --max-time 15 --silent "$POD_URL/" >/dev/null 2>&1; then
        echo "✅ Health check successful at $POD_URL/ after ${elapsed}s"
        exit 0
    fi
    
    # Wait 1 second before next attempt (unless we're at the end)
    if [ $(date +%s) -lt $((end_time - 1)) ]; then
        sleep $SLEEP_INTERVAL
    fi
done

echo "❌ Health check failed: $POD_URL did not respond successfully within $BOOTUP_TIMEOUT_SEC seconds"
exit 1
