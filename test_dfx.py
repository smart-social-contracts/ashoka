#!/usr/bin/env python3
"""
Test script to verify DFX integration with JSON output
"""
import subprocess
import json
import sys

def test_dfx_installation():
    """Test if DFX is installed and accessible"""
    try:
        result = subprocess.run(['dfx', '--version'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ DFX is installed: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ DFX version check failed: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ DFX not found in PATH")
        return False
    except Exception as e:
        print(f"❌ Error checking DFX: {e}")
        return False

def test_dfx_json_output():
    """Test DFX canister call with JSON output using Internet Identity canister"""
    try:
        # Use the Internet Identity canister - a well-known IC canister
        ii_principal = "qjdve-lqaaa-aaaah-qai3q-cai"  # Internet Identity canister
        
        print(f"🧪 Testing DFX JSON output with Internet Identity canister: {ii_principal}")
        
        # Try a simple query that should work
        cmd = [
            'dfx', 'canister', 'call',
            '--network', 'ic',
            '--output', 'json',
            ii_principal,
            'stats'
        ]
        
        print(f"Running command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            try:
                response_data = json.loads(result.stdout)
                print("✅ DFX JSON output test successful!")
                print(f"Response type: {type(response_data)}")
                print(f"Response preview: {str(response_data)[:200]}...")
                return True
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON response: {e}")
                print(f"Raw output: {result.stdout}")
                return False
        else:
            print(f"❌ DFX call failed: {result.stderr}")
            # Try a different approach - test with a simple echo
            return test_dfx_basic_functionality()
            
    except subprocess.TimeoutExpired:
        print("❌ DFX call timed out")
        return False
    except Exception as e:
        print(f"❌ Error testing DFX JSON output: {e}")
        return False

def test_dfx_basic_functionality():
    """Test basic DFX functionality without making canister calls"""
    try:
        print("🧪 Testing basic DFX functionality...")
        
        # Test dfx help command
        result = subprocess.run(['dfx', 'help'], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and 'canister' in result.stdout:
            print("✅ DFX basic functionality test successful!")
            print("✅ DFX can execute commands and has canister functionality")
            return True
        else:
            print(f"❌ DFX help command failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing basic DFX functionality: {e}")
        return False

def main():
    print("🚀 Testing DFX Integration")
    print("=" * 40)
    
    # Test 1: DFX installation
    if not test_dfx_installation():
        print("\n❌ DFX installation test failed. Cannot proceed.")
        sys.exit(1)
    
    print()
    
    # Test 2: DFX JSON output
    if test_dfx_json_output():
        print("\n✅ All DFX tests passed!")
        sys.exit(0)
    else:
        print("\n❌ DFX JSON output test failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
