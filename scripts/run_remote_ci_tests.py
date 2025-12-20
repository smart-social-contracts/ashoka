#!/usr/bin/env python3

"""
Remote CI Test Runner Script
This script handles pod deployment, health checking, and remote CI test execution
Used by GitHub Actions workflows for automated testing

API Endpoints Used:
==================
1. POST /start-test - Initiate CI test run
2. GET /test-status/{test_id} - Check test progress  
3. GET /test-results/{test_id} - Get detailed results

Equivalent Curl Commands:
========================
# 1. Start remote CI test
curl -X POST "https://POD_URL/start-test" \
  -H "Content-Type: application/json" \
  --max-time 30

# 2. Poll test status
curl -X GET "https://POD_URL/test-status/TEST_ID" \
  -H "Content-Type: application/json" \
  --max-time 30

# 3. Fetch detailed results
curl -X GET "https://POD_URL/test-results/TEST_ID" \
  -H "Content-Type: application/json" \
  --max-time 30

Example Usage:
==============
# Manual testing workflow
POD_URL="https://l8z3rgn4jxy14c-5000.proxy.runpod.net"

# Start test
RESPONSE=$(curl -s -X POST "$POD_URL/start-test" --max-time 30)
TEST_ID=$(echo "$RESPONSE" | jq -r '.test_id')

# Poll until complete
while true; do
    sleep 15
    STATUS=$(curl -s -X GET "$POD_URL/test-status/$TEST_ID" --max-time 30 | jq -r '.status')
    if [ "$STATUS" = "success" ] || [ "$STATUS" = "failed" ]; then break; fi
done

# Get results
curl -s -X GET "$POD_URL/test-results/$TEST_ID" --max-time 30 | jq '.'
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
        self.test_success = False
        
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
            self.pod_url = "https://" + self.pod_url if not self.pod_url.startswith("https://") else self.pod_url
            
            # Log equivalent curl command
            print(f"📋 Equivalent curl command:")
            print(f"curl -X POST \"{self.pod_url}/start-test\" \\")
            print(f"  -H \"Content-Type: application/json\" \\")
            print(f"  --max-time 30")
            print()
            
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
                # Log equivalent curl command (only on first poll to avoid spam)
                if elapsed == self.poll_interval:
                    print(f"📋 Equivalent curl command:")
                    print(f"curl -X GET \"{self.pod_url}/test-status/{test_id}\" \\")
                    print(f"  -H \"Content-Type: application/json\" \\")
                    print(f"  --max-time 30")
                    print()
                
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
                    self.test_success = True
                    return
                elif status == "failed":
                    print("❌ Tests failed!")
                    print("📄 Test output:")
                    output = self.parse_json_field(status_response, "output", "No output available")
                    print(output)
                    return
                    
            except requests.RequestException as e:
                print(f"⚠️ Error polling test status: {e}")
                # Continue polling on network errors
                continue
        
        print(f"⏰ Tests timed out after {self.max_wait} seconds")
    
    def fetch_detailed_results(self, test_id: str) -> None:
        """Fetch and display detailed test results"""
        try:
            print("\n📊 Fetching detailed test results...")
            
            # Log equivalent curl command
            print(f"📋 Equivalent curl command:")
            print(f"curl -X GET \"{self.pod_url}/test-results/{test_id}\" \\")
            print(f"  -H \"Content-Type: application/json\" \\")
            print(f"  --max-time 30")
            print()
            
            response = requests.get(f"{self.pod_url}/test-results/{test_id}", timeout=30)
            response.raise_for_status()
            
            results_data = response.json()
            print('results_data', results_data)
            
            print("\n" + "="*60)
            print("DETAILED TEST RESULTS")
            print("="*60)
            
            if isinstance(results_data, list):
                for i, test in enumerate(results_data, 1):
                    print(f"\n🔍 Test {i}/{len(results_data)}")
                    print(f"📝 QUESTION: {test.get('question', 'Unknown question')}")
                    print(f"🎯 EXPECTED ANSWER: {test.get('expected_answer', 'N/A')}")
                    print(f"🤖 ACTUAL ANSWER: {test.get('actual_answer', 'N/A')}")
                    print(f"📊 Similarity Score: {test.get('similarity_score', 'N/A'):.3f}")
                    print(f"🎯 Status: {'✅ PASS' if test.get('passed', False) else '❌ FAIL'}")
                    print("-" * 80)
            else:
                print(f"Results: {results_data}")
                
        except requests.RequestException as e:
            print(f"⚠️ Could not fetch detailed results: {e}")
        except Exception as e:
            print(f"⚠️ Error processing detailed results: {e}")
            traceback.print_exc()
    
    def run(self) -> None:
        """Run the complete CI test workflow"""
        try:
            # Step 1: Start remote CI test
            test_id = self.start_remote_test()
            
            # Step 2: Poll for test completion
            self.poll_test_completion(test_id)

            # Step 3: Fetch and display detailed test results
            self.fetch_detailed_results(test_id)

            if self.test_success:
                sys.exit(0)
            else:
                sys.exit(1)
            
        except KeyboardInterrupt:
            print("\n⚠️ Test runner interrupted by user")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            traceback.print_exc()
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
