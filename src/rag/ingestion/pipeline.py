import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from src.common.database.service import DatabaseService
from src.common.database.models import DocumentMetadata
from src.rag.ingestion.loader import DocumentLoader
from src.rag.ingestion.splitter import RecursiveCharacterTextSplitter
from src.rag.embeddings.embedding_service import EmbeddingService
from src.rag.vector_store.chroma_service import ChromaService
from src.common.config.settings import get_settings

logger = logging.getLogger("eakap.rag.ingestion")

class IngestionPipeline:
    """
    Orchestrates the entire document ingestion sequence:
    1. Loads the raw document and calculates its SHA-256 hash.
    2. Checks the database for duplicate hash values (idempotency check).
    3. Handles file updates if content has changed.
    4. Splits text into semantically overlapping chunks.
    5. Computes high-dimensional vector embeddings for each chunk.
    6. Saves text chunks and vectors in ChromaDB.
    7. Logs the ingestion event in the relational metadata catalog.
    """
    
    def __init__(self) -> None:
        self.settings = get_settings()
        self.embedding_service = EmbeddingService()
        self.chroma_service = ChromaService()
        
    def ingest_document(
        self,
        filepath: Path,
        document_type: str,
        source_system: str,
        collection_name: str = "healthcare_knowledge"
    ) -> Optional[int]:
        """
        Executes document ingestion. Returns the created document_id, 
        or the existing ID if skipped due to duplicate content.
        """
        logger.info(f"Pipeline execution started for file: {filepath}")
        
        # 1. Load document and calculate SHA-256
        doc = DocumentLoader.load(filepath)
        
        # 2. Check DocumentMetadata table for existing hash (Idempotency check)
        check_query = "SELECT document_id, filename FROM document_metadata WHERE sha256 = :sha256 LIMIT 1"
        duplicate_records = DatabaseService.execute_raw_sql(check_query, {"sha256": doc.sha256})
        
        if duplicate_records:
            dup_id = duplicate_records[0]["document_id"]
            dup_file = duplicate_records[0]["filename"]
            logger.info(
                f"Content match found. Skipping ingestion for '{doc.filename}'. "
                f"Existing Document ID: {dup_id} (Filename: {dup_file}) contains identical content."
            )
            return dup_id

        # 3. Check for filename duplicate (Update scenario)
        name_query = "SELECT document_id FROM document_metadata WHERE filename = :filename LIMIT 1"
        existing_names = DatabaseService.execute_raw_sql(name_query, {"filename": doc.filename})
        
        is_update = False
        existing_doc_id = None
        if existing_names:
            is_update = True
            existing_doc_id = existing_names[0]["document_id"]
            logger.info(
                f"Filename conflict detected for '{doc.filename}'. "
                f"Updating existing record (ID: {existing_doc_id}) with new content."
            )
            
            # Clear old vector entries in Chroma for this document_id to prevent orphan vectors
            try:
                col = self.chroma_service.create_collection(collection_name)
                # ChromaDB's delete allows filtering elements by metadata queries
                col.delete(where={"document_id": existing_doc_id})
                logger.info(f"Cleared existing vector chunks in collection '{collection_name}' for document ID {existing_doc_id}.")
            except Exception as e:
                logger.warning(
                    f"Attempted to clear old vectors for doc ID {existing_doc_id} but encountered: {str(e)}"
                )

        # 4. Register or Update database metadata with PENDING status (Fail-Fast state management)
        if is_update and existing_doc_id is not None:
            doc_meta = DatabaseService.update_record(
                DocumentMetadata,
                existing_doc_id,
                {
                    "sha256": doc.sha256,
                    "upload_date": datetime.utcnow(),
                    "chunk_count": 0,
                    "embedding_status": "PENDING",
                    "processing_status": "PENDING",
                    "file_size": doc.file_size,
                    "source_system": source_system
                }
            )
            doc_id = doc_meta.document_id
        else:
            doc_meta = DocumentMetadata(
                filename=doc.filename,
                sha256=doc.sha256,
                document_type=document_type,
                upload_date=datetime.utcnow(),
                chunk_count=0,
                embedding_status="PENDING",
                processing_status="PENDING",
                file_size=doc.file_size,
                source_system=source_system
            )
            inserted_meta = DatabaseService.insert_record(doc_meta)
            doc_id = inserted_meta.document_id

        try:
            logger.info(f"Registered document in DB (ID: {doc_id}). Starting chunking...")
            
            # 5. Split text into overlapping chunks
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.settings.DEFAULT_CHUNK_SIZE,
                chunk_overlap=self.settings.DEFAULT_CHUNK_OVERLAP
            )
            chunks = splitter.split_document(doc.content, doc.metadata, doc_id)
            logger.info(f"Generated {len(chunks)} text chunks.")
            
            # 6. Generate embeddings for chunks
            texts = [c.content for c in chunks]
            logger.info(f"Generating vectors via provider: {self.settings.EMBEDDING_PROVIDER}...")
            embeddings = self.embedding_service.embed_documents(texts)
            
            # 7. Write chunk contents and vectors into ChromaDB
            ids = [f"doc_{doc_id}_chunk_{c.metadata['chunk_index']}" for c in chunks]
            metadatas = [c.metadata for c in chunks]
            
            self.chroma_service.create_collection(collection_name)
            self.chroma_service.add_documents(
                collection_name=collection_name,
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas
            )
            logger.info("ChromaDB vector insertions completed.")
            
            # 8. Update database metadata state to COMPLETED / PROCESSED
            DatabaseService.update_record(
                DocumentMetadata,
                doc_id,
                {
                    "chunk_count": len(chunks),
                    "embedding_status": "COMPLETED",
                    "processing_status": "PROCESSED"
                }
            )
            logger.info(f"Ingestion pipeline successfully finalized for document ID {doc_id}.")
            return doc_id
            
        except Exception as e:
            logger.error(f"Ingestion pipeline failed for document ID {doc_id}: {str(e)}", exc_info=True)
            # Update state catalog to FAILED to alert governance dashboards
            try:
                DatabaseService.update_record(
                    DocumentMetadata,
                    doc_id,
                    {
                        "embedding_status": "FAILED",
                        "processing_status": "FAILED"
                    }
                )
            except Exception as db_err:
                logger.error(f"Fail-Safe error status write failed for document ID {doc_id}: {db_err}")
            raise e
