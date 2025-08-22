#!/usr/bin/env python3
"""
Persona Manager - Handles multiple AI personas for the governance system
"""
import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class PersonaManager:
    """Manages multiple AI personas for the governance system"""
    
    def __init__(self, personas_dir: str = None):
        """Initialize the persona manager
        
        Args:
            personas_dir: Directory containing persona files. Defaults to prompts/personas/
        """
        if personas_dir is None:
            self.personas_dir = Path(__file__).parent / "prompts" / "personas"
        else:
            self.personas_dir = Path(personas_dir)
        
        # Ensure personas directory exists
        self.personas_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache for loaded personas
        self._personas_cache: Dict[str, Dict] = {}
        self._last_modified: Dict[str, float] = {}
        
        # Default persona (backward compatibility)
        self.default_persona = "ashoka"
        
        # Initialize personas
        self._initialize_personas()
    
    def _initialize_personas(self):
        """Initialize personas directory and migrate existing persona.txt if needed"""
        # Check if old persona.txt exists and migrate it
        old_persona_file = Path(__file__).parent / "prompts" / "persona.txt"
        ashoka_persona_file = self.personas_dir / "ashoka.txt"
        
        if old_persona_file.exists() and not ashoka_persona_file.exists():
            # Migrate old persona.txt to ashoka.txt
            ashoka_persona_file.write_text(old_persona_file.read_text())
            print(f"Migrated {old_persona_file} to {ashoka_persona_file}")
    
    def load_persona(self, persona_name: str) -> Optional[str]:
        """Load a persona by name
        
        Args:
            persona_name: Name of the persona (without .txt extension)
            
        Returns:
            Persona content as string, or None if not found
        """
        persona_file = self.personas_dir / f"{persona_name}.txt"
        
        if not persona_file.exists():
            return None
        
        # Check if we need to reload (file modified)
        try:
            last_modified = persona_file.stat().st_mtime
            if (persona_name not in self._personas_cache or 
                self._last_modified.get(persona_name, 0) < last_modified):
                
                content = persona_file.read_text(encoding='utf-8').strip()
                self._personas_cache[persona_name] = {
                    'content': content,
                    'file_path': str(persona_file),
                    'last_modified': last_modified
                }
                self._last_modified[persona_name] = last_modified
                
            return self._personas_cache[persona_name]['content']
            
        except Exception as e:
            print(f"Error loading persona {persona_name}: {e}")
            return None
    
    def get_persona_or_default(self, persona_name: Optional[str] = None) -> Tuple[str, str]:
        """Get persona content with fallback to default
        
        Args:
            persona_name: Requested persona name, or None for default
            
        Returns:
            Tuple of (actual_persona_name_used, persona_content)
        """
        if not persona_name:
            persona_name = self.default_persona
        
        content = self.load_persona(persona_name)
        if content is not None:
            return persona_name, content
        
        # Fallback to default persona
        if persona_name != self.default_persona:
            content = self.load_persona(self.default_persona)
            if content is not None:
                return self.default_persona, content
        
        # Last resort: return empty persona with warning
        return "unknown", "You are an AI assistant. Please provide helpful responses."
    
    def list_available_personas(self) -> List[Dict[str, any]]:
        """List all available personas with metadata
        
        Returns:
            List of persona metadata dictionaries
        """
        personas = []
        
        if not self.personas_dir.exists():
            return personas
        
        for persona_file in self.personas_dir.glob("*.txt"):
            persona_name = persona_file.stem
            try:
                stat = persona_file.stat()
                content = persona_file.read_text(encoding='utf-8')
                
                # Extract first line as description if it looks like a description
                lines = content.strip().split('\n')
                description = ""
                if lines and (lines[0].startswith('You are') or lines[0].startswith('#')):
                    description = lines[0].replace('#', '').strip()[:100] + "..." if len(lines[0]) > 100 else lines[0].replace('#', '').strip()
                
                personas.append({
                    'name': persona_name,
                    'description': description,
                    'file_path': str(persona_file),
                    'size_bytes': stat.st_size,
                    'last_modified': stat.st_mtime,
                    'is_default': persona_name == self.default_persona
                })
                
            except Exception as e:
                print(f"Error reading persona {persona_name}: {e}")
                continue
        
        # Sort by name, with default first
        personas.sort(key=lambda x: (not x['is_default'], x['name']))
        return personas
    
    def validate_persona(self, persona_name: str) -> Dict[str, any]:
        """Validate a persona file
        
        Args:
            persona_name: Name of the persona to validate
            
        Returns:
            Validation result dictionary
        """
        result = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'stats': {}
        }
        
        content = self.load_persona(persona_name)
        if content is None:
            result['errors'].append(f"Persona '{persona_name}' not found")
            return result
        
        # Basic validation checks
        if len(content.strip()) < 50:
            result['warnings'].append("Persona content is very short (< 50 characters)")
        
        if len(content) > 10000:
            result['warnings'].append("Persona content is very long (> 10,000 characters)")
        
        lines = content.split('\n')
        if not any(line.strip().startswith('You are') for line in lines[:5]):
            result['warnings'].append("Persona doesn't start with 'You are...' in first 5 lines")
        
        # Statistics
        result['stats'] = {
            'character_count': len(content),
            'word_count': len(content.split()),
            'line_count': len(lines),
            'non_empty_lines': len([l for l in lines if l.strip()])
        }
        
        # If no errors, mark as valid
        if not result['errors']:
            result['valid'] = True
        
        return result
    
    def create_persona(self, persona_name: str, content: str) -> bool:
        """Create a new persona file
        
        Args:
            persona_name: Name for the new persona
            content: Persona content
            
        Returns:
            True if created successfully, False otherwise
        """
        if not persona_name or not content.strip():
            return False
        
        # Sanitize persona name
        safe_name = "".join(c for c in persona_name if c.isalnum() or c in "-_").lower()
        if not safe_name:
            return False
        
        persona_file = self.personas_dir / f"{safe_name}.txt"
        
        try:
            persona_file.write_text(content.strip(), encoding='utf-8')
            # Clear cache for this persona
            if safe_name in self._personas_cache:
                del self._personas_cache[safe_name]
            return True
        except Exception as e:
            print(f"Error creating persona {safe_name}: {e}")
            return False
    
    def delete_persona(self, persona_name: str) -> bool:
        """Delete a persona file
        
        Args:
            persona_name: Name of the persona to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        if persona_name == self.default_persona:
            return False  # Cannot delete default persona
        
        persona_file = self.personas_dir / f"{persona_name}.txt"
        
        try:
            if persona_file.exists():
                persona_file.unlink()
                # Clear cache
                if persona_name in self._personas_cache:
                    del self._personas_cache[persona_name]
                if persona_name in self._last_modified:
                    del self._last_modified[persona_name]
                return True
            return False
        except Exception as e:
            print(f"Error deleting persona {persona_name}: {e}")
            return False
