"""
Ollama Client Module - Handles interactions with the Ollama API for LLM inference
"""

import json
import logging
import requests
from typing import Dict

logger = logging.getLogger("oshaka.ollama")

class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, api_url: str, model: str = "llama2"):
        """Initialize the Ollama client."""
        self.api_url = api_url.rstrip("/")
        self.model = model
        logger.info(f"OllamaClient initialized with URL: {api_url} and model: {model}")
    
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
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "")
            
        except requests.RequestException as e:
            logger.error(f"Error communicating with Ollama API: {str(e)}")
            return f"Error: {str(e)}"
    
    def parse_proposal(self, response: str) -> Dict[str, str]:
        """Parse the JSON proposal from the model's response."""
        try:
            # Extract JSON object if embedded in text
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                proposal = json.loads(json_str)
                
                # Validate required fields
                if "title" not in proposal or "content" not in proposal:
                    raise ValueError("Proposal must contain 'title' and 'content' fields")
                
                return proposal
            else:
                raise ValueError("No JSON object found in response")
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error parsing proposal: {str(e)}")
            raise ValueError(f"Failed to parse proposal: {str(e)}")
