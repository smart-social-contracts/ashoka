# Ashoka

An AI-powered question-answering system for Internet Computer Protocol realms. Ask questions about realm governance via HTTP API and get intelligent responses powered by LLMs and retrieval-augmented generation (RAG).

## Quick Start

```bash
# Start the system with Docker Compose
docker-compose up

# Ask a question via HTTP POST
curl -X POST http://localhost:5000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "realm_canister_id": "your-realm-id",
    "question": "What is the current governance status?"
  }'
```

## What Ashoka Does

Ashoka enables you to ask natural language questions about Internet Computer realms and receive AI-generated answers that combine:

1. **Live realm data** - Fetched directly from the realm's smart contract
2. **Governance knowledge** - Retrieved from a curated knowledge base using RAG
3. **AI reasoning** - Powered by Ollama LLM for intelligent synthesis

## Architecture Overview

```
                    ┌──────────────────┐
                    │                  │
                    │   User/Client   │
                    │                  │
                    └─────────┼─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │                  │
                    │   Ashoka API     │
                    │   (Flask)        │
                    └─────────┼─────────┘
                             │
        ┌────────────────┼────────────────┐
        │                ▼                │
        ▼           ┌──────────────────┐  ▼
┌─────────────────┐ │                  │ ┌─────────────────┐
│                 │ │   CLI Interface  │ │ Internet Computer│
│   ChromaDB      │ │   (main.py)      │ │   Realms        │
│   (RAG/Vector   │ └──────────────────┘ └─────────────────┘
│   Database)     │         │
└─────────────────┘         ▼
        │           ┌──────────────┐
        ▼           │              │
┌─────────────────┐ │   Ollama     │
│   Governance    │ │   (LLM)      │
│   Knowledge     │ └──────────────┘
│   Base          │         │
└─────────────────┘         ▼
                    ┌──────────────┐
                    │  AI Governor │
                    │  Proposals   │
                    │  (MCP)       │
                    └──────────────┘
```

**Key Components:**
- **Ashoka API**: Flask-based HTTP API for external integrations
- **CLI Interface**: Command-line tools for governance operations
- **ChromaDB**: Vector database for RAG-based knowledge retrieval
- **Ollama**: Local LLM service for AI reasoning and proposal generation
- **IC Realms**: Internet Computer Protocol governance canisters

## Core Features

- **HTTP API** for easy integration (`/api/ask` endpoint)
- **Realm Integration** via Internet Computer Protocol
- **RAG System** with ChromaDB for governance knowledge retrieval
- **Streaming responses** for real-time interaction
- **Docker deployment** with multi-service architecture

## Installation

### Using Docker Compose (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd ashoka

# Start all services (ChromaDB, Ollama, Ashoka API)
docker-compose up
```

### Manual Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Start ChromaDB and Ollama services separately
# Then run the API server
python api.py
```

## HTTP API Usage

### Ask Questions About a Realm

**Endpoint:** `POST /api/ask`

```bash
curl -X POST http://localhost:5000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "realm_canister_id": "rrkah-fqaaa-aaaaa-aaaaq-cai",
    "question": "What are the current treasury allocations?"
  }'
```

**Request Parameters:**
- `realm_canister_id` (required) - The IC realm canister ID
- `question` (required) - Your question about the realm
- `stream` (optional) - Set to `true` for streaming responses
- `ollama_url` (optional) - Custom Ollama URL (defaults to localhost:11434)

**Response:**
```json
{
  "success": true,
  "answer": "Based on the realm data, the current treasury allocations are...",
  "realm_data": {...},
  "rag_context": [...]
}
```

### Streaming Responses

For real-time responses, set `stream: true`:

```bash
curl -X POST http://localhost:5000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "realm_canister_id": "your-realm-id",
    "question": "Explain the governance structure",
    "stream": true
  }'
```

## Model Context Protocol (MCP)

ashoka supports the Model Context Protocol (MCP), which enables structured interactions between LLMs and external systems. With MCP:

- LLMs can access external context and tools through standardized messages
- The protocol provides a consistent way to pass context between the AI and canister systems
- Message formats ensure structured communication for governance proposals

This enables AI governors to effectively analyze governance systems and generate valuable proposals.

## Training and Testing

ashoka includes a comprehensive framework for training and testing AI governors:

### Enhanced Prompting System

Multiple prompt templates in the `prompts/` directory provide deep governance knowledge:

- `governor_init.txt` - Basic introduction to governance and GGG
- `governance_principles.txt` - Core governance concepts and frameworks
- `decision_framework.txt` - Structured approach to proposal evaluation
- `case_studies/` - Real-world governance examples and lessons

### Evaluation Commands

```bash
# Evaluate a single scenario
ashoka evaluate [ollama_url] <scenario_file> [options]

# Options:
# --output <file>         Save evaluation results as JSON
# --use-llm-evaluator     Use LLM to evaluate proposals
# --mock                  Use mock realm for testing
# --submit-mock           Submit proposal to mock realm
```

### Benchmarking

```bash
# Run multiple scenarios to benchmark governor quality
ashoka benchmark [ollama_url] <scenarios_dir> [--output <file>]
```

The benchmarking system evaluates proposals on multiple criteria:
- Comprehensiveness
- Practicality
- Clarity
- Ethical considerations

## Project Structure

```
ashoka/
├── main.py                # CLI entry point
├── ollama_client.py       # Interacts with the LLM via HTTP
├── realm_interface.py     # Uses ic-py to query GGG and submit proposals
├── messages.py            # MCP message formats
├── evaluator.py           # Proposal evaluation tools
├── mock_realm.py          # Mock realm for testing
├── prompts/
│   ├── governor_init.txt  # Basic introduction to governance
│   ├── governance_principles.txt # Core governance concepts
│   ├── decision_framework.txt # Proposal evaluation framework
│   └── case_studies/      # Real-world governance examples
├── config.yaml            # Stores default model endpoint, test realm ID
└── tests/                 # Unit tests and test scenarios
    └── scenarios/         # Governance test scenarios
```

