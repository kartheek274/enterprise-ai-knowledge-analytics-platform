import logging
from sqlalchemy import inspect
from src.common.database.connection import engine
from src.common.database.models import Base
from src.common.errors.exceptions import DatabaseConnectionError

logger = logging.getLogger("eakap.database.init")

def init_database() -> None:
    """
    Constructs all defined ORM tables in the database schema if they do not exist.
    Runs schema checks to verify all expected tables are actively registered.
    This operation is safe to execute repeatedly (idempotent).
    """
    logger.info("Initializing relational database schema creation...")
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Verify schema table registration
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        expected_tables = ["patients", "claims", "financial_records", "document_metadata"]
        
        missing_tables = [table for table in expected_tables if table not in existing_tables]
        
        if missing_tables:
            raise DatabaseConnectionError(
                message=f"Database schema validation failed. Expected tables missing: {missing_tables}"
            )
            
        logger.info(f"Database schema validated successfully. Tables present: {existing_tables}")
        
    except Exception as e:
        logger.critical(f"Failed to initialize database schema: {str(e)}")
        if isinstance(e, DatabaseConnectionError):
            raise e
        raise DatabaseConnectionError(
            message="Failed during DDL database schema execution.",
            original_exception=e
        )

if __name__ == "__main__":
    from src.common.logging.logger import setup_logger
    setup_logger("eakap.database.init")
    init_database()
