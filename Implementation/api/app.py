from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import sys
import os
import threading
import time

# Ajouter le dossier src au path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from chatbot import OptimFinanceChatbot
from config import Config

# Modèles Pydantic pour l'API
class QueryRequest(BaseModel):
    query: str
    search_type: Optional[str] = "hybrid"
    top_k: Optional[int] = None

class QueryResponse(BaseModel):
    query: str
    response: str
    intent: str
    confidence: str
    sources: List[str]
    num_sources: int

# Initialiser FastAPI
app = FastAPI(
    title="OPTIM Finance Chatbot API",
    description="API pour le chatbot intelligent d'OPTIM Finance",
    version="1.0.0"
)

# CORS pour permettre les requêtes depuis le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialiser le chatbot
chatbot = OptimFinanceChatbot()



@app.on_event("startup")
async def startup_event():
    """Initialiser le chatbot et démarrer l'API d'administration au démarrage"""
    print("Initialisation du chatbot OPTIM Finance...")
    chatbot.initialize()
    
    # Démarrer l'API d'administration dans un thread séparé
    '''admin_thread = threading.Thread(target=start_admin_api, daemon=True)
    admin_thread.start()
    
    # Attendre un peu pour laisser le temps au thread admin de démarrer
    time.sleep(2)'''
    print("✅ Chatbot initialisé avec succès!")
    

@app.get("/")
async def root():
    """Point d'entrée de l'API"""
    return {
        "message": "OPTIM Finance Chatbot API",
        "version": "1.0.0",
        "status": "active"
    }

@app.get("/health")
async def health_check():
    """Vérification de santé de l'API"""
    return {
        "status": "healthy",
        "initialized": chatbot.is_initialized
    }

@app.get("/admin-health")
async def admin_health_check():
    """Vérifier le statut de l'API d'administration"""
    try:
        import requests
        response = requests.get("http://localhost:8001/health", timeout=3)
        return {
            "admin_status": "running",
            "admin_port": 8001,
            "admin_response": response.json()
        }
    except Exception as e:
        return {
            "admin_status": "not_running",
            "admin_port": 8001,
            "error": str(e)
        }

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """Traiter une requête utilisateur"""
    try:
        result = chatbot.process_query(
            user_query=request.query,
            search_type=request.search_type,
            top_k=request.top_k
        )
        
        if 'error' in result:
            raise HTTPException(status_code=500, detail=result['error'])
        
        return QueryResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.post("/chat")
async def chat_endpoint(request: QueryRequest):
    """Chat endpoint for frontend compatibility"""
    return await process_query(request)

@app.options("/chat")
async def chat_options():
    """Handle preflight OPTIONS request for /chat"""
    return {"message": "OK"}

@app.options("/query") 
async def query_options():
    """Handle preflight OPTIONS request for /query"""
    return {"message": "OK"}
@app.get("/suggestions")
async def get_suggestions(q: Optional[str] = ""):
    """Obtenir des suggestions de questions"""
    suggestions = chatbot.get_suggestions(q or "")
    return {"suggestions": suggestions}

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", Config.API_PORT))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=False  # Set to False for production
    )