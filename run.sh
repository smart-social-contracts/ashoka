#!/bin/bash

set -e # Exit on error
set -x # Print commands

# Create logs directory if it doesn't exist
mkdir -p logs

# Create workspace directories if they don't exist
mkdir -p /workspace/ollama
mkdir -p /workspace/venv
mkdir -p /workspace/chromadb_data

# Setup Python virtual environment in the persistent volume
if [ ! -f "/workspace/venv/bin/activate" ]; then
    echo "Creating new virtual environment in /workspace/venv..."
    python3 -m venv /workspace/venv
fi

# Activate the virtual environment
source /workspace/venv/bin/activate

# export DFX_WARNING=-mainnet_plaintext_identity

# # Set default realm ID
# export ASHOKA_REALM_ID="h5vpp-qyaaa-aaaac-qai3a-cai"
# export ASHOKA_MODEL="llama3:8b"
# export ASHOKA_USE_LLM=true
# export ASHOKA_DFX_NETWORK="staging"
# echo "ASHOKA_REALM_ID=$ASHOKA_REALM_ID"
# echo "ASHOKA_MODEL=$ASHOKA_MODEL"
# echo "ASHOKA_USE_LLM=$ASHOKA_USE_LLM"
# echo "ASHOKA_DFX_NETWORK=$ASHOKA_DFX_NETWORK"

# # Export OLLAMA_HOME explicitly
# export OLLAMA_HOST=0.0.0.0
# export OLLAMA_HOME=/workspace/ollama
# export OLLAMA_MODELS=/workspace/ollama/models
# echo "OLLAMA_HOST=$OLLAMA_HOST"
# echo "OLLAMA_HOME=$OLLAMA_HOME"
# echo "OLLAMA_MODELS=$OLLAMA_MODELS"
# chmod -R 777 $OLLAMA_HOME

# # Start Ollama in the background
# ollama serve 2>&1 | tee -a logs/ollama.log &

# # Wait until Ollama is ready (port 11434 open)
# echo "Waiting for Ollama to become available..."
# while ! nc -z localhost 11434; do
#   sleep 1
# done

# echo "Ollama is up and running at http://localhost:11434"

# # Pull the models
# echo "Pulling models..."
# ollama pull deepseek-r1:8b
# ollama pull llama3:8b
# # ollama pull llama3.3:70b

# # Check if requirements have been installed already
# if [ ! -f "/workspace/venv/.requirements_installed" ]; then
#     echo "Installing Python requirements..."
#     pip3 install --upgrade pip
#     pip3 install -r requirements.txt
#     # Create a flag file to indicate requirements are installed
#     touch /workspace/venv/.requirements_installed
# else
#     echo "Python requirements already installed, skipping installation."
# fi

# # Start ChromaDB server in background
# echo "Starting ChromaDB server..."
# chromadb run --host 0.0.0.0 --port 8000 --path /workspace/chromadb_data 2>&1 | tee -a logs/chromadb.log &
# CHROMADB_PID=$!

# echo "Waiting for ChromaDB to be ready..."
# for i in {1..30}; do
#     if curl -s http://localhost:8000/api/v1/heartbeat > /dev/null 2>&1; then
#         echo "ChromaDB is ready!"
#         break
#     fi
#     if [ $i -eq 30 ]; then
#         echo "ChromaDB failed to start within 30 seconds"
#         exit 1
#     fi
#     sleep 1
# done

# # Run API server
# python3 api.py 2>&1 | tee -a logs/api.log &

# # Create AI governor
# python3 cli/main.py create 2>&1 | tee -a logs/cli_main_create.log
# # #--ollama-url http://localhost:11434 --realm-id $ASHOKA_REALM_ID

# # Keep container running
# echo "Container is ready. Use 'docker exec' to run commands or attach to this container."
# tail -f /dev/null
