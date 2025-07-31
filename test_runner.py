#!/usr/bin/env python3
"""
CI Test Runner - Semantic validation of Ashoka's answers
"""
import json
import requests
import time
import warnings
import os

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

def load_test_cases(file_path):
    """Load test cases from JSONL file"""
    test_cases = []
    with open(file_path, 'r') as f:
        for line in f:
            test_cases.append(json.loads(line.strip()))
    return test_cases

def ask_ashoka(question, api_url="http://localhost:5000/api/ask"):
    """Ask Ashoka a question via API"""
    try:
        print(f"Asking: {question[:50]}...")
        response = requests.post(api_url, json={
            "user_principal": "test_user",
            "realm_principal": "test_realm",
            "question": question
        }, timeout=60)  # Increased timeout
        
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

def semantic_similarity(text1, text2):
    """Calculate semantic similarity between two texts"""
    embeddings = model.encode([text1, text2])
    similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
    return float(similarity)

def run_tests(test_file="tests/tests.jsonl"):
    """Run all tests and return results"""
    print("Loading test cases...")
    test_cases = load_test_cases(test_file)
    
    results = []
    total_tests = len(test_cases)
    
    print(f"Running {total_tests} tests...")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}/{total_tests}: {test_case['question'][:60]}...")
        
        # Ask Ashoka
        actual_answer = ask_ashoka(test_case['question'])
        expected_answer = test_case['expected_answer']
        
        # Calculate semantic similarity
        similarity = semantic_similarity(actual_answer, expected_answer)
        
        # Determine pass/fail (threshold: 0.7)
        passed = similarity >= 0.7
        
        result = {
            'test_id': i,
            'question': test_case['question'],
            'expected_answer': expected_answer,
            'actual_answer': actual_answer,
            'similarity_score': similarity,
            'passed': passed
        }
        
        results.append(result)
        
        print(f"Similarity: {similarity:.3f} - {'PASS' if passed else 'FAIL'}")
        
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

if __name__ == "__main__":
    print("Ashoka CI Test Runner")
    print("=" * 50)
    
    # Run tests
    results = run_tests()
    
    # Print summary
    print_summary(results)
    
    # Save results
    save_results(results)
    
    # Exit with appropriate code
    failed_count = sum(1 for r in results if not r['passed'])
    exit(0 if failed_count == 0 else 1)
