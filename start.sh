#!/bin/bash

# Start Ollama in the background
ollama serve &

# Wait until Ollama is ready (port 11434 open)
echo "Waiting for Ollama to become available..."
while ! nc -z localhost 11434; do
  sleep 1
done

# Run your AI governor logic here (or wait for remote connection)
echo "Ollama is up. You can now SSH in or run 'ashoka run ...'"
tail -f /dev/null
