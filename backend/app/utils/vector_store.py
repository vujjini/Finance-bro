from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from langchain_google_vertexai import VertexAIEmbeddings
from typing import List, Dict, Any, Optional
import hashlib
import json
import os
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class VectorStoreManager:
    def __init__(self):
        self.client = self._get_qdrant_client()
        self.embeddings = VertexAIEmbeddings(model="text-embedding-004")
        self.collection_name = "stock_analysis_docs"
        self._ensure_collection_exists()
    
    def _get_qdrant_client(self) -> QdrantClient:
        """Initialize Qdrant client based on environment."""
        qdrant_url = os.getenv("QDRANT_URL", ":memory:")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        
        if qdrant_url == ":memory:":
            logger.info("Using in-memory Qdrant instance")
            return QdrantClient(":memory:")
        else:
            logger.info(f"Connecting to Qdrant at {qdrant_url}")
            return QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    
    def _ensure_collection_exists(self):
        """Create collection if it doesn't exist."""
        try:
            self.client.get_collection(self.collection_name)
            logger.info(f"Collection '{self.collection_name}' already exists")
        except Exception:
            logger.info(f"Creating collection '{self.collection_name}'")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE),
            )
    
    def add_documents(self, documents: List[Dict[str, Any]], symbol: str) -> List[str]:
        """Add documents to the vector store with metadata."""
        points = []
        doc_ids = []
        
        for i, doc in enumerate(documents):
            # Create unique ID for each document
            doc_content = doc.get("content", "")
            doc_id = hashlib.md5(f"{symbol}_{doc_content}_{i}".encode()).hexdigest()
            doc_ids.append(doc_id)
            
            # Generate embedding
            embedding = self.embeddings.embed_query(doc_content)
            
            # Create point with metadata
            point = PointStruct(
                id=doc_id,
                vector=embedding,
                payload={
                    "content": doc_content,
                    "symbol": symbol,
                    "title": doc.get("title", ""),
                    "url": doc.get("url", ""),
                    "published_date": doc.get("published_date", ""),
                    "source": doc.get("source", ""),
                    "document_type": "news_article"
                }
            )
            points.append(point)
        
        # Upload points to Qdrant
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        
        logger.info(f"Added {len(points)} documents for symbol {symbol}")
        return doc_ids
    
    def search_documents(self, query: str, symbol: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant documents."""
        # Generate query embedding
        query_embedding = self.embeddings.embed_query(query)
        
        # Prepare search filter
        search_filter = None
        if symbol:
            search_filter = {
                "must": [
                    {"key": "symbol", "match": {"value": symbol}}
                ]
            }
        
        # Search in Qdrant
        search_results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=search_filter,
            limit=limit,
            with_payload=True
        )
        
        # Format results
        results = []
        for result in search_results:
            results.append({
                "content": result.payload["content"],
                "title": result.payload.get("title", ""),
                "url": result.payload.get("url", ""),
                "source": result.payload.get("source", ""),
                "score": result.score,
                "symbol": result.payload.get("symbol", "")
            })
        
        return results
    
    def get_documents_by_symbol(self, symbol: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all documents for a specific symbol."""
        # Use scroll to get all documents for a symbol
        points, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter={
                "must": [
                    {"key": "symbol", "match": {"value": symbol}}
                ]
            },
            limit=limit,
            with_payload=True
        )
        
        results = []
        for point in points:
            results.append({
                "id": point.id,
                "content": point.payload["content"],
                "title": point.payload.get("title", ""),
                "url": point.payload.get("url", ""),
                "source": point.payload.get("source", ""),
                "symbol": point.payload.get("symbol", "")
            })
        
        return results
    
    def delete_documents_by_symbol(self, symbol: str):
        """Delete all documents for a specific symbol."""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector={
                "filter": {
                    "must": [
                        {"key": "symbol", "match": {"value": symbol}}
                    ]
                }
            }
        )
        logger.info(f"Deleted all documents for symbol {symbol}")

def get_vector_store() -> VectorStoreManager:
    """Get vector store manager instance."""
    return VectorStoreManager()