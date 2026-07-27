from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import ForeignKey, String, Date, Numeric, DateTime, Integer, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    """
    Unified Declarative Mapping Base class using SQLAlchemy 2.x standards.
    Registers metadata definitions for all database schema structures.
    """
    pass

class Patient(Base):
    """
    Represents structured Patient demographic details.
    Acts as the core entity for operational healthcare tracking.
    """
    __tablename__ = "patients"

    patient_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str] = mapped_column(String(10), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False)

    # Relationships
    claims: Mapped[List["Claim"]] = relationship(
        back_populates="patient", 
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    # Indexes for optimal querying
    __table_args__ = (
        Index("idx_patient_names", "last_name", "first_name"),
        Index("idx_patient_demographics", "state", "city"),
    )

    def __repr__(self) -> str:
        return f"<Patient(id={self.patient_id}, name='{self.first_name} {self.last_name}', state='{self.state}')>"


class Claim(Base):
    """
    Represents healthcare service claims filed by medical providers.
    Forms the transactional dataset for business intelligence and search operations.
    """
    __tablename__ = "claims"

    claim_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False)
    diagnosis_code: Mapped[str] = mapped_column(String(20), nullable=False)  # ICD-10 codes
    procedure_code: Mapped[str] = mapped_column(String(20), nullable=False)  # CPT codes
    claim_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    claim_status: Mapped[str] = mapped_column(String(30), nullable=False)  # APPROVED, PENDING, DENIED
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)
    claim_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Relationships
    patient: Mapped["Patient"] = relationship(back_populates="claims", lazy="joined")
    financial_record: Mapped[Optional["FinancialRecord"]] = relationship(
        back_populates="claim", 
        lazy="joined",
        uselist=False, 
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_claim_patient", "patient_id"),
        Index("idx_claim_date_status", "claim_date", "claim_status"),
        Index("idx_claim_codes", "diagnosis_code", "procedure_code"),
    )

    def __repr__(self) -> str:
        return f"<Claim(id={self.claim_id}, amount={self.claim_amount}, status='{self.claim_status}')>"


class FinancialRecord(Base):
    """
    Tracks financial transactions, approvals, and payouts associated with individual Claims.
    Provides data to answer complex conversational BI queries around payment audit loops.
    """
    __tablename__ = "financial_records"

    record_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.claim_id", ondelete="CASCADE"), unique=True, nullable=False)
    approved_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    payment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Relationships
    claim: Mapped["Claim"] = relationship(back_populates="financial_record", lazy="joined")

    __table_args__ = (
        Index("idx_financial_claim", "claim_id"),
        Index("idx_financial_payment_date", "payment_date"),
    )

    def __repr__(self) -> str:
        return f"<FinancialRecord(id={self.record_id}, approved={self.approved_amount}, paid={self.paid_amount})>"


class DocumentMetadata(Base):
    """
    Stores metadata definitions for unstructured text resources loaded into RAG.
    Acts as the source-of-truth metadata registry for governance audits and lineage tracking.
    """
    __tablename__ = "document_metadata"

    document_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)  # CLINICAL_GUIDELINE, PRIOR_AUTH, HUB_NOTE
    upload_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    embedding_status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)  # PENDING, COMPLETED, FAILED
    processing_status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)  # PENDING, PROCESSED, FAILED
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # in bytes
    source_system: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., CLINICAL_HUB, HUB_PORTAL

    __table_args__ = (
        Index("idx_doc_type_status", "document_type", "processing_status"),
        Index("idx_doc_filename", "filename"),
    )

    def __repr__(self) -> str:
        return f"<DocumentMetadata(id={self.document_id}, filename='{self.filename}', chunks={self.chunk_count})>"
