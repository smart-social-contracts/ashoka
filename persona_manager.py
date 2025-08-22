#!/usr/bin/env python3
"""
PersonaManager - Manages AI personas for the Ashoka governance assistant
"""
import os
from pathlib import Path


class PersonaManager:
    """Manages different AI personas for contextual responses"""
    
    def __init__(self):
        self.default_persona = "ashoka"
        self.personas_dir = Path(__file__).parent / "prompts" / "personas"
        self.base_persona_file = Path(__file__).parent / "prompts" / "persona.txt"
        self._persona_cache = {}
        self._load_personas()
    
    def _load_personas(self):
        """Load all available personas from the personas directory"""
        try:
            # Load base persona content
            if self.base_persona_file.exists():
                with open(self.base_persona_file, 'r', encoding='utf-8') as f:
                    self._persona_cache['base'] = f.read().strip()
            
            # Load individual personas
            if self.personas_dir.exists():
                for persona_file in self.personas_dir.glob("*.txt"):
                    persona_name = persona_file.stem
                    with open(persona_file, 'r', encoding='utf-8') as f:
                        self._persona_cache[persona_name] = f.read().strip()
        except Exception as e:
            print(f"Warning: Error loading personas: {e}")
    
    def get_available_personas(self):
        """Get list of available persona names"""
        return [name for name in self._persona_cache.keys() if name != 'base']
    
    def get_persona_content(self, persona_name):
        """Get the content for a specific persona"""
        if not persona_name or persona_name not in self._persona_cache:
            return None
        return self._persona_cache[persona_name]
    
    def get_persona_or_default(self, persona_name=None):
        """
        Get persona content with fallback to default
        Returns tuple of (actual_persona_name, persona_content)
        """
        # If no persona specified, use default
        if not persona_name:
            persona_name = self.default_persona
        
        # Try to get the requested persona
        persona_content = self.get_persona_content(persona_name)
        
        # If persona not found, fall back to default
        if persona_content is None:
            persona_name = self.default_persona
            persona_content = self.get_persona_content(persona_name)
            
            # If default also not found, use base persona
            if persona_content is None:
                persona_name = "base"
                persona_content = self.get_persona_content("base")
                
                # If even base not found, use minimal fallback
                if persona_content is None:
                    persona_name = "assistant"
                    persona_content = "You are a helpful AI assistant for decentralized governance."
        
        return persona_name, persona_content
    
    def persona_exists(self, persona_name):
        """Check if a persona exists"""
        return persona_name in self._persona_cache
    
    def reload_personas(self):
        """Reload all personas from disk"""
        self._persona_cache.clear()
        self._load_personas()
