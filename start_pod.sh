#!/bin/bash

# === CONFIGURATION ===
# Check if pod type argument is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <pod_type>"
    echo "pod_type: 'main' or 'branch'"
    exit 1
fi

POD_TYPE=$1

# Source the env file to get pod configurations
source $(dirname "$0")/env

# Select the appropriate server host based on pod type
if [ "$POD_TYPE" == "main" ]; then
    SERVER_HOST=$SERVER_HOST_MAIN
    echo "Using main pod configuration"
elif [ "$POD_TYPE" == "branch" ]; then
    SERVER_HOST=$SERVER_HOST_BRANCH
    echo "Using branch pod configuration"
else
    echo "Error: Invalid pod type '$POD_TYPE'. Use 'main' or 'branch'"
    exit 1
fi

# Extract POD_ID from SERVER_HOST
POD_ID=$(echo $SERVER_HOST | cut -d'-' -f1)
API="https://rest.runpod.io/v1/pods"

echo "Pod ID: $POD_ID"
echo "Server Host: $SERVER_HOST"

# Function to get pod status with error handling
get_pod_status() {
    local response=$(curl -s -H "Authorization: Bearer $RUNPOD_API_KEY" "$API/$POD_ID" 2>/dev/null)
    if [ $? -ne 0 ] || [ -z "$response" ]; then
        echo "API_ERROR"
        return 1
    fi
    echo "$response" | grep -o '"desiredStatus":"[^"]*"' | cut -d':' -f2 | tr -d '"' 2>/dev/null || echo "PARSE_ERROR"
}

# === CHECK INITIAL STATUS ===
echo "Checking current pod status..."
CURRENT_STATUS=$(get_pod_status)
echo "Current status: $CURRENT_STATUS"

if [ "$CURRENT_STATUS" == "RUNNING" ]; then
    echo "Pod is already running. No action needed."
    exit 0
fi

if [ "$CURRENT_STATUS" != "EXITED" ] && [ "$CURRENT_STATUS" != "STOPPED" ]; then
    echo "Pod is in unexpected state: $CURRENT_STATUS"
    echo "Waiting for pod to reach a stable state..."
    
    # Wait for stable state with timeout
    timeout_seconds=300  # 5 minutes
    elapsed=0
    while [ $elapsed -lt $timeout_seconds ]; do
        STATUS=$(get_pod_status)
        echo "Current status: $STATUS (elapsed: ${elapsed}s)"
        if [ "$STATUS" == "EXITED" ] || [ "$STATUS" == "STOPPED" ] || [ "$STATUS" == "RUNNING" ]; then
            break
        fi
        if [ "$STATUS" == "API_ERROR" ] || [ "$STATUS" == "PARSE_ERROR" ]; then
            echo "❌ API error while checking pod status. Retrying..."
        fi
        sleep 5
        elapsed=$((elapsed + 5))
    done
    
    if [ $elapsed -ge $timeout_seconds ]; then
        echo "❌ Timeout waiting for pod to reach stable state after ${timeout_seconds}s"
        exit 1
    fi
    
    if [ "$STATUS" == "RUNNING" ]; then
        echo "Pod is now running. No action needed."
        exit 0
    fi
fi

# === START POD ===
echo "Starting Pod $POD_ID..."
curl -s -X POST -H "Authorization: Bearer $RUNPOD_API_KEY" "$API/$POD_ID/start"
echo "Start command sent. Waiting for pod to start..."

# === WAIT FOR START ===
timeout_seconds=600  # 10 minutes for pod startup
elapsed=0
while [ $elapsed -lt $timeout_seconds ]; do
    STATUS=$(get_pod_status)
    echo "Current status: $STATUS (elapsed: ${elapsed}s)"
    if [ "$STATUS" == "RUNNING" ]; then
        echo "✅ Pod is now running successfully!"
        break
    fi
    if [ "$STATUS" == "FAILED" ] || [ "$STATUS" == "ERROR" ]; then
        echo "❌ Pod failed to start. Status: $STATUS"
        exit 1
    fi
    if [ "$STATUS" == "API_ERROR" ]; then
        echo "❌ API error while checking pod status. This may indicate network issues or invalid API key."
        exit 1
    fi
    if [ "$STATUS" == "PARSE_ERROR" ]; then
        echo "⚠️ Unable to parse API response. Retrying..."
    fi
    sleep 5
    elapsed=$((elapsed + 5))
done

if [ $elapsed -ge $timeout_seconds ]; then
    echo "❌ Timeout waiting for pod to start after ${timeout_seconds}s"
    exit 1
fi

echo "Pod startup completed successfully!"
