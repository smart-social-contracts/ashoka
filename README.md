# Ashoka

An AI-powered governance advisor for Internet Computer Protocol realms and DAOs. Ashoka provides intelligent responses to governance questions using multiple AI personas, powered by LLMs and retrieval-augmented generation (RAG).

## Features

- **Multi-Persona AI Governance**: Choose from specialized personas (advisor, facilitator, analyst)
- **Realm Status Integration**: Context-aware responses using real-time realm data
- **CLI & HTTP API**: Flexible interfaces for different use cases
- **RunPod Cloud Deployment**: Scalable GPU-powered infrastructure
- **Conversation History**: Track governance discussions and decisions

## Quick Start

### Using CLI (Recommended)

```bash
# Ask a governance question

# Use specific persona for strategic advice
./pod_manager.py main ask -q "Should we approve this treasury proposal?" -p advisor

# Ask complex questions from file with realm context
./pod_manager.py main ask -qf complex_proposal.txt -p facilitator --realm-status-file realm_data.json

# List available personas
./pod_manager.py main personas

# Check API health
./pod_manager.py main health

# Deploy new pod with cheapest available GPU
./pod_manager.py main deploy

# Start existing pod (deploy new if needed)
./pod_manager.py main start --deploy-new-if-needed --verbose
# Check pod status
./pod_manager.py main status
```

### Pod Operations

```bash
# Stop pod
./pod_manager.py main stop

# Restart pod
./pod_manager.py main restart

# Terminate pod (delete)
./pod_manager.py main terminate
```

## API Commands

### Ask Questions

```bash
# Simple question
./pod_manager.py main ask -q "What is quadratic voting?"

# Question from file (for long/complex questions)
./pod_manager.py main ask -qf governance_proposal.txt

# With specific persona
./pod_manager.py main ask -q "Analyze this budget proposal" -p advisor

# With realm context data
./pod_manager.py main ask -q "Should we proceed?" --realm-status-file current_state.json
```

### Persona Management

```bash
# List all available personas
./pod_manager.py main personas

# Get details for specific persona
./pod_manager.py main persona -p ashoka

# Available personas: ashoka (default), advisor, facilitator
```

### Realm Status

```bash
# Get status for all tracked realms
./pod_manager.py main realm-status

# Get status for specific realm
./pod_manager.py main realm-status -r realm_principal_id
```

### Health Check

```bash
# Check API health and connectivity
./pod_manager.py main health
```

## Architecture Overview

- **Pod Manager**: RunPod cloud deployment and management
- **API Service**: Flask HTTP API with CORS support
- **Persona System**: Multiple specialized AI governance advisors
- **Database**: PostgreSQL for conversation history and realm status
- **LLM Integration**: Ollama for local LLM inference
- **RAG System**: ChromaDB for document embeddings and retrieval

## Configuration

Set environment variables:

```bash
export RUNPOD_API_KEY="your_runpod_api_key"
export ASHOKA_DEFAULT_MODEL="llama3.2:1b"
```

## File Structure

- `pod_manager.py` - Main CLI tool for pod management and API interaction
- `api.py` - HTTP API service
- `persona_manager.py` - Multi-persona system
- `database/` - Database client and schema
- `prompts/personas/` - AI persona definitions
- `tests/` - Test cases and scenarios
