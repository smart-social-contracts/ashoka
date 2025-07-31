import json
import logging
import os
import requests
import sys
import time
import traceback
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.embeddings import EmbeddingPipeline

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

SIMILARITY_THRESHOLD = 0.85
API_BASE_URL = os.environ.get('ASHOKA_API_URL', 'http://localhost:5000')

def setup_embedding_pipeline():
    return EmbeddingPipeline()

def setup_api_client():
    max_retries = 30
    retry_delay = 2
    
    print(f"Testing API at {API_BASE_URL}")
    for attempt in range(max_retries):
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                logger.info(f"API is ready at {API_BASE_URL}")
                return API_BASE_URL
        except requests.exceptions.RequestException:
            pass
        
        if attempt < max_retries - 1:
            logger.info(f"API not ready, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
            time.sleep(retry_delay)
    
    raise AssertionError(f"API at {API_BASE_URL} did not become ready within {max_retries * retry_delay} seconds")

def test_ask_endpoint_basic_functionality(api_client):
    print("Testing ask endpoint basic functionality...")
    url = f"{api_client}/api/ask"
    
    payload = {
        "user_principal": "user_test_001",
        "realm_principal": "realm_001", 
        "question": "How should a DAO allocate treasury funds for community development?"
    }
    
    response = requests.post(url, json=payload, timeout=30)
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert data["success"] is True, f"Request failed: {data}"
    assert "ai_response" in data, "Response should contain ai_response"
    assert "conversation_id" in data, "Response should contain conversation_id"
    assert "realm_data" in data, "Response should contain realm_data"
    
    assert len(data["ai_response"].strip()) > 0, "AI response should not be empty"
    
    print(f"✓ Basic ask endpoint test passed. Conversation ID: {data.get('conversation_id')}")
    return data

def test_ask_endpoint_semantic_similarity(api_client, embedding_pipeline):
    print("Testing ask endpoint semantic similarity...")
    url = f"{api_client}/api/ask"
    
    test_cases = [
        {
            "question": "How should a DAO allocate treasury funds for community development?",
            "expected_answer": "Treasury allocation should follow a balanced approach: 40% for developer grants to build ecosystem tools and applications, 30% for marketing and community outreach to attract new members, 20% for infrastructure improvements including security audits and platform upgrades, and 10% reserved as emergency funds. All allocations should be subject to community voting with clear milestones and accountability measures."
        },
        {
            "question": "What governance structure works best for a multi-stakeholder blockchain project?",
            "expected_answer": "A hybrid governance structure works best with specialized councils for different stakeholder groups: Technical Council for developers handling protocol upgrades, Token Holder Assembly for economic decisions, Validator Committee for network security matters, and User Advisory Board for UX/product decisions. Major decisions require approval from multiple councils with weighted voting based on stake and expertise relevance."
        }
    ]
    
    results = []
    passed_tests = 0
    
    for i, test_case in enumerate(test_cases):
        payload = {
            "user_principal": f"user_test_{i+2:03d}",
            "realm_principal": "realm_001",
            "question": test_case["question"]
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            assert response.status_code == 200, f"Request failed for test case {i+1}"
            
            data = response.json()
            assert data["success"] is True, f"Request failed for test case {i+1}: {data}"
            
            actual_answer = data["ai_response"]
            expected_answer = test_case["expected_answer"]
            
            actual_embedding = embedding_pipeline.encode_single(actual_answer)
            expected_embedding = embedding_pipeline.encode_single(expected_answer)
            
            similarity = embedding_pipeline.compute_similarity(actual_embedding, expected_embedding)
            
            results.append({
                "question": test_case["question"][:50] + "...",
                "similarity": similarity,
                "passed": similarity >= SIMILARITY_THRESHOLD,
                "conversation_id": data.get("conversation_id")
            })
            
            print(f"  Test case {i+1}: Similarity = {similarity:.3f} ({'PASS' if similarity >= SIMILARITY_THRESHOLD else 'FAIL'})")
            
            if similarity >= SIMILARITY_THRESHOLD:
                passed_tests += 1
            else:
                print(f"    ✗ Similarity {similarity:.3f} below threshold {SIMILARITY_THRESHOLD}")
                print(f"    Question: {test_case['question'][:50]}...")
                
        except Exception as e:
            print(f"  ✗ Test case {i+1} failed with error: {str(e)}")
    
    print(f"✓ Semantic similarity tests completed ({passed_tests}/{len(test_cases)} passed with threshold ≥ {SIMILARITY_THRESHOLD})")
    assert passed_tests >= len(test_cases) * 0.8, f"At least 80% of tests should pass, got {passed_tests}/{len(test_cases)}"
    return results

def test_database_storage_verification(api_client):
    print("Testing database storage verification...")
    url = f"{api_client}/api/ask"
    
    payload = {
        "user_principal": "user_db_test_001",
        "realm_principal": "realm_tech_002",
        "question": "What are best practices for DAO treasury management?"
    }
    
    response = requests.post(url, json=payload, timeout=30)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    conversation_id = data.get("conversation_id")
    assert conversation_id is not None, "Conversation ID should be returned"
    
    get_url = f"{api_client}/api/conversations/{conversation_id}"
    get_response = requests.get(get_url, timeout=10)
    
    assert get_response.status_code == 200, f"Failed to retrieve conversation: {get_response.text}"
    
    conversation_data = get_response.json()
    assert conversation_data["status"] == "success"
    
    conversation = conversation_data["conversation"]
    assert conversation["user_principal"] == payload["user_principal"]
    assert conversation["realm_principal"] == payload["realm_principal"]
    assert conversation["question"] == payload["question"]
    assert conversation["response"] == data["ai_response"]
    assert conversation["prompt_context"] is not None
    assert conversation["metadata"] is not None
    assert conversation["created_at"] is not None
    
    print(f"✓ Database storage verification passed. Conversation ID: {conversation_id}")
    return conversation_id

def test_missing_parameters(api_client):
    print("Testing missing parameters error handling...")
    url = f"{api_client}/api/ask"
    
    # Test missing user_principal
    payload = {
        "realm_principal": "realm_001",
        "question": "Test question"
    }
    response = requests.post(url, json=payload, timeout=10)
    assert response.status_code == 400
    data = response.json()
    assert "user_principal is required" in data["error"]
    
    # Test missing realm_principal
    payload = {
        "user_principal": "user_001",
        "question": "Test question"
    }
    response = requests.post(url, json=payload, timeout=10)
    assert response.status_code == 400
    data = response.json()
    assert "realm_principal is required" in data["error"]
    
    # Test missing question
    payload = {
        "user_principal": "user_001",
        "realm_principal": "realm_001"
    }
    response = requests.post(url, json=payload, timeout=10)
    assert response.status_code == 400
    data = response.json()
    assert "question is required" in data["error"]
    
    print("✓ Missing parameters error handling test passed")
    return True


def run_all_tests():
    """Run all API integration tests."""
    print("=" * 60)
    print("Running Ashoka API Integration Tests")
    print("=" * 60)
    
    failed_tests = []
    passed_tests = []
    
    try:
        # Setup
        print("\n--- Setup Phase ---")
        api_client = setup_api_client()
        embedding_pipeline = setup_embedding_pipeline()
        
        # Run tests
        print("\n--- Running Tests ---")
        
        tests = [
            ("Ask Endpoint Basic Functionality", lambda: test_ask_endpoint_basic_functionality(api_client)),
            ("Ask Endpoint Semantic Similarity", lambda: test_ask_endpoint_semantic_similarity(api_client, embedding_pipeline)),
            ("Database Storage Verification", lambda: test_database_storage_verification(api_client)),
            ("Missing Parameters Error Handling", lambda: test_missing_parameters(api_client)),
        ]
        
        for test_name, test_func in tests:
            try:
                test_func()
                passed_tests.append(test_name)
            except Exception as e:
                print(f"✗ {test_name} failed: {str(e)}")
                print(f"  Error details: {traceback.format_exc()}")
                failed_tests.append((test_name, str(e)))
            
    except Exception as e:
        print(f"Setup failed: {str(e)}")
        print(f"Error details: {traceback.format_exc()}")
        return False
    
    # Results
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    print(f"Passed: {len(passed_tests)}")
    print(f"Failed: {len(failed_tests)}")
    
    if passed_tests:
        print("\nPassed tests:")
        for test in passed_tests:
            print(f"  ✓ {test}")
    
    if failed_tests:
        print("\nFailed tests:")
        for test, error in failed_tests:
            print(f"  ✗ {test}: {error}")
    
    success = len(failed_tests) == 0
    print(f"\nOverall result: {'SUCCESS' if success else 'FAILURE'}")
    return success


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
