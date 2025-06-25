#!/bin/bash

# === CONFIGURATION ===
POD_ID="wln5vv6cvqorp9"
API="https://rest.runpod.io/v1/pods"

# === STOP POD ===
echo "Stopping Pod $POD_ID..."
curl -s -X POST -H "Authorization: Bearer $RUNPOD_API_KEY" "$API/$POD_ID/stop"
echo "Stop command sent. Waiting for pod to stop..."

# === WAIT FOR STOP ===
while true; do
    STATUS=$(curl -s -H "Authorization: Bearer $RUNPOD_API_KEY" "$API/$POD_ID" | grep -o '"desiredStatus":"[^"]*"' | cut -d':' -f2 | tr -d '"')
    echo "Current status: $STATUS"
    if [ "$STATUS" == "EXITED" ]; then
        echo "Pod is stopped."
        break
    fi
    sleep 5
done

# === START POD ===
echo "Starting Pod $POD_ID..."
curl -s -X POST -H "Authorization: Bearer $RUNPOD_API_KEY" "$API/$POD_ID/start"
echo "Start command sent. Done!"
