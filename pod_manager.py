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
import traceback
import json
import requests
import argparse
from pathlib import Path
from typing import Dict, Optional, Tuple


class PodManager:
    def __init__(self, verbose: bool = False):
        self.script_dir = Path(__file__).parent
        self.api_base = "https://rest.runpod.io/v1/pods"
        self.verbose = verbose
        self.api_key = self._get_api_key()
        self.config = self._load_config()
        
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
        
        # Set basic defaults
        config.setdefault('MAX_GPU_PRICE', '0.30')
        config.setdefault('TEMPLATE_ID', 'ashoka1')
        
        # Set fallback defaults for template-based deployment
        config.setdefault('CONTAINER_DISK', '20')
        config.setdefault('IMAGE_NAME', 'docker.io/smartsocialcontracts/ashoka:latest')
        config.setdefault('START_COMMAND', '')
        config.setdefault('VOLUME_ID_MAIN', '74qwk1f72z9')  # ashoka1_main_volume
        config.setdefault('VOLUME_ID_BRANCH', 'ipy89pj504')  # ashoka1_branch_volume
        
        # Template fetching disabled for now - using fallback configuration
        # TODO: Fix GraphQL template query later
        if self.verbose:
            self._print(f"Using fallback configuration for template {config.get('TEMPLATE_ID', 'ashoka1')}")
        
        return config
    
    def _get_template_config(self, template_id: str) -> Dict[str, str]:
        """Fetch template configuration from RunPod API"""
        try:
            # Query to get template details
            query = """
            query getTemplate($templateId: String!) {
                template(id: $templateId) {
                    id
                    name
                    containerDiskInGb
                    dockerArgs
                    imageName
                    volumeInGb
                    volumeMountPath
                    networkVolumeId
                }
            }
            """
            
            variables = {"templateId": template_id}
            response = self._make_graphql_request(query, variables)
            
            if response and 'data' in response and response['data']['template']:
                template = response['data']['template']
                return {
                    'CONTAINER_DISK': str(template.get('containerDiskInGb', '20')),
                    'IMAGE_NAME': template.get('imageName', 'docker.io/smartsocialcontracts/ashoka:latest'),
                    'START_COMMAND': template.get('dockerArgs', ''),
                    'VOLUME_ID': template.get('networkVolumeId', ''),
                    'VOLUME_SIZE': str(template.get('volumeInGb', '300')),
                    'VOLUME_MOUNT_PATH': template.get('volumeMountPath', '/workspace')
                }
            else:
                self._print(f"⚠️  Could not fetch template {template_id}, using defaults", force=True)
                return {}
                
        except Exception as e:
            self._print(f"⚠️  Error fetching template config: {e}", force=True)
            return {}
    
    def _get_api_key(self) -> str:
        """Get RunPod API key from environment or production.env"""
        # Try environment variable first
        api_key = os.getenv('RUNPOD_API_KEY')
        if api_key:
            return api_key
        
        # Try production.env file
        prod_env_file = self.script_dir / "production.env"
        if prod_env_file.exists():
            with open(prod_env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('RUNPOD_API_KEY='):
                        return line.split('=', 1)[1].strip()
        
        raise ValueError("RUNPOD_API_KEY not found in environment or production.env file. Please set RUNPOD_API_KEY environment variable or add it to production.env")
    
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
    
    def _format_curl_command(self, method: str, url: str, headers: dict, data: dict = None) -> str:
        """Format HTTP request as curl command for debugging"""
        curl_cmd = f"curl -X {method} '{url}'"
        
        # Add headers
        for key, value in headers.items():
            curl_cmd += f" \\\n  -H '{key}: {value}'"
        
        # Add data if present
        if data:
            import json
            json_data = json.dumps(data, indent=2)
            curl_cmd += f" \\\n  -d '{json_data}'"
        
        return curl_cmd
    
    def _log_request_response(self, method: str, url: str, headers: dict, data: dict = None, response = None):
        """Log request as curl command and response for debugging"""
        if self.verbose:
            print("\n" + "="*60)
            print("🔍 DEBUG: HTTP REQUEST")
            print("="*60)
            curl_cmd = self._format_curl_command(method, url, headers, data)
            print(curl_cmd)
            
            if response:
                print("\n" + "-"*60)
                print("📥 RESPONSE:")
                print("-"*60)
                print(f"Status Code: {response.status_code}")
                print(f"Headers: {dict(response.headers)}")
                try:
                    response_json = response.json()
                    import json
                    print(f"Body: {json.dumps(response_json, indent=2)}")
                except:
                    print(f"Body: {response.text}")
            print("="*60 + "\n")
    
    def _make_api_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make API request to RunPod"""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        url = f"{self.api_base}/{endpoint}" if endpoint else self.api_base
        
        try:
            response = requests.request(method, url, headers=headers, timeout=30, **kwargs)
            
            # Log request and response for debugging
            data = kwargs.get('json') if 'json' in kwargs else None
            self._log_request_response(method, url, headers, data, response)
            
            return response
        except requests.RequestException as e:
            self._print(f"❌ API request failed: {e}", force=True)
            sys.exit(1)
    
    def _make_graphql_request(self, query: str, variables: dict = None) -> dict:
        """Make GraphQL request to RunPod"""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {'query': query}
        if variables:
            payload['variables'] = variables
        
        try:
            response = requests.post(
                'https://api.runpod.io/graphql',
                json=payload,
                headers=headers,
                timeout=30
            )
            
            # Log request and response for debugging
            self._log_request_response('POST', 'https://api.runpod.io/graphql', headers, payload, response)
            
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self._print(f"❌ GraphQL request failed: {e}", force=True)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_details = e.response.json()
                    self._print(f"Error details: {error_details}", force=True)
                except:
                    self._print(f"Response text: {e.response.text}", force=True)
            traceback.print_exc()
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
            traceback.print_exc()
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
    
    def start_pod(self, pod_type: str, deploy_new_if_needed: bool = False) -> bool:
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
            if deploy_new_if_needed:
                self._print("Attempting to deploy a new pod...")
                return self.deploy_pod(pod_type)
            return False
        
        self._print("Start command sent. Waiting for pod to start...")
        
        if self.wait_for_status(pod_id, ["RUNNING"]):
            self._print("✅ Pod is now running successfully!")
            if not self.verbose:
                print("RUNNING")
            return True
        else:
            self._print("❌ Pod failed to start", force=True)
            if deploy_new_if_needed:
                self._print("Pod failed to start, attempting to deploy a new pod...")
                return self.deploy_pod(pod_type)
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
    
    def restart_pod(self, pod_type: str, deploy_new_if_needed: bool = False) -> bool:
        """Restart a pod (stop then start)"""
        self._print(f"Restarting {pod_type} pod...")
        
        if not self.stop_pod(pod_type):
            return False
        
        # Wait a bit between stop and start
        time.sleep(5)
        
        return self.start_pod(pod_type, deploy_new_if_needed)
    
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

    def restart_pod(self, pod_type: str, deploy_new_if_needed: bool = False) -> bool:
        """Restart a pod (stop then start)"""
        self._print(f"Restarting {pod_type} pod...")
        
        if not self.stop_pod(pod_type):
            return False
        
        # Wait a bit between stop and start
        time.sleep(5)  # TODO: instead you should wait for the pod to be stopped with some timeout
        
        return self.start_pod(pod_type, deploy_new_if_needed)

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

    def deploy_pod(self, pod_type: str) -> bool:
        """Deploy a new pod using the cheapest available GPU under $0.30/hr"""
        self._print(f"Deploying new {pod_type} pod...")
        
        # GraphQL query to get available GPUs
        gpu_query = """
        query {
            gpuTypes {
                id
                displayName
                communitySpotPrice
                secureSpotPrice
            }
        }
        """
        
        try:
            # Get available GPUs
            response = self._make_graphql_request(gpu_query)
            
            if 'errors' in response:
                self._print(f"❌ GraphQL errors: {response['errors']}", force=True)
                return False
            
            gpu_types = response.get('data', {}).get('gpuTypes', [])
            
            # Filter GPUs by price threshold
            max_price = float(self.config.get('MAX_GPU_PRICE', '0.30'))
            affordable_gpus = []
            
            for gpu in gpu_types:
                community_price = gpu.get('communitySpotPrice')
                secure_price = gpu.get('secureSpotPrice')
                
                # Get the minimum available price (prefer community over secure)
                min_price = None
                if community_price is not None:
                    min_price = community_price
                elif secure_price is not None:
                    min_price = secure_price
                
                if min_price is not None and min_price <= max_price:
                    affordable_gpus.append({
                        'id': gpu['id'],
                        'name': gpu['displayName'],
                        'price': min_price
                    })
            
            if not affordable_gpus:
                self._print(f"❌ No GPUs found under ${max_price}/hr", force=True)
                return False
            
            # Sort by price (cheapest first)
            affordable_gpus.sort(key=lambda x: x['price'])
            
            # Use multiple GPU types to increase chances of finding available pods
            gpu_type_ids = [gpu['id'] for gpu in affordable_gpus[:5]]  # Use top 5 cheapest
            
            self._print(f"Trying {len(gpu_type_ids)} GPU types (cheapest first):")
            for i, gpu in enumerate(affordable_gpus[:5]):
                self._print(f"  {i+1}. {gpu['name']} - ${gpu['price']:.3f}/hr")
            
            # Get volume ID based on pod type
            if pod_type == "main":
                volume_id = self.config.get('VOLUME_ID_MAIN', '74qwk1f72z9')
            else:
                volume_id = self.config.get('VOLUME_ID_BRANCH', 'ipy89pj504')
            
            # Create pod using REST API
            pod_data = {
                "name": f"ashoka-{pod_type}-{int(time.time())}",
                "imageName": self.config.get('IMAGE_NAME', 'docker.io/smartsocialcontracts/ashoka:latest'),
                "gpuTypeIds": gpu_type_ids,
                "gpuCount": 1,
                "containerDiskInGb": int(self.config.get('CONTAINER_DISK', '20')),
                "networkVolumeId": volume_id
            }
            
            # Make REST API request to create pod
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                'https://api.runpod.io/v2/pods',
                json=pod_data,
                headers=headers,
                timeout=30
            )
            
            # Log request and response for debugging
            self._log_request_response('POST', 'https://api.runpod.io/v2/pods', headers, pod_data, response)
            
            if response.status_code == 200:
                result = response.json()
                pod_id = result.get('id')
                
                if pod_id:
                    self._print(f"✅ Pod created successfully!")
                    self._print(f"Pod ID: {pod_id}")
                    
                    # Generate pod URL
                    pod_url = f"https://{pod_id}-5000.proxy.runpod.net"
                    self._print(f"Pod URL: {pod_url}")
                    
                    if not self.verbose:
                        print(pod_id)
                    
                    return True
                else:
                    self._print(f"❌ Pod creation failed: No pod ID in response", force=True)
                    return False
            else:
                self._print(f"❌ Pod creation failed: {response.status_code}", force=True)
                # Show response details for debugging
                try:
                    error_response = response.json()
                    self._print(f"Error response: {error_response}", force=True)
                except:
                    self._print(f"Error response text: {response.text}", force=True)
                return False
                
        except requests.RequestException as e:
            self._print(f"❌ Pod creation request failed: {e}", force=True)
            return False
        except Exception as e:
            self._print(f"❌ Deployment failed: {e}", force=True)
            traceback.print_exc()
            return False

    def terminate_pod(self, pod_type: str) -> bool:
        """Terminate (delete) a pod"""
        self._print(f"Terminating {pod_type} pod...")
        
        try:
            server_host = self._get_server_host(pod_type)
            pod_id = self._extract_pod_id(server_host)
            
            self._print(f"Pod ID: {pod_id}")
            self._print(f"Server Host: {server_host}")
            
            # Delete the pod
            response = self._make_api_request('DELETE', pod_id)
            
            if response.status_code in [200, 204]:
                self._print(f"✅ Pod {pod_id} terminated successfully!")
                if not self.verbose:
                    print("TERMINATED")
                return True
            else:
                self._print(f"❌ Failed to terminate pod: {response.status_code} - {response.text}", force=True)
                return False
                
        except Exception as e:
            self._print(f"❌ Termination failed: {e}", force=True)
            return False
            
            return True
            
        except Exception as e:
            self._print(f"❌ Deployment failed: {e}", force=True)
            return False
    
    def terminate_pod(self, pod_type: str) -> bool:
        """Terminate (delete) a pod"""
        self._print(f"Terminating {pod_type} pod...")
        
        try:
            server_host = self._get_server_host(pod_type)
            pod_id = self._extract_pod_id(server_host)
            
            self._print(f"Pod ID: {pod_id}")
            self._print(f"Server Host: {server_host}")
            
            # Delete the pod
            response = self._make_api_request('DELETE', pod_id)
            
            if response.status_code in [200, 204]:
                self._print(f"✅ Pod {pod_id} terminated successfully!")
                if not self.verbose:
                    print("TERMINATED")
                return True
            else:
                self._print(f"❌ Failed to terminate pod: {response.status_code} - {response.text}", force=True)
                return False
                
        except Exception as e:
            self._print(f"❌ Termination failed: {e}", force=True)
            return False


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
  %(prog)s main deploy    - Deploy new main pod with cheapest GPU
  %(prog)s branch terminate - Terminate (delete) the branch pod
  %(prog)s main start --deploy-new-if-needed - Start pod, deploy new if needed
  %(prog)s branch restart --deploy-new-if-needed - Restart pod, deploy new if needed
        """
    )
    
    parser.add_argument('pod_type', choices=['main', 'branch'], 
                       help='Pod type to manage')
    parser.add_argument('action', choices=['start', 'stop', 'restart', 'status', 'deploy', 'terminate'],
                       help='Action to perform')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output (default: concise)')
    parser.add_argument('--deploy-new-if-needed', action='store_true',
                       help='Deploy a new pod if current one cannot be started (for start/restart only)')
    
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    
    args = parser.parse_args()
    
    try:
        manager = PodManager(verbose=args.verbose)
        
        if args.action == 'start':
            success = manager.start_pod(args.pod_type, args.deploy_new_if_needed)
        elif args.action == 'stop':
            success = manager.stop_pod(args.pod_type)
        elif args.action == 'restart':
            success = manager.restart_pod(args.pod_type, args.deploy_new_if_needed)
        elif args.action == 'status':
            success = manager.status_pod(args.pod_type)
        elif args.action == 'deploy':
            success = manager.deploy_pod(args.pod_type)
        elif args.action == 'terminate':
            success = manager.terminate_pod(args.pod_type)
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
