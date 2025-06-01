#!/usr/bin/env python3
"""
Ashoka HTTP API Wrapper - Exposes Ashoka functionality via HTTP endpoints
"""

from flask import Flask, request, jsonify
import subprocess
import json
import logging
import sys
import os
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ashoka-api")

# Ensure we're in the correct directory
os.chdir(Path(__file__).parent)

app = Flask(__name__)

@app.route('/health', methods=['GET'])
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
        realm_canister_id = os.environ.get('DEFAULT_REALM_ID')
        if not realm_canister_id:
            return jsonify({"success": False, "error": "realm_canister_id is required and DEFAULT_REALM_ID environment variable is not set"}), 400
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

@app.route('/api/realm-query', methods=['POST'])
def realm_query():
    """Query a realm canister directly using ic-py."""
    data = request.json or {}
    
    # Required parameters
    canister_id = data.get('canister_id')
    if not canister_id:
        return jsonify({"success": False, "error": "canister_id is required"}), 400
    
    method = data.get('method')
    if not method:
        method = "get_summary"  # Default method
    
    args = data.get('args', [])
    
    logger.info(f"API: Querying realm canister {canister_id} with method {method}")
    
    # We'll use a simple script to call ic-py directly
    temp_script = """
import sys
from ic.client import Client
from ic.identity import Identity
from ic.agent import Agent
from ic.candid import encode, decode

def main():
    try:
        canister_id = sys.argv[1]
        method = sys.argv[2]
        args_str = sys.argv[3] if len(sys.argv) > 3 else "[]"
        
        import json
        args = json.loads(args_str)
        
        # Create an identity and agent
        identity = Identity()
        client = Client()
        agent = Agent(identity, client)
        
        # Call the canister
        response = agent.query_raw(canister_id, method, encode(args))
        result = decode(response)
        
        print(json.dumps(result))
        return 0
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
    """
    
    temp_script_path = "temp_ic_query.py"
    with open(temp_script_path, "w") as f:
        f.write(temp_script)
    
    try:
        args_json = json.dumps(args)
        result = subprocess.run(
            ['python', temp_script_path, canister_id, method, args_json],
            capture_output=True, 
            text=True
        )
        
        # Clean up temp script
        os.remove(temp_script_path)
        
        if result.returncode != 0:
            logger.error(f"Canister query failed: {result.stderr}")
            return jsonify({
                "success": False,
                "error": result.stderr
            }), 500
        
        # Parse the response
        try:
            query_result = json.loads(result.stdout)
            return jsonify({
                "success": True,
                "result": query_result
            })
        except json.JSONDecodeError:
            logger.error(f"Failed to parse query result as JSON: {result.stdout}")
            return jsonify({
                "success": False,
                "error": "Failed to parse query result",
                "raw_result": result.stdout
            }), 500
    
    except Exception as e:
        logger.error(f"Error querying canister: {str(e)}")
        # Clean up temp script if it exists
        if os.path.exists(temp_script_path):
            os.remove(temp_script_path)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/ask', methods=['POST'])
def ask():
    """Ask a custom question about a realm."""
    data = request.json or {}
    
    # Required parameters
    realm_canister_id = data.get('realm_canister_id')
    if not realm_canister_id:
        # Try to get realm ID from environment variable
        realm_canister_id = os.environ.get('DEFAULT_REALM_ID')
        if not realm_canister_id:
            return jsonify({"success": False, "error": "realm_canister_id is required and DEFAULT_REALM_ID environment variable is not set"}), 400
        logger.info(f"Using realm canister ID from environment: {realm_canister_id}")
    
    question = data.get('question')
    if not question:
        return jsonify({"success": False, "error": "question is required"}), 400
    
    # Optional parameters
    ollama_url = data.get('ollama_url', 'http://localhost:11434')
    
    logger.info(f"API: Asking question about realm {realm_canister_id}")
    
    # Build command with named arguments
    command = ['python', 'cli/main.py', 'ask', '--realm-id', realm_canister_id, '--ollama-url', ollama_url, question]
    
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        
        # Parse the output to extract the AI Governor response if possible
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
        
        if ai_response:
            response["ai_response"] = ai_response
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error running CLI command: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

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
    
    # Start the Flask server
    app.run(host='0.0.0.0', port=5000, debug=True)
