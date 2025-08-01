#!/usr/bin/env python3
"""
Ashoka API - Simple HTTP service for AI governance advice
"""
import json
import requests
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from pathlib import Path
import traceback
import threading
import subprocess
import uuid
import os
from database.db_client import DatabaseClient

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Load Ashoka persona once at startup
PERSONA = (Path(__file__).parent / "prompts" / "governor_init.txt").read_text()

# Initialize database client
db_client = DatabaseClient()

# In-memory test status storage
test_jobs = {}

def build_prompt(user_principal, realm_principal, question):
    """Build complete prompt with persona + history + question"""
    history = db_client.get_conversation_history(user_principal, realm_principal)
    
    # Build conversation history text
    history_text = ""
    for msg in history:
        history_text += f"User: {msg['question']}\nAshoka: {msg['response']}\n\n"
    
    # Complete prompt
    prompt = f"{PERSONA}\n\n{history_text}User: {question}\nAshoka:"
    return prompt

def save_to_conversation(user_principal, realm_principal, question, answer, prompt=None):
    """Save Q&A to conversation history"""
    db_client.store_conversation(user_principal, realm_principal, question, answer, prompt)

@app.route('/api/ask', methods=['POST'])
def ask():
    print("Received ask request")
    print(request.json)
    
    """Main endpoint for asking Ashoka questions"""
    data = request.json
    user_principal = data.get('user_principal')
    realm_principal = data.get('realm_principal') 
    question = data.get('question')
    ollama_url = data.get('ollama_url', 'http://localhost:11434')
    
    if not all([user_principal, realm_principal, question]):
        return jsonify({"error": "Missing required fields"}), 400
    
    # Build complete prompt
    prompt = build_prompt(user_principal, realm_principal, question)
    
    # Check if streaming is requested
    stream = data.get('stream', False)
    
    # Send to Ollama
    try:
        if stream:
            return Response(stream_response(ollama_url, prompt, user_principal, realm_principal, question), 
                          mimetype='text/plain')
        else:
            response = requests.post(f"{ollama_url}/api/generate", json={
                "model": "llama3.2:1b",
                "prompt": prompt,
                "stream": False
            })
            answer = response.json()['response']
            
            # Save to conversation history
            save_to_conversation(user_principal, realm_principal, question, answer, prompt)
            
            return jsonify({
                "success": True,
                "answer": answer
            })
    except Exception as e:
        print(f"Error: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

def stream_response(ollama_url, prompt, user_principal, realm_principal, question):
    """Generator function for streaming responses"""
    try:
        response = requests.post(f"{ollama_url}/api/generate", json={
            "model": "llama3.2:1b",
            "prompt": prompt,
            "stream": True
        }, stream=True)
        
        full_answer = ""
        for line in response.iter_lines():
            if line:
                data = json.loads(line.decode('utf-8'))
                if 'response' in data:
                    chunk = data['response']
                    full_answer += chunk
                    yield chunk
                    
                if data.get('done', False):
                    # Save complete answer to conversation history
                    save_to_conversation(user_principal, realm_principal, question, full_answer, prompt)
                    break
    except Exception as e:
        yield f"Error: {str(e)}"

def run_test_background(test_id):
    """Run test in background thread"""
    try:
        test_jobs[test_id]['status'] = 'running'
        test_jobs[test_id]['output'] = 'Starting test execution...\n'
        
        # Run the test_runner.py script with real-time output
        process = subprocess.Popen(
            ['./test_runner.sh'],  # -u for unbuffered output
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=0,  # Unbuffered
            universal_newlines=True,
            env=dict(os.environ, PYTHONUNBUFFERED='1')  # Force unbuffered
        )
        
        output_lines = []
        for line in process.stdout:
            output_lines.append(line)
            test_jobs[test_id]['output'] = ''.join(output_lines)
        
        process.wait(timeout=300)  # 5 minute timeout
        
        if process.returncode == 0:
            test_jobs[test_id]['status'] = 'success'
        else:
            test_jobs[test_id]['status'] = 'failed'
            
    except subprocess.TimeoutExpired:
        test_jobs[test_id]['status'] = 'failed'
        test_jobs[test_id]['output'] += '\nTest timed out after 5 minutes'
        if 'process' in locals():
            process.kill()
    except Exception as e:
        test_jobs[test_id]['status'] = 'failed'
        test_jobs[test_id]['output'] += f'\nError: {str(e)}'

@app.route('/start-test', methods=['POST'])
def start_test():
    """Start CI test in background"""
    test_id = str(uuid.uuid4())
    
    # Initialize test job
    test_jobs[test_id] = {
        'status': 'pending',
        'output': ''
    }
    
    # Start background thread
    thread = threading.Thread(target=run_test_background, args=(test_id,))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'test_id': test_id,
        'status': 'pending'
    })

@app.route('/test-status/<test_id>', methods=['GET'])
def test_status(test_id):
    """Get test status"""
    if test_id not in test_jobs:
        return jsonify({'error': 'Test ID not found'}), 404
    
    job = test_jobs[test_id]
    return jsonify({
        'test_id': test_id,
        'status': job['status'],
        'output': job['output']
    })

@app.route('/test-results/<test_id>', methods=['GET'])
def test_results(test_id):
    """Get detailed test results"""
    if test_id not in test_jobs:
        return jsonify({'error': 'Test ID not found'}), 404
    
    # Check if test is completed
    job = test_jobs[test_id]
    if job['status'] not in ['success', 'failed']:
        return jsonify({'error': 'Test not completed yet'}), 400
    
    # Try to read test_results.json file
    try:
        results_file = Path(__file__).parent / 'test_results.json'
        if results_file.exists():
            with open(results_file, 'r') as f:
                results_data = json.load(f)
            return jsonify(results_data)
        else:
            return jsonify({'error': 'Test results file not found'}), 404
    except Exception as e:
        return jsonify({'error': f'Failed to read test results: {str(e)}'}), 500

@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
