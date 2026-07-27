from typing import Iterator, Tuple

import pytest

from src.analytics.exceptions import AnalyticsExecutionError
from src.analytics.models import (
    AnalyticsTelemetry,
    SQLExecutionResult,
    SQLQueryRequest,
)
from src.analytics.pipeline import ConversationalBIEngine
from src.analytics.result_formatter import ResultFormatter
from src.analytics.schema_inspector import SchemaInspector
from src.analytics.sql_executor import SQLExecutor
from src.analytics.sql_generator import SQLGenerator
from src.analytics.sql_validator import SQLValidator
from src.analytics.summary_generator import SummaryGenerator
from src.rag.llm.base import BaseLLMProvider


class FakeDatabaseService:
    calls = []

    @classmethod
    def reset(cls):
        cls.calls = []

    @classmethod
    def execute_query(cls, query, params=None):
        cls.calls.append(query)
        if "sqlite_master" in query:
            return [
                {"name": "patients"},
                {"name": "claims"},
                {"name": "financial_records"},
                {"name": "document_metadata"},
            ]
        if "pragma_table_info('patients')" in query:
            return [
                {"name": "patient_id", "type": "INTEGER", "pk": 1, "not_null": 1},
                {"name": "first_name", "type": "VARCHAR", "pk": 0, "not_null": 1},
                {"name": "state", "type": "VARCHAR", "pk": 0, "not_null": 1},
            ]
        if "pragma_table_info('claims')" in query:
            return [
                {"name": "claim_id", "type": "INTEGER", "pk": 1, "not_null": 1},
                {"name": "patient_id", "type": "INTEGER", "pk": 0, "not_null": 1},
                {"name": "claim_amount", "type": "NUMERIC", "pk": 0, "not_null": 1},
                {"name": "claim_status", "type": "VARCHAR", "pk": 0, "not_null": 1},
            ]
        if "pragma_table_info('financial_records')" in query:
            return [
                {"name": "record_id", "type": "INTEGER", "pk": 1, "not_null": 1},
                {"name": "claim_id", "type": "INTEGER", "pk": 0, "not_null": 1},
                {"name": "paid_amount", "type": "NUMERIC", "pk": 0, "not_null": 1},
            ]
        if "pragma_foreign_key_list('claims')" in query:
            return [
                {"from_column": "patient_id", "to_table": "patients", "to_column": "patient_id"}
            ]
        if "pragma_foreign_key_list('financial_records')" in query:
            return [
                {"from_column": "claim_id", "to_table": "claims", "to_column": "claim_id"}
            ]
        if "pragma_foreign_key_list" in query:
            return []
        if "WHERE state = 'ZZ'" in query:
            return []
        return [{"state": "MA", "claim_count": 2, "total_amount": 300.0}]


class FakeLLMProvider(BaseLLMProvider):
    def __init__(self, sql_response=None, summary_response="There are 2 claims totaling 300.0.") -> None:
        self.sql_response = sql_response or "SELECT state FROM patients"
        self.summary_response = summary_response
        self.prompts = []

    @property
    def provider_name(self) -> str:
        return "fake"

    @property
    def model_name(self) -> str:
        return "fake-model"

    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.0) -> Tuple[str, int, int]:
        self.prompts.append(prompt)
        if "SQL:" in prompt:
            return self.sql_response, 10, 5
        return self.summary_response, 10, 5

    def stream_generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.0,
    ) -> Iterator[str]:
        yield self.summary_response


def make_inspector():
    FakeDatabaseService.reset()
    return SchemaInspector(database_service=FakeDatabaseService)


def test_schema_inspector_generates_compact_context_and_caches():
    inspector = make_inspector()

    context_1 = inspector.get_schema_context()
    first_call_count = len(FakeDatabaseService.calls)
    context_2 = inspector.get_schema_context()

    assert "TABLE patients" in context_1
    assert "FK claims.patient_id -> patients.patient_id" in context_1
    assert context_1 == context_2
    assert len(FakeDatabaseService.calls) == first_call_count


def test_sql_generation_uses_schema_grounded_prompt():
    llm = FakeLLMProvider(sql_response="SELECT COUNT(claim_id) AS claim_count FROM claims")
    generator = SQLGenerator(llm)

    sql = generator.generate_sql("How many claims?", "TABLE claims: claim_id INTEGER")

    assert sql == "SELECT COUNT(claim_id) AS claim_count FROM claims"
    assert "Never invent tables or columns" in llm.prompts[0]
    assert "Return SQL only" in llm.prompts[0]


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM patients",
        "UPDATE patients SET state = 'MA'",
        "DROP TABLE claims",
        "PRAGMA table_info(patients)",
        "VACUUM",
        "ATTACH DATABASE 'x' AS x",
    ],
)
def test_sql_validator_rejects_forbidden_statements(sql):
    validator = SQLValidator(make_inspector(), max_rows=100)

    result = validator.validate(sql)

    assert result.is_valid is False


def test_sql_validator_rejects_semicolon_injection():
    validator = SQLValidator(make_inspector(), max_rows=100)

    result = validator.validate("SELECT state FROM patients; DROP TABLE claims")

    assert result.is_valid is False
    assert "Semicolon" in result.error_message


def test_sql_validator_rejects_unknown_table_and_invalid_column():
    validator = SQLValidator(make_inspector(), max_rows=100)

    unknown_table = validator.validate("SELECT name FROM employees")
    invalid_column = validator.validate("SELECT salary FROM patients")

    assert unknown_table.is_valid is False
    assert "Unknown table" in unknown_table.error_message
    assert invalid_column.is_valid is False
    assert "Invalid column" in invalid_column.error_message


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT state FROM patients",
        "SELECT COUNT(claim_id) AS claim_count FROM claims",
        "SELECT SUM(claim_amount) AS total_amount FROM claims",
        (
            "SELECT patients.state, COUNT(claims.claim_id) AS claim_count "
            "FROM patients JOIN claims ON patients.patient_id = claims.patient_id "
            "GROUP BY patients.state"
        ),
    ],
)
def test_sql_validator_accepts_positive_select_patterns(sql):
    validator = SQLValidator(make_inspector(), max_rows=50)

    result = validator.validate(sql)

    assert result.is_valid is True
    assert result.sanitized_sql.endswith("LIMIT 50")


def test_sql_validator_preserves_existing_limit():
    validator = SQLValidator(make_inspector(), max_rows=50)

    result = validator.validate("SELECT state FROM patients LIMIT 10")

    assert result.is_valid is True
    assert result.sanitized_sql == "SELECT state FROM patients LIMIT 10"


def test_sql_executor_returns_execution_result_and_empty_result_set():
    executor = SQLExecutor(database_service=FakeDatabaseService)

    result = executor.execute("SELECT state FROM patients WHERE state = 'ZZ'")

    assert result == SQLExecutionResult(rows=[], columns=[], row_count=0, execution_time_ms=result.execution_time_ms)
    assert result.execution_time_ms >= 0


def test_summary_generator_uses_base_llm_provider():
    llm = FakeLLMProvider(summary_response="No rows matched the question.")
    generator = SummaryGenerator(llm)

    summary = generator.generate_summary(
        "Show missing state",
        SQLExecutionResult(rows=[], columns=[], row_count=0, execution_time_ms=1.0),
    )

    assert summary == "No rows matched the question."
    assert "ROWS_JSON" in llm.prompts[0]


def test_result_formatter_assembles_response():
    formatter = ResultFormatter()
    telemetry = AnalyticsTelemetry(model_name="fake-model")
    execution_result = SQLExecutionResult(
        rows=[{"state": "MA"}],
        columns=["state"],
        row_count=1,
        execution_time_ms=2.0,
    )

    response = formatter.format(
        question="Show states",
        generated_sql="SELECT state FROM patients LIMIT 100",
        execution_result=execution_result,
        summary="One state returned.",
        telemetry=telemetry,
    )

    assert response.question == "Show states"
    assert response.telemetry.row_count == 1
    assert response.telemetry.sql_execution_ms == 2.0


def test_conversational_bi_engine_orchestrates_end_to_end():
    llm = FakeLLMProvider(
        sql_response=(
            "SELECT patients.state, COUNT(claims.claim_id) AS claim_count "
            "FROM patients JOIN claims ON patients.patient_id = claims.patient_id "
            "GROUP BY patients.state"
        ),
        summary_response="MA has 2 claims.",
    )
    inspector = make_inspector()
    engine = ConversationalBIEngine(
        schema_inspector=inspector,
        llm_provider=llm,
        sql_executor=SQLExecutor(database_service=FakeDatabaseService),
    )

    response = engine.execute(SQLQueryRequest(question="Count claims by state", user_id="u1"))

    assert response.summary == "MA has 2 claims."
    assert "LIMIT" in response.generated_sql
    assert response.execution_result.row_count == 1
    assert response.telemetry.status == "SUCCESS"
    assert response.telemetry.model_name == "fake-model"


def test_conversational_bi_engine_wraps_validation_failures():
    llm = FakeLLMProvider(sql_response="SELECT salary FROM patients")
    engine = ConversationalBIEngine(
        schema_inspector=make_inspector(),
        llm_provider=llm,
        sql_executor=SQLExecutor(database_service=FakeDatabaseService),
    )

    with pytest.raises(AnalyticsExecutionError):
        engine.execute(SQLQueryRequest(question="Show patient salary"))
