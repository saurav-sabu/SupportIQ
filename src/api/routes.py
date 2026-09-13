from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Header
from pydantic import BaseModel, Field
from src.core.config import get_settings
from src.rag.workflow import ask
from src.rag.vectorstore import add_documents
from src.services.ingestion import load_file,chunk_documents, SUPPORTED_FILE_TYPES

router = APIRouter(prefix="/api")
settings = get_settings()

class ChatRequest(BaseModel):
    question: str = Field(..., description="The question to ask the RAG agent.")

@router.get("/health")
def health():
    return {"status": "healthy","app_name": settings.app_name, "app_env": settings.app_env}

@router.post("/chat")
def chat_with_agent(request: ChatRequest):
    try:
        response = ask(request.question)
        return {
            "answer": response.answer,
            "source_used": response.source_used,
            "citations": response.citations,
            "rewritten_query": response.get("current_query",request.question),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        # Load and chunk the document
        document = await load_file(destination)
        chunks = chunk_documents(document)

        # Add chunks to the vector store
        add_documents(chunks)

        return {"message": f"Successfully ingested {len(chunks)} chunks from {file.filename}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    