#!/usr/bin/env python3

"""
Remote CI Test Runner Script
This script handles pod deployment, health checking, and remote CI test execution
Used by GitHub Actions workflows for automated testing
"""

import os
import sys
import time
import json
import subprocess
import requests
import argparse
from typing import Optional, Dict, Any


class RemoteCITestRunner:
    def __init__(self, pod_url: str):
        self.max_wait = int(os.getenv('MAX_WAIT', '600'))  # 10 minutes max
        self.poll_interval = int(os.getenv('POLL_INTERVAL', '15'))
        self.pod_url = pod_url
        
        print("🚀 Starting remote CI test runner...")
        print("📋 Configuration:")
        print(f"   - Pod URL: {self.pod_url}")
        print(f"   - Max test wait: {self.max_wait}s")
        print(f"   - Poll interval: {self.poll_interval}s")
    
    def run_command(self, cmd: list, capture_output: bool = True) -> subprocess.CompletedProcess:
        """Run a shell command and return the result"""
        try:
            result = subprocess.run(cmd, capture_output=capture_output, text=True, check=True)
            return result
        except subprocess.CalledProcessError as e:
            print(f"❌ Command failed: {' '.join(cmd)}")
            print(f"Error: {e.stderr}")
            sys.exit(1)
    
    def parse_json_field(self, json_str: str, field: str, default_value: str = "") -> str:
        """Parse a JSON field with error handling"""
        try:
            data = json.loads(json_str)
            return data.get(field, default_value)
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON field '{field}': {e}", file=sys.stderr)
            if default_value:
                return default_value
            sys.exit(1)
    
    def start_remote_test(self) -> str:
        """Start remote CI test and return test ID"""
        print("🚀 Starting remote CI tests...")
        
        try:
            response = requests.post(f"{self.pod_url}/start-test", timeout=30)
            response.raise_for_status()
            test_response = response.text
            print(f"🔍 Test response: {test_response}")
            
            test_id = self.parse_json_field(test_response, "test_id")
            if not test_id:
                print("❌ Could not parse test ID from response")
                sys.exit(1)
            
            print(f"📋 Test ID: {test_id}")
            return test_id
            
        except requests.RequestException as e:
            print(f"❌ Failed to start remote test: {e}")
            sys.exit(1)
    
    def poll_test_completion(self, test_id: str) -> None:
        """Poll for test completion and handle results"""
        print("⏳ Polling for test completion...")
        elapsed = 0
        
        while elapsed < self.max_wait:
            time.sleep(self.poll_interval)
            elapsed += self.poll_interval
            
            try:
                response = requests.get(f"{self.pod_url}/test-status/{test_id}", timeout=30)
                response.raise_for_status()
                status_response = response.text
                print(f"🔍 Status response: {status_response}")
                
                status = self.parse_json_field(status_response, "status", "failed")
                print(f"📊 Test status after {elapsed}s: {status}")
                
                if status == "success":
                    print("✅ Tests passed!")
                    print("📄 Test output:")
                    output = self.parse_json_field(status_response, "output", "No output available")
                    print(output)
                    sys.exit(0)
                elif status == "failed":
                    print("❌ Tests failed!")
                    print("📄 Test output:")
                    output = self.parse_json_field(status_response, "output", "No output available")
                    print(output)
                    sys.exit(1)
                    
            except requests.RequestException as e:
                print(f"⚠️ Error polling test status: {e}")
                # Continue polling on network errors
                continue
        
        print(f"⏰ Tests timed out after {self.max_wait} seconds")
        sys.exit(1)
    
    def run(self) -> None:
        """Run the complete CI test workflow"""
        try:
            # Step 1: Start remote CI test
            test_id = self.start_remote_test()
            
            # Step 2: Poll for test completion
            self.poll_test_completion(test_id)
            
        except KeyboardInterrupt:
            print("\n⚠️ Test runner interrupted by user")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            sys.exit(1)


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Remote CI Test Runner for Ashoka pods',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s http://localhost:5000
"""
    )
    
    parser.add_argument(
        'pod_url',
        help='URL of the pod to test'
    )
    
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    runner = RemoteCITestRunner(pod_url=args.pod_url)
    runner.run()
