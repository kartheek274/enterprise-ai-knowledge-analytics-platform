"""Schema inspection service for conversational analytics."""

import logging
import time
from typing import Any, Dict, List, Optional

from src.analytics.exceptions import SchemaInspectionError
from src.common.database.service import DatabaseService

logger = logging.getLogger("eakap.analytics.schema_inspector")


class SchemaInspector:
    """Inspect and cache the business schema exposed to Text-to-SQL."""

    BUSINESS_TABLES = ("patients", "claims", "financial_records")

    def __init__(self, database_service: type[DatabaseService] = DatabaseService) -> None:
        self.database_service = database_service
        self._schema_cache: Optional[Dict[str, Dict[str, Any]]] = None
        self._context_cache: Optional[str] = None

    def inspect_schema(self, force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """Return cached business table schema, refreshing when requested."""
        if self._schema_cache is not None and not force_refresh:
            return self._schema_cache

        try:
            schema: Dict[str, Dict[str, Any]] = {}
            existing_tables = {
                row["name"]
                for row in self.database_service.execute_query(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }

            for table_name in self.BUSINESS_TABLES:
                if table_name not in existing_tables:
                    continue
                columns = self._inspect_columns(table_name)
                foreign_keys = self._inspect_foreign_keys(table_name)
                schema[table_name] = {
                    "columns": columns,
                    "foreign_keys": foreign_keys,
                }

            self._schema_cache = schema
            self._context_cache = None
            logger.info("Analytics schema inspected | tables=%s", list(schema.keys()))
            return schema
        except Exception as exc:
            raise SchemaInspectionError(
                message="Failed to inspect analytics schema.",
                original_exception=exc,
            )

    def get_schema_context(self, force_refresh: bool = False) -> str:
        """Return a compact schema prompt context for SQL generation."""
        if self._context_cache is not None and not force_refresh:
            return self._context_cache

        schema = self.inspect_schema(force_refresh=force_refresh)
        parts: List[str] = []
        for table_name, table_info in schema.items():
            column_specs = [
                f"{column['name']} {column['type']}"
                for column in table_info["columns"]
            ]
            parts.append(f"TABLE {table_name}: {', '.join(column_specs)}")
            for foreign_key in table_info["foreign_keys"]:
                parts.append(
                    "FK "
                    f"{table_name}.{foreign_key['from_column']} -> "
                    f"{foreign_key['to_table']}.{foreign_key['to_column']}"
                )
        self._context_cache = "\n".join(parts)
        return self._context_cache

    def required_tables_exist(self) -> bool:
        """Return true when all business tables are available."""
        return set(self.BUSINESS_TABLES).issubset(set(self.inspect_schema().keys()))

    def _inspect_columns(self, table_name: str) -> List[Dict[str, Any]]:
        rows = self.database_service.execute_query(
            f"SELECT name, type, pk, \"notnull\" AS not_null FROM pragma_table_info('{table_name}')"
        )
        return [
            {
                "name": row["name"],
                "type": row["type"],
                "primary_key": bool(row["pk"]),
                "nullable": not bool(row["not_null"]),
            }
            for row in rows
        ]

    def _inspect_foreign_keys(self, table_name: str) -> List[Dict[str, str]]:
        rows = self.database_service.execute_query(
            f"SELECT \"from\" AS from_column, \"table\" AS to_table, \"to\" AS to_column "
            f"FROM pragma_foreign_key_list('{table_name}')"
        )
        return [
            {
                "from_column": row["from_column"],
                "to_table": row["to_table"],
                "to_column": row["to_column"],
            }
            for row in rows
        ]

    @property
    def cache_timestamp_ms(self) -> float:
        """Expose current time for simple diagnostics without storing wall-clock state."""
        return time.time() * 1_000
