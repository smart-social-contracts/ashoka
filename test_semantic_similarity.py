#!/usr/bin/env python3
"""
Test semantic similarity functionality for RAG system.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rag.embeddings import EmbeddingPipeline

def main():
    print("Testing semantic similarity...")
    
    try:
        embedder = EmbeddingPipeline()
        
        text1 = "A DAO should allocate treasury funds with community oversight and transparency."
        text2 = "DAOs must allocate treasury resources with community supervision and openness."
        
        emb1 = embedder.encode_single(text1)
        emb2 = embedder.encode_single(text2)
        similarity = embedder.compute_similarity(emb1, emb2)
        
        print(f"Similarity score: {similarity:.3f}")
        
        if similarity >= 0.80:
            print("✓ Semantic similarity threshold test passed!")
            return 0
        else:
            print(f"✗ Similarity {similarity:.3f} below threshold 0.80")
            return 1
            
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
