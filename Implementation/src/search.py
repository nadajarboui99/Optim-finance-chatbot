import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import numpy as np
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from config import Config
from embedding import EmbeddingManager
from chromadb_manager import ChromaDBManager
import faiss

class SearchEngine:
    def __init__(self, use_chromadb: bool = True):
        self.use_chromadb = use_chromadb
        
        if use_chromadb:
            self.chromadb_manager = ChromaDBManager()
        else:
            self.embedding_manager = EmbeddingManager()
        
        self.model = SentenceTransformer(Config.EMBEDDING_MODEL)
        
        # Patterns pour classification d'intention
        self.intent_patterns = {
            'pricing': ['prix', 'coût', 'tarif', 'combien', 'frais', 'facturation'],
            'comparison': ['différence', 'comparer', 'mieux', 'choisir', 'avantage', 'vs'],
            'contact': ['contact', 'téléphone', 'email', 'rendez-vous', 'joindre'],
            'definition': ['qu\'est-ce', 'définition', 'c\'est quoi', 'signifie'],
            'process': ['comment', 'étapes', 'procédure', 'démarche'],
            'requirements': ['conditions', 'critères', 'éligible', 'requis']
        }
    
    def initialize(self) -> None:
        """Initialiser le moteur de recherche"""
        if not self.use_chromadb:
            self.embedding_manager.initialize()
    
    def classify_intent(self, query: str) -> str:
        """Classifier l'intention de la requête"""
        query_lower = query.lower()
        
        for intent, keywords in self.intent_patterns.items():
            if any(keyword in query_lower for keyword in keywords):
                return intent
        
        return 'general'
    
    def search_semantic(self, query: str, top_k: Optional[int] = None, category_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Recherche sémantique avec ChromaDB ou FAISS"""
        if top_k is None:
            top_k = Config.TOP_K_RESULTS
        
        if self.use_chromadb:
            return self._search_chromadb(query, top_k, category_filter)
        else:
            return self._search_faiss(query, top_k, category_filter)
    
    def _search_chromadb(self, query: str, top_k: int, category_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Recherche avec ChromaDB"""
        try:
            results = self.chromadb_manager.search_similar(query, top_k, category_filter)
            
            # Filter by similarity threshold
            filtered_results = []
            for result in results:
                if result['similarity_score'] >= Config.SIMILARITY_THRESHOLD:
                    filtered_results.append(result)
            
            return filtered_results
        except Exception as e:
            print(f"ChromaDB search error: {e}")
            return []
    
    def _search_faiss(self, query: str, top_k: int, category_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Recherche avec FAISS (fallback)"""
        if self.embedding_manager.index is None:
            return []
        
        # Encoder la requête
        query_embedding = self.model.encode([query])
        query_embedding = query_embedding.astype('float32')
        
        # Normaliser pour similarité cosinus
        faiss.normalize_L2(query_embedding)
        
        # Recherche dans l'index FAISS
        scores, indices = self.embedding_manager.index.search(query_embedding, top_k * 2)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
                
            chunk = self.embedding_manager.chunks[idx]
            
            # Filtrer par catégorie si spécifié
            if category_filter and chunk['category'] != category_filter:
                continue
            
            # Filtrer par seuil de similarité
            if score < Config.SIMILARITY_THRESHOLD:
                continue
            
            chunk_copy = chunk.copy()
            chunk_copy['similarity_score'] = float(score)
            results.append(chunk_copy)
        
        return results[:top_k]
    
    def search_by_keywords(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """Recherche par mots-clés"""
        if top_k is None:
            top_k = Config.TOP_K_RESULTS
        
        query_words = set(query.lower().split())
        results = []
        
        # Get chunks based on storage type
        if self.use_chromadb:
            # For ChromaDB, we need to get all chunks first (not optimal for large datasets)
            all_results = self.chromadb_manager.search_similar(query, top_k * 3)
            chunks = all_results
        else:
            chunks = self.embedding_manager.chunks
        
        for chunk in chunks:
            score = 0
            
            # Score basé sur les keywords
            chunk_keywords = [kw.lower() for kw in chunk['keywords']]
            keyword_matches = len(query_words.intersection(set(chunk_keywords)))
            score += keyword_matches * 2
            
            # Score basé sur le contenu
            content_words = set(chunk['content'].lower().split())
            content_matches = len(query_words.intersection(content_words))
            score += content_matches
            
            if score > 0:
                chunk_copy = chunk.copy()
                chunk_copy['keyword_score'] = score
                results.append(chunk_copy)
        
        # Trier par score décroissant
        results.sort(key=lambda x: x['keyword_score'], reverse=True)
        return results[:top_k]
    
    def hybrid_search(self, query: str, top_k: Optional[int] = None, semantic_weight: float = 0.7) -> List[Dict[str, Any]]:
        """Recherche hybride combinant sémantique et mots-clés"""
        if top_k is None:
            top_k = Config.TOP_K_RESULTS
        
        # Recherches séparées
        semantic_results = self.search_semantic(query, top_k + 3)
        keyword_results = self.search_by_keywords(query, top_k + 3)
        
        # Combiner les résultats
        combined_scores = {}
        
        # Scores sémantiques
        for result in semantic_results:
            chunk_id = result['id']
            combined_scores[chunk_id] = {
                'chunk': result,
                'semantic_score': result.get('similarity_score', 0),
                'keyword_score': 0
            }
        
        # Ajouter scores mots-clés
        for result in keyword_results:
            chunk_id = result['id']
            if chunk_id in combined_scores:
                combined_scores[chunk_id]['keyword_score'] = result.get('keyword_score', 0)
            else:
                combined_scores[chunk_id] = {
                    'chunk': result,
                    'semantic_score': 0,
                    'keyword_score': result.get('keyword_score', 0)
                }
        
        # Normaliser et combiner
        max_semantic = max([s['semantic_score'] for s in combined_scores.values()], default=1)
        max_keyword = max([s['keyword_score'] for s in combined_scores.values()], default=1)
        
        final_results = []
        for chunk_data in combined_scores.values():
            norm_semantic = chunk_data['semantic_score'] / max_semantic if max_semantic > 0 else 0
            norm_keyword = chunk_data['keyword_score'] / max_keyword if max_keyword > 0 else 0
            
            final_score = semantic_weight * norm_semantic + (1 - semantic_weight) * norm_keyword
            
            chunk = chunk_data['chunk'].copy()
            chunk['final_score'] = final_score
            final_results.append(chunk)
        
        # Trier par score final
        final_results.sort(key=lambda x: x['final_score'], reverse=True)
        return final_results[:top_k]
    
    def search(self, query: str, search_type: str = "hybrid", top_k: Optional[int] = None, category_filter: Optional[str] = None) -> Dict[str, Any]:
        """Interface principale de recherche"""
        intent = self.classify_intent(query)
        
        if search_type == "semantic":
            results = self.search_semantic(query, top_k, category_filter)
        elif search_type == "keyword":
            results = self.search_by_keywords(query, top_k)
        else:  # hybrid
            results = self.hybrid_search(query, top_k)
        
        return {
            'query': query,
            'intent': intent,
            'results': results,
            'num_results': len(results)
        }
