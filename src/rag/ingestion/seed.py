"""Auto-seeding service for raw document ingestion into ChromaDB."""

import logging
from pathlib import Path
from src.common.config.settings import get_settings
from src.rag.ingestion.pipeline import IngestionPipeline
from src.rag.vector_store.chroma_service import ChromaService

logger = logging.getLogger("eakap.rag.ingestion.seed")

DOC_1_CONTENT = """CLINICAL WORKFLOW & PRIOR AUTHORIZATION GUIDELINES
Document ID: DOC-2026-001
Source System: ENTERPRISE_CLINICAL_REPOSITORY

1. Prior Authorization Procedures:
Prior authorization is required for all elective inpatient admissions, specialized outpatient procedures, and high-cost imaging (MRI, PET, CT scans).
- Standard Turnaround Time: 14 calendar days from receipt of complete clinical documentation.
- Urgent Turnaround Time: 72 hours when delay could jeopardize patient health.
- Appeals Process: First-level peer-to-peer review must be requested within 30 days of initial denial notification.

2. Medical Necessity Criteria:
All care decisions must satisfy evidence-based medical necessity criteria derived from InterQual and MCG clinical care guidelines.
- Primary Care Referral: Mandatory for specialist visits under HMO plans.
- Emergency Services: No prior authorization required for emergency medical conditions under the prudent layperson standard.

3. Claims Submission Standards:
Clean claims must be submitted within 90 days of service date for Massachusetts (MA) and 180 days for New York (NY).
- Denial Codes: CO-50 (non-covered service), CO-16 (missing clinical info), CO-97 (bundled service)."""

DOC_2_CONTENT = """ENTERPRISE DATA GOVERNANCE & AI PRIVACY POLICY
Document ID: GOV-2026-002
Source System: ENTERPRISE_GOVERNANCE_CATALOG

1. HIPAA & PII/PHI Protection Rules:
All AI pipelines, RAG retrievers, and natural language analytics engines must enforce automatic PII/PHI redaction prior to rendering outputs to end users.
- Redacted Categories: Social Security Numbers [SSN], Medical Record Numbers [MRN], Patient Names, Email Addresses, Phone Numbers, Credit Card Numbers.
- Strict Mode: When GUARDRAIL_STRICT_MODE is enabled, input prompt injection attempts (DAN jailbreaks, instruction overrides, system prompt extraction) will immediately halt pipeline execution.

2. Business Glossary & Data Quality Standards:
- Patient Entity: Identified by patient_id. Contains demographic info including state, first_name, last_name, and date_of_birth.
- Claims Entity: Identified by claim_id, linked to patient_id via foreign key constraint. Fields include claim_amount, claim_status (APPROVED, DENIED, PENDING), and service_date.
- Financial Records Entity: Identified by record_id, linked to claim_id. Contains paid_amount and payment_date."""


def seed_knowledge_base(collection_name: str = "healthcare_knowledge") -> bool:
    """Check ChromaDB and raw_documents directory. Seed and ingest documents if empty."""
    try:
        settings = get_settings()
        chroma_svc = ChromaService()

        # Check if collection already has documents
        if collection_name in chroma_svc.list_collections():
            count = chroma_svc.count_documents(collection_name)
            if count > 0:
                logger.info(f"Knowledge base collection '{collection_name}' already contains {count} documents.")
                return True

        # Create raw documents directory and write seed files
        raw_dir = settings.RAW_DOCUMENTS_DIR
        raw_dir.mkdir(parents=True, exist_ok=True)

        doc1_path = raw_dir / "clinical_workflow_guidelines.txt"
        doc2_path = raw_dir / "data_governance_policy.txt"

        doc1_path.write_text(DOC_1_CONTENT, encoding="utf-8")
        doc2_path.write_text(DOC_2_CONTENT, encoding="utf-8")

        # Execute ingestion pipeline
        pipeline = IngestionPipeline()
        pipeline.ingest_document(
            filepath=doc1_path,
            document_type="CLINICAL_GUIDELINE",
            source_system="CLINICAL_CATALOG",
            collection_name=collection_name,
        )
        pipeline.ingest_document(
            filepath=doc2_path,
            document_type="GOVERNANCE_POLICY",
            source_system="GOVERNANCE_CATALOG",
            collection_name=collection_name,
        )
        logger.info(f"Successfully seeded and ingested knowledge base into collection '{collection_name}'.")
        return True
    except Exception as e:
        logger.error(f"Failed to seed knowledge base: {e}")
        return False
