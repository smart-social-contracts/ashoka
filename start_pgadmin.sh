#!/bin/bash

# pgAdmin4 startup script for Ashoka container

echo "Starting pgAdmin4..."

# Ensure pgAdmin directories exist with proper permissions
sudo mkdir -p /var/lib/pgadmin /var/log/pgadmin
sudo chown -R ubuntu:ubuntu /var/lib/pgadmin /var/log/pgadmin

# Start pgAdmin4 using the proper script
cd /home/ubuntu/.local/lib/python3.13/site-packages/pgadmin4

# Kill any existing pgAdmin4 process
pkill -f pgAdmin4.py 2>/dev/null || true

# Start pgAdmin4 in background
nohup python3 pgAdmin4.py > /tmp/pgadmin/startup.log 2>&1 &

echo "pgAdmin4 startup initiated. Check logs at /tmp/pgadmin/startup.log"
echo "pgAdmin4 should be available at http://localhost:5050"

# Give it a moment to start
sleep 3

# Show startup status
if ps aux | grep -q '[p]gAdmin4.py'; then
    echo "✓ pgAdmin4 process is running"
else
    echo "✗ pgAdmin4 process not found"
fi

# Show the first few lines of the log
echo "Startup log preview:"
head -10 /tmp/pgadmin/startup.log 2>/dev/null || echo "Log not available yet"