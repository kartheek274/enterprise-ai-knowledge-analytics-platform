import logging
import time
from typing import Any, Dict, List, Type, TypeVar, Optional
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from sqlalchemy.orm import DeclarativeBase
from src.common.database.connection import get_session
from src.common.errors.exceptions import (
    EAKAPBaseException, 
    DatabaseConnectionError, 
    ValidationError, 
    ResourceNotFoundError
)

logger = logging.getLogger("eakap.database.service")

# Generic TypeVar representing subclasses of ORM DeclarativeBase
T = TypeVar("T", bound=DeclarativeBase)

class DatabaseService:
    """
    Abstractions for interacting with the database.
    Encapsulates all SQLAlchemy session management and transaction cycles.
    Provides parameterized raw SQL runners, standardized CRUD, transaction rollbacks,
    logging, and latency metrics.
    """

    @staticmethod
    def execute_raw_sql(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Executes a parameterized raw SQL query and returns results as a list of dicts.
        Captures execution times and intercepts query engine failures.
        """
        start_time = time.perf_counter()
        sql_text = text(query)
        bind_params = params or {}
        
        try:
            with get_session() as session:
                result = session.execute(sql_text, bind_params)
                
                # Check if query yields records (e.g. SELECT)
                if result.returns_rows:
                    columns = result.keys()
                    rows = [dict(zip(columns, row)) for row in result.all()]
                else:
                    rows = []
                    
                execution_time = (time.perf_counter() - start_time) * 1000
                logger.info(
                    f"Raw SQL executed successfully in {execution_time:.2f}ms. "
                    f"Query: '{query[:100]}...' | Rows: {len(rows)}"
                )
                return rows
                
        except (OperationalError, SQLAlchemyError) as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"Raw SQL execution failed after {execution_time:.2f}ms. "
                f"Query: '{query[:100]}...' | Error: {str(e)}"
            )
            raise DatabaseConnectionError(
                message="Raw query execution failed due to database engine runtime error.",
                original_exception=e
            )

    @staticmethod
    def execute_query(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Executes a parameterized SQL query through the managed database service.

        This method is the stable query execution API for higher-level bounded
        contexts such as conversational analytics. It delegates to the existing
        raw SQL runner so all session management remains centralized here.
        """
        return DatabaseService.execute_raw_sql(query=query, params=params)

    @staticmethod
    def insert_record(instance: T) -> T:
        """
        Inserts an ORM record, handling transaction and validation errors.
        """
        start_time = time.perf_counter()
        try:
            with get_session() as session:
                session.add(instance)
                session.flush()
                # Because expire_on_commit=False is set in connection layer,
                # we can safely return the object and read its attributes.
                
                logger.info(
                    f"Inserted record ID {getattr(instance, 'patient_id', getattr(instance, 'claim_id', 'unknown'))} "
                    f"into '{instance.__tablename__}' in {(time.perf_counter() - start_time)*1000:.2f}ms."
                )
                return instance
        except IntegrityError as e:
            logger.error(f"Constraint integrity violation during insert: {str(e)}")
            raise ValidationError(
                message="Data integrity constraint violated. Invalid field parameters.",
                original_exception=e
            )
        except SQLAlchemyError as e:
            logger.error(f"Database engine error during insert: {str(e)}")
            raise DatabaseConnectionError(
                message="Failed to insert entity due to database runtime exception.",
                original_exception=e
            )

    @staticmethod
    def get_record(model_class: Type[T], record_id: Any) -> T:
        """
        Retrieves a record by its primary key.
        Raises ResourceNotFoundError if the record does not exist.
        """
        start_time = time.perf_counter()
        try:
            with get_session() as session:
                record = session.get(model_class, record_id)
                if not record:
                    raise ResourceNotFoundError(
                        message=f"Record with ID '{record_id}' not found in table '{model_class.__tablename__}'."
                    )
                logger.info(
                    f"Retrieved record ID {record_id} from '{model_class.__tablename__}' "
                    f"in {(time.perf_counter() - start_time)*1000:.2f}ms."
                )
                return record
        except EAKAPBaseException:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database engine error during retrieve: {str(e)}")
            raise DatabaseConnectionError(
                message="Failed to retrieve entity from database store.",
                original_exception=e
            )

    @staticmethod
    def update_record(model_class: Type[T], record_id: Any, update_data: Dict[str, Any]) -> T:
        """
        Updates an existing record, applying field changes in a single transaction.
        """
        start_time = time.perf_counter()
        try:
            with get_session() as session:
                record = session.get(model_class, record_id)
                if not record:
                    raise ResourceNotFoundError(
                        message=f"Record with ID '{record_id}' not found in table '{model_class.__tablename__}' for update."
                    )
                
                for key, value in update_data.items():
                    if hasattr(record, key):
                        setattr(record, key, value)
                    else:
                        raise ValidationError(
                            message=f"Invalid attribute '{key}' for table '{model_class.__tablename__}'."
                        )
                
                session.flush()
                
                logger.info(
                    f"Updated record ID {record_id} in '{model_class.__tablename__}' "
                    f"in {(time.perf_counter() - start_time)*1000:.2f}ms."
                )
                return record
        except IntegrityError as e:
            logger.error(f"Constraint integrity violation during update: {str(e)}")
            raise ValidationError(
                message="Data integrity constraint violated during update operations.",
                original_exception=e
            )
        except EAKAPBaseException:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error during update: {str(e)}")
            raise DatabaseConnectionError(
                message="Failed to update record in database store.",
                original_exception=e
            )

    @staticmethod
    def delete_record(model_class: Type[T], record_id: Any) -> None:
        """
        Deletes a record by its primary key.
        """
        start_time = time.perf_counter()
        try:
            with get_session() as session:
                record = session.get(model_class, record_id)
                if not record:
                    raise ResourceNotFoundError(
                        message=f"Record with ID '{record_id}' not found in table '{model_class.__tablename__}' for deletion."
                    )
                session.delete(record)
                
            logger.info(
                f"Deleted record ID {record_id} from '{model_class.__tablename__}' "
                f"in {(time.perf_counter() - start_time)*1000:.2f}ms."
            )
        except EAKAPBaseException:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error during deletion: {str(e)}")
            raise DatabaseConnectionError(
                message="Failed to delete record from database store.",
                original_exception=e
            )
