#!/usr/bin/env python3
"""
RunPod Manager - A Python CLI tool for managing RunPod instances using the official RunPod SDK
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
import argparse
import traceback
import runpod
from pathlib import Path
from typing import Dict, Optional, List, Any


class PodManager:
    def __init__(self, verbose: bool = False):
        self.script_dir = Path(__file__).parent
        self.verbose = verbose
        self.api_key = self._get_api_key()
        self.config = self._load_config()
        
        # Initialize RunPod SDK
        runpod.api_key = self.api_key
        
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
        config.setdefault('MAX_GPU_PRICE', '0.40')
        config.setdefault('TEMPLATE_ID', 'ashoka1')
        
        # Set fallback defaults for template-based deployment
        config.setdefault('CONTAINER_DISK', '20')
        config.setdefault('IMAGE_NAME', 'docker.io/smartsocialcontracts/ashoka:latest')
        config.setdefault('VOLUME_ID_MAIN', '74qwk1f72z9')  # ashoka1_main_volume
        config.setdefault('VOLUME_ID_BRANCH', 'ipy89pj504')  # ashoka1_branch_volume
        
        return config
    
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
        
        raise ValueError("RUNPOD_API_KEY not found in environment or production.env")
    
    def _get_server_host(self, pod_type: str) -> str:
        """Get server host based on pod type"""
        if pod_type == "main":
            return self.config.get('SERVER_HOST_MAIN', 'default-main-host')
        else:
            return self.config.get('SERVER_HOST_BRANCH', 'default-branch-host')
    
    def _extract_pod_id(self, server_host: str) -> str:
        """Extract pod ID from server host"""
        return server_host.split('-')[0]
    
    def _print(self, message: str, force: bool = False):
        """Print message if verbose mode is enabled or force is True"""
        if self.verbose or force:
            print(message)
    
    def get_pod_status(self, pod_id: str) -> str:
        """Get the current status of a pod using RunPod SDK"""
        try:
            pods = runpod.get_pods()
            if self.verbose:
                self._print(f"🔍 Found {len(pods)} total pods")
            
            # Find the specific pod
            for pod in pods:
                if pod['id'] == pod_id:
                    status = pod.get('desiredStatus', 'UNKNOWN')
                    if self.verbose:
                        self._print(f"Pod {pod_id} status: {status}")
                    return status
            
            self._print(f"❌ Pod {pod_id} not found", force=True)
            return 'NOT_FOUND'
                
        except Exception as e:
            self._print(f"❌ Failed to get pod status: {e}", force=True)
            return 'ERROR'
    
    def wait_for_status(self, pod_id: str, target_statuses: list, timeout: int = 300) -> bool:
        """Wait for pod to reach one of the target statuses"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            current_status = self.get_pod_status(pod_id)
            if current_status in target_statuses:
                return True
            if current_status in ['ERROR', 'NOT_FOUND']:
                return False
            
            if self.verbose:
                self._print(f"Waiting for pod status... Current: {current_status}")
            time.sleep(5)
        
        return False
    
    def start_pod(self, pod_type: str, deploy_new_if_needed: bool = False) -> bool:
        """Start a pod using RunPod SDK"""
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
        
        if current_status in ['NOT_FOUND', 'ERROR']:
            if deploy_new_if_needed:
                self._print("Pod not found, attempting to deploy a new pod...")
                return self.deploy_pod(pod_type)
            else:
                self._print("❌ Pod not found and deploy_new_if_needed is False", force=True)
                return False
        
        # Start the pod using RunPod SDK
        self._print(f"Starting pod {pod_id}...")
        try:
            result = runpod.start_pod(pod_id)
            if self.verbose:
                self._print(f"🔍 Start result: {result}")
            
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
                
        except Exception as e:
            self._print(f"❌ Start failed: {e}", force=True)
            if deploy_new_if_needed:
                self._print("Start command failed, attempting to deploy a new pod...")
                return self.deploy_pod(pod_type)
            return False
    
    def stop_pod(self, pod_type: str) -> bool:
        """Stop a pod using RunPod SDK"""
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
        
        if current_status in ['NOT_FOUND', 'ERROR']:
            self._print("❌ Pod not found or error getting status", force=True)
            return False
        
        # Stop the pod using RunPod SDK
        self._print(f"Stopping pod {pod_id}...")
        try:
            result = runpod.stop_pod(pod_id)
            if self.verbose:
                self._print(f"🔍 Stop result: {result}")
            
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
                
        except Exception as e:
            self._print(f"❌ Stop failed: {e}", force=True)
            return False
    
    def restart_pod(self, pod_type: str, deploy_new_if_needed: bool = False) -> bool:
        """Restart a pod (stop then start)"""
        self._print(f"Restarting {pod_type} pod...")
        
        # Stop the pod first
        if not self.stop_pod(pod_type):
            self._print("❌ Failed to stop pod for restart", force=True)
            return False
        
        # Start the pod
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
        """Deploy a new pod using RunPod SDK with the cheapest available GPU"""
        self._print(f"Deploying new {pod_type} pod...")
        
        try:
            # Get available GPU types and their detailed prices
            gpu_types = runpod.get_gpus()
            if self.verbose:
                self._print(f"🔍 Found {len(gpu_types)} GPU types")
            
            # Get detailed pricing for each GPU
            detailed_gpus = []
            print("\n=== Available GPUs with Spot Prices ===")
            print("=" * 60)
            
            for i, gpu_basic in enumerate(gpu_types, 1):
                try:
                    # Get detailed info including pricing for each GPU
                    gpu_detailed = runpod.get_gpu(gpu_basic['id'])
                    detailed_gpus.append(gpu_detailed)
                    
                    name = gpu_detailed.get('displayName', gpu_basic.get('id', 'Unknown'))
                    community_spot = gpu_detailed.get('communitySpotPrice')
                    secure_spot = gpu_detailed.get('secureSpotPrice')
                    
                    print(f'{i:2d}. {name}')
                    print(f'    ID: {gpu_basic.get("id", "N/A")}')
                    
                    if community_spot is not None:
                        print(f'    Community Spot: ${community_spot:.3f}/hr')
                    else:
                        print(f'    Community Spot: N/A')
                        
                    if secure_spot is not None:
                        print(f'    Secure Spot: ${secure_spot:.3f}/hr')
                    else:
                        print(f'    Secure Spot: N/A')
                    
                    # Show lowest price info if available
                    if gpu_detailed.get('lowestPrice'):
                        lowest = gpu_detailed['lowestPrice']
                        if lowest.get('minimumBidPrice'):
                            print(f'    Min Bid: ${lowest["minimumBidPrice"]:.3f}/hr')
                    
                    print()
                    
                except Exception as e:
                    if self.verbose:
                        self._print(f"Warning: Could not get detailed pricing for {gpu_basic.get('id', 'Unknown')}: {e}")
                    # Fallback to basic info
                    detailed_gpus.append(gpu_basic)
            
            print("=" * 60)
            
            # Filter GPUs by price threshold using detailed pricing
            max_price = float(self.config.get('MAX_GPU_PRICE', '0.30'))
            affordable_gpus = []
            
            print(f"\n🔍 Filtering GPUs under ${max_price}/hr...")
            
            for gpu in detailed_gpus:
                community_spot = gpu.get('communitySpotPrice')
                secure_spot = gpu.get('secureSpotPrice')
                
                # Get the minimum available spot price (prefer community over secure)
                min_price = None
                if community_spot is not None:
                    min_price = community_spot
                elif secure_spot is not None:
                    min_price = secure_spot
                
                if min_price is not None and min_price <= max_price:
                    affordable_gpus.append({
                        'id': gpu['id'],
                        'name': gpu.get('displayName', gpu['id']),
                        'price': min_price,
                        'community_spot': community_spot,
                        'secure_spot': secure_spot
                    })
                    if self.verbose:
                        self._print(f"✅ {gpu.get('displayName', gpu['id'])} - ${min_price:.3f}/hr (affordable)")
            
            if not affordable_gpus:
                self._print(f"❌ No GPUs found under ${max_price}/hr", force=True)
                return False
            
            # Sort by price (cheapest first) and select the best option
            affordable_gpus.sort(key=lambda x: x['price'])
            selected_gpu = affordable_gpus[0]
            
            self._print(f"Selected GPU: {selected_gpu['name']} - ${selected_gpu['price']:.3f}/hr")
            
            # Create pod using RunPod SDK
            pod_name = f"ashoka-{pod_type}-{int(time.time())}"
            image_name = self.config.get('IMAGE_NAME', 'docker.io/smartsocialcontracts/ashoka:latest')
            volume_size = int(self.config.get('VOLUME_SIZE', '50'))  # GB for persistent storage
            container_disk = int(self.config.get('CONTAINER_DISK', '20'))  # GB for container disk
            
            self._print(f"Creating pod: {pod_name}")
            self._print(f"Image: {image_name}")
            self._print(f"GPU: {selected_gpu['id']}")
            self._print(f"Volume: {volume_size}GB")
            self._print(f"Container Disk: {container_disk}GB")
            
            # Use the RunPod SDK to create the pod with proper parameters
            result = runpod.create_pod(
                name=pod_name,
                image_name=image_name,
                gpu_type_id=selected_gpu['id'],
                cloud_type="COMMUNITY",  # Use community cloud for better pricing
                gpu_count=1,
                volume_in_gb=volume_size,  # Persistent storage
                container_disk_in_gb=container_disk,  # Container disk
                ports="5000/http,22/tcp",  # Flask app on 5000, SSH on 22
                env={
                    "FLASK_ENV": "production",
                    "PYTHONPATH": "/workspace"
                },
                support_public_ip=True,
                start_ssh=True
            )
            
            if self.verbose:
                self._print(f"🔍 Create result: {result}")
            
            # Extract pod ID from result
            pod_id = result.get('id') if isinstance(result, dict) else str(result)
            
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
                self._print(f"❌ Pod creation failed: No pod ID returned", force=True)
                return False
                
        except Exception as e:
            self._print(f"❌ Deployment failed: {e}", force=True)
            traceback.print_exc()
            return False
    
    def terminate_pod(self, pod_type: str) -> bool:
        """Terminate (delete) a pod using RunPod SDK"""
        self._print(f"Terminating {pod_type} pod...")
        
        try:
            server_host = self._get_server_host(pod_type)
            pod_id = self._extract_pod_id(server_host)
            
            self._print(f"Pod ID: {pod_id}")
            self._print(f"Server Host: {server_host}")
            
            # Delete the pod using RunPod SDK
            result = runpod.terminate_pod(pod_id)
            if self.verbose:
                self._print(f"🔍 Terminate result: {result}")
            
            self._print(f"✅ Pod {pod_id} terminated successfully!")
            if not self.verbose:
                print("TERMINATED")
            return True
                
        except Exception as e:
            self._print(f"❌ Termination failed: {e}", force=True)
            return False


def main():
    parser = argparse.ArgumentParser(
        description="RunPod Manager - Manage RunPod instances using the official RunPod SDK",
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
