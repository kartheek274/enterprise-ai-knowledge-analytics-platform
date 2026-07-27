import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.rag.ingestion.loader import DocumentLoader
from src.rag.ingestion.splitter import RecursiveCharacterTextSplitter
from src.rag.embeddings.embedding_service import EmbeddingService
from src.rag.vector_store.chroma_service import ChromaService
from src.rag.ingestion.pipeline import IngestionPipeline
from src.common.database.init_db import init_database
from src.app.main import check_health

@pytest.fixture(scope="module", autouse=True)
def init_test_db():
    """Ensure database schema is created before running tests."""
    init_database()

def test_txt_loading(tmp_path):
    """Verify that a standard txt file loads and metadata extracts correctly."""
    txt_file = tmp_path / "test_doc.txt"
    txt_content = "This is a mock clinical guideline text for testing document loading."
    txt_file.write_text(txt_content, encoding="utf-8")
    
    doc = DocumentLoader.load(txt_file)
    assert doc.content == txt_content
    assert doc.filename == "test_doc.txt"
    assert doc.filepath == txt_file
    assert len(doc.sha256) == 64
    assert doc.file_size > 0
    assert doc.metadata["filename"] == "test_doc.txt"

def test_md_loading(tmp_path):
    """Verify that a markdown file loads and parses metadata correctly."""
    md_file = tmp_path / "test_note.md"
    md_content = "# Clinical Note\nPatient presented with mild hypertension symptoms."
    md_file.write_text(md_content, encoding="utf-8")
    
    doc = DocumentLoader.load(md_file)
    assert doc.content == md_content
    assert doc.filename == "test_note.md"
    assert doc.metadata["file_size"] > 0

@patch("pypdf.PdfReader")
def test_pdf_loading_mocked(mock_pdf_reader, tmp_path):
    """Verify that PDF parsing extracts page content correctly using mocked PDF reader."""
    pdf_file = tmp_path / "test_doc.pdf"
    pdf_file.write_text("dummy binary content", encoding="utf-8")
    
    # Mock pypdf reader behaviors
    mock_reader_instance = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Extracted clinical guidelines text from PDF pages."
    mock_reader_instance.pages = [mock_page]
    mock_pdf_reader.return_value = mock_reader_instance

    doc = DocumentLoader.load(pdf_file)
    assert doc.content == "Extracted clinical guidelines text from PDF pages."
    assert doc.filename == "test_doc.pdf"

def test_chunk_generation():
    """Verify that splitting segment text respects sizes and retains metadata."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=15)
    text = "Line number one text block. Line number two text block. Line number three text block."
    base_meta = {"source": "test_env"}
    
    chunks = splitter.split_document(text, base_meta, document_id=42)
    assert len(chunks) > 0
    
    # Assert metadata carries indexes and lineage values
    for index, chunk in enumerate(chunks):
        assert chunk.metadata["document_id"] == 42
        assert chunk.metadata["chunk_index"] == index
        assert chunk.metadata["chunk_count"] == len(chunks)
        assert chunk.metadata["source"] == "test_env"

def test_embedding_generation():
    """Verify that embedding service computes dimensions correctly."""
    service = EmbeddingService()
    # Testing env runs MockEmbeddingProvider by default
    query_vector = service.embed_query("test query text")
    assert isinstance(query_vector, list)
    assert len(query_vector) == 384
    
    doc_vectors = service.embed_documents(["doc chunk one", "doc chunk two"])
    assert len(doc_vectors) == 2
    assert len(doc_vectors[0]) == 384

def test_vector_store_operations():
    """Verify vector store collection, insertion, and similarity queries work."""
    chroma = ChromaService()
    collection_name = "test_ingestion_collection"
    
    # Ensure collection is clean
    if collection_name in chroma.list_collections():
        chroma.delete_collection(collection_name)
        
    chroma.create_collection(collection_name)
    assert collection_name in chroma.list_collections()
    
    # Insert mock chunks
    ids = ["c1", "c2"]
    documents = ["Patient claims prior authorization request.", "Clinical notes about hypertension medications."]
    embeddings = [[0.1] * 384, [0.9] * 384]
    metadatas = [{"doc_id": 1, "chunk_index": 0}, {"doc_id": 1, "chunk_index": 1}]
    
    chroma.add_documents(collection_name, ids, documents, embeddings, metadatas)
    assert chroma.count_documents(collection_name) == 2
    
    # Perform vector similarity query
    search_results = chroma.similarity_search(collection_name, [0.12] * 384, n_results=1)
    assert len(search_results) == 1
    assert search_results[0]["id"] == "c1"
    assert "Patient claims" in search_results[0]["document"]
    
    # Cleanup
    chroma.delete_collection(collection_name)

def test_pipeline_execution_and_idempotency(tmp_path):
    """Verify pipeline executes end-to-end, maps metadata, and enforces idempotency."""
    doc_file = tmp_path / "clinical_workflow_v1.txt"
    doc_file.write_text("Detailed prior auth criteria for healthcare operations workflow.", encoding="utf-8")
    
    pipeline = IngestionPipeline()
    collection_name = "pipeline_test_collection"
    
    # Make sure vector collection is clean
    if collection_name in pipeline.chroma_service.list_collections():
        pipeline.chroma_service.delete_collection(collection_name)
        
    # Execute first ingestion
    doc_id_1 = pipeline.ingest_document(
        filepath=doc_file,
        document_type="CLINICAL_GUIDELINE",
        source_system="TEST_SYS",
        collection_name=collection_name
    )
    assert doc_id_1 is not None
    
    # Execute duplicate content ingestion (checks idempotency)
    doc_id_2 = pipeline.ingest_document(
        filepath=doc_file,
        document_type="CLINICAL_GUIDELINE",
        source_system="TEST_SYS",
        collection_name=collection_name
    )
    # Must yield identical doc_id and not duplicate entries
    assert doc_id_1 == doc_id_2
    
    # Cleanup
    pipeline.chroma_service.delete_collection(collection_name)

def test_ingestion_health_check():
    """Verify that main application startup checks yield successful RAG statuses."""
    is_healthy, diagnostics = check_health()
    assert is_healthy is True
    assert diagnostics["vector_store"]["status"] == "healthy"
    assert diagnostics["embeddings"]["status"] == "healthy"
