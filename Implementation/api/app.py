from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import sys
import os

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
    """Initialiser le chatbot au démarrage"""
    chatbot.initialize()

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

@app.get("/suggestions")
async def get_suggestions(q: Optional[str] = ""):
    """Obtenir des suggestions de questions"""
    suggestions = chatbot.get_suggestions(q or "")
    return {"suggestions": suggestions}

@app.get("/stats")
async def get_stats():
    """Statistiques du chatbot"""
    return {
        "total_chunks": len(chatbot.search_engine.embedding_manager.chunks),
        "categories": list(set(chunk['category'] for chunk in chatbot.search_engine.embedding_manager.chunks)) if chatbot.search_engine.embedding_manager.chunks else [],
        "intents": list(chatbot.search_engine.intent_patterns.keys())
    }

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=Config.API_HOST,
        port=Config.API_PORT,
        reload=True
    )