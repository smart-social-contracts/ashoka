#!/usr/bin/env python3
"""
Create a RunPod Network Volume for Ashoka.

Usage:
    python scripts/create_volume.py [--name NAME] [--size SIZE] [--datacenter DC]

Examples:
    python scripts/create_volume.py
    python scripts/create_volume.py --name ashoka-storage --size 50 --datacenter EU-RO-1
"""

import os
import sys
import argparse
import requests

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_api_key():
    """Get RunPod API key from environment"""
    api_key = os.getenv('RUNPOD_API_KEY')
    if not api_key:
        raise ValueError("RUNPOD_API_KEY not found in environment")
    return api_key


def list_datacenters(api_key: str):
    """List available data centers"""
    query = """
    query {
        dataCenters {
            id
            name
            location
        }
    }
    """
    response = requests.post(
        'https://api.runpod.io/graphql',
        headers={'Authorization': f'Bearer {api_key}'},
        json={'query': query}
    )
    response.raise_for_status()
    data = response.json()
    
    if 'errors' in data:
        raise Exception(f"GraphQL errors: {data['errors']}")
    
    return data.get('data', {}).get('dataCenters', [])


def list_volumes(api_key: str):
    """List existing network volumes"""
    query = """
    query {
        myself {
            networkVolumes {
                id
                name
                size
                dataCenterId
            }
        }
    }
    """
    response = requests.post(
        'https://api.runpod.io/graphql',
        headers={'Authorization': f'Bearer {api_key}'},
        json={'query': query}
    )
    response.raise_for_status()
    data = response.json()
    
    if 'errors' in data:
        raise Exception(f"GraphQL errors: {data['errors']}")
    
    return data.get('data', {}).get('myself', {}).get('networkVolumes', [])


def create_volume(api_key: str, name: str, size: int, datacenter_id: str):
    """Create a new network volume"""
    mutation = """
    mutation createNetworkVolume($input: CreateNetworkVolumeInput!) {
        createNetworkVolume(input: $input) {
            id
            name
            size
            dataCenterId
        }
    }
    """
    variables = {
        "input": {
            "name": name,
            "size": size,
            "dataCenterId": datacenter_id
        }
    }
    
    response = requests.post(
        'https://api.runpod.io/graphql',
        headers={'Authorization': f'Bearer {api_key}'},
        json={'query': mutation, 'variables': variables}
    )
    response.raise_for_status()
    data = response.json()
    
    if 'errors' in data:
        raise Exception(f"GraphQL errors: {data['errors']}")
    
    return data.get('data', {}).get('createNetworkVolume')


def main():
    parser = argparse.ArgumentParser(
        description="Create a RunPod Network Volume for Ashoka",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--name', '-n', type=str, default='ashoka-storage',
                       help='Volume name (default: ashoka-storage)')
    parser.add_argument('--size', '-s', type=int, default=300,
                       help='Volume size in GB (default: 300 GB)')
    parser.add_argument('--datacenter', '-d', type=str, default=None,
                       help='Data center ID (e.g., EU-RO-1, US-GA-1). If not specified, lists available options.')
    parser.add_argument('--list-volumes', '-l', action='store_true',
                       help='List existing volumes')
    
    args = parser.parse_args()
    
    try:
        api_key = get_api_key()
    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    
    # List existing volumes
    if args.list_volumes:
        print("\n=== Existing Network Volumes ===")
        volumes = list_volumes(api_key)
        if volumes:
            for vol in volumes:
                print(f"  • {vol['name']} (ID: {vol['id']}, Size: {vol['size']}GB, DC: {vol['dataCenterId']})")
        else:
            print("  No volumes found.")
        return
    
    # List data centers if no datacenter specified
    if not args.datacenter:
        print("\n=== Available Data Centers ===")
        datacenters = list_datacenters(api_key)
        if datacenters:
            for dc in datacenters:
                print(f"  • {dc['id']}: {dc['name']} ({dc.get('location', 'N/A')})")
        else:
            print("  Could not retrieve data centers.")
        print("\nRe-run with --datacenter <ID> to create a volume.")
        print(f"Example: python {sys.argv[0]} --datacenter EU-RO-1")
        return
    
    # Create the volume
    print(f"\n🔄 Creating network volume...")
    print(f"   Name: {args.name}")
    print(f"   Size: {args.size}GB")
    print(f"   Data Center: {args.datacenter}")
    
    try:
        volume = create_volume(api_key, args.name, args.size, args.datacenter)
        
        if volume:
            print(f"\n✅ Volume created successfully!")
            print(f"   Volume ID: {volume['id']}")
            print(f"\n📝 Add this to your env file:")
            print(f"   NETWORK_VOLUME_ID={volume['id']}")
        else:
            print("\n❌ Failed to create volume - no data returned")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error creating volume: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
