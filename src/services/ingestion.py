from pathlib import Path
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader

SUPPORTED = {".pdf",".txt",".md"}

def load_file(path:Path):

    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return PyPDFLoader(str(path)).load()
    if suffix in {".txt",".md"}:
        return TextLoader(str(path)).load()

def chunk_documents(docs):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000,chunk_overlap=200,add_start_index=True)
    chunks = text_splitter.split_documents(docs)
    return chunks