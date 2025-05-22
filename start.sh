#!/bin/bash

# Start Ollama in the background
ollama serve &

# Wait until Ollama is ready (port 11434 open)
echo "Waiting for Ollama to become available..."
while ! nc -z localhost 11434; do
  sleep 1
done

echo "Ollama is up and running at http://localhost:11434"

# Make the main CLI script executable if needed
if [ -f /app/cli/main.py ]; then
  chmod +x /app/cli/main.py
  echo "You can now use the ashoka CLI with: python3 /app/cli/main.py [command]"
else
  echo "Warning: Main CLI script not found at expected location"
fi

# Keep container running
echo "Container is ready. Use 'docker exec' to run commands or attach to this container."
tail -f /dev/null
