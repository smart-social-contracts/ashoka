#!/usr/bin/env python3
"""
CI Test Runner - Semantic validation of Ashoka's answers

Supports two modes:
- Legacy mode: Uses /api/ask with mock realm_status JSON
- Tool mode (--use-tools): Uses /api/ask-with-tools with real realm data via tool calling
"""
import json
import requests
import time
import warnings
import os
import glob
import argparse

# Suppress warnings
warnings.filterwarnings('ignore')
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Load semantic similarity model
print("Loading semantic similarity model...")
try:
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print("Model loaded successfully!")
except Exception as e:
    print(f"Error loading model: {e}")
    exit(1)

def load_test_cases(tests_dir="tests"):
    """Load test cases from individual JSON files in the tests directory"""
    test_cases = []
    json_files = glob.glob(os.path.join(tests_dir, "*.json"))
    
    for file_path in sorted(json_files):
        with open(file_path, 'r') as f:
            test_case = json.load(f)
            test_cases.append(test_case)
    
    return test_cases

def ask_ashoka(question, realm_status=None, api_url="http://localhost:5000/api/ask"):
    """Ask Ashoka a question via API with optional realm context (legacy mode)"""
    try:
        print(f"Asking: {question[:50]}...")
        payload = {
            "user_principal": "test_user",
            "realm_principal": "test_realm",
            "question": question
        }
        
        # Add realm_status if provided
        if realm_status:
            payload["realm_status"] = realm_status
            
        response = requests.post(api_url, json=payload, timeout=60)  # Increased timeout
        
        if response.status_code == 200:
            answer = response.json().get('answer', '')
            print(f"Got answer: {len(answer)} characters")
            return answer
        else:
            error_msg = f"API Error: {response.status_code}"
            print(error_msg)
            return error_msg
    except Exception as e:
        error_msg = f"Request Error: {str(e)}"
        print(error_msg)
        return error_msg


def ask_ashoka_with_tools(question, realm_folder, network="local", api_url="http://localhost:5000/api/ask-with-tools"):
    """Ask Ashoka a question using tool calling with real realm data"""
    try:
        print(f"Asking (with tools): {question[:50]}...")
        payload = {
            "question": question,
            "realm_folder": realm_folder,
            "network": network
        }
            
        response = requests.post(api_url, json=payload, timeout=120)  # Longer timeout for tool calls
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get('answer', '')
            tools_used = result.get('tools_used', False)
            print(f"Got answer: {len(answer)} characters (tools_used: {tools_used})")
            return answer
        else:
            error_msg = f"API Error: {response.status_code}"
            print(error_msg)
            return error_msg
    except Exception as e:
        error_msg = f"Request Error: {str(e)}"
        print(error_msg)
        return error_msg

def semantic_similarity(text1, text2):
    """Calculate semantic similarity between two texts"""
    embeddings = model.encode([text1, text2])
    similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
    return float(similarity)

def run_tests(tests_dir="tests", use_tools=False, realm_folder=None, network="local"):
    """Run all tests and return results"""
    print("Loading test cases...")
    test_cases = load_test_cases(tests_dir)
    
    results = []
    total_tests = len(test_cases)
    
    mode = "tool calling" if use_tools else "legacy"
    print(f"Running {total_tests} tests in {mode} mode...")
    if use_tools:
        print(f"  Realm folder: {realm_folder}")
        print(f"  Network: {network}")
    
    for i, test_case in enumerate(test_cases, 1):
        test_name = test_case.get('name', f'test_{i}')
        user_prompt = test_case['user_prompt']
        print(f"\nTest {i}/{total_tests} ({test_name}): {user_prompt[:60]}...")
        
        # Ask Ashoka - use tools mode or legacy mode
        if use_tools:
            actual_answer = ask_ashoka_with_tools(user_prompt, realm_folder, network)
        else:
            realm_status = test_case.get('realm_status')  # Extract realm context for legacy mode
            actual_answer = ask_ashoka(user_prompt, realm_status)
        
        expected_answer = test_case['expected_answer']
        
        # Calculate semantic similarity
        similarity = semantic_similarity(actual_answer, expected_answer)
        
        threshold = test_case.get('semantic_threshold', 0.7)
        passed = similarity >= threshold
        
        result = {
            'test_id': i,
            'test_name': test_name,
            'question': user_prompt,
            'expected_answer': expected_answer,
            'actual_answer': actual_answer,
            'similarity_score': similarity,
            'threshold': threshold,
            'passed': passed
        }
        
        results.append(result)
        
        print(f"Similarity: {similarity:.3f} (threshold: {threshold:.3f}) - {'PASS' if passed else 'FAIL'}")
        
        # Small delay to avoid overwhelming the API
        time.sleep(1)
    
    return results

def print_summary(results):
    """Print test summary"""
    total = len(results)
    passed = sum(1 for r in results if r['passed'])
    failed = total - passed
    avg_similarity = np.mean([r['similarity_score'] for r in results])
    
    print(f"\n{'='*50}")
    print(f"TEST SUMMARY")
    print(f"{'='*50}")
    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Pass Rate: {passed/total*100:.1f}%")
    print(f"Average Similarity: {avg_similarity:.3f}")
    
    if failed > 0:
        print(f"\nFAILED TESTS:")
        for r in results:
            if not r['passed']:
                print(f"- Test {r['test_id']}: {r['similarity_score']:.3f} - {r['question'][:60]}...")

def save_results(results, output_file="test_results.json"):
    """Save detailed results to JSON file"""
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed results saved to: {output_file}")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Ashoka CI Test Runner')
    parser.add_argument('--use-tools', action='store_true',
                        help='Use tool calling mode with real realm data')
    parser.add_argument('--realm-folder', type=str,
                        default=os.environ.get('REALM_FOLDER', '.'),
                        help='Path to realm folder (default: from REALM_FOLDER env or current dir)')
    parser.add_argument('--network', type=str,
                        default=os.environ.get('REALM_NETWORK', 'local'),
                        help='Network to use (default: from REALM_NETWORK env or local)')
    parser.add_argument('--tests-dir', type=str, default='tests',
                        help='Directory containing test JSON files')
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    
    print("Ashoka CI Test Runner")
    print("=" * 50)
    
    # Run tests
    results = run_tests(
        tests_dir=args.tests_dir,
        use_tools=args.use_tools,
        realm_folder=args.realm_folder,
        network=args.network
    )
    
    # Print summary
    print_summary(results)
    
    # Save results
    save_results(results)
    
    # Exit with appropriate code
    failed_count = sum(1 for r in results if not r['passed'])
    exit(0 if failed_count == 0 else 1)
