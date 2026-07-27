import sys
from pathlib import Path
from typing import Dict, Any, Tuple
from src.common.config.settings import get_settings
from src.common.logging.logger import setup_logger
from src.common.errors.exceptions import EAKAPBaseException, ConfigurationError

# Initialize system logger
logger = setup_logger("eakap.app")

def check_health() -> Tuple[bool, Dict[str, Any]]:
    """
    Performs platform health checks to verify that EAKAP can start safely.
    Checks config loading, logger status, required directories, python version, 
    relational database, vector store, and embedding provider.
    """
    health_status: Dict[str, Any] = {
        "configuration": "unknown",
        "logging": "unknown",
        "directories": "unknown",
        "runtime": "unknown",
        "database": "unknown",
        "vector_store": "unknown",
        "embeddings": "unknown",
        "llm_provider": "unknown",
        "prompt_manager": "unknown",
        "analytics": "unknown",
        "advanced_retrieval": "unknown",
        "memory": "unknown",
        "governance": "unknown"
    }
    is_healthy = True

    # 1. Verify Configuration
    try:
        settings = get_settings()
        health_status["configuration"] = {
            "status": "healthy",
            "environment": settings.APP_ENV
        }
    except ConfigurationError as e:
        is_healthy = False
        health_status["configuration"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        return False, health_status  # Fail early if settings cannot load
    except Exception as e:
        is_healthy = False
        health_status["configuration"] = {
            "status": "unhealthy",
            "error": f"Unexpected error during configuration loading: {str(e)}"
        }
        return False, health_status

    # 2. Verify Logger
    try:
        if logger and len(logger.handlers) > 0:
            health_status["logging"] = {
                "status": "healthy",
                "handlers": [type(h).__name__ for h in logger.handlers]
            }
        else:
            is_healthy = False
            health_status["logging"] = {
                "status": "unhealthy",
                "error": "Logger initialized with no active handlers."
            }
    except Exception as e:
        is_healthy = False
        health_status["logging"] = {
            "status": "unhealthy",
            "error": f"Logger health check failed: {str(e)}"
        }

    # 3. Verify Required Directories (Fail-safe directory checks)
    try:
        base_dir = Path(__file__).resolve().parent.parent.parent
        required_dirs = {
            "logs": base_dir / "logs",
            "data": base_dir / "data",
            "raw_documents": settings.RAW_DOCUMENTS_DIR,
            "vector_store": settings.VECTOR_STORE_DIR
        }
        
        dir_status = {}
        for name, path in required_dirs.items():
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
            
            # Check read and write permissions in directory
            test_file = path / ".healthcheck_write_test"
            try:
                test_file.write_text("healthcheck", encoding="utf-8")
                test_file.unlink()
                dir_status[name] = "exists_and_writable"
            except IOError as io_err:
                is_healthy = False
                dir_status[name] = f"not_writable: {str(io_err)}"
                
        health_status["directories"] = {
            "status": "healthy" if is_healthy else "unhealthy",
            "paths": dir_status
        }
    except Exception as e:
        is_healthy = False
        health_status["directories"] = {
            "status": "unhealthy",
            "error": f"Directory verification failed: {str(e)}"
        }

    # 4. Verify Python Runtime
    try:
        sys_version = sys.version_info
        if sys_version.major == 3 and sys_version.minor >= 10:
            health_status["runtime"] = {
                "status": "healthy",
                "version": f"{sys_version.major}.{sys_version.minor}.{sys_version.micro}"
            }
        else:
            is_healthy = False
            health_status["runtime"] = {
                "status": "unhealthy",
                "version": f"{sys_version.major}.{sys_version.minor}.{sys_version.micro}",
                "error": "Python version must be >= 3.10"
            }
    except Exception as e:
        is_healthy = False
        health_status["runtime"] = {
            "status": "unhealthy",
            "error": f"Runtime verification failed: {str(e)}"
        }

    # 5. Verify Database Connectivity and Schemas
    try:
        from src.common.database.connection import verify_connection, get_session
        from sqlalchemy import inspect
        
        # Ping the database engine
        verify_connection()
        
        # Verify database file accessibility if SQLite
        file_status = "not_applicable"
        if settings.DATABASE_URL.startswith("sqlite:///"):
            db_file_relative = settings.DATABASE_URL.replace("sqlite:///", "")
            db_file_path = base_dir / db_file_relative
            if not db_file_path.exists():
                is_healthy = False
                file_status = f"missing: Database file does not exist at {db_file_path}"
            else:
                try:
                    # Test write access
                    with open(db_file_path, "r+"):
                        file_status = "exists_and_accessible"
                except IOError as io_err:
                    is_healthy = False
                    file_status = f"not_accessible: {str(io_err)}"

        # Verify active session creation and schema integrity
        db_tables = []
        with get_session() as session:
            inspector = inspect(session.bind)
            db_tables = inspector.get_table_names()
            
        expected_tables = ["patients", "claims", "financial_records", "document_metadata"]
        missing_tables = [table for table in expected_tables if table not in db_tables]
        
        if missing_tables:
            is_healthy = False
            health_status["database"] = {
                "status": "unhealthy",
                "error": f"Database schema incomplete. Missing expected tables: {missing_tables}",
                "existing_tables": db_tables,
                "file_status": file_status
            }
        elif file_status.startswith("missing") or file_status.startswith("not_accessible"):
            is_healthy = False
            health_status["database"] = {
                "status": "unhealthy",
                "error": f"Database file state issue: {file_status}",
                "existing_tables": db_tables
            }
        else:
            health_status["database"] = {
                "status": "healthy",
                "tables_present": db_tables,
                "file_status": file_status
            }
    except Exception as e:
        is_healthy = False
        health_status["database"] = {
            "status": "unhealthy",
            "error": f"Database verification failed: {str(e)}"
        }

    # 6. Verify Vector Store (ChromaDB)
    try:
        from src.rag.vector_store.chroma_service import ChromaService
        chroma_service = ChromaService()
        collections = chroma_service.list_collections()
        health_status["vector_store"] = {
            "status": "healthy",
            "collections_count": len(collections),
            "directory": chroma_service.chroma_dir
        }
    except Exception as e:
        is_healthy = False
        health_status["vector_store"] = {
            "status": "unhealthy",
            "error": f"Vector Store health check failed: {str(e)}"
        }

    # 7. Verify Embedding Provider
    try:
        from src.rag.embeddings.embedding_service import EmbeddingService
        embedding_service = EmbeddingService()
        test_vector = embedding_service.embed_query("healthcheck")
        health_status["embeddings"] = {
            "status": "healthy",
            "provider": embedding_service.provider.__class__.__name__,
            "dimension": len(test_vector)
        }
    except Exception as e:
        is_healthy = False
        health_status["embeddings"] = {
            "status": "unhealthy",
            "error": f"Embedding provider verification failed: {str(e)}"
        }

    # 8. Verify LLM Provider configuration without forcing a live model call
    try:
        from src.rag.llm.llm_provider import get_llm_provider
        llm_provider = get_llm_provider()
        health_status["llm_provider"] = {
            "status": "healthy",
            "provider": llm_provider.provider_name,
            "model": llm_provider.model_name
        }
    except Exception as e:
        is_healthy = False
        health_status["llm_provider"] = {
            "status": "unhealthy",
            "error": f"LLM provider verification failed: {str(e)}"
        }

    # 9. Verify Prompt Manager registry availability
    try:
        from src.rag.prompts.manager import PromptManager
        prompt_manager = PromptManager()
        templates = prompt_manager.list_templates()
        if not templates:
            is_healthy = False
            health_status["prompt_manager"] = {
                "status": "unhealthy",
                "error": "No prompt templates registered."
            }
        else:
            health_status["prompt_manager"] = {
                "status": "healthy",
                "templates": templates
            }
    except Exception as e:
        is_healthy = False
        health_status["prompt_manager"] = {
            "status": "unhealthy",
            "error": f"Prompt Manager verification failed: {str(e)}"
        }

    # 10. Verify Conversational Analytics configuration and schema access
    try:
        from src.analytics.schema_inspector import SchemaInspector
        inspector = SchemaInspector()
        schema = inspector.inspect_schema()
        required_tables = list(inspector.BUSINESS_TABLES)
        missing_tables = [table for table in required_tables if table not in schema]
        if missing_tables:
            is_healthy = False
            health_status["analytics"] = {
                "status": "unhealthy",
                "sql_max_rows": settings.SQL_MAX_ROWS,
                "missing_tables": missing_tables,
                "available_tables": list(schema.keys())
            }
        else:
            health_status["analytics"] = {
                "status": "healthy",
                "sql_max_rows": settings.SQL_MAX_ROWS,
                "business_tables": list(schema.keys())
            }
    except Exception as e:
        is_healthy = False
        health_status["analytics"] = {
            "status": "unhealthy",
            "error": f"Analytics verification failed: {str(e)}"
        }

    # 11. Verify Advanced Retrieval configuration and component availability
    try:
        from src.rag.retrieval import (
            BM25Retriever,
            CrossEncoderReranker,
            HybridRetriever,
            RankFusionService,
            VectorRetriever,
        )

        bm25 = BM25Retriever()
        reranker = CrossEncoderReranker()
        health_status["advanced_retrieval"] = {
            "status": "healthy",
            "configuration": {
                "rrf_k": settings.RRF_K,
                "hybrid_top_k": settings.HYBRID_TOP_K,
                "rerank_top_k": settings.RERANK_TOP_K,
            },
            "components": {
                "vector_retriever": VectorRetriever.__name__,
                "bm25_available": bm25 is not None,
                "bm25_initialized": bm25.is_initialized(),
                "rank_fusion": RankFusionService.__name__,
                "hybrid_retriever": HybridRetriever.__name__,
                "reranker": reranker.name,
                "reranker_available": reranker.available,
            },
        }
    except Exception as e:
        is_healthy = False
        health_status["advanced_retrieval"] = {
            "status": "unhealthy",
            "error": f"Advanced retrieval verification failed: {str(e)}"
        }

    # 12. Verify short-term conversational memory configuration and store availability
    try:
        from src.rag.memory import InMemorySessionStore, MemoryConfig, MemoryFormatter, SessionMemoryManager

        store = InMemorySessionStore()
        manager = SessionMemoryManager(
            store=store,
            formatter=MemoryFormatter(),
            config=MemoryConfig(
                max_turns=settings.MAX_MEMORY_TURNS,
                max_tokens=settings.MAX_MEMORY_TOKENS,
                compression_strategy=settings.MEMORY_COMPRESSION_STRATEGY,
            ),
        )
        health_status["memory"] = {
            "status": "healthy",
            "configuration": {
                "max_turns": settings.MAX_MEMORY_TURNS,
                "max_tokens": settings.MAX_MEMORY_TOKENS,
                "compression_strategy": settings.MEMORY_COMPRESSION_STRATEGY,
            },
            "components": {
                "store": store.__class__.__name__,
                "manager": manager.__class__.__name__,
                "sessions": len(store.list_sessions()),
            },
        }
    except Exception as e:
        is_healthy = False
        health_status["memory"] = {
            "status": "unhealthy",
            "error": f"Memory verification failed: {str(e)}"
        }

    # 13. Verify governance configuration, registry, and redaction policy setup
    try:
        from src.governance.service import GovernanceService
        from src.governance.guardrails import PIIDetector, PIIRedactor

        governance_service = GovernanceService()
        redactor = PIIRedactor(PIIDetector())
        health_status["governance"] = {
            "status": "healthy",
            "configuration": {
                "strict_mode": settings.GUARDRAIL_STRICT_MODE,
                "input_guardrails": settings.ENABLE_INPUT_GUARDRAILS,
                "output_guardrails": settings.ENABLE_OUTPUT_GUARDRAILS,
                "pii_redaction": settings.ENABLE_PII_REDACTION,
            },
            "registry": governance_service.guardrail_registry(),
            "redaction_policies": sorted(redactor.REPLACEMENTS.keys()),
        }
    except Exception as e:
        is_healthy = False
        health_status["governance"] = {
            "status": "unhealthy",
            "error": f"Governance verification failed: {str(e)}"
        }

    return is_healthy, health_status

def run_startup() -> None:
    """
    Core entry startup sequence. Loads configurations, runs diagnostics,
    fails fast on errors.
    """
    banner = """
======================================================
  ENTERPRISE AI KNOWLEDGE & ANALYTICS PLATFORM (EAKAP)
  [Step 9: Enterprise AI Governance & Security]
======================================================
    """
    print(banner)
    
    logger.info("Starting EAKAP Platform...")
    
    try:
        # Load and validate settings (Fail fast)
        settings = get_settings()
        logger.info(f"Configuration loaded. Environment: {settings.APP_ENV}")
        
        # Execute health checks
        is_healthy, health_details = check_health()
        
        if is_healthy:
            logger.info("Platform health check: HEALTHY")
            logger.info(f"Health details: {health_details}")
            print("\n>>> EAKAP Knowledge Platform initialized successfully. STATUS: healthy. <<<\n")
        else:
            logger.critical("Platform health check: UNHEALTHY. Startup aborted.")
            logger.critical(f"Diagnostics: {health_details}")
            print("\n>>> EAKAP Knowledge Platform startup FAILED. Check logs for details. <<<\n", file=sys.stderr)
            sys.exit(1)
            
    except EAKAPBaseException as e:
        logger.critical(f"EAKAP Core initialization failed: {str(e)}", exc_info=True)
        print(f"\nCRITICAL SHUTDOWN: {e}\n", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Unexpected system crash during startup: {str(e)}", exc_info=True)
        print(f"\nSYSTEM CRASH: {e}\n", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run_startup()
