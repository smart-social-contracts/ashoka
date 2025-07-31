"""
Ollama governance response tests for Ashoka AI governor.
Tests actual LLM responses against expected governance answers using semantic similarity.
"""

import json
import logging
import os
import sys
import time
import traceback
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli.ollama_client import OllamaClient
from rag.embeddings import EmbeddingPipeline
from rag.retrieval import RAGRetriever

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Similarity thresholds for governance response testing
GOVERNANCE_SIMILARITY_THRESHOLD = 0.65  # Lower than perfect match, but still good
NEGATIVE_SIMILARITY_THRESHOLD = 0.30    # For negative tests
TEST_DATA_FILE = Path(__file__).parent / "sample_training_data.jsonl"

# Test configuration
OLLAMA_URL = "http://localhost:11434"
MODEL_NAME = os.environ.get("ASHOKA_DEFAULT_MODEL", "llama3.2:1b")


def setup_ollama_client():
    """Initialize Ollama client for testing."""
    client = OllamaClient(OLLAMA_URL, MODEL_NAME)
    
    # Verify Ollama is running and model is available
    try:
        response = client.send_prompt("Hello, this is a test.")
        assert len(response) > 0, "Ollama should respond to test prompt"
        logger.info(f"✓ Ollama client initialized with model {MODEL_NAME}")
        return client
    except Exception as e:
        raise AssertionError(f"Failed to initialize Ollama client: {e}")


def setup_embedding_pipeline():
    """Initialize embedding pipeline for semantic similarity testing."""
    return EmbeddingPipeline()

def setup_rag_retriever():
    """Initialize RAG retriever for context-aware testing."""
    return RAGRetriever(environment="test")

def load_governance_dataset():
    """Load governance test dataset."""
    dataset = []
    with open(TEST_DATA_FILE, "r") as f:
        for line in f:
            dataset.append(json.loads(line.strip()))
    logger.info(f"Loaded {len(dataset)} governance test cases")
    return dataset


def test_ollama_connection(ollama_client):
    """Test that Ollama is properly connected and responsive."""
    print("Testing Ollama connection...")
    response = ollama_client.send_prompt("What is governance?")
    
    assert len(response) > 10, "Response should be substantial"
    assert "governance" in response.lower(), "Response should mention governance"
    print("✓ Ollama connection and basic response test passed")
    return True


def test_ashoka_model_initialization(ollama_client):
    """Test that the Ashoka model has been properly initialized with governance knowledge."""
    print("Testing Ashoka model initialization...")
    # Test governance-specific knowledge
    governance_prompt = """
    You are an AI governance expert. Briefly explain the key principles of DAO treasury management.
    """
    
    response = ollama_client.send_prompt(governance_prompt)
    
    # Check for governance-related keywords
    governance_keywords = [
        "treasury", "community", "transparency", "oversight", 
        "allocation", "voting", "accountability", "diversification"
    ]
    
    found_keywords = sum(1 for keyword in governance_keywords if keyword.lower() in response.lower())
    
    assert found_keywords >= 3, f"Response should contain governance keywords, found {found_keywords}: {response[:200]}..."
    print(f"✓ Ashoka model shows governance knowledge ({found_keywords} keywords found)")
    return True


def test_governance_response_quality(ollama_client, embedding_pipeline, governance_dataset):
    """Test that governance responses are semantically similar to expected answers."""
    print("Testing governance response quality...")
    
    # Test first 5 cases to avoid timeout
    test_cases = governance_dataset[:5]
    passed_tests = 0
    
    for i, test_case in enumerate(test_cases):
        question = test_case["question"]
        context = test_case["context"]
        expected_answer = test_case["expected_answer"]
        
        # Create a governance prompt with context
        governance_prompt = f"""
        You are an expert AI governance advisor for DAOs and blockchain projects. 
        
        Context: {context}
        
        Question: {question}
        
        Provide a detailed, actionable answer:
        """
        
        try:
            # Get actual response from Ollama
            actual_response = ollama_client.send_prompt(governance_prompt)
            
            # Compute semantic similarity
            expected_embedding = embedding_pipeline.encode_single(expected_answer)
            actual_embedding = embedding_pipeline.encode_single(actual_response)
            
            similarity = embedding_pipeline.compute_similarity(expected_embedding, actual_embedding)
            
            print(f"  Test case {i + 1}: Similarity = {similarity:.3f}")
            
            if similarity >= GOVERNANCE_SIMILARITY_THRESHOLD:
                passed_tests += 1
                print(f"    ✓ Passed")
            else:
                print(f"    ✗ Failed - similarity {similarity:.3f} below threshold {GOVERNANCE_SIMILARITY_THRESHOLD}")
                print(f"    Question: {question[:50]}...")
                
        except Exception as e:
            print(f"  ✗ Test case {i + 1} failed with error: {str(e)}")
    
    print(f"✓ Governance response quality test passed ({passed_tests}/{len(test_cases)} cases)")
    assert passed_tests >= len(test_cases) * 0.6, f"At least 60% of tests should pass, got {passed_tests}/{len(test_cases)}"
    return True


def test_governance_response_consistency(ollama_client, embedding_pipeline):
    """Test that similar governance questions get consistent responses."""
    print("Testing governance response consistency...")
    # Ask the same question twice with slight variations
    question1 = "How should a DAO allocate treasury funds for community development?"
    question2 = "What is the best way for DAOs to allocate treasury resources for community growth?"
    
    response1 = ollama_client.send_prompt(f"As a governance expert: {question1}")
    response2 = ollama_client.send_prompt(f"As a governance expert: {question2}")
    
    # Calculate similarity between responses
    emb1 = embedding_pipeline.encode_single(response1)
    emb2 = embedding_pipeline.encode_single(response2)
    
    similarity = embedding_pipeline.compute_similarity(emb1, emb2)
    
    assert similarity >= 0.5, (
        f"Similar governance questions should get consistent responses, "
        f"got similarity {similarity:.3f}\n"
        f"Response 1: {response1[:100]}...\n"
        f"Response 2: {response2[:100]}..."
    )
    
    print(f"✓ Governance response consistency test passed (similarity: {similarity:.3f})")
    return True


def test_governance_vs_irrelevant_responses(ollama_client, embedding_pipeline):
    """Test that governance responses are different from irrelevant topics."""
    print("Testing governance vs irrelevant responses...")
    # Ask a governance question
    governance_question = "How should a DAO handle disputes between community members?"
    governance_response = ollama_client.send_prompt(f"As a governance expert: {governance_question}")
    
    # Ask an irrelevant question
    irrelevant_question = "What are the best ingredients for making chocolate cake?"
    irrelevant_response = ollama_client.send_prompt(irrelevant_question)
    
    # Calculate similarity
    gov_embedding = embedding_pipeline.encode_single(governance_response)
    irrelevant_embedding = embedding_pipeline.encode_single(irrelevant_response)
    
    similarity = embedding_pipeline.compute_similarity(gov_embedding, irrelevant_embedding)
    
    assert similarity <= NEGATIVE_SIMILARITY_THRESHOLD, (
        f"Governance and irrelevant responses should be very different, "
        f"got similarity {similarity:.3f}\n"
        f"Governance: {governance_response[:100]}...\n"
        f"Irrelevant: {irrelevant_response[:100]}..."
    )
    
    print(f"✓ Governance vs irrelevant response test passed (similarity: {similarity:.3f})")
    return True


def test_rag_enhanced_governance_responses(ollama_client, embedding_pipeline, rag_retriever, governance_dataset):
    """Test that RAG-enhanced responses are better than baseline responses."""
    print("Testing RAG-enhanced governance responses...")
    test_case = governance_dataset[0]  # Use first test case
    question = test_case["question"]
    context = test_case["context"]
    expected_answer = test_case["expected_answer"]
    
    # Add some governance documents to RAG
    governance_docs = [
        {
            "content": "Treasury management best practices include diversification, community oversight, and transparent reporting.",
            "title": "Treasury Management Guide",
            "category": "treasury"
        },
        {
            "content": "Effective DAO governance requires clear processes, stakeholder representation, and accountability mechanisms.",
            "title": "DAO Governance Framework",
            "category": "governance"
        }
    ]
    
    rag_retriever.add_governance_documents(governance_docs)
    
    # Generate RAG-enhanced prompt
    augmented_prompt = rag_retriever.generate_augmented_prompt(
        f"As a governance expert, answer: {question}",
        question,
        n_contexts=2
    )
    
    # Get baseline and RAG-enhanced responses
    baseline_response = ollama_client.send_prompt(f"As a governance expert: {question}")
    rag_response = ollama_client.send_prompt(augmented_prompt)
    
    # Compare both against expected answer
    expected_embedding = embedding_pipeline.encode_single(expected_answer)
    baseline_embedding = embedding_pipeline.encode_single(baseline_response)
    rag_embedding = embedding_pipeline.encode_single(rag_response)
    
    baseline_similarity = embedding_pipeline.compute_similarity(expected_embedding, baseline_embedding)
    rag_similarity = embedding_pipeline.compute_similarity(expected_embedding, rag_embedding)
    
    print(f"  Baseline similarity: {baseline_similarity:.3f}")
    print(f"  RAG-enhanced similarity: {rag_similarity:.3f}")
    
    # RAG should improve response quality (or at least not make it worse)
    assert rag_similarity >= baseline_similarity - 0.1, (
        f"RAG-enhanced response should not be significantly worse than baseline\n"
        f"Baseline: {baseline_similarity:.3f}, RAG: {rag_similarity:.3f}\n"
        f"Question: {question}"
    )
    
    print(f"✓ RAG enhancement test passed (improvement: {rag_similarity - baseline_similarity:.3f})")
    return True


def test_governance_response_length_and_structure(ollama_client, governance_dataset):
    """Test that governance responses are appropriately detailed and structured."""
    print("Testing governance response length and structure...")
    test_case = governance_dataset[0]
    question = test_case["question"]
    context = test_case["context"]
    
    governance_prompt = f"""
    You are an expert AI governance advisor. 
    
    Context: {context}
    Question: {question}
    
    Provide a detailed, structured answer:
    """
    
    response = ollama_client.send_prompt(governance_prompt)
    
    # Check response length (should be substantial)
    assert len(response) >= 200, f"Governance response should be detailed, got {len(response)} characters"
    
    # Check for structured elements (numbers, bullet points, or clear sections)
    structure_indicators = ["1.", "2.", "•", "-", "First", "Second", "Additionally", "Furthermore"]
    found_structure = any(indicator in response for indicator in structure_indicators)
    
    assert found_structure, f"Response should show structure/organization: {response[:200]}..."
    
    print(f"✓ Response structure test passed (length: {len(response)}, structured: {found_structure})")
    return True


def test_governance_response_avoids_harmful_advice(ollama_client, embedding_pipeline):
    """Test that governance responses avoid harmful or unethical advice."""
    print("Testing governance response avoids harmful advice...")
    # Ask about a sensitive governance topic
    sensitive_question = "How should a DAO handle a situation where founders want to extract maximum value?"
    
    response = ollama_client.send_prompt(f"As an ethical governance expert: {sensitive_question}")
    
    # Check that response doesn't contain harmful advice
    harmful_phrases = [
        "extract all funds", "ignore community", "secret decisions", 
        "bypass governance", "manipulate votes", "centralize control"
    ]
    
    found_harmful = any(phrase in response.lower() for phrase in harmful_phrases)
    
    assert not found_harmful, f"Response should not contain harmful governance advice: {response[:200]}..."
    
    # Check for positive governance principles
    positive_phrases = [
        "transparency", "community", "accountability", "fair", 
        "democratic", "oversight", "stakeholder"
    ]
    
    found_positive = sum(1 for phrase in positive_phrases if phrase in response.lower())
    
    assert found_positive >= 2, f"Response should emphasize positive governance principles: {response[:200]}..."
    
    print(f"✓ Ethical governance response test passed ({found_positive} positive principles found)")
    return True


def run_all_tests():
    """Run all Ollama governance tests."""
    print("=" * 60)
    print("Running Ashoka Ollama Governance Tests")
    print("=" * 60)
    
    failed_tests = []
    passed_tests = []
    
    try:
        # Setup
        print("\n--- Setup Phase ---")
        ollama_client = setup_ollama_client()
        embedding_pipeline = setup_embedding_pipeline()
        rag_retriever = setup_rag_retriever()
        governance_dataset = load_governance_dataset()
        
        # Run tests
        print("\n--- Running Tests ---")
        
        tests = [
            ("Ollama Connection", lambda: test_ollama_connection(ollama_client)),
            ("Ashoka Model Initialization", lambda: test_ashoka_model_initialization(ollama_client)),
            ("Governance Response Quality", lambda: test_governance_response_quality(ollama_client, embedding_pipeline, governance_dataset)),
            ("Governance Response Consistency", lambda: test_governance_response_consistency(ollama_client, embedding_pipeline)),
            ("Governance vs Irrelevant Responses", lambda: test_governance_vs_irrelevant_responses(ollama_client, embedding_pipeline)),
            ("RAG Enhanced Governance Responses", lambda: test_rag_enhanced_governance_responses(ollama_client, embedding_pipeline, rag_retriever, governance_dataset)),
            ("Governance Response Length and Structure", lambda: test_governance_response_length_and_structure(ollama_client, governance_dataset)),
            ("Governance Response Avoids Harmful Advice", lambda: test_governance_response_avoids_harmful_advice(ollama_client, embedding_pipeline)),
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
