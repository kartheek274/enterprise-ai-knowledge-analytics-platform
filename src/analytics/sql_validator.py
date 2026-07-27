"""Enterprise SQL validation guardrails for conversational BI."""

import logging
import re
from typing import Dict, Optional, Set

from src.analytics.models import SQLValidationResult
from src.analytics.schema_inspector import SchemaInspector
from src.common.config.settings import get_settings

logger = logging.getLogger("eakap.analytics.sql_validator")


class SQLValidator:
    """Validate generated SQL for read-only execution and schema compliance."""

    FORBIDDEN_KEYWORDS = (
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "TRUNCATE",
        "CREATE",
        "REPLACE",
        "GRANT",
        "PRAGMA",
        "ATTACH",
        "DETACH",
        "VACUUM",
        "EXPLAIN",
        "ANALYZE",
    )

    def __init__(
        self,
        schema_inspector: SchemaInspector,
        max_rows: Optional[int] = None,
    ) -> None:
        self.schema_inspector = schema_inspector
        self.max_rows = max_rows or get_settings().SQL_MAX_ROWS

    def validate(self, sql: str) -> SQLValidationResult:
        """Return validation result with sanitized SQL when safe."""
        candidate = self._normalize(sql)
        if not candidate:
            return SQLValidationResult(is_valid=False, error_message="SQL is empty.")

        if ";" in candidate:
            return SQLValidationResult(
                is_valid=False,
                error_message="Semicolon and multi-statement SQL are not allowed.",
            )

        if not re.match(r"^\s*(SELECT|WITH)\b", candidate, flags=re.IGNORECASE):
            return SQLValidationResult(
                is_valid=False,
                error_message="Only SELECT and WITH statements are allowed.",
            )

        forbidden = self._find_forbidden_keyword(candidate)
        if forbidden:
            return SQLValidationResult(
                is_valid=False,
                error_message=f"Forbidden SQL keyword detected: {forbidden}.",
            )

        schema = self.schema_inspector.inspect_schema()
        schema_error = self._validate_schema_references(candidate, schema)
        if schema_error:
            return SQLValidationResult(is_valid=False, error_message=schema_error)

        sanitized = self._enforce_limit(candidate)
        logger.info("SQL validated successfully")
        return SQLValidationResult(is_valid=True, sanitized_sql=sanitized)

    @staticmethod
    def _normalize(sql: str) -> str:
        return re.sub(r"\s+", " ", sql.strip())

    def _find_forbidden_keyword(self, sql: str) -> Optional[str]:
        for keyword in self.FORBIDDEN_KEYWORDS:
            if re.search(rf"\b{keyword}\b", sql, flags=re.IGNORECASE):
                return keyword
        return None

    def _validate_schema_references(
        self,
        sql: str,
        schema: Dict[str, Dict[str, object]],
    ) -> Optional[str]:
        allowed_tables = set(schema.keys())
        referenced_tables = self._extract_referenced_tables(sql)
        unknown_tables = referenced_tables - allowed_tables
        if unknown_tables:
            return f"Unknown table referenced: {sorted(unknown_tables)[0]}."

        table_aliases = self._extract_table_aliases(sql)
        allowed_aliases = set(table_aliases.keys())
        allowed_columns = {
            table: {column["name"] for column in info["columns"]}
            for table, info in schema.items()
        }

        for qualifier, column in re.findall(r"\b([A-Za-z_][\w]*)\.([A-Za-z_][\w]*)\b", sql):
            if qualifier in allowed_tables:
                table_name = qualifier
            elif qualifier in allowed_aliases:
                table_name = table_aliases[qualifier]
            else:
                return f"Unknown table or alias referenced: {qualifier}."
            if column not in allowed_columns.get(table_name, set()):
                return f"Invalid column referenced: {qualifier}.{column}."

        unqualified_error = self._validate_unqualified_select_columns(sql, allowed_columns)
        if unqualified_error:
            return unqualified_error
        return None

    @staticmethod
    def _extract_referenced_tables(sql: str) -> Set[str]:
        return {
            match.group(1)
            for match in re.finditer(r"\b(?:FROM|JOIN)\s+([A-Za-z_][\w]*)\b", sql, re.IGNORECASE)
        }

    @staticmethod
    def _extract_table_aliases(sql: str) -> Dict[str, str]:
        aliases: Dict[str, str] = {}
        for match in re.finditer(
            r"\b(?:FROM|JOIN)\s+([A-Za-z_][\w]*)(?:\s+(?:AS\s+)?([A-Za-z_][\w]*))?",
            sql,
            re.IGNORECASE,
        ):
            table, alias = match.group(1), match.group(2)
            if alias and alias.upper() not in {"ON", "WHERE", "GROUP", "ORDER", "LIMIT", "JOIN"}:
                aliases[alias] = table
        return aliases

    @staticmethod
    def _validate_unqualified_select_columns(
        sql: str,
        allowed_columns: Dict[str, Set[str]],
    ) -> Optional[str]:
        select_match = re.search(r"\bSELECT\b(.*?)\bFROM\b", sql, re.IGNORECASE)
        if not select_match:
            return None
        select_clause = select_match.group(1)
        if "*" in select_clause:
            return None

        known_all_columns = set().union(*allowed_columns.values()) if allowed_columns else set()
        expressions = [expr.strip() for expr in select_clause.split(",")]
        for expression in expressions:
            expression = re.sub(r"\bAS\s+[A-Za-z_][\w]*$", "", expression, flags=re.IGNORECASE).strip()
            expression = re.sub(r"\b(COUNT|SUM|AVG|MIN|MAX)\s*\((.*?)\)", r"\2", expression, flags=re.IGNORECASE)
            if "." in expression or expression == "*" or re.search(r"['\"0-9()+\-*/]", expression):
                continue
            token_match = re.match(r"^([A-Za-z_][\w]*)$", expression)
            if token_match and token_match.group(1) not in known_all_columns:
                return f"Invalid column referenced: {token_match.group(1)}."
        return None

    def _enforce_limit(self, sql: str) -> str:
        if re.search(r"\bLIMIT\s+\d+\b", sql, flags=re.IGNORECASE):
            return sql
        return f"{sql} LIMIT {self.max_rows}"
