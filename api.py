#!/usr/bin/env python3
"""
Ashoka API - Simple HTTP service for AI governance advice
"""
import json
import requests
from flask import Flask, request, jsonify
from pathlib import Path
import traceback

app = Flask(__name__)

# Load Ashoka persona once at startup
PERSONA = (Path(__file__).parent / "prompts" / "governor_init.txt").read_text()

# Simple in-memory conversation storage (user_realm -> messages)
conversations = {}

def get_conversation_key(user_principal, realm_principal):
    return f"{user_principal}:{realm_principal}"

def build_prompt(user_principal, realm_principal, question):
    """Build complete prompt with persona + history + question"""
    key = get_conversation_key(user_principal, realm_principal)
    history = conversations.get(key, [])
    
    # Build conversation history text
    history_text = ""
    for msg in history:
        history_text += f"User: {msg['question']}\nAshoka: {msg['answer']}\n\n"
    
    # Complete prompt
    prompt = f"{PERSONA}\n\n{history_text}User: {question}\nAshoka:"
    return prompt

def save_to_conversation(user_principal, realm_principal, question, answer):
    """Save Q&A to conversation history"""
    key = get_conversation_key(user_principal, realm_principal)
    if key not in conversations:
        conversations[key] = []
    conversations[key].append({"question": question, "answer": answer})

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
    
    # Send to Ollama
    try:
        response = requests.post(f"{ollama_url}/api/generate", json={
            "model": "llama3.2:1b",
            "prompt": prompt,
            "stream": False
        })
        print('response.json(): ', response.json())
        answer = response.json()['response']
        
        # Save to conversation history
        save_to_conversation(user_principal, realm_principal, question, answer)
        
        return jsonify({
            "success": True,
            "answer": answer
        })
    except Exception as e:
        print(f"Error: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
