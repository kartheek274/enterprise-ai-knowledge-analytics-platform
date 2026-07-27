import logging
import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy import select, func
from src.common.database.connection import get_session
from src.common.database.models import Patient, Claim, FinancialRecord, DocumentMetadata

logger = logging.getLogger("eakap.database.seed")

# Fix random seed for deterministic synthetic records generation
random.seed(42)

# Source data lists for generation logic
FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "William", "Elizabeth",
    "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen",
    "Christopher", "Nancy", "Daniel", "Lisa", "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra",
    "Donald", "Ashley", "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
    "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson"
]

CITIES = ["Boston", "New York", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose"]
STATES = ["MA", "NY", "IL", "TX", "AZ", "PA", "TX", "CA", "TX", "CA"]
CITY_STATE_MAP = list(zip(CITIES, STATES))

DIAGNOSIS_CODES = ["I10", "E11.9", "J45.909", "M54.5", "E78.5", "F41.1", "Z00.00", "K21.9", "U07.1", "H10.9"]
PROCEDURE_CODES = ["99213", "99214", "99203", "36415", "80053", "85025", "93000", "71045", "99283", "90686"]
PROVIDERS = [
    "Partners Healthcare", "Mass General Brigham", "Mayo Clinic", "Cleveland Clinic", "Johns Hopkins Medicine",
    "Cedars-Sinai Medical Center", "UCSF Health", "Texas Medical Center", "Northwestern Medicine", "Mount Sinai Health"
]
DOCUMENT_TYPES = ["CLINICAL_GUIDELINE", "PRIOR_AUTH", "HUB_NOTE"]
SOURCE_SYSTEMS = ["CLINICAL_HUB", "HUB_PORTAL", "CLAIMS_WAREHOUSE", "CARE_MGMT"]

def seed_database() -> None:
    """
    Populates database tables with realistic, anonymized healthcare analytics data.
    Ensures complete idempotency by verifying record counts before executing insertions.
    """
    logger.info("Initializing database seed engine...")
    
    with get_session() as session:
        # Check current record count to maintain idempotency
        current_patients = session.scalar(select(func.count(Patient.patient_id)))
        current_claims = session.scalar(select(func.count(Claim.claim_id)))
        current_docs = session.scalar(select(func.count(DocumentMetadata.document_id)))

        # If data is already populated, skip insertions to avoid duplicates
        if current_patients >= 100 and current_claims >= 500 and current_docs >= 50:
            logger.info("Database is already seeded with sufficient data. Seeding execution skipped.")
            return

        logger.info(f"Current database state: Patients={current_patients}, Claims={current_claims}, Documents={current_docs}")

        # 1. Populate Patients
        patients_list = []
        if current_patients < 100:
            logger.info("Generating synthetic patient demographic records...")
            # Generating 120 patients to exceed minimum requirement
            for _ in range(120):
                first_name = random.choice(FIRST_NAMES)
                last_name = random.choice(LAST_NAMES)
                dob = date.today() - timedelta(days=random.randint(18 * 365, 85 * 365))  # Age between 18 and 85
                gender = random.choice(["Male", "Female", "Other"])
                city, state = random.choice(CITY_STATE_MAP)

                patient = Patient(
                    first_name=first_name,
                    last_name=last_name,
                    date_of_birth=dob,
                    gender=gender,
                    city=city,
                    state=state
                )
                session.add(patient)
                patients_list.append(patient)
            
            session.flush()  # Flushes session to fetch auto-assigned primary keys
            logger.info(f"Successfully seeded {len(patients_list)} patients.")
        else:
            # Query existing patients to link Claims
            patients_list = list(session.scalars(select(Patient)).all())

        # 2. Populate Claims and FinancialRecords
        if current_claims < 500:
            logger.info("Generating claims transaction logs and ledger mappings...")
            statuses = ["APPROVED", "DENIED", "PENDING"]
            claims_count_to_seed = 550
            claims_seeded = 0

            for _ in range(claims_count_to_seed):
                patient = random.choice(patients_list)
                diag_code = random.choice(DIAGNOSIS_CODES)
                proc_code = random.choice(PROCEDURE_CODES)
                amount = Decimal(round(random.uniform(75.00, 6500.00), 2))
                status = random.choice(statuses)
                provider = random.choice(PROVIDERS)
                claim_date = date.today() - timedelta(days=random.randint(1, 730))

                claim = Claim(
                    patient_id=patient.patient_id,
                    diagnosis_code=diag_code,
                    procedure_code=proc_code,
                    claim_amount=amount,
                    claim_status=status,
                    provider_name=provider,
                    claim_date=claim_date
                )
                session.add(claim)
                session.flush()
                claims_seeded += 1

                # Generate matching financial transaction for processed claims
                if status in ["APPROVED", "DENIED"]:
                    if status == "APPROVED":
                        approved = Decimal(round(float(amount) * random.uniform(0.70, 1.00), 2))
                        paid = approved
                        payment_date = claim_date + timedelta(days=random.randint(14, 45))
                    else:  # DENIED
                        approved = Decimal("0.00")
                        paid = Decimal("0.00")
                        payment_date = None

                    financial_record = FinancialRecord(
                        claim_id=claim.claim_id,
                        approved_amount=approved,
                        paid_amount=paid,
                        payment_date=payment_date
                    )
                    session.add(financial_record)

            logger.info(f"Successfully seeded {claims_seeded} claims and corresponding financial details.")

        # 3. Populate Document Metadata
        if current_docs < 50:
            logger.info("Generating synthetic document ingestion metadata tables...")
            docs_seeded = 0
            for i in range(60):
                doc_type = random.choice(DOCUMENT_TYPES)
                system = random.choice(SOURCE_SYSTEMS)
                size_bytes = random.randint(20 * 1024, 8 * 1024 * 1024)  # 20 KB to 8 MB
                chunks = random.randint(5, 120)

                if doc_type == "CLINICAL_GUIDELINE":
                    filename = f"guideline_clinical_{random.choice(DIAGNOSIS_CODES).lower()}_v{i}.pdf"
                elif doc_type == "PRIOR_AUTH":
                    filename = f"auth_request_patient_{random.randint(1000, 9999)}_{i}.txt"
                else:
                    filename = f"patient_hub_interaction_notes_{i}.md"

                doc = DocumentMetadata(
                    filename=filename,
                    document_type=doc_type,
                    upload_date=datetime.utcnow() - timedelta(days=random.randint(1, 180)),
                    chunk_count=chunks,
                    embedding_status=random.choice(["PENDING", "COMPLETED"]),
                    processing_status=random.choice(["PENDING", "PROCESSED"]),
                    file_size=size_bytes,
                    source_system=system
                )
                session.add(doc)
                docs_seeded += 1

            logger.info(f"Successfully seeded {docs_seeded} document metadata records.")
            
        logger.info("Database transaction seeding finalized and committed.")

if __name__ == "__main__":
    from src.common.logging.logger import setup_logger
    setup_logger("eakap.database.seed")
    seed_database()
