import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Chemins des fichiers
    DATA_DIR = "data"
    KNOWLEDGE_BASE_PATH = os.path.join(DATA_DIR, "knowledge_base.json")
    FAISS_INDEX_PATH = os.path.join(DATA_DIR, "optim_finance_index.faiss")
    CHUNKS_METADATA_PATH = os.path.join(DATA_DIR, "chunks_metadata.pkl")
    
    # Configuration LLM
    #OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    #LLM_MODEL = os.getenv('LLM_MODEL', 'mistralai/mistral-7b-instruct:free')
    MISTRAL_API_KEY= os.getenv('MISTRAL_API_KEY','')
    LLM_MODEL = os.getenv('LLM_MODEL', 'mistral-small')
    # Configuration Embedding
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    
    # Configuration Recherche
    TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", 3))
    SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", 0.7))
    
    # Configuration API
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", 8000))
    
    # Informations de contact OPTIM Finance
    CONTACT_EMAIL = "contact@optim-finance.com"
    CONTACT_PHONE = "+33 1 59 06 80 86"