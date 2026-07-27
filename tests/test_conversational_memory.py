from concurrent.futures import ThreadPoolExecutor
from typing import List

from src.common.config.settings import get_settings
from src.rag.llm.mock import MockLLMProvider
from src.rag.memory import (
    ChatTurn,
    InMemorySessionStore,
    MemoryConfig,
    MemoryFormatter,
    MemoryTelemetry,
    SessionMemoryManager,
    SessionNotFoundError,
)
from src.rag.models import RAGQuery, RetrievedChunk
from src.rag.pipeline.query_engine import QueryEngine
from src.rag.retrieval.base import BaseRetriever


class StaticRetriever(BaseRetriever):
    def __init__(self, chunks: List[RetrievedChunk]) -> None:
        self.chunks = chunks

    def retrieve(self, query: RAGQuery) -> List[RetrievedChunk]:
        return self.chunks[: query.top_k]


class CapturingLLMProvider(MockLLMProvider):
    def __init__(self) -> None:
        super().__init__(fixed_response="The policy requires prior authorization [1].")
        self.prompts: List[str] = []

    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.0):
        self.prompts.append(prompt)
        return super().generate(prompt, max_tokens=max_tokens, temperature=temperature)


def token_counter(text: str) -> int:
    return len(text.split())


def make_manager(max_turns=10, max_tokens=100) -> SessionMemoryManager:
    return SessionMemoryManager(
        store=InMemorySessionStore(),
        formatter=MemoryFormatter(),
        config=MemoryConfig(
            max_turns=max_turns,
            max_tokens=max_tokens,
            compression_strategy="trim_oldest",
        ),
        token_counter=token_counter,
    )


def make_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        content="Prior authorization is required for infusion therapy.",
        similarity_score=0.9,
        source_filename="policy.md",
        source_document_hash="hash",
        chunk_index=0,
        metadata={"chunk_id": "hash:0"},
    )


def test_session_creation_and_add_turn():
    manager = make_manager()

    session = manager.add_turn("s1", "user", "hello there", user_id="u1")

    assert session.session_id == "s1"
    assert session.user_id == "u1"
    assert len(session.turns) == 1
    assert session.turns[0].token_count == 2


def test_session_isolation():
    manager = make_manager()

    manager.add_turn("s1", "user", "first session")
    manager.add_turn("s2", "user", "second session")

    assert manager.get_session("s1").turns[0].content == "first session"
    assert manager.get_session("s2").turns[0].content == "second session"


def test_history_retrieval_and_formatting():
    manager = make_manager()
    manager.add_turn("s1", "user", "What is required?")
    manager.add_turn("s1", "assistant", "Prior authorization.")

    history = manager.get_formatted_history("s1")

    assert "User:\nWhat is required?" in history
    assert "Assistant:\nPrior authorization." in history
    assert manager.last_telemetry.formatting_time_ms >= 0


def test_memory_formatter_has_no_storage_logic():
    formatter = MemoryFormatter()
    turns = [
        ChatTurn(role="user", content="Question", token_count=1),
        ChatTurn(role="assistant", content="Answer", token_count=1),
    ]

    assert formatter.format(turns) == "User:\nQuestion\n\nAssistant:\nAnswer"


def test_token_accumulation():
    manager = make_manager()

    manager.add_turn("s1", "user", "one two")
    session = manager.add_turn("s1", "assistant", "three four five")

    assert session.total_tokens == 5
    assert manager.last_telemetry.total_tokens == 5


def test_turn_trimming_removes_oldest_turns():
    manager = make_manager(max_turns=2, max_tokens=100)

    manager.add_turn("s1", "user", "turn one")
    manager.add_turn("s1", "assistant", "turn two")
    session = manager.add_turn("s1", "user", "turn three")

    assert [turn.content for turn in session.turns] == ["turn two", "turn three"]
    assert manager.last_telemetry.trimmed_turns == 1


def test_token_trimming_removes_oldest_turns():
    manager = make_manager(max_turns=10, max_tokens=4)

    manager.add_turn("s1", "user", "one two")
    session = manager.add_turn("s1", "assistant", "three four five")

    assert [turn.content for turn in session.turns] == ["three four five"]
    assert session.total_tokens == 3
    assert manager.last_telemetry.trimmed_turns == 1


def test_clearing_sessions():
    manager = make_manager()
    manager.add_turn("s1", "user", "hello")

    manager.clear_session("s1")

    try:
        manager.get_session("s1")
        assert False, "Session should have been deleted"
    except SessionNotFoundError:
        assert True


def test_multiple_concurrent_sessions():
    manager = make_manager(max_turns=100, max_tokens=1000)

    def add(index: int) -> str:
        session_id = f"s{index % 5}"
        manager.add_turn(session_id, "user", f"message {index}")
        return session_id

    with ThreadPoolExecutor(max_workers=5) as executor:
        session_ids = list(executor.map(add, range(25)))

    stored_ids = {session.session_id for session in manager.store.list_sessions()}
    assert stored_ids == set(session_ids)
    assert sum(len(manager.get_session(session_id).turns) for session_id in stored_ids) == 25


def test_query_engine_multi_turn_conversations():
    manager = make_manager()
    llm = CapturingLLMProvider()
    engine = QueryEngine(
        retriever=StaticRetriever([make_chunk()]),
        llm_provider=llm,
        memory_manager=manager,
        embedding_provider_name="fake",
    )

    first = engine.execute(RAGQuery(query_text="What is required?", session_id="s1"))
    second = engine.execute(RAGQuery(query_text="Does it apply to infusion?", session_id="s1"))

    session = manager.get_session("s1")
    assert first.answer == "The policy requires prior authorization [1]."
    assert second.answer == "The policy requires prior authorization [1]."
    assert len(session.turns) == 4
    assert "CONVERSATION HISTORY" in llm.prompts[1]
    assert "User:\nWhat is required?" in llm.prompts[1]
    assert "Assistant:\nThe policy requires prior authorization [1]." in llm.prompts[1]


def test_query_engine_without_session_does_not_use_memory():
    manager = make_manager()
    llm = CapturingLLMProvider()
    engine = QueryEngine(
        retriever=StaticRetriever([make_chunk()]),
        llm_provider=llm,
        memory_manager=manager,
        embedding_provider_name="fake",
    )

    engine.execute(RAGQuery(query_text="What is required?"))

    assert manager.store.list_sessions() == []
    assert "CONVERSATION HISTORY" not in llm.prompts[0]


def test_memory_telemetry_generation():
    telemetry = MemoryTelemetry(
        session_id="s1",
        total_turns=2,
        total_tokens=5,
        trimmed_turns=1,
        retrieval_time_ms=1.0,
        formatting_time_ms=2.0,
    )

    assert telemetry.session_id == "s1"
    assert telemetry.trimmed_turns == 1


def test_memory_configuration_loading():
    settings = get_settings()

    assert settings.MAX_MEMORY_TURNS >= 1
    assert settings.MAX_MEMORY_TOKENS >= 1
    assert settings.MEMORY_COMPRESSION_STRATEGY == "trim_oldest"
