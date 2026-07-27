"""Unit tests for Step 10 Streamlit UI components and state management.

Runs without requiring Ollama, Chroma, or live database instances.
All services and Streamlit calls are mocked.
"""

from unittest.mock import MagicMock, patch
import pytest

from src.app.health_service import HealthService
from src.app.ui.state import UIStateManager
from src.app.ui.components.sidebar import render_sidebar
from src.app.ui.components.rag_tab import render_rag_tab
from src.app.ui.components.bi_tab import render_bi_tab
from src.app.ui.components.governance_tab import render_governance_tab
from src.app.ui.components.tables import render_citations_table, render_dict_table
from src.app.ui.components.charts import auto_chart
from src.rag.models.query import RAGQuery
from src.rag.models.rag_response import RAGResponse
from src.rag.models.retrieved_chunk import RetrievedChunk
from src.rag.models.telemetry import QueryTelemetry
from src.analytics.models import AnalyticsResponse, AnalyticsTelemetry, SQLExecutionResult
from src.analytics.exceptions import AnalyticsExecutionError


@pytest.fixture
def mock_session_state():
    """Mock streamlit.session_state with a simple dictionary."""
    state_dict = {}
    with patch("streamlit.session_state", state_dict):
        yield state_dict


@pytest.fixture
def state_manager(mock_session_state):
    """Return an initialized UIStateManager."""
    sm = UIStateManager()
    sm.initialize()
    return sm


# ============================================================================
# 1. UI State Manager & State Transitions Tests
# ============================================================================

def test_ui_state_manager_initialization(state_manager, mock_session_state):
    assert "current_session_id" in mock_session_state
    assert mock_session_state["chat_history"] == []
    assert mock_session_state["telemetry_logs"] == []
    assert mock_session_state["active_tab"] == "🧠 Knowledge Assistant"


def test_ui_state_manager_add_chat_turn(state_manager):
    state_manager.add_chat_turn("user", "Hello RAG")
    history = state_manager.get_chat_history()
    assert len(history) == 1
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hello RAG"


def test_ui_state_manager_telemetry_append(state_manager):
    state_manager.append_telemetry({"source": "rag", "latency": 120})
    logs = state_manager.get_telemetry_logs()
    assert len(logs) == 1
    assert logs[0]["source"] == "rag"
    assert logs[0]["latency"] == 120


def test_ui_state_manager_clear_session(state_manager):
    old_session_id = state_manager.get_session_id()
    state_manager.add_chat_turn("user", "Hello")
    state_manager.append_telemetry({"event": "test"})

    state_manager.clear_session()

    assert state_manager.get_chat_history() == []
    assert state_manager.get_telemetry_logs() == []
    assert state_manager.get_session_id() != old_session_id


def test_ui_state_manager_active_tab(state_manager):
    state_manager.set_active_tab("📊 Conversational BI")
    assert state_manager.get_active_tab() == "📊 Conversational BI"


# ============================================================================
# 2. HealthService Tests & Unavailable Health Service
# ============================================================================

def test_health_service_facade():
    health_service = HealthService()
    fake_health_details = {
        "configuration": {"status": "healthy"},
        "database": {"status": "healthy"},
        "vector_store": {"status": "unhealthy"},
    }
    with patch("src.app.main.check_health", return_value=(False, fake_health_details)):
        is_healthy, details = health_service.run()
        assert is_healthy is False
        assert details == fake_health_details
        assert health_service.extract_status(details["database"]) == "healthy"
        assert health_service.extract_status(details["vector_store"]) == "unhealthy"
        assert health_service.extract_status("invalid") == "unknown"


@patch("streamlit.warning")
def test_sidebar_unavailable_health_service(mock_warning, state_manager):
    mock_health = MagicMock(spec=HealthService)
    mock_health.run.side_effect = Exception("Database connection timeout")

    render_sidebar(state=state_manager, health_service=mock_health)

    assert mock_warning.called
    warning_args = str(mock_warning.call_args)
    assert "Health check unavailable" in warning_args


# ============================================================================
# 3. Sidebar Rendering Tests
# ============================================================================

@patch("streamlit.sidebar")
@patch("streamlit.caption")
@patch("streamlit.code")
@patch("streamlit.text_input", return_value="")
@patch("streamlit.columns", return_value=[MagicMock(), MagicMock()])
@patch("streamlit.button", return_value=False)
def test_render_sidebar_healthy(mock_btn, mock_cols, mock_txt, mock_code, mock_cap, mock_sidebar, state_manager):
    mock_health = MagicMock(spec=HealthService)
    mock_health.run.return_value = (True, {
        "configuration": {"status": "healthy", "environment": "testing"},
        "database": {"status": "healthy", "tables_present": ["patients"]},
        "llm_provider": {"status": "healthy", "provider": "mock", "model": "mock-v1"},
    })

    render_sidebar(state=state_manager, health_service=mock_health)
    assert mock_health.run.called


# ============================================================================
# 4. Knowledge Assistant (RAG) Tab & Exception Tests
# ============================================================================

@patch("streamlit.chat_input", return_value="What is clinical policy?")
@patch("streamlit.chat_message")
@patch("streamlit.spinner")
def test_render_rag_tab(mock_spinner, mock_chat_message, mock_chat_input, state_manager):
    mock_engine = MagicMock()
    chunk = RetrievedChunk(
        content="Policy text",
        similarity_score=0.95,
        source_filename="policy.pdf",
        chunk_index=1,
    )
    telemetry = QueryTelemetry(
        query_id="q1",
        retrieval_time_ms=10.0,
        generation_time_ms=20.0,
        total_time_ms=30.0,
        embedding_provider="test",
        llm_provider="test",
        model_name="test-model",
    )
    response = RAGResponse(
        answer="This is the policy response.",
        retrieved_chunks=[chunk],
        citations=["[policy.pdf | chunk 1]"],
        telemetry=telemetry,
        execution_metadata={"governance": {"redaction_count": 1}},
    )
    mock_engine.execute_with_error_response.return_value = response

    render_rag_tab(state=state_manager, query_engine=mock_engine)

    assert mock_engine.execute_with_error_response.called
    chat_history = state_manager.get_chat_history()
    assert len(chat_history) == 2  # user + assistant
    assert chat_history[0]["content"] == "What is clinical policy?"
    assert chat_history[1]["content"] == "This is the policy response."
    assert len(state_manager.get_telemetry_logs()) == 1


@patch("streamlit.chat_input", return_value="Throw exception query")
@patch("streamlit.chat_message")
@patch("streamlit.spinner")
@patch("streamlit.error")
def test_render_rag_tab_service_exception(mock_error, mock_spinner, mock_chat_message, mock_chat_input, state_manager):
    mock_engine = MagicMock()
    mock_engine.execute_with_error_response.side_effect = RuntimeError("Vector DB connection failed")

    render_rag_tab(state=state_manager, query_engine=mock_engine)

    assert mock_error.called
    assert "Vector DB connection failed" in str(mock_error.call_args)


# ============================================================================
# 5. Citation Rendering & Empty Citations Tests
# ============================================================================

@patch("streamlit.dataframe")
def test_render_citations_table(mock_dataframe):
    chunk = RetrievedChunk(
        content="Evidence content",
        similarity_score=0.88,
        source_filename="doc.pdf",
        chunk_index=0,
    )
    render_citations_table([chunk])
    assert mock_dataframe.called


@patch("streamlit.info")
def test_render_empty_citations_table(mock_info):
    render_citations_table([])
    assert mock_info.called
    assert "No citations available" in str(mock_info.call_args)


# ============================================================================
# 6. Conversational BI Tab, Empty DataFrame & Invalid SQL Tests
# ============================================================================

@patch("streamlit.text_area", return_value="Count claims by state")
@patch("streamlit.button", return_value=True)
@patch("streamlit.spinner")
@patch("streamlit.dataframe")
def test_render_bi_tab(mock_df, mock_spinner, mock_btn, mock_txt, state_manager):
    mock_bi_engine = MagicMock()
    exec_result = SQLExecutionResult(
        rows=[{"state": "MA", "claim_count": 5}],
        columns=["state", "claim_count"],
        row_count=1,
        execution_time_ms=15.0,
    )
    telemetry = AnalyticsTelemetry(
        sql_generation_ms=10.0,
        sql_execution_ms=15.0,
        total_execution_ms=25.0,
        model_name="fake-model",
        row_count=1,
        status="SUCCESS",
    )
    response = AnalyticsResponse(
        question="Count claims by state",
        generated_sql="SELECT state, COUNT(claim_id) FROM claims GROUP BY state",
        execution_result=exec_result,
        summary="MA has 5 claims.",
        telemetry=telemetry,
    )
    mock_bi_engine.execute.return_value = response

    with patch("src.app.ui.components.bi_tab.auto_chart") as mock_chart:
        render_bi_tab(state=state_manager, bi_engine=mock_bi_engine)
        assert mock_bi_engine.execute.called
        assert mock_chart.called
        assert len(state_manager.get_telemetry_logs()) == 1


@patch("streamlit.text_area", return_value="Show invalid query")
@patch("streamlit.button", return_value=True)
@patch("streamlit.spinner")
@patch("streamlit.error")
def test_render_bi_tab_invalid_sql_exception(mock_error, mock_spinner, mock_btn, mock_txt, state_manager):
    mock_bi_engine = MagicMock()
    mock_bi_engine.execute.side_effect = AnalyticsExecutionError("Forbidden SQL pattern detected: DROP TABLE")

    render_bi_tab(state=state_manager, bi_engine=mock_bi_engine)

    assert mock_error.called
    assert "Forbidden SQL pattern detected" in str(mock_error.call_args)


@patch("streamlit.text_area", return_value="Show empty dataset")
@patch("streamlit.button", return_value=True)
@patch("streamlit.spinner")
@patch("streamlit.info")
def test_render_bi_tab_empty_dataframe(mock_info, mock_spinner, mock_btn, mock_txt, state_manager):
    mock_bi_engine = MagicMock()
    exec_result = SQLExecutionResult(
        rows=[],
        columns=["state", "claim_count"],
        row_count=0,
        execution_time_ms=5.0,
    )
    telemetry = AnalyticsTelemetry(
        sql_generation_ms=5.0,
        sql_execution_ms=5.0,
        total_execution_ms=10.0,
        model_name="fake-model",
        row_count=0,
        status="SUCCESS",
    )
    response = AnalyticsResponse(
        question="Show empty dataset",
        generated_sql="SELECT state FROM patients WHERE state = 'ZZ'",
        execution_result=exec_result,
        summary="No rows matched.",
        telemetry=telemetry,
    )
    mock_bi_engine.execute.return_value = response

    render_bi_tab(state=state_manager, bi_engine=mock_bi_engine)

    assert mock_info.called


# ============================================================================
# 7. Smart Chart Heuristics Tests
# ============================================================================

@patch("streamlit.metric")
def test_auto_chart_single_numeric_metric(mock_metric):
    rows = [{"total_claims": 42}]
    cols = ["total_claims"]
    auto_chart(rows, cols)
    assert mock_metric.called
    assert mock_metric.call_args[1]["label"] == "Total Claims"
    assert mock_metric.call_args[1]["value"] == "42"


@patch("streamlit.bar_chart")
def test_auto_chart_categorical_and_numeric(mock_bar):
    rows = [{"state": "MA", "val": 10}, {"state": "NY", "val": 20}]
    cols = ["state", "val"]
    auto_chart(rows, cols)
    assert mock_bar.called


@patch("streamlit.line_chart")
def test_auto_chart_datetime_and_numeric(mock_line):
    rows = [{"claim_date": "2026-01-01", "amount": 100.0}, {"claim_date": "2026-01-02", "amount": 200.0}]
    cols = ["claim_date", "amount"]
    auto_chart(rows, cols)
    assert mock_line.called


# ============================================================================
# 8. Governance & Configuration Redaction Rendering Tests
# ============================================================================

@patch("streamlit.metric")
@patch("streamlit.dataframe")
def test_render_governance_tab(mock_df, mock_metric, state_manager):
    state_manager.append_telemetry({
        "source": "rag",
        "pii_count": 2,
        "injection_attempts": 1,
    })
    mock_gov_service = MagicMock()
    mock_gov_service.guardrail_registry.return_value = {"input": ["InputGuardrail"]}

    with patch("src.common.config.settings.get_settings") as mock_settings:
        mock_settings.return_value.GUARDRAIL_STRICT_MODE = False
        mock_settings.return_value.ENABLE_INPUT_GUARDRAILS = True
        mock_settings.return_value.ENABLE_OUTPUT_GUARDRAILS = True
        mock_settings.return_value.ENABLE_PII_REDACTION = True
        mock_settings.return_value.model_dump.return_value = {
            "APP_ENV": "testing",
            "SECRET_KEY": "supersecret123",
            "DATABASE_URL": "sqlite:///data/test.db",
            "API_KEY_VAL": "key-xyz",
        }

        render_governance_tab(state=state_manager, governance_service=mock_gov_service)
        assert mock_metric.called


@patch("streamlit.dataframe")
def test_render_dict_table_redaction(mock_df):
    data = {
        "APP_ENV": "production",
        "SECRET_KEY": "my-secret-key",
        "OLLAMA_API_KEY": "api-token-value",
        "DB_CONNECTION_STRING": "postgres://user:pass@host/db",
    }
    render_dict_table(data)
    assert mock_df.called
    df_passed = mock_df.call_args[0][0]
    redacted_rows = df_passed[df_passed["Value"] == "[REDACTED]"]
    assert len(redacted_rows) == 3


def test_bi_pipeline_count_claims_by_status_integration(state_manager):
    """Integration test proving 'Count claims by status' produces SELECT..., validates, executes, and renders."""
    from src.analytics.pipeline.bi_engine import ConversationalBIEngine
    from src.analytics.models import SQLQueryRequest
    from src.app.ui.components.bi_tab import render_bi_tab

    bi_engine = ConversationalBIEngine()
    request = SQLQueryRequest(question="Count claims by status")

    # 1. BI Pipeline execution
    response = bi_engine.execute(request)

    # 2. Verify candidate SQL
    assert response.generated_sql.upper().startswith("SELECT")
    assert "CLAIMS" in response.generated_sql.upper()

    # 3. Verify execution result
    assert response.execution_result.row_count > 0
    assert len(response.execution_result.rows) > 0

    # 4. Verify Streamlit UI rendering
    with patch("streamlit.text_area", return_value="Count claims by status"), \
         patch("streamlit.button", return_value=True), \
         patch("streamlit.spinner"), \
         patch("streamlit.dataframe") as mock_df, \
         patch("src.app.ui.components.bi_tab.auto_chart") as mock_chart:
        render_bi_tab(state=state_manager, bi_engine=bi_engine)
        assert mock_df.called
        assert mock_chart.called

