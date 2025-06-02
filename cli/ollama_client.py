"""
Ollama Client Module - Handles interactions with the Ollama API for LLM inference
"""

import json
import logging
import os
import requests
from typing import Dict
from constants import DEFAULT_MODEL

logger = logging.getLogger("ashoka.ollama")
logger.setLevel(logging.DEBUG)

class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, api_url: str, model: str = None):
        """Initialize the Ollama client."""
        self.api_url = api_url.rstrip("/")
        # Get model from environment variable first, then fall back to parameter or DEFAULT_MODEL
        self.model = model or os.environ.get('ASHOKA_MODEL') or DEFAULT_MODEL
        logger.info(f"OllamaClient initialized with URL: {api_url} and model: {self.model}")
    
    def send_prompt(self, prompt: str) -> str:
        """Send a prompt to the Ollama API and get the response."""
        try:
            url = f"{self.api_url}/api/generate"
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
            
            logger.debug(f"Sending prompt to Ollama: {prompt[:100]}...")
            logger.debug(f"API Request URL: {url}")
            logger.debug(f"API Request Payload: {payload}")
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            logger.debug(f"API Response Status Code: {response.status_code}")
            logger.debug(f"API Response Headers: {response.headers}")
            logger.debug(f"API Response Content: {response.text[:1000]}...")
            
            result = response.json()
            return result.get("response", "")
            
        except requests.RequestException as e:
            logger.error(f"Error communicating with Ollama API: {str(e)}")
            return f"Error: {str(e)}"
    
    def parse_proposal(self, response: str) -> Dict[str, str]:
        """Parse the JSON proposal from the model's response."""
        try:
            # Log first part of response for debugging
            logger.debug(f"Response from LLM (first 200 chars): {response[:200]}...")
            
            # Extract JSON object if embedded in text
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                
                # Attempt to fix common JSON issues
                json_str = self._fix_json_string(json_str)
                
                proposal = json.loads(json_str)
                
                # Validate and provide defaults for required fields
                proposal["title"] = proposal.get("title", "Untitled Proposal")
                proposal["content"] = proposal.get("content", "No content provided")
                proposal["summary"] = proposal.get("summary", "No summary provided")
                proposal["tags"] = proposal.get("tags", [])
                
                return proposal
            else:
                # Fallback: If no JSON structure found, create one from the text
                logger.warning("No JSON structure found in response, creating fallback structure")
                return {
                    "title": "AI-Generated Proposal",
                    "content": response,
                    "summary": response[:200] + "...",
                    "tags": ["auto-generated"]
                }
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error parsing proposal: {str(e)}")
            # Instead of raising an error, return a fallback proposal
            return {
                "title": "Error-Recovery Proposal",
                "content": response,
                "summary": "Generated content could not be parsed as JSON",
                "tags": ["error-recovery"]
            }
    
    def _fix_json_string(self, json_str: str) -> str:
        """Apply fixes to common JSON formatting issues."""
        # Initial debugging
        logger.debug(f"Original JSON string (first 100 chars): {json_str[:100]}...")
        
        # First, attempt to sanitize invalid escape sequences
        sanitized = ""
        i = 0
        while i < len(json_str):
            if json_str[i] == '\\' and i + 1 < len(json_str):
                next_char = json_str[i + 1]
                # Valid escape sequences in JSON: \", \\, \/, \b, \f, \n, \r, \t, \uXXXX
                if next_char in ('"', '\\', '/', 'b', 'f', 'n', 'r', 't', 'u'):
                    sanitized += json_str[i:i+2]
                else:
                    # For invalid escape sequences, escape the backslash itself
                    sanitized += '\\\\' + next_char
                i += 2
            else:
                sanitized += json_str[i]
                i += 1
                
        # Now process quotes and structure
        fixed = ""
        in_string = False
        prev_char = None
        
        for char in sanitized:
            if char == '"' and prev_char != '\\':
                in_string = not in_string
            elif char == "'" and not in_string:
                char = '"'
                
            fixed += char
            prev_char = char
        
        # Handle unterminated strings by adding missing quotes
        quotes_count = fixed.count('"')
        if quotes_count % 2 != 0:
            fixed += '"'
            
        # Ensure proper array terminators
        bracket_count = fixed.count('[') - fixed.count(']')
        if bracket_count > 0:
            fixed += ']' * bracket_count
            
        # Ensure proper object terminators
        brace_count = fixed.count('{') - fixed.count('}')
        if brace_count > 0:
            fixed += '}' * brace_count
            
        # Last resort - try to recover any JSON by finding valid JSON substrings
        if '{' in fixed and '}' in fixed:
            try:
                json.loads(fixed)
            except json.JSONDecodeError as e:
                # If we still have JSON errors, try a more aggressive approach
                # Extract just the content between the outermost braces
                start = fixed.find('{')
                end = fixed.rfind('}')
                if start >= 0 and end > start:
                    substring = fixed[start:end+1]
                    try:
                        # Test if this is valid JSON
                        json.loads(substring)
                        fixed = substring
                    except json.JSONDecodeError:
                        # If still invalid, fall back to a minimal valid JSON
                        fixed = '{"title":"Sanitized Proposal","content":"Content was unparseable"}'                
        
        return fixed
