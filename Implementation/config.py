import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ========== PATH CONFIGURATION ==========
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    #  CORRECTION : Utiliser une variable d'environnement pour la persistance
    # En production (Docker), monter un volume persistant
    # En local, utiliser un dossier local
    DATA_DIR = os.getenv("DATA_DIR", os.path.join(BASE_DIR, "admin", "data"))
    
    # Configuration LLM
    MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY', '')
    LLM_MODEL = os.getenv('LLM_MODEL', 'mistral-small')
    
    # Configuration Embedding
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-MiniLM-L3-v2")
    
    # ========== RÉPONSES CONCISES ==========
    #  NOUVEAU : Paramètres pour contrôler la longueur des réponses
    MAX_RESPONSE_TOKENS = int(os.getenv("MAX_RESPONSE_TOKENS", 250))  # Limite stricte
    MIN_RESPONSE_TOKENS = int(os.getenv("MIN_RESPONSE_TOKENS", 50))   # Minimum acceptable
    TEMPERATURE = float(os.getenv("TEMPERATURE", 0.3))  # Plus bas = plus déterministe
    
    # Configuration Recherche
    TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", 3))
    SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", 0.7))
    
    # Configuration API
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", 8000))
    
    # Informations de contact OPTIM Finance
    CONTACT_EMAIL = "contact@optim-finance.com"
    CONTACT_PHONE = "+33 1 59 06 80 86"
    
    # ========== CHROMADB CONFIGURATION ==========
    CHROMADB_PATH = os.path.join(DATA_DIR, "chromadb")
    CHROMADB_COLLECTION_NAME = os.getenv("CHROMADB_COLLECTION_NAME", "optim_finance_knowledge")
    
    # Admin Interface Configuration
    ADMIN_API_HOST = os.getenv("ADMIN_API_HOST", "localhost")
    ADMIN_API_PORT = int(os.getenv("ADMIN_API_PORT", 8001))
    ADMIN_UPLOAD_FOLDER = os.path.join(DATA_DIR, "uploads")
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 50 * 1024 * 1024))  # 50MB
    
    # ==========  CHUNKING AUTOMATIQUE ==========
    # Retirer les paramètres manuels et utiliser la détection automatique
    CHUNK_CONFIGS = {
        'faq': {'size': 300, 'overlap': 50},
        'document': {'size': 1000, 'overlap': 200},
        'technical': {'size': 1500, 'overlap': 300},
        'short': {'size': 500, 'overlap': 100}
    }
    
    SUPPORTED_FILE_TYPES = ['.pdf', '.docx', '.doc', '.txt', '.json', '.csv', '.md']
    
    # Database Configuration
    USE_CHROMADB = os.getenv("USE_CHROMADB", "True").lower() in ('true', '1', 'yes', 'on')
    FALLBACK_TO_FAISS = os.getenv("FALLBACK_TO_FAISS", "False").lower() in ('true', '1', 'yes', 'on')
    
    # Advanced Configuration
    KEYWORD_EXTRACTION_MAX = int(os.getenv("KEYWORD_EXTRACTION_MAX", 10))
    AUTO_GENERATE_TITLES = os.getenv("AUTO_GENERATE_TITLES", "True").lower() in ('true', '1', 'yes', 'on')
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.path.join(DATA_DIR, "admin.log")
    
    # ========== INITIALISATION DES DOSSIERS ==========
    @classmethod
    def initialize_directories(cls):
        """Créer tous les dossiers nécessaires"""
        directories = [
            cls.DATA_DIR,
            cls.CHROMADB_PATH,
            cls.ADMIN_UPLOAD_FOLDER,
            os.path.dirname(cls.LOG_FILE)
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        
        print(f" Dossiers initialisés dans: {os.path.abspath(cls.DATA_DIR)}")
        print(f"   ├── chromadb/ → {os.path.abspath(cls.CHROMADB_PATH)}")
        print(f"   ├── uploads/ → {os.path.abspath(cls.ADMIN_UPLOAD_FOLDER)}")
        print(f"   └── logs/")
    
    # ========== VALIDATION DE LA CONFIGURATION ==========
    @classmethod
    def validate_config(cls):
        """Valider la configuration"""
        errors = []
        
        print(f" Validation de la configuration...")
        print(f" DATA_DIR utilisé: {os.path.abspath(cls.DATA_DIR)}")
        
        if cls.USE_CHROMADB and not cls.MISTRAL_API_KEY:
            errors.append("MISTRAL_API_KEY est requis")
        
        if cls.MAX_FILE_SIZE <= 0:
            errors.append("MAX_FILE_SIZE doit être positif")
        
        if not (1024 <= cls.API_PORT <= 65535):
            errors.append("API_PORT doit être entre 1024 et 65535")
        
        if not (1024 <= cls.ADMIN_API_PORT <= 65535):
            errors.append("ADMIN_API_PORT doit être entre 1024 et 65535")
        
        if cls.API_PORT == cls.ADMIN_API_PORT:
            errors.append("API_PORT et ADMIN_API_PORT doivent être différents")
        
        if errors:
            raise ValueError(f"❌ Erreurs de configuration: {'; '.join(errors)}")
        
        print(" Configuration validée avec succès")
    
    # ========== MÉTHODES UTILITAIRES ==========
    @classmethod
    def get_chunk_config(cls, content_type: str = 'document'):
        """Obtenir la configuration de chunking selon le type"""
        return cls.CHUNK_CONFIGS.get(content_type, cls.CHUNK_CONFIGS['document'])
    
    @classmethod
    def detect_content_type(cls, text: str, filename: str = '') -> str:
        """Détecter automatiquement le type de contenu"""
        text_lower = text.lower()
        
        # FAQ si beaucoup de questions
        if text.count('?') > len(text) / 200:
            return 'faq'
        
        # Technique si code ou termes techniques
        if any(marker in text for marker in ['```', 'def ', 'class ', 'function']):
            return 'technical'
        
        # Court si moins de 1000 caractères
        if len(text) < 1000:
            return 'short'
        
        return 'document'
    
    @classmethod
    def get_file_size_mb(cls):
        """Retourner la taille max des fichiers en MB"""
        return cls.MAX_FILE_SIZE / (1024 * 1024)
    
    @classmethod
    def is_supported_file(cls, filename):
        """Vérifier si le format de fichier est supporté"""
        ext = os.path.splitext(filename.lower())[1]
        return ext in cls.SUPPORTED_FILE_TYPES
    
    @classmethod
    def get_upload_path(cls, filename):
        """Générer le chemin complet pour un fichier uploadé"""
        return os.path.join(cls.ADMIN_UPLOAD_FOLDER, filename)
    
    @classmethod
    def print_config_summary(cls):
        """Afficher un résumé de la configuration"""
        print("\n" + "="*50)
        print("🔧 CONFIGURATION SUMMARY")
        print("="*50)
        print(f" Base Directory: {cls.BASE_DIR}")
        print(f" Data Directory: {os.path.abspath(cls.DATA_DIR)}")
        print(f"  ChromaDB Path: {os.path.abspath(cls.CHROMADB_PATH)}")
        print(f" Upload Folder: {os.path.abspath(cls.ADMIN_UPLOAD_FOLDER)}")
        print(f" Log File: {os.path.abspath(cls.LOG_FILE)}")
        print(f" Admin API: http://{cls.ADMIN_API_HOST}:{cls.ADMIN_API_PORT}")
        print(f" Chat API: http://{cls.API_HOST}:{cls.API_PORT}")
        print(f" Max File Size: {cls.get_file_size_mb():.1f} MB")
        print(f" Max Response Tokens: {cls.MAX_RESPONSE_TOKENS}")
        print(f"  Temperature: {cls.TEMPERATURE}")
        print("="*50)
    
    @classmethod
    def check_data_consistency(cls):
        """Vérifier la cohérence des données"""
        print("\n VÉRIFICATION DE COHÉRENCE")
        print("-" * 30)
        
        paths_to_check = {
            "Data Directory": cls.DATA_DIR,
            "ChromaDB Path": cls.CHROMADB_PATH,
            "Upload Folder": cls.ADMIN_UPLOAD_FOLDER
        }
        
        all_good = True
        for name, path in paths_to_check.items():
            exists = os.path.exists(path)
            is_writable = os.access(path, os.W_OK) if exists else False
            print(f"{'✅' if exists and is_writable else '❌'} {name}: {path}")
            if not exists or not is_writable:
                all_good = False
        
        if all_good:
            print(" Tous les dossiers sont correctement configurés!")
        else:
            print(" Certains dossiers manquent ou ne sont pas accessibles en écriture.")
            print("   Exécutez Config.initialize_directories()")
        
        return all_good

# Initialisation automatique au chargement du module
Config.initialize_directories()
Config.print_config_summary()