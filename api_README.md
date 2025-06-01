# Ashoka HTTP API Wrapper

This API wrapper provides HTTP endpoints for interacting with Ashoka, allowing you to use its capabilities via REST API calls instead of the command line interface.

## Setup

1. Make sure all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   pip install flask requests
   ```

2. Make the API script executable:
   ```bash
   chmod +x api.py
   ```

3. Start the API server:
   ```bash
   python api.py
   ```

The server will start on `http://localhost:5000` by default.

## API Endpoints

### Health Check
```
GET /health
```
Simple health check to verify the API is running.

### Initialize AI Governor
```
POST /api/create
```
**Request Body:**
```json
{
  "ollama_url": "http://localhost:11434"  // Optional, defaults to this value
}
```

### Run AI Governor on a Realm
```
POST /api/run
```
**Request Body:**
```json
{
  "realm_canister_id": "rrkah-fqaaa-aaaaa-aaaaq-cai",  // Required
  "ollama_url": "http://localhost:11434",  // Optional
  "mcp_only": true  // Optional, defaults to false
}
```

### Evaluate AI Governor
```
POST /api/evaluate
```
**Request Body:**
```json
{
  "scenario_file": "tests/scenarios/treasury_allocation.txt",  // Required
  "ollama_url": "http://localhost:11434",  // Optional
  "use_llm_evaluator": false,  // Optional
  "mock": true,  // Optional
  "submit_mock": false,  // Optional
  "output_file": "evaluation_results.json"  // Optional
}
```

### Benchmark AI Governor
```
POST /api/benchmark
```
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
  "method": "get_summary",  // Optional, defaults to get_summary
  "args": []  // Optional, defaults to empty array
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
```

## Notes

- The API server runs in debug mode by default, which is not recommended for production use.
- Make sure Ollama is running at the specified URL before making requests.
- For endpoints that interact with Internet Computer canisters, make sure ic-py is properly installed.
