#!/bin/bash

# Export OLLAMA_HOME explicitly
export OLLAMA_HOST=0.0.0.0
export OLLAMA_HOME=/workspace/ollama
export OLLAMA_MODELS=/workspace/ollama/models
echo "OLLAMA_HOST=$OLLAMA_HOST"
echo "OLLAMA_HOME=$OLLAMA_HOME"
echo "OLLAMA_MODELS=$OLLAMA_MODELS"
chmod -R 777 $OLLAMA_HOME

# Start Ollama in the background
ollama serve &

# Wait until Ollama is ready (port 11434 open)
echo "Waiting for Ollama to become available..."
while ! nc -z localhost 11434; do
  sleep 1
done

echo "Ollama is up and running at http://localhost:11434"

# Pull the llama3 model
echo "Pulling llama3 model..."
ollama pull deepseek-r1:8b
ollama pull llama3:8b
#ollama pull deepseek-r1:70b

echo "Deleting and cloning ashoka repository..."
rm -rf ashoka
git clone https://github.com/smart-social-contracts/ashoka.git
echo "Ashoka repository cloned"

# Keep container running
echo "Container is ready. Use 'docker exec' to run commands or attach to this container."
tail -f /dev/null