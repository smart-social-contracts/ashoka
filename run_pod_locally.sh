#!/bin/bash

# Runs the Docker image like it is in runpod but using a lightweight model that can run without GPU

set -e
set -x

# docker build -t smartsocialcontracts/ashoka:branch .

docker run \
    -it --rm \
    --name ashoka \
    -p 5000:5000 \
    -p 5050:5050 \
    -p 5432:5432 \
    -p 2222:2222 \
    -v $PWD/workspace/venv:/workspace/venv:rw \
    -v $PWD/workspace/chromadb_data:/workspace/chromadb_data:rw \
    -v $PWD/workspace/ollama:/workspace/ollama:rw \
    smartsocialcontracts/ashoka:branch

