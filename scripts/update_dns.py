#!/usr/bin/env python3
"""
Update Infomaniak DNS CNAME record to point to RunPod proxy.

This script manages the ashoka.realmsgos.ch CNAME record via Infomaniak's API.
It can create, update, or check the current DNS record pointing to RunPod.

Requirements:
1. Create an API token at https://manager.infomaniak.com/v3/ng/profile/user/developer
2. Grant the token 'dns:write' and 'dns:read' scopes
3. Set INFOMANIAK_API_TOKEN environment variable or pass via --token

Usage:
    # Update CNAME to point to RunPod proxy
    ./update_dns.py --target u5t2qjmf740dig-5000.proxy.runpod.net

    # Check current DNS record
    ./update_dns.py --check

    # List all records in zone
    ./update_dns.py --list
"""

import argparse
import json
import os
import sys
from typing import Optional

import requests

# Configuration
INFOMANIAK_API_BASE = "https://api.infomaniak.com"
ZONE_NAME = "realmsgos.ch"
SUBDOMAIN = "ashoka"
DEFAULT_TTL = 300  # 5 minutes - good for dynamic updates


def get_api_token() -> str:
    """Get API token from environment or raise error."""
    token = os.environ.get("INFOMANIAK_API_TOKEN")
    if not token:
        print("Error: INFOMANIAK_API_TOKEN environment variable not set")
        print("\nTo create a token:")
        print("1. Go to https://manager.infomaniak.com/v3/ng/profile/user/developer")
        print("2. Create a new API token with 'dns:read' and 'dns:write' scopes")
        print("3. Export it: export INFOMANIAK_API_TOKEN='your_token_here'")
        sys.exit(1)
    return token


def api_request(method: str, endpoint: str, token: str, data: dict = None) -> dict:
    """Make authenticated request to Infomaniak API."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    url = f"{INFOMANIAK_API_BASE}{endpoint}"
    
    if method == "GET":
        response = requests.get(url, headers=headers)
    elif method == "POST":
        response = requests.post(url, headers=headers, json=data)
    elif method == "PUT":
        response = requests.put(url, headers=headers, json=data)
    elif method == "DELETE":
        response = requests.delete(url, headers=headers)
    else:
        raise ValueError(f"Unknown method: {method}")
    
    try:
        result = response.json()
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON response: {response.text}")
        sys.exit(1)
    
    if result.get("result") == "error":
        error = result.get("error", {})
        print(f"API Error: {error.get('code', 'unknown')} - {error.get('description', 'No description')}")
        sys.exit(1)
    
    return result


def list_records(token: str) -> list:
    """List all DNS records in the zone."""
    result = api_request("GET", f"/2/zones/{ZONE_NAME}/records", token)
    return result.get("data", [])


def find_record(token: str, subdomain: str, record_type: str = "CNAME") -> Optional[dict]:
    """Find a specific DNS record by subdomain and type."""
    records = list_records(token)
    for record in records:
        if record.get("source") == subdomain and record.get("type") == record_type:
            return record
    return None


def create_cname_record(token: str, subdomain: str, target: str, ttl: int = DEFAULT_TTL) -> dict:
    """Create a new CNAME record."""
    data = {
        "source": subdomain,
        "target": target,
        "type": "CNAME",
        "ttl": ttl,
    }
    result = api_request("POST", f"/2/zones/{ZONE_NAME}/records", token, data)
    return result.get("data", {})


def update_cname_record(token: str, record_id: int, target: str, ttl: int = DEFAULT_TTL) -> dict:
    """Update an existing CNAME record."""
    data = {
        "target": target,
        "ttl": ttl,
    }
    result = api_request("PUT", f"/2/zones/{ZONE_NAME}/records/{record_id}", token, data)
    return result.get("data", {})


def delete_record(token: str, record_id: int) -> bool:
    """Delete a DNS record."""
    api_request("DELETE", f"/2/zones/{ZONE_NAME}/records/{record_id}", token)
    return True


def update_or_create_cname(token: str, subdomain: str, target: str, ttl: int = DEFAULT_TTL) -> dict:
    """Update existing CNAME or create new one if it doesn't exist."""
    # Ensure target ends with a dot for proper CNAME format
    if not target.endswith("."):
        target = target + "."
    
    existing = find_record(token, subdomain, "CNAME")
    
    if existing:
        print(f"Updating existing CNAME record (ID: {existing['id']})")
        print(f"  Old target: {existing.get('target')}")
        print(f"  New target: {target}")
        return update_cname_record(token, existing["id"], target, ttl)
    else:
        print(f"Creating new CNAME record")
        print(f"  Subdomain: {subdomain}")
        print(f"  Target: {target}")
        return create_cname_record(token, subdomain, target, ttl)


def main():
    parser = argparse.ArgumentParser(
        description="Manage Infomaniak DNS CNAME for Ashoka RunPod proxy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--target", "-t",
        help="Target hostname for CNAME (e.g., u5t2qjmf740dig-5000.proxy.runpod.net)"
    )
    parser.add_argument(
        "--check", "-c",
        action="store_true",
        help="Check current DNS record"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all DNS records in zone"
    )
    parser.add_argument(
        "--delete", "-d",
        action="store_true",
        help="Delete the CNAME record"
    )
    parser.add_argument(
        "--ttl",
        type=int,
        default=DEFAULT_TTL,
        help=f"TTL in seconds (default: {DEFAULT_TTL})"
    )
    parser.add_argument(
        "--token",
        help="API token (overrides INFOMANIAK_API_TOKEN env var)"
    )
    parser.add_argument(
        "--subdomain",
        default=SUBDOMAIN,
        help=f"Subdomain to manage (default: {SUBDOMAIN})"
    )
    
    args = parser.parse_args()
    
    # Get token
    token = args.token or get_api_token()
    
    if args.list:
        print(f"DNS records for {ZONE_NAME}:")
        print("-" * 60)
        records = list_records(token)
        for record in records:
            print(f"  {record.get('type'):6} {record.get('source', '@'):20} -> {record.get('target')}")
        return
    
    if args.check:
        record = find_record(token, args.subdomain, "CNAME")
        if record:
            print(f"✓ CNAME record found:")
            print(f"  {args.subdomain}.{ZONE_NAME} -> {record.get('target')}")
            print(f"  TTL: {record.get('ttl')} seconds")
            print(f"  ID: {record.get('id')}")
        else:
            print(f"✗ No CNAME record found for {args.subdomain}.{ZONE_NAME}")
        return
    
    if args.delete:
        record = find_record(token, args.subdomain, "CNAME")
        if record:
            delete_record(token, record["id"])
            print(f"✓ Deleted CNAME record for {args.subdomain}.{ZONE_NAME}")
        else:
            print(f"✗ No CNAME record found to delete")
        return
    
    if args.target:
        result = update_or_create_cname(token, args.subdomain, args.target, args.ttl)
        print(f"✓ CNAME record updated successfully!")
        print(f"  {args.subdomain}.{ZONE_NAME} -> {result.get('target')}")
        print(f"  TTL: {result.get('ttl')} seconds")
        print(f"\nNote: DNS propagation may take a few minutes.")
        return
    
    # No action specified
    parser.print_help()


if __name__ == "__main__":
    main()
