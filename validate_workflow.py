#!/usr/bin/env python3
"""
Validate the updated workflow file to ensure it's properly structured.
"""

import yaml
import json
from pathlib import Path

def validate_workflow():
    workflow_path = Path('.github/workflows/ci-cd-rag.yml')
    
    if not workflow_path.exists():
        print(f"❌ Workflow file not found: {workflow_path}")
        return False
    
    print(f"✅ Workflow file exists: {workflow_path}")
    
    try:
        with open(workflow_path, 'r') as f:
            workflow = yaml.safe_load(f)
        
        print("✅ YAML syntax is valid")
        
        required_keys = ['name', 'on', 'jobs']
        all_good = True
        for key in required_keys:
            if key in workflow:
                print(f"✅ Has required key: {key}")
            else:
                print(f"❌ Missing required key: {key}")
                all_good = False
        
        if 'on' in workflow:
            triggers = workflow['on']
            print(f"✅ Triggers configured: {list(triggers.keys())}")
            
            if 'pull_request' in triggers:
                print(f"✅ Pull request trigger configured")
            else:
                print("❌ No pull_request trigger found")
                all_good = False
                
            if 'workflow_dispatch' in triggers:
                print(f"✅ Manual workflow_dispatch trigger configured")
            else:
                print("❌ No workflow_dispatch trigger found")
                all_good = False
        
        if 'jobs' in workflow:
            jobs = workflow['jobs']
            print(f"✅ Jobs defined: {list(jobs.keys())}")
            
            for job_name, job_config in jobs.items():
                print(f"\n📋 Job: {job_name}")
                if 'runs-on' in job_config:
                    print(f"  ✅ runs-on: {job_config['runs-on']}")
                else:
                    print(f"  ❌ Missing runs-on")
                    all_good = False
                
                if 'permissions' in job_config:
                    print(f"  ✅ permissions: {job_config['permissions']}")
                else:
                    print(f"  ❌ Missing permissions")
                    all_good = False
                
                if 'steps' in job_config:
                    print(f"  ✅ {len(job_config['steps'])} steps defined")
                else:
                    print(f"  ❌ No steps defined")
                    all_good = False
        
        print(f"\n🔍 Workflow validation summary:")
        print(f"  Name: {workflow.get('name', 'MISSING')}")
        print(f"  Triggers: {list(workflow.get('on', {}).keys())}")
        print(f"  Jobs: {list(workflow.get('jobs', {}).keys())}")
        
        return all_good
        
    except yaml.YAMLError as e:
        print(f"❌ YAML syntax error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error validating workflow: {e}")
        return False

if __name__ == "__main__":
    success = validate_workflow()
    if success:
        print("\n✅ Workflow file is valid and ready for GitHub Actions!")
    else:
        print("\n❌ Workflow file has issues that need to be fixed!")
