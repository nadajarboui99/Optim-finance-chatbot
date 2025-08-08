import chromadb
import uuid
import json
import os
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import numpy as np
from config import Config

class ChromaDBManager:
    def __init__(self):
        self.model = SentenceTransformer(Config.EMBEDDING_MODEL)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=Config.CHROMADB_PATH)
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=Config.CHROMADB_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )
    
    def add_chunks(self, chunks: List[Dict[str, Any]]) -> bool:
        """Add chunks to ChromaDB"""
        try:
            documents = []
            metadatas = []
            ids = []
            embeddings = []
            
            for chunk in chunks:
                # Generate embedding for the text
                text = f"{chunk['title']}: {chunk['content']}"
                embedding = self.model.encode([text])[0].tolist()
                
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
                embeddings.append(embedding)
            
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
                    'similarity_score': 1 - distance,  # Convert distance to similarity
                    'distance': distance
                })
            
            return formatted_results
            
        except Exception as e:
            print(f"Error searching ChromaDB: {e}")
            return []
    
    def delete_chunks_by_filename(self, filename: str) -> bool:
        """Delete all chunks from a specific file"""
        try:
            # Get all chunks from the file
            results = self.collection.get(
                where={"filename": filename},
                include=["metadatas"]
            )
            
            if results['ids']:
                # Delete the chunks
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
            
            # Get all metadata to analyze
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
            # Delete the collection and recreate it
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