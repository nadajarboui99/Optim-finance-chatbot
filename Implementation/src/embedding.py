import json
import numpy as np
import pickle
import faiss
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
from config import Config

class EmbeddingManager:
    def __init__(self):
        self.model = SentenceTransformer(Config.EMBEDDING_MODEL)
        self.index: Optional[faiss.Index] = None
        self.chunks: List[Dict[str, Any]] = []
    
    def load_knowledge_base(self) -> List[Dict[str, Any]]:
        """Charger et préparer les chunks de la base de connaissances"""
        with open(Config.KNOWLEDGE_BASE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        chunks = []
        for chunk in data['knowledge_base']['chunks']:
            # Combiner titre + contenu pour un embedding plus riche
            full_text = f"{chunk['title']}: {chunk['content']}"
            
            chunks.append({
                'id': chunk['id'],
                'text': full_text,
                'content': chunk['content'],
                'title': chunk['title'],
                'keywords': chunk['keywords'],
                'category': chunk['category'],
                'intent': chunk['intent']
            })
        
        return chunks
    
    def create_embeddings(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Créer les embeddings pour tous les chunks"""
        texts = [chunk['text'] for chunk in chunks]
        embeddings = self.model.encode(texts, show_progress_bar=True)
        
        for i, chunk in enumerate(chunks):
            chunk['embedding'] = embeddings[i].tolist()
        
        return chunks
    
    def build_faiss_index(self, chunks_with_embeddings: List[Dict[str, Any]]) -> None:
        """Construire et sauvegarder l'index FAISS"""
        embeddings = np.array([chunk['embedding'] for chunk in chunks_with_embeddings])
        
        # Créer l'index FAISS
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)  # Inner Product pour similarité cosinus
        
        # Normaliser les embeddings pour la similarité cosinus
        embeddings_normalized = embeddings.astype('float32')
        faiss.normalize_L2(embeddings_normalized)
        self.index.add(embeddings_normalized)
        
        # Sauvegarder l'index et les métadonnées
        faiss.write_index(self.index, Config.FAISS_INDEX_PATH)
        
        with open(Config.CHUNKS_METADATA_PATH, "wb") as f:
            pickle.dump(chunks_with_embeddings, f)
        
        self.chunks = chunks_with_embeddings
        print(f"Index FAISS créé avec {len(chunks_with_embeddings)} chunks")
    
    def load_faiss_index(self) -> bool:
        """Charger l'index FAISS existant"""
        try:
            self.index = faiss.read_index(Config.FAISS_INDEX_PATH)
            
            with open(Config.CHUNKS_METADATA_PATH, "rb") as f:
                self.chunks = pickle.load(f)
            
            print(f"Index FAISS chargé avec {len(self.chunks)} chunks")
            return True
        except FileNotFoundError:
            print("Aucun index FAISS trouvé. Création nécessaire.")
            return False
    
    def initialize(self) -> None:
        """Initialiser le système d'embedding"""
        # Essayer de charger l'index existant
        if not self.load_faiss_index():
            # Si pas d'index, en créer un nouveau
            print("Création de l'index FAISS...")
            chunks = self.load_knowledge_base()
            chunks_with_embeddings = self.create_embeddings(chunks)
            self.build_faiss_index(chunks_with_embeddings)