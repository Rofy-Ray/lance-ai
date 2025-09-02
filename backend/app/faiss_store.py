import os
import faiss
import numpy as np
from typing import List, Dict, Any, Optional
from pathlib import Path
from openai import OpenAI
import json
import asyncio

class FAISSStore:
    """FAISS vector store for document embeddings and retrieval"""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.embedding_model = "text-embedding-3-small"
        self.faiss_data_dir = Path(os.getenv("FAISS_DATA_DIR", "/tmp/faiss"))
        self.faiss_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache for session indexes
        self.session_indexes = {}
        self.session_metadata = {}
    
    async def create_session_index(self, session_id: str, documents: List[Dict[str, Any]]):
        """Create FAISS index for session documents"""
        try:
            # Extract and chunk text from all documents
            chunks = []
            metadata = []
            
            for doc in documents:
                doc_chunks = self._chunk_document(doc["content"], doc["doc_id"])
                chunks.extend([chunk["text"] for chunk in doc_chunks])
                metadata.extend(doc_chunks)
            
            if not chunks:
                raise ValueError("No text content found in documents")
            
            # Generate embeddings
            embeddings = await self._generate_embeddings(chunks)
            
            # Create FAISS index
            dimension = len(embeddings[0])
            index = faiss.IndexFlatL2(dimension)
            index.add(np.array(embeddings).astype('float32'))
            
            # Save index and metadata
            index_path = self.faiss_data_dir / f"session_{session_id}.index"
            metadata_path = self.faiss_data_dir / f"session_{session_id}.metadata"
            
            faiss.write_index(index, str(index_path))
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
            
            # Cache in memory for faster access
            self.session_indexes[session_id] = index
            self.session_metadata[session_id] = metadata
            
            return len(chunks)
            
        except Exception as e:
            raise Exception(f"Failed to create FAISS index: {str(e)}")
    
    async def search_session(self, session_id: str, query: str, k: int = 10) -> List[Dict[str, Any]]:
        """Search session documents for relevant chunks"""
        try:
            # Load index if not in cache
            if session_id not in self.session_indexes:
                await self._load_session_index(session_id)
            
            if session_id not in self.session_indexes:
                return []
            
            # Generate query embedding
            query_embedding = await self._generate_embeddings([query])
            
            # Search FAISS index
            distances, indices = self.session_indexes[session_id].search(
                np.array(query_embedding).astype('float32'), k
            )
            
            # Retrieve matching chunks with metadata
            results = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx < len(self.session_metadata[session_id]):
                    chunk_metadata = self.session_metadata[session_id][idx]
                    results.append({
                        "text": chunk_metadata["text"],
                        "doc_id": chunk_metadata["doc_id"],
                        "page": chunk_metadata["page"],
                        "line_range": chunk_metadata["line_range"],
                        "score": float(distance),
                        "rank": i + 1
                    })
            
            return results
            
        except Exception as e:
            raise Exception(f"Failed to search session: {str(e)}")
    
    async def get_supporting_quotes(self, session_id: str, query: str, min_score: float = 0.8) -> List[Dict[str, Any]]:
        """Get supporting quotes for a specific query with minimum relevance score"""
        results = await self.search_session(session_id, query, k=5)
        
        # Filter by relevance score (lower distance = higher relevance)
        filtered_results = []
        for result in results:
            # Convert distance to relevance score (1 - normalized_distance)
            relevance = max(0, 1 - (result["score"] / 2))  # Normalize distance to 0-1 range
            if relevance >= min_score:
                result["relevance"] = relevance
                filtered_results.append(result)
        
        return filtered_results
    
    def cleanup_session(self, session_id: str):
        """Remove session index files and cache"""
        try:
            # Remove from cache
            if session_id in self.session_indexes:
                del self.session_indexes[session_id]
            if session_id in self.session_metadata:
                del self.session_metadata[session_id]
            
            # Remove files
            index_path = self.faiss_data_dir / f"session_{session_id}.index"
            metadata_path = self.faiss_data_dir / f"session_{session_id}.metadata"
            
            if index_path.exists():
                index_path.unlink()
            if metadata_path.exists():
                metadata_path.unlink()
                
        except Exception as e:
            print(f"Warning: Failed to cleanup FAISS session {session_id}: {e}")
    
    async def _load_session_index(self, session_id: str):
        """Load session index from disk to cache"""
        try:
            index_path = self.faiss_data_dir / f"session_{session_id}.index"
            metadata_path = self.faiss_data_dir / f"session_{session_id}.metadata"
            
            if not index_path.exists() or not metadata_path.exists():
                return
            
            # Load index
            index = faiss.read_index(str(index_path))
            
            # Load metadata
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Cache
            self.session_indexes[session_id] = index
            self.session_metadata[session_id] = metadata
            
        except Exception as e:
            print(f"Warning: Failed to load FAISS session {session_id}: {e}")
    
    async def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for list of texts"""
        try:
            # OpenAI API call
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=texts
            )
            
            return [embedding.embedding for embedding in response.data]
            
        except Exception as e:
            raise Exception(f"Failed to generate embeddings: {str(e)}")
    
    def _chunk_document(self, text: str, doc_id: str, chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
        """Split document into overlapping chunks with metadata"""
        chunks = []
        words = text.split()
        
        # Estimate page and line numbers (rough approximation)
        words_per_page = 250  # Average words per page
        words_per_line = 10   # Average words per line
        
        start = 0
        chunk_id = 0
        
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk_text = " ".join(words[start:end])
            
            # Estimate page and line range
            start_page = max(1, start // words_per_page + 1)
            end_page = max(1, end // words_per_page + 1)
            start_line = max(1, (start % words_per_page) // words_per_line + 1)
            end_line = max(1, (end % words_per_page) // words_per_line + 1)
            
            chunks.append({
                "text": chunk_text,
                "doc_id": doc_id,
                "chunk_id": chunk_id,
                "page": start_page if start_page == end_page else start_page,
                "line_range": f"{start_line}-{end_line}" if start_page == end_page else f"{start_page}:{start_line}-{end_page}:{end_line}"
            })
            
            chunk_id += 1
            start = max(start + chunk_size - overlap, start + 1)  # Ensure progress
        
        return chunks
