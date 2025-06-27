#!/usr/bin/env python3
"""
Integration test script for RAG CI/CD system.
Tests the complete RAG pipeline including ChromaDB, embeddings, and semantic similarity.
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rag.chromadb_client import ChromaDBClient
from rag.embeddings import EmbeddingPipeline
from rag.retrieval import RAGRetriever

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_chromadb_connection():
    """Test ChromaDB connection and health."""
    logger.info("Testing ChromaDB connection...")
    
    try:
        client = ChromaDBClient(environment="test")
        assert client.health_check(), "ChromaDB should be healthy"
        logger.info("✓ ChromaDB connection successful")
        return True
    except Exception as e:
        logger.error(f"✗ ChromaDB connection failed: {e}")
        return False

def test_embedding_pipeline():
    """Test embedding pipeline functionality."""
    logger.info("Testing embedding pipeline...")
    
    try:
        embedder = EmbeddingPipeline()
        test_texts = ["DAO treasury management", "Governance proposal evaluation"]
        embeddings = embedder.encode(test_texts)
        
        assert len(embeddings) == 2, "Should return embeddings for both texts"
        assert len(embeddings[0]) > 0, "Embeddings should have dimensions"
        assert isinstance(embeddings[0][0], float), "Embeddings should be floats"
        
        logger.info("✓ Embedding pipeline working correctly")
        return True
    except Exception as e:
        logger.error(f"✗ Embedding pipeline failed: {e}")
        return False

def test_semantic_similarity():
    """Test semantic similarity calculations."""
    logger.info("Testing semantic similarity...")
    
    try:
        embedder = EmbeddingPipeline()
        
        text1 = "A DAO should allocate treasury funds with community oversight and transparency."
        text2 = "DAOs must allocate treasury resources with community supervision and openness."
        
        emb1 = embedder.encode_single(text1)
        emb2 = embedder.encode_single(text2)
        similarity = embedder.compute_similarity(emb1, emb2)
        
        logger.info(f"Similarity score: {similarity:.3f}")
        assert similarity >= 0.75, f"Similar sentences should have high similarity, got {similarity:.3f}"
        
        logger.info("✓ Semantic similarity working correctly")
        return True
    except Exception as e:
        logger.error(f"✗ Semantic similarity failed: {e}")
        return False

def test_rag_system():
    """Test complete RAG system integration."""
    logger.info("Testing RAG system integration...")
    
    try:
        rag = RAGRetriever(environment="test")
        
        health = rag.health_check()
        assert health['chromadb'], "ChromaDB should be healthy"
        assert health['embedding_model'], "Embedding model should be healthy"
        
        test_docs = [
            {
                "content": "Treasury management requires careful balance between growth and sustainability.",
                "title": "Treasury Management Guide",
                "category": "treasury"
            },
            {
                "content": "Governance proposals should include clear implementation plans and success metrics.",
                "title": "Proposal Guidelines",
                "category": "governance"
            }
        ]
        
        rag.add_governance_documents(test_docs)
        
        contexts = rag.retrieve_context("How should DAOs manage treasury funds?", n_results=2)
        assert len(contexts) > 0, "Should retrieve relevant contexts"
        assert "content" in contexts[0], "Context should have content"
        
        logger.info("✓ RAG system integration working correctly")
        return True
    except Exception as e:
        logger.error(f"✗ RAG system integration failed: {e}")
        return False

def test_sample_dataset():
    """Test loading and processing sample training data."""
    logger.info("Testing sample dataset...")
    
    try:
        dataset_file = Path(__file__).parent / "tests" / "sample_training_data.jsonl"
        assert dataset_file.exists(), f"Sample dataset not found at {dataset_file}"
        
        dataset = []
        with open(dataset_file, "r") as f:
            for line in f:
                item = json.loads(line.strip())
                dataset.append(item)
        
        assert len(dataset) > 0, "Dataset should not be empty"
        
        for item in dataset[:3]:  # Check first 3 items
            assert "question" in item, "Each item should have a question"
            assert "context" in item, "Each item should have context"
            assert "expected_answer" in item, "Each item should have expected_answer"
        
        logger.info(f"✓ Sample dataset loaded successfully ({len(dataset)} items)")
        return True
    except Exception as e:
        logger.error(f"✗ Sample dataset test failed: {e}")
        return False

def main():
    """Run all integration tests."""
    logger.info("Starting RAG CI/CD integration tests...")
    
    tests = [
        test_chromadb_connection,
        test_embedding_pipeline,
        test_semantic_similarity,
        test_rag_system,
        test_sample_dataset
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            logger.error(f"Test {test.__name__} crashed: {e}")
            results.append(False)
    
    passed = sum(results)
    total = len(results)
    
    logger.info(f"\nTest Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All RAG CI/CD integration tests passed!")
        return 0
    else:
        logger.error("❌ Some tests failed. Check the logs above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
