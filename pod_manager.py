#!/usr/bin/env python3
"""
RunPod Manager - A Python CLI tool for managing RunPod instances
Usage: pod_manager.py <pod_type> <action>
Examples:
    pod_manager.py main start
    pod_manager.py branch stop
    pod_manager.py main status
"""

import os
import sys
import time
import json
import requests
import argparse
from pathlib import Path
from typing import Dict, Optional, Tuple


class PodManager:
    def __init__(self, verbose: bool = True):
        self.script_dir = Path(__file__).parent
        self.api_base = "https://rest.runpod.io/v1/pods"
        self.config = self._load_config()
        self.api_key = self._get_api_key()
        self.verbose = verbose
        
    def _load_config(self) -> Dict[str, str]:
        """Load configuration from env file"""
        env_file = self.script_dir / "env"
        config = {}
        
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
        
        return config
    
    def _get_api_key(self) -> str:
        """Get RunPod API key from environment or production.env"""
        # Try environment variable first
        api_key = os.getenv('RUNPOD_API_KEY')
        if api_key:
            return api_key
        
        raise ValueError("RUNPOD_API_KEY not found in environment")
    
    def _get_server_host(self, pod_type: str) -> str:
        """Get server host based on pod type"""
        if pod_type == "main":
            host = self.config.get('SERVER_HOST_MAIN')
        elif pod_type == "branch":
            host = self.config.get('SERVER_HOST_BRANCH')
        else:
            raise ValueError(f"Invalid pod type '{pod_type}'. Use 'main' or 'branch'")
        
        if not host:
            raise ValueError(f"SERVER_HOST_{pod_type.upper()} not found in env file")
        
        return host
    
    def _extract_pod_id(self, server_host: str) -> str:
        """Extract pod ID from server host"""
        return server_host.split('-')[0]
    
    def _print(self, message: str, force: bool = False):
        """Print message only if verbose mode is enabled or force is True"""
        if self.verbose or force:
            print(message)
    
    def _make_api_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make API request to RunPod"""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        url = f"{self.api_base}/{endpoint}" if endpoint else self.api_base
        
        try:
            response = requests.request(method, url, headers=headers, timeout=30, **kwargs)
            return response
        except requests.RequestException as e:
            self._print(f"❌ API request failed: {e}", force=True)
            sys.exit(1)
    
    def get_pod_status(self, pod_id: str) -> Optional[str]:
        """Get current pod status"""
        try:
            response = self._make_api_request('GET', pod_id)
            if response.status_code == 200:
                data = response.json()
                return data.get('desiredStatus')
            else:
                self._print(f"❌ Failed to get pod status: {response.status_code}", force=True)
                return None
        except Exception as e:
            self._print(f"❌ Error getting pod status: {e}", force=True)
            return None
    
    def wait_for_status(self, pod_id: str, target_statuses: list, timeout: int = 300) -> bool:
        """Wait for pod to reach one of the target statuses"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_pod_status(pod_id)
            self._print(f"Current status: {status}")
            
            if status in target_statuses:
                return True
            
            if status in ['FAILED', 'ERROR']:
                self._print(f"❌ Pod entered error state: {status}", force=True)
                return False
            
            time.sleep(5)
        
        self._print(f"❌ Timeout waiting for pod to reach {target_statuses}", force=True)
        return False
    
    def start_pod(self, pod_type: str) -> bool:
        """Start a pod"""
        self._print(f"Starting {pod_type} pod...")
        
        server_host = self._get_server_host(pod_type)
        pod_id = self._extract_pod_id(server_host)
        
        self._print(f"Pod ID: {pod_id}")
        self._print(f"Server Host: {server_host}")
        
        # Check current status
        current_status = self.get_pod_status(pod_id)
        self._print(f"Current status: {current_status}")
        
        if current_status == "RUNNING":
            self._print("✅ Pod is already running. No action needed.")
            if not self.verbose:
                print("RUNNING")
            return True
        
        if current_status not in ["EXITED", "STOPPED", None]:
            self._print(f"Pod is in unexpected state: {current_status}")
            self._print("Waiting for pod to reach a stable state...")
            
            if not self.wait_for_status(pod_id, ["EXITED", "STOPPED", "RUNNING"]):
                return False
            
            # Check again after waiting
            current_status = self.get_pod_status(pod_id)
            if current_status == "RUNNING":
                self._print("✅ Pod is now running. No action needed.")
                if not self.verbose:
                    print("RUNNING")
                return True
        
        # Start the pod
        self._print(f"Starting pod {pod_id}...")
        response = self._make_api_request('POST', f"{pod_id}/start")
        
        if response.status_code not in [200, 202]:
            self._print(f"❌ Failed to start pod: {response.status_code} - {response.text}", force=True)
            return False
        
        self._print("Start command sent. Waiting for pod to start...")
        
        if self.wait_for_status(pod_id, ["RUNNING"]):
            self._print("✅ Pod is now running successfully!")
            if not self.verbose:
                print("RUNNING")
            return True
        else:
            self._print("❌ Pod failed to start", force=True)
            return False
    
    def stop_pod(self, pod_type: str) -> bool:
        """Stop a pod"""
        self._print(f"Stopping {pod_type} pod...")
        
        server_host = self._get_server_host(pod_type)
        pod_id = self._extract_pod_id(server_host)
        
        self._print(f"Pod ID: {pod_id}")
        self._print(f"Server Host: {server_host}")
        
        # Check current status
        current_status = self.get_pod_status(pod_id)
        self._print(f"Current status: {current_status}")
        
        if current_status in ["EXITED", "STOPPED"]:
            self._print("✅ Pod is already stopped. No action needed.")
            if not self.verbose:
                print(current_status)
            return True
        
        if current_status != "RUNNING":
            self._print(f"Pod is in unexpected state: {current_status}")
            self._print("Waiting for pod to reach a stable state...")
            
            if not self.wait_for_status(pod_id, ["EXITED", "STOPPED", "RUNNING"]):
                return False
            
            # Check again after waiting
            current_status = self.get_pod_status(pod_id)
            if current_status in ["EXITED", "STOPPED"]:
                self._print("✅ Pod is now stopped. No action needed.")
                if not self.verbose:
                    print(current_status)
                return True
        
        # Stop the pod
        self._print(f"Stopping pod {pod_id}...")
        response = self._make_api_request('POST', f"{pod_id}/stop")
        
        if response.status_code not in [200, 202]:
            self._print(f"❌ Failed to stop pod: {response.status_code} - {response.text}", force=True)
            return False
        
        self._print("Stop command sent. Waiting for pod to stop...")
        
        if self.wait_for_status(pod_id, ["EXITED", "STOPPED"]):
            final_status = self.get_pod_status(pod_id)
            self._print("✅ Pod is now stopped successfully!")
            if not self.verbose:
                print(final_status)
            return True
        else:
            self._print("❌ Pod failed to stop", force=True)
            return False
    
    def restart_pod(self, pod_type: str) -> bool:
        """Restart a pod (stop then start)"""
        self._print(f"Restarting {pod_type} pod...")
        
        if not self.stop_pod(pod_type):
            return False
        
        # Wait a bit between stop and start
        time.sleep(5)
        
        return self.start_pod(pod_type)
    
    def status_pod(self, pod_type: str) -> bool:
        """Get pod status"""
        server_host = self._get_server_host(pod_type)
        pod_id = self._extract_pod_id(server_host)
        
        self._print(f"Pod Type: {pod_type}")
        self._print(f"Pod ID: {pod_id}")
        self._print(f"Server Host: {server_host}")
        
        status = self.get_pod_status(pod_id)
        if self.verbose:
            print(f"Status: {status}")
        else:
            print(status)
        
        return True


def main():
    parser = argparse.ArgumentParser(
        description="RunPod Manager - Manage RunPod instances",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s main start     - Start the main pod
  %(prog)s branch stop    - Stop the branch pod
  %(prog)s main restart   - Restart the main pod
  %(prog)s branch status  - Get branch pod status
        """
    )
    
    parser.add_argument('pod_type', choices=['main', 'branch'], 
                       help='Pod type to manage')
    parser.add_argument('action', choices=['start', 'stop', 'restart', 'status'],
                       help='Action to perform')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output (default: concise)')
    
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    
    args = parser.parse_args()
    
    try:
        manager = PodManager(verbose=args.verbose)
        
        if args.action == 'start':
            success = manager.start_pod(args.pod_type)
        elif args.action == 'stop':
            success = manager.stop_pod(args.pod_type)
        elif args.action == 'restart':
            success = manager.restart_pod(args.pod_type)
        elif args.action == 'status':
            success = manager.status_pod(args.pod_type)
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
