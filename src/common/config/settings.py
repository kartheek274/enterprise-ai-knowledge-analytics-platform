import os
from functools import lru_cache
from pathlib import Path
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from src.common.errors.exceptions import ConfigurationError

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

class Settings(BaseSettings):
    """
    Strongly typed application configuration settings.
    Loads variables from local environment or .env file and validates them.
    """
    APP_ENV: str = Field(default="development", description="Application execution environment (e.g., development, production)")
    LOG_LEVEL: str = Field(default="INFO", description="Global logging level")
    DATABASE_URL: str = Field(..., description="Connection URL for the relational database")
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434", description="Base URL for the local Ollama LLM server")
    VECTOR_DB_PATH: Path = Field(..., description="Filesystem path to local vector database files")
    SECRET_KEY: str = Field(..., description="Secret key used for cryptography and session signing")

    # RAG and Embedding Configuration
    RAW_DOCUMENTS_DIR: Path = Field(default=BASE_DIR / "data" / "raw_documents", description="Directory for raw document ingestion")
    VECTOR_STORE_DIR: Path = Field(default=BASE_DIR / "data" / "vector_store", description="Root directory for vector database storage")
    CHROMA_DB_DIR: Path = Field(default=BASE_DIR / "data" / "vector_store" / "chromadb", description="ChromaDB persistent directory")
    EMBEDDING_MODEL_NAME: str = Field(default="all-MiniLM-L6-v2", description="Name of the embedding model to use")
    EMBEDDING_PROVIDER: str = Field(default="sentence-transformers", description="Embedding provider: sentence-transformers, ollama, openai, azure-openai, snowflake")
    DEFAULT_CHUNK_SIZE: int = Field(default=500, description="Default character chunk size for splitting text")
    DEFAULT_CHUNK_OVERLAP: int = Field(default=50, description="Default character overlap size for splitting text")
    SQL_MAX_ROWS: int = Field(default=100, ge=1, le=10000, description="Maximum rows returned by conversational BI SQL queries")
    RRF_K: int = Field(default=60, ge=1, le=1000, description="Reciprocal Rank Fusion damping constant")
    HYBRID_TOP_K: int = Field(default=10, ge=1, le=1000, description="Maximum candidate count for hybrid retrieval")
    RERANK_TOP_K: int = Field(default=5, ge=1, le=1000, description="Maximum candidate count retained after reranking")
    MAX_MEMORY_TURNS: int = Field(default=20, ge=1, le=1000, description="Maximum turns retained in short-term conversation memory")
    MAX_MEMORY_TOKENS: int = Field(default=2000, ge=1, le=100000, description="Maximum approximate tokens retained in short-term conversation memory")
    MEMORY_COMPRESSION_STRATEGY: str = Field(default="trim_oldest", description="Short-term memory compression strategy")
    GUARDRAIL_STRICT_MODE: bool = Field(default=False, description="Raise on guardrail violations when enabled")
    ENABLE_INPUT_GUARDRAILS: bool = Field(default=True, description="Enable input safety guardrails")
    ENABLE_OUTPUT_GUARDRAILS: bool = Field(default=True, description="Enable output safety guardrails")
    ENABLE_PII_REDACTION: bool = Field(default=True, description="Enable PII/PHI redaction in generated outputs")

    # Config to load from .env file
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    from pydantic import model_validator
    
    @model_validator(mode="after")
    def create_required_directories(self) -> "Settings":
        """Automatically creates raw documents and vector database directories if missing."""
        try:
            self.RAW_DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
            self.VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
            self.CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ValueError(f"Failed to initialize required filesystem directories: {str(e)}")
        return self

@lru_cache()
def get_settings() -> Settings:
    """
    Load settings as a singleton instance with caching.
    Raises ConfigurationError if configuration validation fails.
    """
    try:
        return Settings()
    except ValidationError as e:
        # Construct a detailed error message from validation failures for enterprise visibility
        errors = []
        for error in e.errors():
            loc = " -> ".join(str(loc) for loc in error["loc"])
            errors.append(f"{loc}: {error['msg']}")
        err_msg = "; ".join(errors)
        raise ConfigurationError(
            message=f"Configuration validation failed: {err_msg}",
            original_exception=e
        )
