import chromadb
import uuid
import json
import os
import shutil
from typing import List, Dict, Any, Optional
import numpy as np
from config import Config
from model_manager import ModelManager
import sys
# Add project directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))


class ChromaDBManager:
    def __init__(self):
        # Utiliser le modèle partagé via ModelManager
        model_manager = ModelManager()
        self.model = model_manager.get_model()
        
        # Initialize ChromaDB client with error handling
        try:
            self.client = chromadb.PersistentClient(path=Config.CHROMADB_PATH)
            self._initialize_collection()
        except Exception as e:
            print(f"Error initializing ChromaDB: {e}")
            print("Attempting to recover by clearing corrupted database...")
            self._recover_database()
    
    def _initialize_collection(self):
        """Initialize the collection"""
        self.collection = self.client.get_or_create_collection(
            name=Config.CHROMADB_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
    
    def _recover_database(self):
        """Recover from corrupted database by clearing and recreating"""
        try:
            if hasattr(self, 'client'):
                del self.client
            
            if os.path.exists(Config.CHROMADB_PATH):
                print(f"Removing corrupted database at: {Config.CHROMADB_PATH}")
                shutil.rmtree(Config.CHROMADB_PATH)
            
            os.makedirs(Config.CHROMADB_PATH, exist_ok=True)
            self.client = chromadb.PersistentClient(path=Config.CHROMADB_PATH)
            self._initialize_collection()
            print("✓ ChromaDB recovered successfully")
            
        except Exception as e:
            print(f"Failed to recover ChromaDB: {e}")
            raise e
    
    def add_chunks(self, chunks: List[Dict[str, Any]]) -> bool:
        """Add chunks to ChromaDB"""
        try:
            documents = []
            metadatas = []
            ids = []
            embeddings = []
            
            # Traiter par batch pour économiser la mémoire
            batch_size = 10
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                texts = [f"{chunk['title']}: {chunk['content']}" for chunk in batch]
                
                # Générer embeddings en batch (plus efficace)
                if self.model:
                    batch_embeddings = self.model.encode(texts).tolist()
                else:
                    # Fallback si pas de modèle (pour compatibilité)
                    batch_embeddings = [[0.0] * 384 for _ in texts]
                
                for j, chunk in enumerate(batch):
                    documents.append(chunk['content'])
                    metadatas.append({
                        'title': chunk['title'],
                        'category': chunk['category'],
                        'keywords': json.dumps(chunk['keywords']),
                        'intent': chunk['intent'],
                        'filename': chunk.get('filename', ''),
                        'file_type': chunk.get('file_type', ''),
                        'chunk_index': chunk.get('chunk_index', 0)
                    })
                    ids.append(chunk['id'])
                    embeddings.append(batch_embeddings[j])
            
            # Add to collection
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings
            )
            
            print(f"Added {len(chunks)} chunks to ChromaDB")
            return True
            
        except Exception as e:
            print(f"Error adding chunks to ChromaDB: {e}")
            return False
    
    def search_similar(self, query: str, top_k: int = 5, category_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search similar chunks in ChromaDB"""
        try:
            if not self.model:
                print("No embedding model available")
                return []
                
            # Generate query embedding
            query_embedding = self.model.encode([query])[0].tolist()
            
            # Prepare where clause for filtering
            where_clause = {}
            if category_filter:
                where_clause["category"] = category_filter
            
            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_clause if where_clause else None,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            formatted_results = []
            for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0], 
                results['distances'][0]
            )):
                formatted_results.append({
                    'id': results['ids'][0][i],
                    'content': doc,
                    'title': metadata['title'],
                    'category': metadata['category'],
                    'keywords': json.loads(metadata['keywords']),
                    'intent': metadata['intent'],
                    'filename': metadata.get('filename', ''),
                    'file_type': metadata.get('file_type', ''),
                    'similarity_score': 1 - distance,
                    'distance': distance
                })
            
            return formatted_results
            
        except Exception as e:
            print(f"Error searching ChromaDB: {e}")
            return []
    
    # ... (autres méthodes inchangées)
    def delete_chunks_by_filename(self, filename: str) -> bool:
        """Delete all chunks from a specific file"""
        try:
            results = self.collection.get(
                where={"filename": filename},
                include=["metadatas"]
            )
            
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                print(f"Deleted {len(results['ids'])} chunks from file: {filename}")
                return True
            else:
                print(f"No chunks found for file: {filename}")
                return False
                
        except Exception as e:
            print(f"Error deleting chunks: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection"""
        try:
            total_chunks = self.collection.count()
            all_data = self.collection.get(include=["metadatas"])
            
            categories = set()
            file_types = set()
            filenames = set()
            
            for metadata in all_data['metadatas']:
                categories.add(metadata['category'])
                file_types.add(metadata.get('file_type', 'unknown'))
                filenames.add(metadata.get('filename', 'unknown'))
            
            return {
                'total_chunks': total_chunks,
                'categories': list(categories),
                'file_types': list(file_types),
                'total_files': len(filenames),
                'filenames': list(filenames)
            }
            
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {
                'total_chunks': 0,
                'categories': [],
                'file_types': [],
                'total_files': 0,
                'filenames': []
            }
    
    def clear_collection(self) -> bool:
        """Clear all data from the collection"""
        try:
            self.client.delete_collection(Config.CHROMADB_COLLECTION_NAME)
            self.collection = self.client.get_or_create_collection(
                name=Config.CHROMADB_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
            print("ChromaDB collection cleared")
            return True
        except Exception as e:
            print(f"Error clearing collection: {e}")
            return False