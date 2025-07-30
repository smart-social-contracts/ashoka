#!/bin/bash

# Runs the Docker image like it is in runpod but using a lightweight model that can run without GPU

set -e
set -x

docker run \
    -it --rm \
    --name ashoka \
    -p 5000:5000 \
    -p 5050:5050 \
    -p 2222:2222 \
    -p 80:80 \
    -v /workspace/venv:/app/ashoka/venv \
    -v /workspace/chromadb_data:/app/ashoka/chromadb_data \
    -v /workspace/ollama:/root/.ollama \
    smartsocialcontracts/ashoka:branch

