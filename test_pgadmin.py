#!/usr/bin/env python3
"""
Test script to verify pgAdmin4 is running correctly
"""
import requests
import time
import sys

def test_pgadmin_availability():
    """Test if pgAdmin4 web interface is accessible"""
    max_retries = 30
    wait_time = 2
    
    print("Testing pgAdmin4 availability...")
    
    for attempt in range(max_retries):
        try:
            # Test if pgAdmin4 is responding
            response = requests.get('http://localhost:80', timeout=5, allow_redirects=True)
            if response.status_code in [200, 302]:  # 302 is redirect to login
                print(f"✓ pgAdmin4 is running and accessible at http://localhost:80")
                print(f"✓ Response status: {response.status_code}")
                return True
            else:
                print(f"✗ Unexpected status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1}/{max_retries}: pgAdmin4 not yet available - {e}")
            if attempt < max_retries - 1:
                time.sleep(wait_time)
            continue
    
    print("✗ pgAdmin4 failed to become available within the timeout period")
    return False

def test_database_connection():
    """Test if PostgreSQL is running and accessible"""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost",
            database="ashoka_db",
            user="ashoka_user",
            password="ashoka_pass",
            port="5432"
        )
        conn.close()
        print("✓ PostgreSQL database is accessible")
        return True
    except Exception as e:
        print(f"✗ PostgreSQL connection failed: {e}")
        return False

def main():
    """Main test function"""
    print("Running pgAdmin4 startup tests...")
    print("="*50)
    
    # Test database first
    db_ok = test_database_connection()
    
    # Test pgAdmin4 web interface
    pgadmin_ok = test_pgadmin_availability()
    
    print("="*50)
    if db_ok and pgadmin_ok:
        print("✓ All tests passed! pgAdmin4 is ready to use.")
        print("\nAccess information:")
        print("  URL: http://localhost:80")
        print("  Email: admin@ashoka.local")
        print("  Password: ashoka_admin_pass")
        print("  Pre-configured server: Ashoka PostgreSQL (localhost:5432)")
        return 0
    else:
        print("✗ Some tests failed. Check the logs for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())