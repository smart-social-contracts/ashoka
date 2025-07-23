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

# Function to get pod status
get_pod_status() {
    curl -s -H "Authorization: Bearer $RUNPOD_API_KEY" "$API/$POD_ID" | grep -o '"desiredStatus":"[^"]*"' | cut -d':' -f2 | tr -d '"'
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
    
    # Wait for stable state
    while true; do
        STATUS=$(get_pod_status)
        echo "Current status: $STATUS"
        if [ "$STATUS" == "EXITED" ] || [ "$STATUS" == "STOPPED" ] || [ "$STATUS" == "RUNNING" ]; then
            break
        fi
        sleep 5
    done
    
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
while true; do
    STATUS=$(get_pod_status)
    echo "Current status: $STATUS"
    if [ "$STATUS" == "RUNNING" ]; then
        echo "✅ Pod is now running successfully!"
        break
    fi
    if [ "$STATUS" == "FAILED" ] || [ "$STATUS" == "ERROR" ]; then
        echo "❌ Pod failed to start. Status: $STATUS"
        exit 1
    fi
    sleep 5
done

echo "Pod startup completed successfully!"
