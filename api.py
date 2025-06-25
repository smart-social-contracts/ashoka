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
from pathlib import Path

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

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})  # For development - restrict origins in production

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

@app.route('/api/realm-query', methods=['POST'])
def realm_query():
    """Query a realm canister directly using dfx command line."""
    data = request.json or {}
    
    # Required parameters
    canister_id = data.get('canister_id')
    if not canister_id:
        # Try to get realm ID from environment variable
        canister_id = os.environ.get('ASHOKA_REALM_ID')
        if not canister_id:
            return jsonify({"success": False, "error": "canister_id is required and ASHOKA_REALM_ID environment variable is not set"}), 400
        logger.info(f"Using canister ID from environment: {canister_id}")
    
    method = data.get('method')
    if not method:
        method = "get_realm_data"  # Default method
    
    args = data.get('args', [])
    # Check environment variable first, then fall back to the request parameter
    network = os.environ.get('ASHOKA_DFX_NETWORK') or data.get('network', 'ic')
    
    logger.info(f"API: Querying realm canister {canister_id} with method {method} on network {network}")
    
    # Determine network parameter for dfx
    if not network:
        network_param = ""
    else:
        network_param = f"--network {network}"
    
    try:
        # Convert args to a Candid-compatible argument string
        args_str = ''
        if args:
            # Simple handling for basic arguments
            # This is a simplified implementation - for complex types, 
            # you may need more sophisticated Candid encoding
            args_parts = []
            for arg in args:
                if isinstance(arg, str):
                    args_parts.append(f'\\"{arg}\\"')
                elif isinstance(arg, (int, float, bool)):
                    args_parts.append(str(arg).lower())
                else:
                    args_parts.append(str(arg))
            
            args_str = f'({", ".join(args_parts)})'
        
        # Build and execute the dfx command with JSON output
        if args_str:
            command = f'dfx canister {network_param} call {canister_id} {method} "{args_str}" --query --output=json'
        else:
            command = f'dfx canister {network_param} call {canister_id} {method} --query --output=json'
        
        logger.debug(f"Executing command: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Canister query failed: {result.stderr}")
            return jsonify({
                "success": False,
                "error": result.stderr
            }), 500
        
        # Parse the JSON response directly
        try:
            parsed_result = json.loads(result.stdout)
            return jsonify({
                "success": True,
                "result": parsed_result
            })
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            return jsonify({
                "success": False,
                "error": f"Failed to parse response as JSON: {str(e)}",
                "raw_result": result.stdout
            }), 500
    
    except Exception as e:
        logger.error(f"Error querying canister: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/ask', methods=['POST'])
def ask():

    try:
        """Ask a custom question about a realm."""
        data = request.json or {}
        
        # Required parameters
        realm_canister_id = data.get('realm_canister_id')
        if not realm_canister_id:
            # Try to get realm ID from environment variable
            realm_canister_id = os.environ.get('ASHOKA_REALM_ID')
            if not realm_canister_id:
                return jsonify({"success": False, "error": "realm_canister_id is required and ASHOKA_REALM_ID environment variable is not set"}), 400
            logger.info(f"Using realm canister ID from environment: {realm_canister_id}")
        
        question = data.get('question')
        if not question:
            return jsonify({"success": False, "error": "question is required"}), 400
        
        # Optional parameters
        ollama_url = data.get('ollama_url', 'http://localhost:11434')
        
        logger.info(f"API: Asking question about realm {realm_canister_id}")
        
        # Build command with named arguments
        command = ['python', 'cli/main.py', 'ask', '--realm-id', realm_canister_id, '--ollama-url', ollama_url, question]
        logger.info(f'Command: {command}')
        
        if str(os.environ.get('ASHOKA_USE_LLM')).lower() == 'true':

            logger.info('Using LLM')

            result = subprocess.run(command, capture_output=True, text=True)

            logger.info(f'LLM result: {result}')
            logger.info(f'LLM result stdout: {result.stdout}')
            logger.info(f'LLM result stderr: {result.stderr}')
            
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
    app.run(host='0.0.0.0', port=5000, debug=False)
