from pydantic_settings import BaseSettings,SettingsConfigDict
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
    google_api_key:str
    top_k: int = 4
    max_retries: int = 1
    admin_api_key:str = ""
    audit_db_path: str = str(BASE_DIR/"data"/"audit.db")
    upload_dir: str = str(BASE_DIR/"uploads")
    ingest_kb_dir: str = str(BASE_DIR/"data"/"ingest_kb")

    model_config = SettingsConfigDict(env_file=str(BASE_DIR/".env"),extra="ignore")


@lru_cache
def get_settings():
    return Settings()