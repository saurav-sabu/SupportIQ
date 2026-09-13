from pathlib import Path
import logging
from fastapi import APIRouter, HTTPException, UploadFile, File, Header
from pydantic import BaseModel, Field
from src.core.config import get_settings
from src.rag.workflow import ask
from src.rag.vectorstore import add_documents
from src.services.ingestion import load_file, chunk_documents, SUPPORTED_FILE_TYPES

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")
settings = get_settings()

class ChatRequest(BaseModel):
    question: str = Field(..., description="The question to ask the RAG agent.")

@router.get("/health")
def health():
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "app_env": settings.app_env,
        "model": settings.groq_model,
        "vector_index": settings.pinecone_index_name
    }

@router.get("/stats")
def stats():
    return {
        "app_name": settings.app_name,
        "app_env": settings.app_env,
        "groq_model": settings.groq_model,
        "embedding_model": settings.embedding_model,
        "pinecone_index": settings.pinecone_index_name,
        "pinecone_namespace": settings.pinecone_namespace,
        "top_k": settings.top_k,
        "max_retries": settings.max_retries,
        "admin_api_key": settings.admin_api_key
    }

@router.post("/chat")
def chat_with_agent(request: ChatRequest):
    try:
        response = ask(request.question)
        return {
            "answer": response.get("answer", ""),
            "source_used": response.get("source_used", "direct"),
            "citations": response.get("citations", []),
            "rewritten_query": response.get("current_query", request.question),
        }
    except Exception as e:
        logger.error(f"Error during agent invocation: {e}", exc_info=True)
        err_str = str(e)
        if "rate_limit" in err_str.lower() or "429" in err_str or "quota" in err_str.lower():
            return {
                "answer": f"**System Advisory: API Rate Limit Encountered**\n\nThe LLM service reported: `{err_str}`\n\nPlease retry in a moment. SupportIQ uses Groq (`{settings.groq_model}`) and Pinecone for real-time grounded inference.",
                "source_used": "insufficient_evidence",
                "citations": [],
                "rewritten_query": request.question
            }
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/kb/documents")
def list_documents():
    kb_dir = Path(settings.ingest_kb_dir)
    upload_dir = Path(settings.upload_dir)
    
    docs = []
    if kb_dir.exists():
        for file in sorted(kb_dir.glob("*.*")):
            if file.is_file() and file.suffix.lower() in SUPPORTED_FILE_TYPES:
                docs.append({
                    "name": file.name,
                    "category": "Preloaded Guide",
                    "size_kb": round(file.stat().st_size / 1024, 1),
                    "type": file.suffix.lower().replace(".", "")
                })
                
    if upload_dir.exists():
        for file in sorted(upload_dir.glob("*.*")):
            if file.is_file() and file.suffix.lower() in SUPPORTED_FILE_TYPES:
                docs.append({
                    "name": file.name,
                    "category": "User Uploaded",
                    "size_kb": round(file.stat().st_size / 1024, 1),
                    "type": file.suffix.lower().replace(".", "")
                })
                
    return {"documents": docs, "supported_types": SUPPORTED_FILE_TYPES}

@router.post("/kb/reindex-all")
def reindex_all_guides(api_key: str = Header(default="")):
    if api_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Invalid API key.")
    
    kb_dir = Path(settings.ingest_kb_dir)
    if not kb_dir.exists():
        raise HTTPException(status_code=404, detail="Ingest directory not found")
        
    all_docs = []
    files = [f for f in kb_dir.iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED_FILE_TYPES]
    for file in files:
        all_docs.extend(load_file(file))
        
    chunks = chunk_documents(all_docs)
    add_documents(chunks)
    return {
        "message": f"Successfully re-indexed {len(chunks)} chunks across {len(files)} runbook files.",
        "chunks_count": len(chunks),
        "files_count": len(files)
    }

@router.post("/ingest")
async def ingest(
    file: UploadFile = File(..., description="The file to ingest into the knowledge base."),
    api_key: str = Header(..., description="API key for authentication.")
):
    if api_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Invalid API key.")

    if not file.filename.lower().endswith(tuple(SUPPORTED_FILE_TYPES)):
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Supported types are: {', '.join(SUPPORTED_FILE_TYPES)}")

    try:
        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        destination = upload_dir / file.filename
        destination.write_bytes(await file.read())
        
        # Load and chunk the document (load_file is synchronous)
        document = load_file(destination)
        chunks = chunk_documents(document)

        # Add chunks to the vector store
        add_documents(chunks)

        return {
            "message": f"Successfully ingested {len(chunks)} chunks from {file.filename}.",
            "filename": file.filename,
            "chunks_count": len(chunks)
        }
    except Exception as e:
        logger.error(f"Ingestion error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))