#!/usr/bin/env python3

"""
Health Check Script
Checks if a pod URL is responding successfully within a timeout period
"""

import sys
import time
import requests
import argparse
from typing import Optional


def health_check(pod_url: str, timeout_sec: int, sleep_interval: int = 10) -> bool:
    """
    Check if pod URL is responding successfully
    
    Args:
        pod_url: URL to check
        timeout_sec: Maximum time to wait in seconds
        sleep_interval: Time between checks in seconds
    
    Returns:
        True if health check succeeds, False otherwise
    """
    print(f"🔍 Health checking {pod_url} for up to {timeout_sec} seconds...")
    
    start_time = time.time()
    end_time = start_time + timeout_sec
    
    while time.time() < end_time:
        elapsed = int(time.time() - start_time)
        print(f"⏱️  Attempt at {elapsed}s: checking {pod_url}")
        
        try:
            url = f"{pod_url.rstrip('/')}"
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            print(f"✅ Health check successful at {url} after {elapsed}s")
            return True
            
        except requests.RequestException as e:
            print(f"⚠️ Error health checking {pod_url}: {e}")
            continue
    
        if time.time() < (end_time - sleep_interval):
            time.sleep(sleep_interval)
    
    print(f"❌ Health check failed: {pod_url} did not respond successfully within {timeout_sec} seconds")
    return False


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Health check a pod URL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s 600 https://yy2ez2ejueg4pa-5000.proxy.runpod.net/
"""
    )
    
    parser.add_argument('timeout', type=int, help='Timeout in seconds')
    parser.add_argument('pod_url', help='Pod URL to health check')
    parser.add_argument('--sleep-interval', type=int, default=10, 
                       help='Sleep interval between checks (default: 10)')
    
    args = parser.parse_args()
    
    # Perform health check
    success = health_check(args.pod_url, args.timeout, args.sleep_interval)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
