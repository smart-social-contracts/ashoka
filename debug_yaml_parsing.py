#!/usr/bin/env python3
"""
Debug YAML parsing issue with the workflow file.
"""

import yaml
from pathlib import Path

def debug_yaml_parsing():
    workflow_path = Path('.github/workflows/ci-cd-rag.yml')
    
    print("=== Debugging YAML Parsing Issue ===\n")
    
    if not workflow_path.exists():
        print(f"❌ Workflow file not found: {workflow_path}")
        return
    
    with open(workflow_path, 'r') as f:
        raw_content = f.read()
    
    print("📄 Raw file content (first 200 chars):")
    print(repr(raw_content[:200]))
    print()
    
    if raw_content.startswith('\ufeff'):
        print("⚠️  File has BOM (Byte Order Mark)")
    
    try:
        workflow = yaml.safe_load(raw_content)
        print("✅ YAML parsed successfully")
        print(f"Type of parsed object: {type(workflow)}")
        
        if workflow is None:
            print("❌ Parsed workflow is None")
            return
        
        print(f"Top-level keys: {list(workflow.keys()) if isinstance(workflow, dict) else 'Not a dict'}")
        
        if 'on' in workflow:
            print(f"✅ 'on' key found: {workflow['on']}")
            print(f"Type of 'on' value: {type(workflow['on'])}")
        else:
            print("❌ 'on' key not found in parsed YAML")
            print("Available keys:", list(workflow.keys()) if isinstance(workflow, dict) else "None")
        
        lines = raw_content.split('\n')
        for i, line in enumerate(lines[:20], 1):
            if 'on:' in line:
                print(f"Line {i}: {repr(line)}")
                
    except yaml.YAMLError as e:
        print(f"❌ YAML parsing error: {e}")
        print(f"Error position: {e.problem_mark if hasattr(e, 'problem_mark') else 'Unknown'}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    debug_yaml_parsing()
