"""
ChromaDB client for Ashoka RAG system.
Handles vector database operations with separate test/production collections.
"""

import logging
import os
from typing import Dict, List, Optional

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class ChromaDBClient:
    """ChromaDB client with environment-aware collection management."""

    def __init__(self, host: str = None, port: int = None, environment: str = "prod"):
        """Initialize ChromaDB client.
        
        Args:
            host: ChromaDB server host (defaults to CHROMADB_HOST env var or localhost)
            port: ChromaDB server port (defaults to CHROMADB_PORT env var or 8000)
            environment: Environment ('test' or 'prod') for collection separation
        """
        self.host = host or os.environ.get('CHROMADB_HOST', 'localhost')
        self.port = port or int(os.environ.get('CHROMADB_PORT', '8000'))
        self.environment = environment
        self.collection_name = f"ashoka_{environment}"
        
        try:
            self.client = chromadb.HttpClient(
                host=self.host,
                port=self.port,
                settings=Settings(allow_reset=True if environment == "test" else False)
            )
            logger.info(f"Connected to ChromaDB at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
            raise

    def get_or_create_collection(self, embedding_function=None):
        """Get or create the collection for this environment."""
        try:
            collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=embedding_function
            )
            logger.info(f"Using collection: {self.collection_name}")
            return collection
        except Exception as e:
            logger.error(f"Failed to get/create collection {self.collection_name}: {e}")
            raise

    def add_documents(self, documents: List[str], metadatas: List[Dict], ids: List[str]):
        """Add documents to the collection."""
        collection = self.get_or_create_collection()
        try:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Added {len(documents)} documents to {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            raise

    def query_documents(self, query_texts: List[str], n_results: int = 5) -> Dict:
        """Query documents from the collection."""
        collection = self.get_or_create_collection()
        try:
            results = collection.query(
                query_texts=query_texts,
                n_results=n_results
            )
            logger.debug(f"Query returned {len(results.get('documents', [[]]))} results")
            return results
        except Exception as e:
            logger.error(f"Failed to query documents: {e}")
            raise

    def reset_collection(self):
        """Reset collection (test environment only)."""
        if self.environment != "test":
            raise ValueError("Collection reset only allowed in test environment")
        
        try:
            self.client.reset()
            logger.info(f"Reset collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")
            raise

    def health_check(self) -> bool:
        """Check if ChromaDB is healthy."""
        try:
            self.client.heartbeat()
            return True
        except Exception as e:
            logger.error(f"ChromaDB health check failed: {e}")
            return False
