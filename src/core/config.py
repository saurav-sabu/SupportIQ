import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from functools import lru_cache

BASE_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    app_name: str = "SupportIQ"
    app_env: str = "development"
    groq_api_key: str
    tavily_api_key: str
    pinecone_api_key: str
    pinecone_index_name: str
    pinecone_namespace: str
    embedding_model: str
    groq_model: str
    google_api_key: str
    top_k: int = 4
    max_retries: int = 1
    admin_api_key: str = "supportiq-admin-2026"
    database_url: str = ""
    upload_dir: str = str(BASE_DIR/"uploads")
    ingest_kb_dir: str = str(BASE_DIR/"data"/"ingest_kb")

    # LangSmith / LangChain Tracing (parsed via Pydantic Settings)
    langchain_tracing_v2: bool = True
    langchain_api_key: str = ""
    langsmith_api_key: str = ""
    langchain_project: str = "SupportIQ"
    langchain_endpoint: str = "https://api.smith.langchain.com"

    logfire_token: str = ""

    model_config = SettingsConfigDict(env_file=str(BASE_DIR/".env"), extra="ignore")


@lru_cache
def get_settings():
    s = Settings()
    # Bridge Pydantic Settings -> LangChain internal tracer
    api_key = s.langsmith_api_key.strip() or s.langchain_api_key.strip()
    if s.langchain_tracing_v2 and api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = api_key
        os.environ["LANGSMITH_API_KEY"] = api_key
        os.environ["LANGCHAIN_PROJECT"] = s.langchain_project.strip() or "SupportIQ"
        os.environ["LANGCHAIN_ENDPOINT"] = s.langchain_endpoint.strip() or "https://api.smith.langchain.com"
    return s
