from pinecone import Pinecone,ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from src.core.config import get_settings

settings = get_settings()

_embedding = None
_vectorstore = None

def get_embeddings():

    global _embedding

    if _embedding is None:
        if not settings.google_api_key:
            raise RuntimeError("GOOGLE_API_KEY is missing")

        _embedding = GoogleGenerativeAIEmbeddings(
            model= settings.embedding_model,
            api_key=settings.google_api_key
        )

    return _embedding

def indexing():

    if not settings.pinecone_api_key:
        raise RuntimeError("PINECONE_API_KEY is missing")

    pc = Pinecone(api_key=settings.pinecone_api_key)

    existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]

    if settings.pinecone_index_name not in existing_indexes:

        pc.create_index(
            name=settings.pinecone_index_name,
            dimension=3072,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )

    return pc.Index(settings.pinecone_index_name)

def get_vectorstore():

    global _vectorstore
    if  _vectorstore is None:
        index = indexing()
        _vectorstore = PineconeVectorStore(
            index=index,
            embedding=get_embeddings(),
            namespace=settings.pinecone_namespace
        )

    return _vectorstore

def get_retriever():
    return get_vectorstore().as_retriever(search_kwargs={"k":settings.top_k})


def add_documents(chunks):
    store = get_vectorstore()
    return store.add_documents(chunks)