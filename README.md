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
    "realm_principal": "aaa-realm",
    "user_principal": "aaa-user",
    "question": "What is the current governance status?"
  }'
```

## Architecture Overview

TODO

