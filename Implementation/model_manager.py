# Sentence_transformer 
from sentence_transformers import SentenceTransformer
from config import Config

class ModelManager:
    """Singleton pour gérer le modèle d'embedding"""
    _instance = None
    _model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
        return cls._instance
    
    def get_model(self):
        """Obtenir le modèle (lazy loading)"""
        if self._model is None:
            print(f"Loading embedding model: {Config.EMBEDDING_MODEL}")
            # Utilisez le modèle le plus léger possible
            self._model = SentenceTransformer(Config.EMBEDDING_MODEL)
            print("✓ Embedding model loaded")
        return self._model
    
    def clear_model(self):
        """Libérer la mémoire du modèle si nécessaire"""
        if self._model is not None:
            del self._model
            self._model = None
            print("✓ Embedding model cleared from memory")

