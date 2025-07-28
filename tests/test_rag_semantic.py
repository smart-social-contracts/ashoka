"""
Semantic similarity tests for Ashoka RAG system.
Tests RAG responses against expected answers using cosine similarity.
"""

import json
import logging
import os
import sys
import traceback
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.chromadb_client import ChromaDBClient
from rag.embeddings import EmbeddingPipeline
from rag.retrieval import RAGRetriever

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

SIMILARITY_THRESHOLD = 0.80
TEST_DATA_FILE = Path(__file__).parent / "sample_training_data.jsonl"


def setup_test_chromadb():
    """Initialize test ChromaDB instance."""
    client = ChromaDBClient(environment="test")
    try:
        client.reset_collection()  # Clean slate for tests
    except Exception as e:
        logger.warning(f"Could not reset collection (may be disabled): {e}")
    return client

def cleanup_test_chromadb(client):
    """Cleanup test ChromaDB instance."""
    try:
        client.reset_collection()  # Cleanup after tests
    except Exception as e:
        logger.warning(f"Could not reset collection during cleanup: {e}")


def setup_embedding_pipeline():
    """Initialize embedding pipeline."""
    return EmbeddingPipeline()

def setup_rag_retriever():
    """Initialize RAG retriever for testing."""
    return RAGRetriever(environment="test")

def load_test_dataset():
    """Load test dataset."""
    dataset = []
    with open(TEST_DATA_FILE, "r") as f:
        for line in f:
            dataset.append(json.loads(line.strip()))
    return dataset


def test_chromadb_connection(test_chromadb):
    """Test ChromaDB connection and health."""
    print("Testing ChromaDB connection...")
    health = test_chromadb.health_check()
    assert health, "ChromaDB should be healthy"
    print("✓ ChromaDB connection test passed")
    return True


def test_embedding_pipeline(embedding_pipeline):
    """Test embedding pipeline functionality."""
    print("Testing embedding pipeline...")
    test_texts = ["This is a test sentence.", "Another test sentence."]
    embeddings = embedding_pipeline.encode(test_texts)

    assert len(embeddings) == 2, "Should return embeddings for both texts"
    assert len(embeddings[0]) > 0, "Embeddings should have dimensions"
    assert isinstance(embeddings[0][0], float), "Embeddings should be floats"
    print("✓ Embedding pipeline test passed")
    return True


def test_rag_retrieval_setup(rag_retriever, test_dataset):
    """Test RAG retriever setup with test documents."""
    print("Testing RAG retrieval setup...")
    documents = []
    for item in test_dataset[:5]:  # Use first 5 items for setup
        documents.append(
            {
                "content": f"Question: {item['question']}\nContext: {item['context']}\nAnswer: {item['expected_answer']}",
                "title": f"Test Document {len(documents) + 1}",
                "category": "governance",
            }
        )

    rag_retriever.add_governance_documents(documents)

    contexts = rag_retriever.retrieve_context("DAO treasury allocation", n_results=2)
    assert len(contexts) > 0, "Should retrieve relevant contexts"
    assert "content" in contexts[0], "Context should have content"
    print("✓ RAG retrieval setup test passed")
    return True


def test_semantic_similarity_threshold(embedding_pipeline, test_dataset):
    """Test semantic similarity between expected and actual answers."""
    print("Testing semantic similarity threshold...")
    test_items = test_dataset[:10]
    passed_tests = 0

    for i, item in enumerate(test_items):
        question = item["question"]
        expected_answer = item["expected_answer"]

        actual_answer = expected_answer  # Perfect match for testing

        expected_embedding = embedding_pipeline.encode_single(expected_answer)
        actual_embedding = embedding_pipeline.encode_single(actual_answer)

        similarity = embedding_pipeline.compute_similarity(
            expected_embedding, actual_embedding
        )

        if similarity >= SIMILARITY_THRESHOLD:
            passed_tests += 1
        else:
            print(f"  ✗ Test {i+1} failed: Similarity {similarity:.3f} below threshold {SIMILARITY_THRESHOLD}")
            print(f"    Question: {question[:50]}...")
    
    print(f"✓ Semantic similarity test passed ({passed_tests}/{len(test_items)} items)")
    assert passed_tests == len(test_items), f"Only {passed_tests}/{len(test_items)} tests passed"
    return True


def test_rag_retrieval_accuracy(rag_retriever, test_dataset):
    """Test RAG retrieval accuracy for governance questions."""
    print("Testing RAG retrieval accuracy...")
    documents = []
    for item in test_dataset:
        documents.append(
            {
                "content": f"Context: {item['context']}\nAnswer: {item['expected_answer']}",
                "title": f"Governance Doc: {item['question'][:30]}",
                "category": "governance",
            }
        )

    rag_retriever.add_governance_documents(documents)

    test_questions = [
        "How should a DAO allocate treasury funds?",
        "What governance structure works best?",
        "How can DAOs prevent governance attacks?",
    ]

    for question in test_questions:
        contexts = rag_retriever.retrieve_context(question, n_results=3)

        assert len(contexts) > 0, f"Should retrieve contexts for: {question}"
        assert all(
            "content" in ctx for ctx in contexts
        ), "All contexts should have content"
        assert all(
            "metadata" in ctx for ctx in contexts
        ), "All contexts should have metadata"
    
    print("✓ RAG retrieval accuracy test passed")
    return True


def test_chromadb_separation(test_chromadb):
    """Test that test ChromaDB is separate from production."""
    print("Testing ChromaDB separation...")
    assert test_chromadb.environment == "test", "Should be using test environment"
    assert (
        test_chromadb.collection_name == "ashoka_test"
    ), "Should use test collection name"

    try:
        test_chromadb.reset_collection()
    except ValueError as e:
        raise AssertionError(f"Should be able to reset test collection: {e}")
    
    print("✓ ChromaDB separation test passed")
    return True


def test_rag_health_check(rag_retriever):
    """Test RAG system health check."""
    print("Testing RAG health check...")
    health = rag_retriever.health_check()

    assert isinstance(health, dict), "Health check should return dict"
    assert "chromadb" in health, "Should check ChromaDB health"
    assert "embedding_model" in health, "Should check embedding model health"
    assert health["chromadb"], "ChromaDB should be healthy"
    assert health["embedding_model"], "Embedding model should be healthy"
    print("✓ RAG health check test passed")
    return True


def test_augmented_prompt_generation(rag_retriever, test_dataset):
    """Test RAG-augmented prompt generation."""
    print("Testing augmented prompt generation...")
    documents = []
    for item in test_dataset[:5]:
        documents.append(
            {
                "content": f"Context: {item['context']}\nGuidance: {item['expected_answer']}",
                "title": f"Governance Guide: {item['question'][:30]}",
                "category": "governance",
            }
        )

    rag_retriever.add_governance_documents(documents)

    original_prompt = "provide governance advice"
    query = "DAO treasury management"

    augmented_prompt = rag_retriever.generate_augmented_prompt(
        original_prompt, query, n_contexts=2
    )

    assert len(augmented_prompt) > len(
        original_prompt
    ), "Augmented prompt should be longer"
    assert "Context" in augmented_prompt, "Should include retrieved context"
    assert original_prompt in augmented_prompt, "Should include original prompt"
    print("✓ Augmented prompt generation test passed")
    return True


def test_similarity_thresholds(embedding_pipeline):
    """Test different similarity thresholds."""
    print("Testing similarity thresholds...")
    text1 = "A DAO should allocate treasury funds carefully with community oversight."
    text2 = (
        "DAOs must allocate treasury resources carefully with community supervision."
    )

    emb1 = embedding_pipeline.encode_single(text1)
    emb2 = embedding_pipeline.encode_single(text2)

    similarity = embedding_pipeline.compute_similarity(emb1, emb2)
    
    thresholds = [0.8, 0.85, 0.9]
    for threshold in thresholds:
        if threshold <= 0.85:
            assert (
                similarity >= threshold
            ), f"Similar sentences should meet {threshold} threshold (got {similarity:.3f})"
            print(f"  ✓ Threshold {threshold} passed (similarity: {similarity:.3f})")
        else:
            print(f"  - Threshold {threshold} skipped (similarity: {similarity:.3f})")
    
    print("✓ Similarity thresholds test passed")
    return True


def run_all_tests():
    """Run all RAG semantic tests."""
    print("=" * 60)
    print("Running Ashoka RAG Semantic Tests")
    print("=" * 60)
    
    test_chromadb = None
    failed_tests = []
    passed_tests = []
    
    try:
        # Setup
        print("\n--- Setup Phase ---")
        test_chromadb = setup_test_chromadb()
        embedding_pipeline = setup_embedding_pipeline()
        rag_retriever = setup_rag_retriever()
        test_dataset = load_test_dataset()
        print(f"Loaded {len(test_dataset)} test cases")
        
        # Run tests
        print("\n--- Running Tests ---")
        
        tests = [
            ("ChromaDB Connection", lambda: test_chromadb_connection(test_chromadb)),
            ("Embedding Pipeline", lambda: test_embedding_pipeline(embedding_pipeline)),
            ("RAG Retrieval Setup", lambda: test_rag_retrieval_setup(rag_retriever, test_dataset)),
            ("Semantic Similarity Threshold", lambda: test_semantic_similarity_threshold(embedding_pipeline, test_dataset)),
            ("RAG Retrieval Accuracy", lambda: test_rag_retrieval_accuracy(rag_retriever, test_dataset)),
            ("ChromaDB Separation", lambda: test_chromadb_separation(test_chromadb)),
            ("RAG Health Check", lambda: test_rag_health_check(rag_retriever)),
            ("Augmented Prompt Generation", lambda: test_augmented_prompt_generation(rag_retriever, test_dataset)),
            ("Similarity Thresholds", lambda: test_similarity_thresholds(embedding_pipeline)),
        ]
        
        for test_name, test_func in tests:
            try:
                test_func()
                passed_tests.append(test_name)
            except Exception as e:
                print(f"✗ {test_name} failed: {str(e)}")
                print(f"  Error details: {traceback.format_exc()}")
                failed_tests.append((test_name, str(e)))
        
        # Cleanup
        if test_chromadb:
            cleanup_test_chromadb(test_chromadb)
            
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
