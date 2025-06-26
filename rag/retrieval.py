"""
RAG retrieval system for Ashoka governance.
Combines ChromaDB vector search with context generation.
"""

import logging
from typing import Dict, List, Optional

from .chromadb_client import ChromaDBClient
from .embeddings import EmbeddingPipeline

logger = logging.getLogger(__name__)


class RAGRetriever:
    """RAG retrieval system combining vector search and context generation."""

    def __init__(self, chromadb_host: str = "localhost", chromadb_port: int = 8000, 
                 environment: str = "prod", embedding_model: str = "all-MiniLM-L6-v2"):
        """Initialize RAG retriever.
        
        Args:
            chromadb_host: ChromaDB server host
            chromadb_port: ChromaDB server port
            environment: Environment ('test' or 'prod')
            embedding_model: Sentence transformer model name
        """
        self.chromadb_client = ChromaDBClient(chromadb_host, chromadb_port, environment)
        self.embedding_pipeline = EmbeddingPipeline(embedding_model)
        self.environment = environment
        
        logger.info(f"Initialized RAG retriever for {environment} environment")

    def add_governance_documents(self, documents: List[Dict[str, str]]):
        """Add governance documents to ChromaDB.
        
        Args:
            documents: List of documents with 'content', 'title', and 'category' keys
        """
        try:
            doc_texts = [doc["content"] for doc in documents]
            doc_ids = [f"doc_{i}_{doc.get('title', 'untitled')}" for i, doc in enumerate(documents)]
            metadatas = [
                {
                    "title": doc.get("title", ""),
                    "category": doc.get("category", "general"),
                    "source": "governance_docs"
                }
                for doc in documents
            ]
            
            self.chromadb_client.add_documents(doc_texts, metadatas, doc_ids)
            logger.info(f"Added {len(documents)} governance documents")
        except Exception as e:
            logger.error(f"Failed to add governance documents: {e}")
            raise

    def retrieve_context(self, query: str, n_results: int = 3) -> List[Dict[str, str]]:
        """Retrieve relevant context for a query.
        
        Args:
            query: Query text
            n_results: Number of results to retrieve
            
        Returns:
            List of relevant documents with metadata
        """
        try:
            results = self.chromadb_client.query_documents([query], n_results)
            
            contexts = []
            if results.get("documents") and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    context = {
                        "content": doc,
                        "metadata": results.get("metadatas", [[]])[0][i] if results.get("metadatas") else {},
                        "distance": results.get("distances", [[]])[0][i] if results.get("distances") else 0.0
                    }
                    contexts.append(context)
            
            logger.debug(f"Retrieved {len(contexts)} contexts for query")
            return contexts
        except Exception as e:
            logger.error(f"Failed to retrieve context: {e}")
            return []

    def generate_augmented_prompt(self, original_prompt: str, query: str, n_contexts: int = 3) -> str:
        """Generate RAG-augmented prompt with retrieved context.
        
        Args:
            original_prompt: Original prompt template
            query: Query for context retrieval
            n_contexts: Number of contexts to retrieve
            
        Returns:
            Augmented prompt with context
        """
        try:
            contexts = self.retrieve_context(query, n_contexts)
            
            if not contexts:
                logger.warning("No contexts retrieved, using original prompt")
                return original_prompt
            
            context_text = "\n\n".join([
                f"Context {i+1} ({ctx['metadata'].get('category', 'general')}):\n{ctx['content']}"
                for i, ctx in enumerate(contexts)
            ])
            
            augmented_prompt = f"""Based on the following governance context, {original_prompt}

Relevant Governance Context:
{context_text}

Please provide a response that incorporates the above context while addressing the specific governance scenario."""
            
            logger.debug("Generated RAG-augmented prompt")
            return augmented_prompt
        except Exception as e:
            logger.error(f"Failed to generate augmented prompt: {e}")
            return original_prompt

    def health_check(self) -> Dict[str, bool]:
        """Check health of RAG components."""
        return {
            "chromadb": self.chromadb_client.health_check(),
            "embedding_model": self.embedding_pipeline.model is not None
        }
