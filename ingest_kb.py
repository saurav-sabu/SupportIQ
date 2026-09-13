from pathlib import Path
from src.core.config import get_settings
from src.services.ingestion import load_file, chunk_documents
from src.rag.vectorstore import add_documents

settings = get_settings()

data_folder = Path(settings.ingest_kb_dir)
files = [file for file in data_folder.iterdir() if file.is_file()]

all_docs = []

for path in files:
    all_docs.extend(load_file(path))

chunks = chunk_documents(all_docs)
ids = add_documents(chunks)