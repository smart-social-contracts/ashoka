import sys
sys.path.append('.')

def test_database_import():
    try:
        from database.db_client import DatabaseClient
        print('✓ Database client import successful')
        return True
    except Exception as e:
        print(f'✗ Database client import failed: {e}')
        return False

def test_fixture_loading():
    try:
        import json
        with open('fixtures/realm_sample.json') as f:
            data = json.load(f)
        print('✓ Realm fixture loading successful')
        print(f'  - Realm: {data["name"]}')
        print(f'  - Treasury: {data["treasury"]["total_funds"]} {data["treasury"]["currency"]}')
        return True
    except Exception as e:
        print(f'✗ Realm fixture loading failed: {e}')
        return False

def test_persona_loading():
    try:
        with open('cli/prompts/governor_init.txt') as f:
            persona = f.read()
        print('✓ Ashoka persona loading successful')
        print(f'  - Length: {len(persona)} characters')
        return True
    except Exception as e:
        print(f'✗ Ashoka persona loading failed: {e}')
        return False

if __name__ == "__main__":
    print("Testing basic functionality...")
    
    tests = [
        test_database_import,
        test_fixture_loading, 
        test_persona_loading
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
    
    print(f"\nResults: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("✓ All basic functionality tests passed")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)
