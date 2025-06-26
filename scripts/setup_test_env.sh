#!/bin/bash
set -e

echo "Setting up RAG CI/CD test environment..."

mkdir -p logs
mkdir -p /tmp/chromadb_test

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Starting ChromaDB test instance..."
chromadb run --host 0.0.0.0 --port 8000 --path /tmp/chromadb_test &
CHROMADB_PID=$!

echo "Waiting for ChromaDB to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/v1/heartbeat > /dev/null 2>&1; then
        echo "ChromaDB is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "ChromaDB failed to start within 30 seconds"
        kill $CHROMADB_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

echo "Test environment setup complete!"
echo "ChromaDB PID: $CHROMADB_PID"
echo "To stop ChromaDB: kill $CHROMADB_PID"
