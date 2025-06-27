"""
Embedding pipeline for Ashoka RAG system.
Uses sentence-transformers for semantic embeddings.
"""

import logging
from typing import List

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingPipeline:
    """Sentence transformer embedding pipeline."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize embedding pipeline.
        
        Args:
            model_name: Sentence transformer model name
        """
        self.model_name = model_name
        try:
            self.model = SentenceTransformer(model_name)
            logger.info(f"Loaded embedding model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model {model_name}: {e}")
            raise

    def encode(self, texts: List[str]) -> List[List[float]]:
        """Encode texts to embeddings.
        
        Args:
            texts: List of texts to encode
            
        Returns:
            List of embedding vectors
        """
        try:
            embeddings = self.model.encode(texts, convert_to_tensor=False)
            logger.debug(f"Encoded {len(texts)} texts to embeddings")
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Failed to encode texts: {e}")
            raise

    def encode_single(self, text: str) -> List[float]:
        """Encode single text to embedding.
        
        Args:
            text: Text to encode
            
        Returns:
            Embedding vector
        """
        return self.encode([text])[0]

    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score
        """
        try:
            import numpy as np
            from sklearn.metrics.pairwise import cosine_similarity
            
            emb1 = np.array(embedding1).reshape(1, -1)
            emb2 = np.array(embedding2).reshape(1, -1)
            
            similarity = cosine_similarity(emb1, emb2)[0][0]
            return float(similarity)
        except Exception as e:
            logger.error(f"Failed to compute similarity: {e}")
            raise
