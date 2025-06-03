#!/bin/bash

# Pull latest changes
git pull

export DFX_WARNING=-mainnet_plaintext_identity

# Set default realm ID
export ASHOKA_REALM_ID="h5vpp-qyaaa-aaaac-qai3a-cai"
export ASHOKA_MODEL="llama3:8b"
export ASHOKA_USE_LLM=true
export ASHOKA_DFX_NETWORK="staging"
echo "ASHOKA_REALM_ID=$ASHOKA_REALM_ID"
echo "ASHOKA_MODEL=$ASHOKA_MODEL"
echo "ASHOKA_USE_LLM=$ASHOKA_USE_LLM"
echo "ASHOKA_DFX_NETWORK=$ASHOKA_DFX_NETWORK"

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

# Pull the models
echo "Pulling models..."
ollama pull deepseek-r1:8b
ollama pull llama3:8b
# ollama pull llama3.3:70b

pip3 install --upgrade pip
pip3 install -r requirements.txt

# Run API server
python3 api.py &

# Create AI governor
python3 cli/main.py create
# #--ollama-url http://localhost:11434 --realm-id $ASHOKA_REALM_ID

# Keep container running
echo "Container is ready. Use 'docker exec' to run commands or attach to this container."
tail -f /dev/null