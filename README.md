# Ashoka

An AI-powered question-answering system for Internet Computer Protocol realms. Ask questions about realm governance via HTTP API and get intelligent responses powered by LLMs and retrieval-augmented generation (RAG).

## Quick Start

```bash
curl -X POST https://1xze4llp4iff5h-5000.proxy.runpod.net/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "user_principal": "user123",
    "realm_principal": "realm456", 
    "question": "How can we improve voter participation?",
    "stream": true
  }'
```

## Architecture Overview

TODO

