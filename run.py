from src.services.ingestion import load_file,chunk_documents
from src.rag.vectorstore import get_vectorstore, get_embeddings, get_retriever, add_documents
from pathlib import Path

docs = load_file(Path(r"data\sample_kb\01_Network_Troubleshooting_Guide.pdf"))
chunks = chunk_documents(docs)

add_documents(chunks)