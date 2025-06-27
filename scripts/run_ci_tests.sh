#!/bin/bash
set -e

echo "Running RAG CI/CD tests..."

export CHROMADB_HOST=localhost
export CHROMADB_PORT=8000

echo "Running semantic similarity tests..."
python -m pytest tests/test_rag_semantic.py -v --tb=short

echo "Running integration tests..."
python test_rag_integration.py

echo "Testing RAG CLI command..."
python cli/main.py rag-embed --documents governance_docs.jsonl --environment test

echo "All CI tests completed successfully!"
