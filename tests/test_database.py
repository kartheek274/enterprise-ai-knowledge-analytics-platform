import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy import select, func
from src.common.database.connection import get_session, verify_connection
from src.common.database.models import Patient, Claim, FinancialRecord, DocumentMetadata
from src.common.database.init_db import init_database
from src.common.database.seed import seed_database
from src.common.database.service import DatabaseService
from src.common.errors.exceptions import ValidationError, ResourceNotFoundError
from src.app.main import check_health

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    """Ensure database schema is created before running database tests."""
    init_database()

def test_database_health_checks():
    """Verify that database connection check and schema health checks succeed."""
    assert verify_connection() is True
    is_healthy, diagnostics = check_health()
    assert is_healthy is True, f"Startup health check failed: {diagnostics}"
    assert diagnostics["database"]["status"] == "healthy"

def test_crud_and_relationships():
    """Verify standard CRUD operations and relationship loading via DatabaseService."""
    # 1. Create Patient
    patient = Patient(
        first_name="Alice",
        last_name="Smith",
        date_of_birth=date(1985, 5, 20),
        gender="Female",
        city="Chicago",
        state="IL"
    )
    inserted_patient = DatabaseService.insert_record(patient)
    assert inserted_patient.patient_id is not None
    assert inserted_patient.first_name == "Alice"

    # 2. Read Patient
    retrieved_patient = DatabaseService.get_record(Patient, inserted_patient.patient_id)
    assert retrieved_patient.last_name == "Smith"

    # 3. Create Claim linked to Patient
    claim = Claim(
        patient_id=inserted_patient.patient_id,
        diagnosis_code="E11.9",
        procedure_code="99213",
        claim_amount=Decimal("150.00"),
        claim_status="APPROVED",
        provider_name="Mayo Clinic",
        claim_date=date(2026, 1, 15)
    )
    inserted_claim = DatabaseService.insert_record(claim)
    assert inserted_claim.claim_id is not None
    assert inserted_claim.patient_id == inserted_patient.patient_id

    # 4. Create Financial Record linked to Claim
    financial = FinancialRecord(
        claim_id=inserted_claim.claim_id,
        approved_amount=Decimal("130.00"),
        paid_amount=Decimal("130.00"),
        payment_date=date(2026, 2, 1)
    )
    inserted_financial = DatabaseService.insert_record(financial)
    assert inserted_financial.record_id is not None

    # 5. Read and Verify Relationships
    # Access patient's claims
    refreshed_patient = DatabaseService.get_record(Patient, inserted_patient.patient_id)
    assert len(refreshed_patient.claims) == 1
    assert refreshed_patient.claims[0].claim_id == inserted_claim.claim_id
    
    # Access claim's patient and financial record
    refreshed_claim = DatabaseService.get_record(Claim, inserted_claim.claim_id)
    assert refreshed_claim.patient.patient_id == inserted_patient.patient_id
    assert refreshed_claim.financial_record.record_id == inserted_financial.record_id

    # 6. Update Record
    updated_patient = DatabaseService.update_record(Patient, inserted_patient.patient_id, {"city": "Evanston"})
    assert updated_patient.city == "Evanston"

    # 7. Delete Record (Cascading)
    DatabaseService.delete_record(Patient, inserted_patient.patient_id)
    
    # Check patient is gone
    with pytest.raises(ResourceNotFoundError):
        DatabaseService.get_record(Patient, inserted_patient.patient_id)
        
    # Check claim and financial records are deleted due to cascade
    with pytest.raises(ResourceNotFoundError):
        DatabaseService.get_record(Claim, inserted_claim.claim_id)

def test_parameterized_raw_sql():
    """Verify raw SQL execution with parameter bindings works and maps rows properly."""
    # Seed data first to ensure we have records
    seed_database()
    
    # Run parameterized query
    query = "SELECT first_name, last_name, state FROM patients WHERE state = :state_param LIMIT 5"
    rows = DatabaseService.execute_raw_sql(query, {"state_param": "MA"})
    
    assert len(rows) > 0
    for row in rows:
        assert row["state"] == "MA"
        assert "first_name" in row
        assert "last_name" in row

def test_transaction_rollback():
    """Verify that a failed operation within a session triggers rollback."""
    test_first_name = "Rollback_Test_User"
    
    # Execute a block that inserts and throws an exception
    with pytest.raises(ValueError, match="Forced Error"):
        with get_session() as session:
            patient = Patient(
                first_name=test_first_name,
                last_name="Rollback",
                date_of_birth=date(1990, 1, 1),
                gender="Male",
                city="Nowhere",
                state="NW"
            )
            session.add(patient)
            # Raise an error to trigger rollback
            raise ValueError("Forced Error")
            
    # Query database using raw SQL to verify that patient was NOT inserted
    query = "SELECT count(*) as cnt FROM patients WHERE first_name = :first_name"
    rows = DatabaseService.execute_raw_sql(query, {"first_name": test_first_name})
    assert rows[0]["cnt"] == 0, "Transaction did not roll back; patient was written."

def test_seeding_idempotency():
    """Verify database seeding runs without duplicating data on subsequent invocations."""
    # Ensure database is seeded at least once
    seed_database()
    
    # Get current counts
    with get_session() as session:
        pat_count_1 = session.scalar(select(func.count(Patient.patient_id)))
        claim_count_1 = session.scalar(select(func.count(Claim.claim_id)))
        doc_count_1 = session.scalar(select(func.count(DocumentMetadata.document_id)))
        
    # Run seed database again
    seed_database()
    
    # Verify counts remain identical
    with get_session() as session:
        pat_count_2 = session.scalar(select(func.count(Patient.patient_id)))
        claim_count_2 = session.scalar(select(func.count(Claim.claim_id)))
        doc_count_2 = session.scalar(select(func.count(DocumentMetadata.document_id)))
        
    assert pat_count_1 == pat_count_2, "Idempotency failed: Patients count changed after second seed."
    assert claim_count_1 == claim_count_2, "Idempotency failed: Claims count changed after second seed."
    assert doc_count_1 == doc_count_2, "Idempotency failed: DocumentMetadata count changed after second seed."

def test_exception_handling():
    """Verify that database errors are caught and converted to custom EAKAP exceptions."""
    # Test ValidationError for constraint integrity (null value on non-nullable field)
    with pytest.raises(ValidationError):
        invalid_patient = Patient(first_name=None, last_name="Integrity")
        DatabaseService.insert_record(invalid_patient)
