#!/bin/bash

# Comprehensive CI Test Script for Ashoka
# This script runs all CI tests including RAG, Ollama, and governance testing
# Can be run locally via Docker or in CI/CD environments

set -e  # Exit on error
set -x  # Print commands for debugging

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# === CONFIGURATION ===
export CHROMADB_HOST=localhost
export CHROMADB_PORT=8000
export OLLAMA_HOST=localhost
export OLLAMA_PORT=11434
export ASHOKA_DEFAULT_MODEL=${ASHOKA_DEFAULT_MODEL:-"llama3.2:1b"}
export PYTHONPATH=.

# Test configuration
RUN_RAG_TESTS=${RUN_RAG_TESTS:-true}
RUN_OLLAMA_TESTS=${RUN_OLLAMA_TESTS:-true}
RUN_GOVERNANCE_TESTS=${RUN_GOVERNANCE_TESTS:-true}
SKIP_MODEL_DOWNLOAD=${SKIP_MODEL_DOWNLOAD:-false}

log "Starting Ashoka CI Test Suite"
log "Configuration:"
log "  - RAG Tests: $RUN_RAG_TESTS"
log "  - Ollama Tests: $RUN_OLLAMA_TESTS"
log "  - Governance Tests: $RUN_GOVERNANCE_TESTS"
log "  - Model: $ASHOKA_DEFAULT_MODEL"
log "  - Skip Model Download: $SKIP_MODEL_DOWNLOAD"

# === PHASE 1: SETUP AND DEPENDENCIES ===
log "Phase 1: Setup and Dependencies"

# Install Python dependencies if needed
if [ ! -f "/tmp/.deps_installed" ]; then
    info "Installing Python dependencies..."
    pip install -r requirements.txt
    pip install pytest pytest-cov scikit-learn numpy
    pip install -e .
    touch /tmp/.deps_installed
else
    info "Dependencies already installed, skipping..."
fi

# Verify critical imports
info "Verifying critical dependencies..."
python -c "import chromadb; print('ChromaDB: OK')"
python -c "import sentence_transformers; print('sentence-transformers: OK')"
python -c "import sklearn; print('scikit-learn: OK')"
python -c "from rag.chromadb_client import ChromaDBClient; print('RAG modules: OK')"

# === PHASE 2: START SERVICES ===
log "Phase 2: Starting Services"

# Start ChromaDB if not running
if ! curl -s http://$CHROMADB_HOST:$CHROMADB_PORT/api/v2/heartbeat > /dev/null 2>&1; then
    info "Starting ChromaDB..."
    python -c "
import subprocess
import time
from rag.chromadb_client import ChromaDBClient

# Start ChromaDB server in background
proc = subprocess.Popen(['python', '-m', 'chromadb.server', '--host', '0.0.0.0', '--port', '8000'])
time.sleep(10)

# Test connection
client = ChromaDBClient(environment='test')
if client.health_check():
    print('ChromaDB started successfully')
else:
    raise Exception('ChromaDB failed to start')
" &
    
    # Wait for ChromaDB to be ready
    for i in {1..30}; do
        if curl -s http://$CHROMADB_HOST:$CHROMADB_PORT/api/v2/heartbeat > /dev/null 2>&1; then
            log "ChromaDB is ready!"
            break
        fi
        if [ $i -eq 30 ]; then
            error "ChromaDB failed to start within 60 seconds"
            exit 1
        fi
        info "Waiting for ChromaDB... (attempt $i/30)"
        sleep 2
    done
else
    log "ChromaDB already running"
fi

# Start Ollama if governance tests are enabled
if [ "$RUN_OLLAMA_TESTS" = "true" ]; then
    if ! curl -s http://$OLLAMA_HOST:$OLLAMA_PORT/api/version > /dev/null 2>&1; then
        info "Starting Ollama..."
        ollama serve &
        
        # Wait for Ollama to be ready
        for i in {1..30}; do
            if curl -s http://$OLLAMA_HOST:$OLLAMA_PORT/api/version > /dev/null 2>&1; then
                log "Ollama is ready!"
                break
            fi
            if [ $i -eq 30 ]; then
                error "Ollama failed to start within 60 seconds"
                exit 1
            fi
            info "Waiting for Ollama... (attempt $i/30)"
            sleep 2
        done
    else
        log "Ollama already running"
    fi
    
    # Pull model if needed
    if [ "$SKIP_MODEL_DOWNLOAD" != "true" ]; then
        if ! ollama list | grep -q "$ASHOKA_DEFAULT_MODEL"; then
            info "Pulling model $ASHOKA_DEFAULT_MODEL..."
            ollama pull "$ASHOKA_DEFAULT_MODEL"
        else
            log "Model $ASHOKA_DEFAULT_MODEL already available"
        fi
    fi
fi

# === PHASE 3: RAG SYSTEM TESTS ===
if [ "$RUN_RAG_TESTS" = "true" ]; then
    log "Phase 3: RAG System Tests"
    
    info "Running RAG semantic similarity tests..."
    python -m pytest tests/test_rag_semantic.py -v --tb=short
    
    info "Running RAG integration tests..."
    python test_rag_integration.py
    
    info "Testing RAG CLI command..."
    if [ -f "governance_docs.jsonl" ]; then
        python cli/main.py rag-embed --documents governance_docs.jsonl --environment test
    else
        warn "governance_docs.jsonl not found, skipping RAG CLI test"
    fi
    
    log "RAG tests completed successfully!"
else
    warn "Skipping RAG tests (RUN_RAG_TESTS=false)"
fi

# === PHASE 4: OLLAMA GOVERNANCE TESTS ===
if [ "$RUN_OLLAMA_TESTS" = "true" ]; then
    log "Phase 4: Ollama Governance Tests"
    
    info "Initializing Ashoka governance model..."
    python cli/main.py create --ollama-url http://$OLLAMA_HOST:$OLLAMA_PORT
    
    if [ "$RUN_GOVERNANCE_TESTS" = "true" ]; then
        info "Running governance response tests..."
        python -m pytest tests/test_ollama_governance.py -v --tb=short
        log "Governance tests completed successfully!"
    else
        warn "Skipping governance tests (RUN_GOVERNANCE_TESTS=false)"
    fi
else
    warn "Skipping Ollama tests (RUN_OLLAMA_TESTS=false)"
fi

# === PHASE 5: ADDITIONAL TESTS ===
log "Phase 5: Additional Tests"

info "Running semantic similarity threshold tests..."
python test_semantic_similarity.py

info "Running final similarity tests..."
python test_final_similarity.py

# === CLEANUP ===
log "Phase 6: Cleanup"

info "Stopping background services..."
# Kill any background processes we started
pkill -f "chromadb.server" || true
pkill -f "ollama serve" || true

# === SUMMARY ===
log "🎉 All CI tests completed successfully!"
log "Test Summary:"
log "  ✅ RAG System Tests: $([ "$RUN_RAG_TESTS" = "true" ] && echo "PASSED" || echo "SKIPPED")"
log "  ✅ Ollama Tests: $([ "$RUN_OLLAMA_TESTS" = "true" ] && echo "PASSED" || echo "SKIPPED")"
log "  ✅ Governance Tests: $([ "$RUN_GOVERNANCE_TESTS" = "true" ] && echo "PASSED" || echo "SKIPPED")"
log "  ✅ Additional Tests: PASSED"

log "CI test suite completed in $(date)"
