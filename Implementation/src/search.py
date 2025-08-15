import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import numpy as np
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from config import Config
from admin.chromadb_manager import ChromaDBManager

class SearchEngine:
    def __init__(self):
        self.chromadb_manager = ChromaDBManager()
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
        # ChromaDB doesn't need explicit initialization like FAISS
        print("SearchEngine initialized with ChromaDB")
    
    def classify_intent(self, query: str) -> str:
        """Classifier l'intention de la requête"""
        query_lower = query.lower()
        
        for intent, keywords in self.intent_patterns.items():
            if any(keyword in query_lower for keyword in keywords):
                return intent
        
        return 'general'
    
    def search_semantic(self, query: str, top_k: Optional[int] = None, category_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Recherche sémantique avec ChromaDB"""
        if top_k is None:
            top_k = Config.TOP_K_RESULTS
        
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
    
    def search_by_keywords(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """Recherche par mots-clés"""
        if top_k is None:
            top_k = Config.TOP_K_RESULTS
        
        query_words = set(query.lower().split())
        results = []
        
        # Get a broader set of results from ChromaDB to analyze keywords
        all_results = self.chromadb_manager.search_similar(query, top_k * 3)
        
        for chunk in all_results:
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