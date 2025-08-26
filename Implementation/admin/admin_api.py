from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import sys
import os
import shutil
from pathlib import Path
import json


from config import Config
from admin.file_processor import FileProcessor
from admin.chromadb_manager import ChromaDBManager

# Pydantic models
class FileUploadResponse(BaseModel):
    success: bool
    filename: str
    chunks_created: int
    message: str
    file_id: Optional[str] = None

class FileDeleteRequest(BaseModel):
    filename: str

class KnowledgeBaseStats(BaseModel):
    total_chunks: int
    categories: List[str]
    file_types: List[str]
    total_files: int
    filenames: List[str]

# Initialize FastAPI
app = FastAPI(
    title="OPTIM Finance Admin API",
    description="API d'administration pour la gestion des fichiers et de la base de connaissances",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
file_processor = FileProcessor()
chromadb_manager = ChromaDBManager()

# Mount static files for the admin interface
static_path = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_path, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_path), name="static")

@app.get("/", response_class=HTMLResponse)
async def admin_interface():
    """Serve the admin interface"""
    html_path = os.path.join(os.path.dirname(__file__), "static", "admin.html")
    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(content="""
        <html>
        <head><title>OPTIM Finance Admin</title></head>
        <body>
            <h1>OPTIM Finance Admin Interface</h1>
            <p>Interface d'administration en cours de chargement...</p>
            <p>Veuillez créer le fichier admin.html dans le dossier static/</p>
        </body>
        </html>
        """)

@app.get("/health")
async def health_check():
    """Health check"""
    return {"status": "healthy", "service": "admin_api"}

@app.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    category: str = Form(default="general"),
    intent: str = Form(default="general"),
    chunk_size: int = Form(default=Config.DEFAULT_CHUNK_SIZE),
    overlap: int = Form(default=Config.DEFAULT_OVERLAP)
):
    """Upload and process a file"""
    try:
        # Validate file size
        if hasattr(file, 'size') and file.size > Config.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {Config.MAX_FILE_SIZE/1024/1024:.1f}MB"
            )
        
        # Validate file format
        if not file_processor.is_supported_format(file.filename):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format. Supported: {', '.join(Config.SUPPORTED_FILE_TYPES)}"
            )
        
        # Save uploaded file
        file_path = os.path.join(Config.ADMIN_UPLOAD_FOLDER, file.filename)
        
        # Remove existing file if it exists
        if os.path.exists(file_path):
            os.remove(file_path)
            # Also remove existing chunks from database
            chromadb_manager.delete_chunks_by_filename(file.filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process file into chunks
        try:
            chunks = file_processor.process_file(
                file_path, file.filename, category, intent, chunk_size, overlap
            )
        except Exception as e:
            os.remove(file_path)  # Clean up file on processing error
            raise HTTPException(status_code=400, detail=f"File processing error: {str(e)}")
        
        # Add chunks to ChromaDB
        success = chromadb_manager.add_chunks(chunks)
        
        if not success:
            os.remove(file_path)  # Clean up file on database error
            raise HTTPException(status_code=500, detail="Failed to add chunks to database")
        
        # Clean up uploaded file (keep only processed chunks)
        os.remove(file_path)
        
        return FileUploadResponse(
            success=True,
            filename=file.filename,
            chunks_created=len(chunks),
            message=f"File '{file.filename}' processed successfully. {len(chunks)} chunks created.",
            file_id=file.filename
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/delete-file")
async def delete_file(request: FileDeleteRequest):
    """Delete all chunks from a specific file"""
    try:
        success = chromadb_manager.delete_chunks_by_filename(request.filename)
        
        if success:
            return {"success": True, "message": f"File '{request.filename}' deleted successfully"}
        else:
            return {"success": False, "message": f"No chunks found for file '{request.filename}'"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

@app.get("/stats", response_model=KnowledgeBaseStats)
async def get_stats():
    """Get knowledge base statistics"""
    try:
        stats = chromadb_manager.get_collection_stats()
        return KnowledgeBaseStats(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@app.get("/files")
async def list_files():
    """List all files in the knowledge base"""
    try:
        stats = chromadb_manager.get_collection_stats()
        return {
            "files": stats['filenames'],
            "total_files": stats['total_files']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")

@app.post("/clear-all")
async def clear_knowledge_base():
    """Clear all data from the knowledge base"""
    try:
        success = chromadb_manager.clear_collection()
        
        if success:
            return {"success": True, "message": "Knowledge base cleared successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to clear knowledge base")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clear failed: {str(e)}")

@app.get("/search-test")
async def test_search(query: str, top_k: int = 3):
    """Test search functionality"""
    try:
        results = chromadb_manager.search_similar(query, top_k)
        return {
            "query": query,
            "results": results,
            "num_results": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search test failed: {str(e)}")

@app.get("/supported-formats")
async def get_supported_formats():
    """Get list of supported file formats"""
    return {
        "supported_formats": Config.SUPPORTED_FILE_TYPES,
        "max_file_size_mb": Config.MAX_FILE_SIZE / (1024 * 1024)
    }

if __name__ == "__main__":
    uvicorn.run(
        "admin_api:app",
        host=Config.ADMIN_API_HOST,
        port=Config.ADMIN_API_PORT,
        reload=True
    )