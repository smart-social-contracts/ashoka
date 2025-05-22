
# Oshaka

An off-chain AI governor for GGG-compliant realms on the Internet Computer.

## Overview

Oshaka connects to decentralized realms and proposes improvements in governance by leveraging AI models. It uses a local or remote LLM (served via Ollama) and connects to a GGG-compliant realm canister.

## Installation

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Make the main script executable: `chmod +x oshaka/main.py`

## Usage

Oshaka provides two main commands:

### Initialize an AI Governor

```bash
oshaka create [ollama_url]
```

This command:
- Connects to an Ollama LLM at the provided URL (defaults to http://localhost:11434)
- Sends training prompts to make the model behave as a digital governor
- Teaches it the high-level purpose of GGG (Generalized Global Governance)

### Run the AI Governor on a Realm

```bash
oshaka run [ollama_url] <realm_canister_id> [--mcp-only]
```

This command:
- Connects to the realm's canister using `ic-py`
- Queries the realm's public interface using GGG endpoints
- Sends that context to the LLM
- Receives a JSON object containing a proposal
- Wraps the proposal in an MCP ProposalOfferMessage
- Submits the proposal back to the canister (unless --mcp-only is specified)

## Model Context Protocol (MCP)

Oshaka supports the Model Context Protocol (MCP), which enables structured interactions between LLMs and external systems. With MCP:

- LLMs can access external context and tools through standardized messages
- The protocol provides a consistent way to pass context between the AI and canister systems
- Message formats ensure structured communication for governance proposals

This enables AI governors to effectively analyze governance systems and generate valuable proposals.

## Training and Testing

Oshaka includes a comprehensive framework for training and testing AI governors:

### Enhanced Prompting System

Multiple prompt templates in the `prompts/` directory provide deep governance knowledge:

- `governor_init.txt` - Basic introduction to governance and GGG
- `governance_principles.txt` - Core governance concepts and frameworks
- `decision_framework.txt` - Structured approach to proposal evaluation
- `case_studies/` - Real-world governance examples and lessons

### Evaluation Commands

```bash
# Evaluate a single scenario
oshaka evaluate [ollama_url] <scenario_file> [options]

# Options:
# --output <file>         Save evaluation results as JSON
# --use-llm-evaluator     Use LLM to evaluate proposals
# --mock                  Use mock realm for testing
# --submit-mock           Submit proposal to mock realm
```

### Benchmarking

```bash
# Run multiple scenarios to benchmark governor quality
oshaka benchmark [ollama_url] <scenarios_dir> [--output <file>]
```

The benchmarking system evaluates proposals on multiple criteria:
- Comprehensiveness
- Practicality
- Clarity
- Ethical considerations

## Project Structure

```
oshaka/
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
