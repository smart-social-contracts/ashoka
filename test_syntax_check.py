import ast
import sys

def check_syntax(filename):
    try:
        with open(filename, 'r') as f:
            source = f.read()
        ast.parse(source)
        print(f'✓ {filename} syntax valid')
        return True
    except SyntaxError as e:
        print(f'✗ {filename} syntax error: {e}')
        return False
    except Exception as e:
        print(f'✗ {filename} error: {e}')
        return False

if __name__ == "__main__":
    files_to_check = [
        'api.py',
        'database/db_client.py', 
        'tests/test_integration_ask_endpoint.py'
    ]

    print("Checking Python syntax...")
    
    all_valid = True
    for file in files_to_check:
        if not check_syntax(file):
            all_valid = False

    if all_valid:
        print('\n✓ All Python files have valid syntax')
        sys.exit(0)
    else:
        print('\n✗ Some files have syntax errors')
        sys.exit(1)
