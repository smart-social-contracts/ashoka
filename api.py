#!/usr/bin/env python3
"""
Ashoka HTTP API Wrapper - Exposes Ashoka functionality via HTTP endpoints
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import json
import logging
import sys
import os
import time
import threading
from pathlib import Path
from database.db_client import DatabaseClient

try:
    from rag.retrieval import RAGRetriever
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

INACTIVITY_TIMEOUT_SECONDS = int(os.getenv("INACTIVITY_TIMEOUT_SECONDS", 3600))
CHECK_INTERVAL = 60
# Set up logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ashoka-api")
logger.setLevel(logging.DEBUG)

# Set DEBUG level for all loggers
logging.getLogger().setLevel(logging.DEBUG)

# Configure Flask's logger
flask_logger = logging.getLogger('werkzeug')
flask_logger.setLevel(logging.DEBUG)

# Ensure we're in the correct directory
os.chdir(Path(__file__).parent)

# Global variable to track last request time
last_request_time = time.time()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})  # For development - restrict origins in production

rag_retriever = None
if RAG_AVAILABLE:
    try:
        rag_retriever = RAGRetriever(environment="prod")
    except Exception as e:
        logger.error(f"Warning: Failed to initialize RAG retriever: {e}")

db_client = None
try:
    db_client = DatabaseClient()
    logger.info("Database client initialized successfully")
except Exception as e:
    logger.warning(f"Failed to initialize database client: {e}")
    db_client = None

def update_last_request_time():
    """Update the timestamp of the last request."""
    global last_request_time
    last_request_time = time.time()
    logger.debug(f"Updated last request time: {last_request_time}")

def inactivity_monitor(timeout_seconds=INACTIVITY_TIMEOUT_SECONDS, check_interval=CHECK_INTERVAL):
    """
    Background thread that monitors for inactivity and shuts down the pod.
    
    Args:
        timeout_seconds: Time in seconds before shutdown (default: 1 hour)
        check_interval: How often to check for inactivity (default: 1 minute)
    """
    logger.info(f"Starting inactivity monitor - will shutdown after {timeout_seconds} seconds of inactivity")
    
    while True:
        time.sleep(check_interval)
        current_time = time.time()
        time_since_last_request = current_time - last_request_time
        
        logger.debug(f"Checking inactivity: {time_since_last_request:.1f}s since last request. We will shutdown after {timeout_seconds} seconds of inactivity.")
        
        if time_since_last_request > timeout_seconds:
            logger.info(f"No requests for {timeout_seconds} seconds. Shutting down pod.")
            
            # Try to stop the runpod gracefully using runpodctl
            try:
                runpod_id = os.environ.get('RUNPOD_POD_ID')
                if runpod_id:
                    logger.info(f"Stopping runpod {runpod_id} using runpodctl")
                    result = subprocess.run(['runpodctl', 'stop', 'pod', runpod_id],
                                          capture_output=True, text=True, timeout=30)
                    if result.returncode == 0:
                        logger.info("Successfully stopped runpod")
                    else:
                        logger.warning(f"runpodctl stop failed: {result.stderr}")
                else:
                    logger.warning("RUNPOD_POD_ID environment variable not found")
            except subprocess.TimeoutExpired:
                logger.error("runpodctl stop command timed out")
            except Exception as e:
                logger.error(f"Error stopping runpod: {e}")
            
            # Use os._exit(0) to immediately terminate the process
            os._exit(0)

@app.before_request
def before_request():
    """Update the last request time before processing any request."""
    update_last_request_time()
@app.route('/', methods=['GET'])
def health_check():
    """Simple health check endpoint."""
    return jsonify({"status": "healthy", "service": "ashoka-api"})

@app.route('/api/create', methods=['POST'])
def create():
    """Initialize an LLM with governance capabilities."""
    data = request.json or {}
    ollama_url = data.get('ollama_url', 'http://localhost:11434')
    
    logger.info(f"API: Creating AI governor with Ollama at {ollama_url}")
    
    try:
        result = subprocess.run([
            'python', 'cli/main.py', 'create', '--ollama-url', ollama_url
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"CLI command failed: {result.stderr}")
            return jsonify({
                "success": False,
                "error": result.stderr,
                "command_output": result.stdout
            }), 500
        
        return jsonify({
            "success": True,
            "command_output": result.stdout
        })
    
    except Exception as e:
        logger.error(f"Error running CLI command: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/run', methods=['POST'])
def run():
    """Connect to a realm canister and propose improvements."""
    data = request.json or {}
    
    # Required parameters
    realm_canister_id = data.get('realm_canister_id')
    if not realm_canister_id:
        # Try to get realm ID from environment variable
        realm_canister_id = os.environ.get('ASHOKA_REALM_ID')
        if not realm_canister_id:
            return jsonify({"success": False, "error": "realm_canister_id is required and ASHOKA_REALM_ID environment variable is not set"}), 400
        logger.info(f"Using realm canister ID from environment: {realm_canister_id}")
    
    # Optional parameters
    ollama_url = data.get('ollama_url', 'http://localhost:11434')
    mcp_only = data.get('mcp_only', False)
    
    logger.info(f"API: Running AI governor for realm {realm_canister_id}")
    
    # Build command with named arguments
    command = ['python', 'cli/main.py', 'run', '--realm-id', realm_canister_id, '--ollama-url', ollama_url]
    if mcp_only:
        command.append('--mcp-only')
    
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        
        # Parse the output to extract the MCP message if possible
        mcp_message = None
        output_lines = result.stdout.split('\n')
        start_idx = -1
        end_idx = -1
        
        for i, line in enumerate(output_lines):
            if "=== MCP Proposal Offer Message ===" in line:
                start_idx = i + 1
            elif "=================================" in line and start_idx != -1:
                end_idx = i
                break
        
        if start_idx != -1 and end_idx != -1:
            try:
                mcp_json = "\n".join(output_lines[start_idx:end_idx]).strip()
                mcp_message = json.loads(mcp_json)
            except json.JSONDecodeError:
                logger.warning("Failed to parse MCP message from output")
        
        if result.returncode != 0:
            logger.error(f"CLI command failed: {result.stderr}")
            return jsonify({
                "success": False,
                "error": result.stderr,
                "command_output": result.stdout
            }), 500
        
        response = {
            "success": True,
            "command_output": result.stdout
        }
        
        if mcp_message:
            response["mcp_message"] = mcp_message
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error running CLI command: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/evaluate', methods=['POST'])
def evaluate():
    """Evaluate governor performance on test scenarios."""
    data = request.json or {}
    
    # Required parameters
    scenario_file = data.get('scenario_file')
    if not scenario_file:
        return jsonify({"success": False, "error": "scenario_file is required"}), 400
    
    # Optional parameters
    ollama_url = data.get('ollama_url', 'http://localhost:11434')
    use_llm_evaluator = data.get('use_llm_evaluator', False)
    mock = data.get('mock', False)
    submit_mock = data.get('submit_mock', False)
    output_file = data.get('output_file')
    
    logger.info(f"API: Evaluating AI governor with scenario {scenario_file}")
    
    # Build command
    command = ['python', 'cli/main.py', 'evaluate', '--ollama-url', ollama_url, scenario_file]
    
    if use_llm_evaluator:
        command.append('--use-llm-evaluator')
    if mock:
        command.append('--mock')
    if submit_mock:
        command.append('--submit-mock')
    if output_file:
        command.extend(['--output', output_file])
    
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        
        # Try to parse evaluation results
        evaluation_results = None
        if output_file and os.path.exists(output_file):
            try:
                with open(output_file, 'r') as f:
                    evaluation_results = json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse evaluation results from {output_file}")
        
        if result.returncode != 0:
            logger.error(f"CLI command failed: {result.stderr}")
            return jsonify({
                "success": False,
                "error": result.stderr,
                "command_output": result.stdout
            }), 500
        
        response = {
            "success": True,
            "command_output": result.stdout
        }
        
        if evaluation_results:
            response["evaluation_results"] = evaluation_results
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error running CLI command: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/benchmark', methods=['POST'])
def benchmark():
    """Run benchmark tests on multiple scenarios."""
    data = request.json or {}
    
    # Required parameters
    scenarios_dir = data.get('scenarios_dir')
    if not scenarios_dir:
        return jsonify({"success": False, "error": "scenarios_dir is required"}), 400
    
    # Optional parameters
    ollama_url = data.get('ollama_url', 'http://localhost:11434')
    output_file = data.get('output_file')
    
    logger.info(f"API: Running benchmark on scenarios in {scenarios_dir}")
    
    # Build command
    command = ['python', 'cli/main.py', 'benchmark', '--ollama-url', ollama_url, scenarios_dir]
    
    if output_file:
        command.extend(['--output', output_file])
    
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        
        # Try to parse benchmark results
        benchmark_results = None
        if output_file and os.path.exists(output_file):
            try:
                with open(output_file, 'r') as f:
                    benchmark_results = json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse benchmark results from {output_file}")
        
        if result.returncode != 0:
            logger.error(f"CLI command failed: {result.stderr}")
            return jsonify({
                "success": False,
                "error": result.stderr,
                "command_output": result.stdout
            }), 500
        
        response = {
            "success": True,
            "command_output": result.stdout
        }
        
        if benchmark_results:
            response["benchmark_results"] = benchmark_results
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error running CLI command: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/direct-prompt', methods=['POST'])
def direct_prompt():
    """Send a prompt directly to Ollama without using the Ashoka CLI."""
    data = request.json or {}
    
    # Required parameters
    prompt = data.get('prompt')
    if not prompt:
        return jsonify({"success": False, "error": "prompt is required"}), 400
    
    # Optional parameters
    ollama_url = data.get('ollama_url', 'http://localhost:11434')
    model = data.get('model', 'llama3')
    
    logger.info(f"API: Sending direct prompt to Ollama at {ollama_url}")
    
    # Call Ollama API directly
    import requests
    
    try:
        response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt
            }
        )
        
        if response.status_code != 200:
            logger.error(f"Ollama API request failed: {response.text}")
            return jsonify({
                "success": False,
                "error": f"Ollama API request failed with status {response.status_code}",
                "ollama_response": response.text
            }), 500
        
        # Parse the response
        try:
            ollama_response = response.json()
            return jsonify({
                "success": True,
                "response": ollama_response
            })
        except json.JSONDecodeError:
            logger.error(f"Failed to parse Ollama response as JSON: {response.text}")
            return jsonify({
                "success": False,
                "error": "Failed to parse Ollama response",
                "raw_response": response.text
            }), 500
    
    except Exception as e:
        logger.error(f"Error calling Ollama API: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def handle_streaming_ask(realm_canister_id, question, ollama_url):
    """Handle streaming LLM requests with Server-Sent Events."""
    from flask import Response
    import json
    
    def generate_streaming_response():
        try:
            from cli.ollama_client import OllamaClient
            
            ollama_client = OllamaClient(ollama_url)
            
            response = ollama_client.send_prompt_streaming(question)
            
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    try:
                        chunk_data = json.loads(line)
                        
                        content = chunk_data.get('response', '')
                        
                        if content:
                            sse_data = json.dumps({"content": content})
                            yield f"data: {sse_data}\n\n"
                        
                        if chunk_data.get('done', False):
                            break
                            
                    except json.JSONDecodeError:
                        continue
                        
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Error in streaming response: {str(e)}")
            error_data = json.dumps({"error": str(e)})
            yield f"data: {error_data}\n\n"
    
    return Response(
        generate_streaming_response(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
    )

def load_ashoka_persona() -> str:
    """Load Ashoka persona prompt from file."""
    try:
        persona_path = Path(__file__).parent / "cli" / "prompts" / "governor_init.txt"
        with open(persona_path, 'r') as f:
            return f.read().strip()
    except Exception as e:
        logger.error(f"Failed to load Ashoka persona: {e}")
        return "You are Ashoka, an AI governor designed to improve decentralized governance systems."

def load_realm_fixture(realm_principal: str) -> dict:
    """Load realm data from fixture files."""
    try:
        fixtures_dir = Path(__file__).parent / "fixtures"
        
        for fixture_file in fixtures_dir.glob("*.json"):
            with open(fixture_file, 'r') as f:
                realm_data = json.load(f)
                if realm_data.get('realm_principal') == realm_principal:
                    return realm_data
        
        sample_path = fixtures_dir / "realm_sample.json"
        if sample_path.exists():
            with open(sample_path, 'r') as f:
                realm_data = json.load(f)
                realm_data['realm_principal'] = realm_principal
                return realm_data
        
        return {
            "realm_principal": realm_principal,
            "name": f"Realm {realm_principal}",
            "treasury": {"total_funds": 100000, "currency": "USDC"},
            "governance": {"voting_system": "token_weighted", "proposal_threshold": 1000},
            "active_proposals": [],
            "community_stats": {"total_members": 100, "active_voters": 25}
        }
    except Exception as e:
        logger.error(f"Failed to load realm fixture: {e}")
        return {"realm_principal": realm_principal, "name": f"Realm {realm_principal}"}

def handle_non_streaming_ask_new(user_principal: str, realm_principal: str, question: str, ollama_url: str):
    """Handle non-streaming LLM requests with new parameters."""
    try:
        persona_prompt = load_ashoka_persona()
        
        realm_data = load_realm_fixture(realm_principal)
        
        realm_context = f"""
== Realm Information ==
Name: {realm_data.get('name', 'Unknown Realm')}
Principal: {realm_data.get('realm_principal', realm_principal)}
Treasury: {realm_data.get('treasury', {}).get('total_funds', 0)} {realm_data.get('treasury', {}).get('currency', 'tokens')}
Active Proposals: {len(realm_data.get('active_proposals', []))}
Community Members: {realm_data.get('community_stats', {}).get('total_members', 0)}

== User Question ==
{question}

== Instructions ==
Based on the realm information above and your role as an AI governor, provide a thoughtful response to the user's question. Focus on practical governance advice that would benefit this specific realm.
"""
        
        full_prompt = f"{persona_prompt}\n\n{realm_context}"
        
        rag_context = ""
        if rag_retriever:
            try:
                contexts = rag_retriever.retrieve_context(question, n_results=3)
                if contexts:
                    rag_context = "\n\n== Relevant Governance Knowledge ==\n"
                    for i, ctx in enumerate(contexts[:3]):
                        rag_context += f"{i+1}. {ctx.get('content', '')}\n"
                    full_prompt += rag_context
            except Exception as e:
                logger.warning(f"Failed to retrieve RAG context: {e}")
        
        ai_response = None
        
        if str(os.environ.get('ASHOKA_USE_LLM')).lower() == 'true':
            logger.info('Using LLM for response generation')
            
            try:
                from cli.ollama_client import OllamaClient
                ollama_client = OllamaClient(ollama_url)
                ai_response = ollama_client.send_prompt(full_prompt)
                logger.info("Generated AI response using Ollama")
            except Exception as e:
                logger.error(f"Failed to use Ollama client: {e}")
                ai_response = "I apologize, but I'm currently unable to process your request due to a technical issue. Please try again later."
        else:
            ai_response = f"""Based on the governance context for {realm_data.get('name', 'your realm')}, here are my recommendations:

For a realm with {realm_data.get('community_stats', {}).get('total_members', 0)} members and {realm_data.get('treasury', {}).get('total_funds', 0)} {realm_data.get('treasury', {}).get('currency', 'tokens')} in treasury, the key governance priorities should focus on:

1. **Community Engagement**: With {realm_data.get('community_stats', {}).get('active_voters', 0)} active voters, increasing participation through better communication and incentives is crucial.

2. **Treasury Management**: Proper allocation and oversight of the {realm_data.get('treasury', {}).get('total_funds', 0)} {realm_data.get('treasury', {}).get('currency', 'tokens')} treasury requires transparent processes and community input.

3. **Proposal Process**: Streamlining the proposal and voting process to ensure efficient decision-making while maintaining democratic principles.

This is a demonstration response. Enable ASHOKA_USE_LLM=true for full AI-powered responses."""
        
        conversation_id = None
        if db_client:
            try:
                metadata = {
                    "ollama_url": ollama_url,
                    "realm_data": realm_data,
                    "rag_context_used": bool(rag_context)
                }
                conversation_id = db_client.store_conversation(
                    user_principal=user_principal,
                    realm_principal=realm_principal,
                    question=question,
                    response=ai_response,
                    prompt_context=full_prompt,
                    metadata=metadata
                )
                logger.info(f"Stored conversation with ID: {conversation_id}")
            except Exception as e:
                logger.error(f"Failed to store conversation: {e}")
        
        response = {
            "success": True,
            "ai_response": ai_response,
            "conversation_id": conversation_id,
            "realm_data": realm_data
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in handle_non_streaming_ask_new: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

def handle_streaming_ask_new(user_principal: str, realm_principal: str, question: str, ollama_url: str):
    """Handle streaming LLM requests with new parameters."""
    from flask import Response
    
    def generate_streaming_response():
        try:
            persona_prompt = load_ashoka_persona()
            realm_data = load_realm_fixture(realm_principal)
            
            realm_context = f"""
== Realm Information ==
Name: {realm_data.get('name', 'Unknown Realm')}
Principal: {realm_data.get('realm_principal', realm_principal)}
Treasury: {realm_data.get('treasury', {}).get('total_funds', 0)} {realm_data.get('treasury', {}).get('currency', 'tokens')}

== User Question ==
{question}
"""
            
            full_prompt = f"{persona_prompt}\n\n{realm_context}"
            
            from cli.ollama_client import OllamaClient
            ollama_client = OllamaClient(ollama_url)
            
            response = ollama_client.send_prompt_streaming(full_prompt)
            
            full_response = ""
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    try:
                        chunk_data = json.loads(line)
                        content = chunk_data.get('response', '')
                        
                        if content:
                            full_response += content
                            sse_data = json.dumps({"content": content})
                            yield f"data: {sse_data}\n\n"
                        
                        if chunk_data.get('done', False):
                            if db_client:
                                try:
                                    metadata = {
                                        "ollama_url": ollama_url,
                                        "realm_data": realm_data,
                                        "streaming": True
                                    }
                                    conversation_id = db_client.store_conversation(
                                        user_principal=user_principal,
                                        realm_principal=realm_principal,
                                        question=question,
                                        response=full_response,
                                        prompt_context=full_prompt,
                                        metadata=metadata
                                    )
                                    final_data = json.dumps({"conversation_id": conversation_id})
                                    yield f"data: {final_data}\n\n"
                                except Exception as e:
                                    logger.error(f"Failed to store streaming conversation: {e}")
                            break
                            
                    except json.JSONDecodeError:
                        continue
                        
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Error in streaming response: {str(e)}")
            error_data = json.dumps({"error": str(e)})
            yield f"data: {error_data}\n\n"
    
    return Response(
        generate_streaming_response(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
    )

def handle_non_streaming_ask(realm_canister_id, question, ollama_url):
    """Handle non-streaming LLM requests (legacy function for backward compatibility)."""
    command = ['python', 'cli/main.py', 'ask', '--realm-id', realm_canister_id, '--ollama-url', ollama_url, question]
    logger.info(f'Command: {command}')
    
    if str(os.environ.get('ASHOKA_USE_LLM')).lower() == 'true':
        logger.info('Using LLM')
        
        result = subprocess.run(command, capture_output=True, text=True)
        
        logger.info(f'LLM result: {result}')
        logger.info(f'LLM result stdout: {result.stdout}')
        logger.info(f'LLM result stderr: {result.stderr}')
        
        ai_response = None
        output_lines = result.stdout.split('\n')
        start_idx = -1
        end_idx = -1
        
        for i, line in enumerate(output_lines):
            if "=== AI Governor Response ===" in line:
                start_idx = i + 1
            elif "===========================" in line and start_idx != -1:
                end_idx = i
                break
        
        if start_idx != -1 and end_idx != -1:
            ai_response = "\n".join(output_lines[start_idx:end_idx]).strip()
        
        if result.returncode != 0:
            logger.error(f"CLI command failed: {result.stderr}")
            return jsonify({
                "success": False,
                "error": result.stderr,
                "command_output": result.stdout
            }), 500
        
        response = {
            "success": True,
            "command_output": result.stdout
        }
    else:
        response = {
            "success": True,
            "command_output": ""
        }
        ai_response = '''        
# This is a header

This is a paragraph.

* This is a list
* With two items
  1. And a sublist
  2. That is ordered
    * With another
    * Sublist inside

| And this is | A table |
|-------------|---------|
| With two    | columns |`
        '''
    
    if ai_response:
        response["ai_response"] = ai_response
    
    return jsonify(response)

@app.route('/api/ask', methods=['POST'])
def ask():
    try:
        """Ask a custom question about a realm."""
        data = request.json or {}
        
        # Required parameters
        user_principal = data.get('user_principal')
        if not user_principal:
            return jsonify({"success": False, "error": "user_principal is required"}), 400
        
        realm_principal = data.get('realm_principal')
        if not realm_principal:
            return jsonify({"success": False, "error": "realm_principal is required"}), 400
        
        question = data.get('question')
        if not question:
            return jsonify({"success": False, "error": "question is required"}), 400
        
        stream_requested = data.get('stream', False)
        
        ollama_url = data.get('ollama_url', 'http://localhost:11434')
        
        logger.info(f"API: Asking question about realm {realm_principal} from user {user_principal}, streaming: {stream_requested}")
        
        if stream_requested:
            return handle_streaming_ask_new(user_principal, realm_principal, question, ollama_url)
        else:
            return handle_non_streaming_ask_new(user_principal, realm_principal, question, ollama_url)
        
    except Exception as e:
        logger.error(f"Error running CLI command: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/rag-embed', methods=['POST'])
def rag_embed():
    """Embed documents into ChromaDB for RAG system."""
    if not rag_retriever:
        return jsonify({"error": "RAG system not initialized"}), 500
    
    try:
        data = request.get_json()
        documents = data.get("documents", [])
        
        if not documents:
            return jsonify({"error": "No documents provided"}), 400
        
        rag_retriever.add_governance_documents(documents)
        return jsonify({
            "status": "success", 
            "message": f"Embedded {len(documents)} documents"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/rag-query', methods=['POST'])
def rag_query():
    """Query RAG system with context retrieval."""
    if not rag_retriever:
        return jsonify({"error": "RAG system not initialized"}), 500
    
    try:
        data = request.get_json()
        query = data.get("query", "")
        n_results = data.get("n_results", 3)
        
        if not query:
            return jsonify({"error": "No query provided"}), 400
        
        contexts = rag_retriever.retrieve_context(query, n_results)
        return jsonify({
            "status": "success",
            "query": query,
            "contexts": contexts
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/rag-health', methods=['GET'])
def rag_health():
    """Health check for RAG system components."""
    if not rag_retriever:
        return jsonify({"error": "RAG system not initialized"}), 500
    
    try:
        health_status = rag_retriever.health_check()
        
        if db_client:
            health_status["database"] = db_client.health_check()
        else:
            health_status["database"] = False
            
        return jsonify({
            "status": "success",
            "health": health_status
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/conversations/<int:conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Get a specific conversation by ID."""
    if not db_client:
        return jsonify({"error": "Database not initialized"}), 500
    
    try:
        conversation = db_client.get_conversation(conversation_id)
        if conversation:
            return jsonify({
                "status": "success",
                "conversation": conversation
            })
        else:
            return jsonify({"error": "Conversation not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/conversations/user/<user_principal>', methods=['GET'])
def get_user_conversations(user_principal):
    """Get conversations for a specific user."""
    if not db_client:
        return jsonify({"error": "Database not initialized"}), 500
    
    try:
        limit = request.args.get('limit', 10, type=int)
        conversations = db_client.get_conversations_by_user(user_principal, limit)
        return jsonify({
            "status": "success",
            "conversations": conversations
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Add Flask to requirements if not already there
    try:
        import flask
    except ImportError:
        print("Flask not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "flask"], check=True)
    
    # Add requests to requirements if not already there
    try:
        import requests
    except ImportError:
        print("Requests not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "requests"], check=True)
    
    # Start the inactivity monitor thread
    monitor_thread = threading.Thread(target=inactivity_monitor, daemon=True)
    monitor_thread.start()
    logger.info("Inactivity monitor started - pod will shutdown after 1 hour of inactivity")
    
    # Start the Flask server
    app.run(host='0.0.0.0', port=5000, debug=False)
