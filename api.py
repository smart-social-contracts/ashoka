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
import time
import atexit
from database.db_client import DatabaseClient

def log(message):
    """Helper function to print with flush=True for better logging"""
    print(message, flush=True)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Load Ashoka persona once at startup
PERSONA = (Path(__file__).parent / "prompts" / "persona.txt").read_text()

# Model configuration with fallback
ASHOKA_DEFAULT_MODEL = os.getenv('ASHOKA_DEFAULT_MODEL', 'llama3.2:1b')

# Initialize database client
db_client = DatabaseClient()

# In-memory test status storage
test_jobs = {}

# Inactivity timeout configuration
INACTIVITY_TIMEOUT_SECONDS = int(os.getenv('INACTIVITY_TIMEOUT_SECONDS', '0'))  # Default: disabled
INACTIVITY_CHECK_INTERVAL_SECONDS = int(os.getenv('INACTIVITY_CHECK_INTERVAL_SECONDS', '60'))
last_activity_time = time.time()
inactivity_monitor_thread = None
shutdown_initiated = False

def build_prompt(user_principal, realm_principal, question, realm_status=None):
    """Build complete prompt with persona + history + question + realm context"""
    # Try to get conversation history, but don't fail if database is unavailable
    history_text = ""
    try:
        history = db_client.get_conversation_history(user_principal, realm_principal)
        # Build conversation history text
        for msg in history:
            history_text += f"User: {msg['question']}\nAshoka: {msg['response']}\n\n"
    except Exception as e:
        log(f"Error: Could not load conversation history: {e}")
        history_text = ""
    
    # Build realm context if provided
    realm_context = ""
    if realm_status:
        realm_context = f"\n\nCURRENT REALM STATUS:\n{json.dumps(realm_status, indent=2)}\n\n"
    
    # Complete prompt
    prompt = f"{PERSONA}{realm_context}\n\nCONVERSATION_HISTORY:\n{history_text}\n\nUser: {question}\nAshoka:"
    return prompt

def save_to_conversation(user_principal, realm_principal, question, answer, prompt=None):
    """Save Q&A to conversation history"""
    try:
        db_client.store_conversation(user_principal, realm_principal, question, answer, prompt)
    except Exception as e:
        log(f"Error: Could not save conversation to database: {e}")

def update_activity():
    """Update the last activity timestamp"""
    global last_activity_time
    last_activity_time = time.time()
    log(f"Activity updated at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_activity_time))}")

def monitor_inactivity():
    """Background thread to monitor inactivity and exit script if timeout reached"""
    global shutdown_initiated
    
    while not shutdown_initiated:
        try:
            time.sleep(INACTIVITY_CHECK_INTERVAL_SECONDS)  # Check every minute
            
            if shutdown_initiated:
                break
                
            current_time = time.time()
            inactive_duration = current_time - last_activity_time
            
            log(f"Inactivity check: {inactive_duration:.0f}s since last activity (timeout: {INACTIVITY_TIMEOUT_SECONDS}s)")
            
            if INACTIVITY_TIMEOUT_SECONDS > 0 and inactive_duration >= INACTIVITY_TIMEOUT_SECONDS:
                log(f"⚠️  INACTIVITY TIMEOUT REACHED! Inactive for {inactive_duration:.0f} seconds")
                log("🛑 Exiting Python script due to inactivity...")
                
                # Exit the monitoring thread and the entire script
                shutdown_initiated = True
                os._exit(0)  # Force exit the entire Python process
                
        except Exception as e:
            log(f"Error in inactivity monitor: {e}")
            time.sleep(INACTIVITY_CHECK_INTERVAL_SECONDS)  # Continue monitoring even if there's an error

def start_inactivity_monitor():
    """Start the inactivity monitoring thread"""
    global inactivity_monitor_thread
    
    if INACTIVITY_TIMEOUT_SECONDS > 0:
        if inactivity_monitor_thread is None or not inactivity_monitor_thread.is_alive():
            log(f"🕐 Starting inactivity monitor (timeout: {INACTIVITY_TIMEOUT_SECONDS}s = {INACTIVITY_TIMEOUT_SECONDS/3600:.1f}h)")
            inactivity_monitor_thread = threading.Thread(target=monitor_inactivity, daemon=True)
            inactivity_monitor_thread.start()
            
            # Register cleanup function
            atexit.register(lambda: globals().update({'shutdown_initiated': True}))
    else:
        log("🕐 Inactivity timeout disabled (INACTIVITY_TIMEOUT_SECONDS=0)")

def stop_inactivity_monitor():
    """Stop the inactivity monitoring thread"""
    global shutdown_initiated
    shutdown_initiated = True
    log("🛑 Inactivity monitor stopped")

@app.route('/api/ask', methods=['POST'])
def ask():
    # Update activity timestamp
    update_activity()
    
    log("Received ask request")
    log(request.json)
    
    """Main endpoint for asking Ashoka questions"""
    data = request.json
    user_principal = data.get('user_principal') or ""
    realm_principal = data.get('realm_principal') or ""
    question = data.get('question')
    realm_status = data.get('realm_status')  # Optional realm context
    ollama_url = data.get('ollama_url', 'http://localhost:11434')
    
    # Validate required fields - user_principal can be empty for anonymous users
    if not question:
        return jsonify({"error": "Missing required fields: a question is required"}), 400
    
    # Build complete prompt with realm context
    prompt = build_prompt(user_principal, realm_principal, question, realm_status)
    
    # Log the complete prompt for debugging
    log("\n" + "="*80)
    log("COMPLETE PROMPT SENT TO OLLAMA:")
    log("="*80)
    log(prompt)
    log("="*80 + "\n")
    
    # Check if streaming is requested
    stream = data.get('stream', False)
    
    # Send to Ollama
    try:
        if stream:
            return Response(stream_response(ollama_url, prompt, user_principal, realm_principal, question), 
                          mimetype='text/plain')
        else:
            response = requests.post(f"{ollama_url}/api/generate", json={
                "model": ASHOKA_DEFAULT_MODEL,
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
        log(f"Error: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

def stream_response(ollama_url, prompt, user_principal, realm_principal, question):
    """Generator function for streaming responses"""
    try:
        response = requests.post(f"{ollama_url}/api/generate", json={
            "model": ASHOKA_DEFAULT_MODEL,
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
        
        # Clean up database before running tests
        test_jobs[test_id]['output'] += 'Cleaning up database...\n'
        cleanup_process = subprocess.run(
            ['./scripts/cleanup_db.sh'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if cleanup_process.returncode == 0:
            test_jobs[test_id]['output'] += cleanup_process.stdout
        else:
            test_jobs[test_id]['output'] += f'Database cleanup failed: {cleanup_process.stderr}\n'
            # DO NOT continue with tests even if cleanup fails
            raise Exception("Database cleanup failed")
        
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
        test_jobs[test_id]['output'] += f'\nERROR: {str(e)}'

@app.route('/start-test', methods=['POST'])
def start_test():
    """Start CI test in background"""
    # Update activity timestamp
    update_activity()
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
    # Update activity timestamp
    update_activity()
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
    # Update activity timestamp
    update_activity()
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

@app.route('/suggestions', methods=['GET'])
def get_suggestions():
    """Get LLM chat suggestions"""
    # Update activity timestamp
    update_activity()
    
    # Return contextual suggestions for the LLM chat interface
    suggestions = [
        "What is a realm?",
        "What is an AI governance assistant?", 
        "Why should I join this realm?"
    ]
    
    return jsonify({
        "suggestions": suggestions
    })

@app.route('/', methods=['GET'])
def health():
    # Update activity timestamp
    update_activity()
    
    return jsonify({
        "status": "ok",
        "inactivity_timeout_seconds": INACTIVITY_TIMEOUT_SECONDS,
        "seconds_since_last_activity": int(time.time() - last_activity_time) if INACTIVITY_TIMEOUT_SECONDS > 0 else None
    })

if __name__ == '__main__':
    # Start inactivity monitoring if enabled
    start_inactivity_monitor()
    
    try:
        app.run(host='0.0.0.0', port=5000)
    finally:
        # Ensure cleanup on exit
        stop_inactivity_monitor()
