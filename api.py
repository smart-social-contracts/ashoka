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
from realm_status_service import RealmStatusService
from realm_status_scheduler import get_scheduler, start_scheduler, stop_scheduler


def log(message):
    """Helper function to print with flush=True for better logging"""
    print(message, flush=True)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Load Ashoka persona once at startup
PERSONA = (Path(__file__).parent / "prompts" / "persona.txt").read_text()

# Model configuration with fallback
ASHOKA_DEFAULT_MODEL = os.getenv('ASHOKA_DEFAULT_MODEL', 'llama3.2:1b')

# Initialize database client and realm status service
db_client = DatabaseClient()
realm_status_service = RealmStatusService(db_client)

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

                # Stop this pod using pod_manager directly
                try:
                    log("🛑 Stopping pod due to inactivity timeout...")
                    from pod_manager import PodManager
                    pod_manager = PodManager(verbose=True)
                    success = pod_manager.stop_pod(os.getenv('POD_TYPE'))
                    
                    if success:
                        log("✅ Pod stopped successfully")
                    else:
                        log("⚠️ Pod stop failed")
                except Exception as e:
                    log(f"❌ Error stopping pod: {e}")
                
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
    
    # If realm_principal is provided but no realm_status, try to fetch from database
    log(f"Fetching realm status for {realm_principal}")
    log(f"Realm status: {realm_status}")
    if realm_principal and not realm_status:
        try:
            realm_status = realm_status_service.get_realm_status_summary(realm_principal)
            if realm_status:
                log(f"Retrieved realm status from database for {realm_principal}")
            else:
                log(f"No realm status found in database for {realm_principal}")
        except Exception as e:
            log(f"Error retrieving realm status from database: {e}")
            realm_status = None
    
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
    """Get LLM chat suggestions based on conversation history"""
    # Update activity timestamp
    update_activity()
    
    # Get parameters from query string
    user_principal = request.args.get('user_principal', '')
    realm_principal = request.args.get('realm_principal', '')
    ollama_url = request.args.get('ollama_url', 'http://localhost:11434')
    
    try:
        # Get conversation history for context
        history_text = ""
        try:
            history = db_client.get_conversation_history(user_principal, realm_principal)
            # Build conversation history text (last 5 exchanges for context)
            recent_history = history[-5:] if len(history) > 5 else history
            for msg in recent_history:
                history_text += f"User: {msg['question']}\nAshoka: {msg['response']}\n\n"
        except Exception as e:
            log(f"Error: Could not load conversation history for suggestions: {e}")
            history_text = ""
        
        # Create a specialized prompt for generating suggestions
        suggestions_prompt = f"""{PERSONA}

CONVERSATION_HISTORY:
{history_text}

Based on the conversation history above, generate 3 relevant follow-up questions that the user might want to ask next. The suggestions should:
1. Be natural follow-up questions based on the conversation context
2. Help the user explore related topics or dive deeper into the subject
3. Be concise and actionable (under 50 characters each)
4. Be relevant to AI governance, realms, and the Ashoka assistant's capabilities

If there's no conversation history, provide general introductory questions about realms and AI governance.

Format your response as exactly 3 questions, one per line, with no numbering or bullet points:"""

        # Send to Ollama to generate suggestions
        response = requests.post(f"{ollama_url}/api/generate", json={
            "model": ASHOKA_DEFAULT_MODEL,
            "prompt": suggestions_prompt,
            "stream": False
        })
        
        if response.status_code == 200:
            llm_response = response.json()['response'].strip()
            
            # Parse the response into individual suggestions
            suggestions = []
            lines = llm_response.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('-') and not line.startswith('*'):
                    # Clean up any numbering or formatting
                    cleaned_line = line
                    # Remove common prefixes like "1.", "2.", etc.
                    import re
                    cleaned_line = re.sub(r'^\d+\.\s*', '', cleaned_line)
                    cleaned_line = re.sub(r'^[-*]\s*', '', cleaned_line)
                    
                    if cleaned_line:
                        suggestions.append(cleaned_line)
            
            # Ensure we have exactly 3 suggestions
            if len(suggestions) < 3:
                # Add fallback suggestions if needed
                fallback_suggestions = [
                    "What is a realm?",
                    "What is an AI governance assistant?", 
                    "Why should I join this realm?"
                ]
                suggestions.extend(fallback_suggestions[len(suggestions):3])
            elif len(suggestions) > 3:
                suggestions = suggestions[:3]
            
            log(f"Generated dynamic suggestions: {suggestions}")
            
            return jsonify({
                "suggestions": suggestions
            })
        else:
            raise Exception(f"Ollama API error: {response.status_code}")
            
    except Exception as e:
        log(f"Error generating dynamic suggestions: {e}")
        # Fallback to static suggestions on error
        suggestions = [
            "What is a realm?",
            "What is an AI governance assistant?", 
            "Why should I join this realm?"
        ]
        
        return jsonify({
            "suggestions": suggestions
        })

@app.route('/api/realm-status/fetch', methods=['POST'])
def fetch_realm_status():
    """Fetch and store status for a specific realm using DFX"""
    update_activity()
    
    data = request.json
    realm_principal = data.get('realm_principal')
    realm_url = data.get('realm_url')  # Optional, will be constructed if not provided
    network = data.get('network', 'ic')  # Default to IC mainnet
    
    if not realm_principal:
        return jsonify({"error": "Missing required field: realm_principal"}), 400
    
    try:
        success = realm_status_service.fetch_and_store_realm_status(realm_principal, realm_url, network)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"Successfully fetched and stored status for realm {realm_principal} via DFX"
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Failed to fetch status for realm {realm_principal} via DFX"
            }), 500
            
    except Exception as e:
        log(f"Error fetching realm status: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/realm-status/batch-fetch', methods=['POST'])
def batch_fetch_realm_status():
    """Fetch and store status for multiple realms using DFX"""
    update_activity()
    
    data = request.json
    realms = data.get('realms', [])
    network = data.get('network', 'ic')  # Default to IC mainnet
    
    if not realms:
        return jsonify({"error": "Missing required field: realms (array of {principal, url} objects)"}), 400
    
    try:
        results = realm_status_service.fetch_multiple_realms_status(realms, network)
        
        successful_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        return jsonify({
            "success": True,
            "results": results,
            "summary": {
                "total_realms": total_count,
                "successful_fetches": successful_count,
                "failed_fetches": total_count - successful_count,
                "network": network
            }
        })
        
    except Exception as e:
        log(f"Error batch fetching realm status: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/realm-status/<realm_principal>', methods=['GET'])
def get_realm_status(realm_principal):
    """Get the latest status for a specific realm"""
    update_activity()
    
    try:
        summary = realm_status_service.get_realm_status_summary(realm_principal)
        
        if summary:
            return jsonify({
                "success": True,
                "data": summary
            })
        else:
            return jsonify({
                "success": False,
                "error": f"No status data found for realm {realm_principal}"
            }), 404
            
    except Exception as e:
        log(f"Error getting realm status: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/realm-status/<realm_principal>/history', methods=['GET'])
def get_realm_status_history(realm_principal):
    """Get status history for a specific realm"""
    update_activity()
    
    limit = request.args.get('limit', 10, type=int)
    
    try:
        history = db_client.get_realm_status_history(realm_principal, limit)
        
        return jsonify({
            "success": True,
            "data": history,
            "count": len(history)
        })
        
    except Exception as e:
        log(f"Error getting realm status history: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/realm-status/all', methods=['GET'])
def get_all_realms_status():
    """Get latest status summary for all tracked realms"""
    update_activity()
    
    try:
        summaries = realm_status_service.get_all_realms_summary()
        
        return jsonify({
            "success": True,
            "data": summaries,
            "count": len(summaries)
        })
        
    except Exception as e:
        log(f"Error getting all realms status: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/realm-status/scheduler/status', methods=['GET'])
def get_scheduler_status():
    """Get realm status scheduler information"""
    update_activity()
    
    try:
        scheduler = get_scheduler()
        status = scheduler.get_status()
        
        return jsonify({
            "success": True,
            "data": status
        })
        
    except Exception as e:
        log(f"Error getting scheduler status: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/realm-status/scheduler/start', methods=['POST'])
def start_realm_scheduler():
    """Start the realm status scheduler"""
    update_activity()
    
    try:
        scheduler = get_scheduler()
        scheduler.start()
        
        return jsonify({
            "success": True,
            "message": "Realm status scheduler started"
        })
        
    except Exception as e:
        log(f"Error starting scheduler: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/realm-status/scheduler/stop', methods=['POST'])
def stop_realm_scheduler():
    """Stop the realm status scheduler"""
    update_activity()
    
    try:
        scheduler = get_scheduler()
        scheduler.stop()
        
        return jsonify({
            "success": True,
            "message": "Realm status scheduler stopped"
        })
        
    except Exception as e:
        log(f"Error stopping scheduler: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/realm-status/scheduler/fetch-now', methods=['POST'])
def trigger_immediate_fetch():
    """Trigger an immediate status fetch for all configured realms"""
    update_activity()
    
    try:
        scheduler = get_scheduler()
        results = scheduler.fetch_now()
        
        successful_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        return jsonify({
            "success": True,
            "results": results,
            "summary": {
                "total_realms": total_count,
                "successful_fetches": successful_count,
                "failed_fetches": total_count - successful_count
            }
        })
        
    except Exception as e:
        log(f"Error triggering immediate fetch: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/realm-status/scheduler/realms', methods=['POST'])
def add_realm_to_scheduler():
    """Add a realm to the scheduler configuration"""
    update_activity()
    
    data = request.json
    realm_principal = data.get('realm_principal')
    realm_url = data.get('realm_url')
    name = data.get('name')
    
    if not realm_principal or not realm_url:
        return jsonify({"error": "Missing required fields: realm_principal and realm_url"}), 400
    
    try:
        scheduler = get_scheduler()
        success = scheduler.add_realm(realm_principal, realm_url, name)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"Added realm {realm_principal} to scheduler configuration"
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Realm {realm_principal} already exists in configuration"
            }), 400
            
    except Exception as e:
        log(f"Error adding realm to scheduler: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/realm-status/scheduler/realms/<realm_principal>', methods=['DELETE'])
def remove_realm_from_scheduler(realm_principal):
    """Remove a realm from the scheduler configuration"""
    update_activity()
    
    try:
        scheduler = get_scheduler()
        success = scheduler.remove_realm(realm_principal)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"Removed realm {realm_principal} from scheduler configuration"
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Realm {realm_principal} not found in configuration"
            }), 404
            
    except Exception as e:
        log(f"Error removing realm from scheduler: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

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
    
    # Start realm status scheduler if enabled
    start_scheduler()
    
    try:
        app.run(host='0.0.0.0', port=5000)
    finally:
        # Ensure cleanup on exit
        stop_inactivity_monitor()
        stop_scheduler()
