# Ashoka HTTP API

HTTP API for asking questions about Internet Computer Protocol realms. Get AI-powered answers that combine live realm data with governance knowledge.

## Quick Start

### Using Docker Compose (Recommended)
```bash
# Start all services (ChromaDB, Ollama, Ashoka API)
docker-compose up

# API will be available at http://localhost:5000
```

### Manual Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Start the API server
python api.py
```

## Main Use Case: Ask Questions About Realms

The primary endpoint `/api/ask` lets you ask natural language questions about IC realms and get intelligent responses.

## API Endpoints

### 🔥 Primary Endpoint: Ask Questions About Realms

```
POST /api/ask
```

**Description:** Ask natural language questions about Internet Computer realms and get AI-powered answers.

**Request Body:**
```json
{
  "realm_canister_id": "rrkah-fqaaa-aaaaa-aaaaq-cai",  // Required: IC realm canister ID
  "question": "What are the current treasury allocations?",  // Required: Your question
  "stream": false,  // Optional: Set to true for streaming responses
  "ollama_url": "http://localhost:11434"  // Optional: Custom Ollama URL
}
```

**Response:**
```json
{
  "success": true,
  "answer": "Based on the realm data, the current treasury allocations are...",
  "realm_data": {
    "name": "Example Realm",
    "status": "active",
    // ... other realm information
  },
  "rag_context": [
    {
      "content": "Relevant governance knowledge...",
      "source": "governance_docs"
    }
  ]
}
```

**Example Usage:**
```bash
curl -X POST http://localhost:5000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "realm_canister_id": "your-realm-id",
    "question": "How does the voting mechanism work?"
  }'
```

### Health Check
```
GET /
```
Simple health check to verify the API is running.

### RAG System Endpoints

#### Add Governance Documents
```
POST /api/rag-embed
```
**Request Body:**
```json
{
  "documents": [
    {
      "content": "Governance document content...",
      "metadata": {"source": "governance_manual"}
    }
  ]
}
```

#### Query RAG System Directly
```
POST /api/rag-query
```
**Request Body:**
```json
{
  "query": "treasury management",
  "n_results": 3
}
```

#### RAG Health Check
```
GET /api/rag-health
```
Check the status of ChromaDB and RAG components.
**Request Body:**
```json
{
  "scenarios_dir": "tests/scenarios",  // Required
  "ollama_url": "http://localhost:11434",  // Optional
  "output_file": "benchmark_results.json"  // Optional
}
```

### Send Direct Prompt to Ollama
```
POST /api/direct-prompt
```
**Request Body:**
```json
{
  "prompt": "You are an AI Governor...",  // Required
  "ollama_url": "http://localhost:11434",  // Optional
  "model": "llama3"  // Optional
}
```

### Query Realm Canister
```
POST /api/realm-query
```
**Request Body:**
```json
{
  "canister_id": "rrkah-fqaaa-aaaaa-aaaaq-cai",  // Required
  "method": "get_realm_data",  // Optional, defaults to get_realm_data
  "args": []  // Optional, defaults to empty array
}
```

### Ask Custom Question About a Realm
```
POST /api/ask
```
**Request Body:**
```json
{
  "realm_canister_id": "rrkah-fqaaa-aaaaa-aaaaq-cai",  // Required
  "question": "What would be the impact of reducing the voting period to 3 days?",  // Required
  "ollama_url": "http://localhost:11434"  // Optional
}
```

## Example Usage

Using curl:

```bash
# Health check
curl -X GET http://localhost:5000/health

# Initialize AI governor
curl -X POST http://localhost:5000/api/create \
  -H "Content-Type: application/json" \
  -d '{}'

# Run AI governor on a realm
curl -X POST http://localhost:5000/api/run \
  -H "Content-Type: application/json" \
  -d '{"realm_canister_id": "rrkah-fqaaa-aaaaa-aaaaq-cai", "mcp_only": true}'

# Evaluate with mock realm
curl -X POST http://localhost:5000/api/evaluate \
  -H "Content-Type: application/json" \
  -d '{"scenario_file": "tests/scenarios/treasury_allocation.txt", "mock": true}'

# Send direct prompt to Ollama
curl -X POST http://localhost:5000/api/direct-prompt \
  -H "Content-Type: application/json" \
  -d '{"prompt": "You are an AI Governor. Please suggest improvements for a treasury allocation system in a decentralized realm."}'

# Ask a custom question about a realm
curl -X POST http://localhost:5000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"realm_canister_id": "rrkah-fqaaa-aaaaa-aaaaq-cai", "question": "What would be the impact of reducing the voting period to 3 days?"}'
```

## Notes

- The API server runs in debug mode by default, which is not recommended for production use.
- Make sure Ollama is running at the specified URL before making requests.
- For endpoints that interact with Internet Computer canisters, make sure ic-py is properly installed.
