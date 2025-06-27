#!/usr/bin/env python3
"""
Compare our workflow with the working realms workflow to identify differences.
"""

import yaml
from pathlib import Path

def compare_workflows():
    print("=== Comparing Workflows ===\n")
    
    our_workflow_path = Path('.github/workflows/ci-cd-rag.yml')
    realms_workflow_path = Path('../realms/.github/workflows/1-build-branch.yml')
    
    if not our_workflow_path.exists():
        print(f"❌ Our workflow not found: {our_workflow_path}")
        return
    
    if not realms_workflow_path.exists():
        print(f"❌ Realms workflow not found: {realms_workflow_path}")
        return
    
    try:
        with open(our_workflow_path, 'r') as f:
            our_workflow = yaml.safe_load(f)
        
        with open(realms_workflow_path, 'r') as f:
            realms_workflow = yaml.safe_load(f)
        
        print("✅ Both workflows parsed successfully\n")
        
        print("🔍 Structure Comparison:")
        print(f"Our workflow keys: {list(our_workflow.keys()) if our_workflow else 'None'}")
        print(f"Realms workflow keys: {list(realms_workflow.keys()) if realms_workflow else 'None'}")
        print()
        
        if 'on' in our_workflow and 'on' in realms_workflow:
            print("🔍 Trigger Comparison:")
            print(f"Our triggers: {list(our_workflow['on'].keys())}")
            print(f"Realms triggers: {list(realms_workflow['on'].keys())}")
            print()
        
        if 'jobs' in our_workflow and 'jobs' in realms_workflow:
            print("🔍 Jobs Comparison:")
            our_jobs = our_workflow['jobs']
            realms_jobs = realms_workflow['jobs']
            
            print(f"Our jobs: {list(our_jobs.keys())}")
            print(f"Realms jobs: {list(realms_jobs.keys())}")
            
            if our_jobs and realms_jobs:
                our_first_job = list(our_jobs.values())[0]
                realms_first_job = list(realms_jobs.values())[0]
                
                print(f"\nOur first job keys: {list(our_first_job.keys())}")
                print(f"Realms first job keys: {list(realms_first_job.keys())}")
                
                our_has_perms = 'permissions' in our_first_job
                realms_has_perms = 'permissions' in realms_first_job
                print(f"\nOur job has permissions: {our_has_perms}")
                print(f"Realms job has permissions: {realms_has_perms}")
        
        our_has_dispatch = 'workflow_dispatch' in our_workflow.get('on', {})
        realms_has_dispatch = 'workflow_dispatch' in realms_workflow.get('on', {})
        print(f"\nOur workflow has workflow_dispatch: {our_has_dispatch}")
        print(f"Realms workflow has workflow_dispatch: {realms_has_dispatch}")
        
    except Exception as e:
        print(f"❌ Error comparing workflows: {e}")

if __name__ == "__main__":
    compare_workflows()
