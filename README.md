# Enterprise Data Trust Framework (EDTF)
## Phase 1 & 1.5: Metadata Platform Architecture & Relational Schema

This repository contains the physical schemas, DDL scripts, API specifications, and governance frameworks representing **Phase 1 (Metadata Repository Control Plane)** of the Enterprise Data Trust Framework (EDTF). 

This platform serves as the decoupled, metadata-driven control center for downstream Databricks PySpark pipelines, dbt transformations, Power BI dashboards, and enterprise catalog systems (Collibra & Microsoft Purview).

---

## 1. Directory Structure

```text
├── api/
│   └── openapi_spec.yaml           # OpenAPI 3.0 REST API spec for the Microservice Layer
├── db/
│   ├── ddl/
│   │   ├── 01_master_repository.sql      # Glossary, catalog definitions, rules and mapping DDLs
│   │   ├── 02_runtime_repository.sql     # High-volume execution histories, audits and exceptions DDLs
│   │   ├── 03_security_repository.sql    # RBAC, row-level filtering, column masking and encryption DDLs
│   │   ├── 04_reference_repository.sql   # Countries, currencies, SWIFT/IFSC validation tables DDLs
│   │   └── 05_audit_repository.sql       # Schema audit changelogs, approvals, and rollback logs DDLs
│   └── seeds/
│       ├── 01_business_domains.csv       # Business Domains Seed data
│       ├── 03_data_owners.csv            # Data Owners Seed data
│       ├── 04_data_stewards.csv          # Data Stewards Seed data
│       ├── 05_data_classification.csv    # Security Classifications Seed data
│       ├── 06_dataset_registry.csv       # Physical Datasets Seed data
│       ├── 07_column_metadata.csv        # Columns and schema mapping Seed data
│       └── 08_data_quality_rules.csv     # Spark DQ rules configurations Seed data
├── docs/
│   ├── README.md                         # Quick start documentation (this file)
│   ├── data_dictionary.md                # Field definitions, classifications and data types
│   ├── integration_frameworks.md         # PySpark caching, dbt hook mappings, and Collibra syncs
│   ├── governance_policies_lifecycles.md # Policy lifecycles, SLAs, and certification workflows
│   ├── architect_interview_guide.md      # Scaling, high availability, DR and enterprise mistakes
│   ├── architecture_decision_records.md  # Architectural Decision Records (ADRs)
│   └── er_diagram.mermaid                # Full entity relationship model source (Mermaid format)
```

---

## 2. Core Architectural Principles

1. **Decoupled Architecture**: Downstream processing jobs (PySpark, dbt) do not connect directly to the metadata database. They query metadata and publish execution logs through the stateless REST API layer, preventing database locks and security credentials leaks.
2. **Metadata-Driven Execution**: No schema checks, rule formulas, allowed values, regex patterns, or encryption keys are hardcoded in downstream processing code. They are configured dynamically in the Metadata Master Repository and served via the API.
3. **Collibra as Governance System of Record (SoR)**: Business glossaries, data classifications, policy configurations, and asset owners are defined in Collibra. Changes are synchronized to the Metadata DB via webhook triggers.

---

## 3. Physical Database Setup

The DDL scripts are written in standard, high-compliance PostgreSQL syntax. To initialize the metadata repository:

1. Create a database named `metadata_db`.
2. Execute the scripts in the `/db/ddl/` folder in sequential order:
   ```bash
   psql -h <host> -U <user> -d metadata_db -f db/ddl/01_master_repository.sql
   psql -h <host> -U <user> -d metadata_db -f db/ddl/02_runtime_repository.sql
   psql -h <host> -U <user> -d metadata_db -f db/ddl/03_security_repository.sql
   psql -h <host> -U <user> -d metadata_db -f db/ddl/04_reference_repository.sql
   psql -h <host> -U <user> -d metadata_db -f db/ddl/05_audit_repository.sql
   ```

---

## 4. Documentation Index

* **Physical Data Model & Schemas**: Detailed definitions of tables and column properties can be found in the [Data Dictionary](file:///c:/kartheek/Krish/Data%20Quality/docs/data_dictionary.md).
* **Consumer Integration Guide**: Learn about Spark Driver caching strategies, dbt pre-run hooks, and Collibra/Purview sync pipelines in the [Integration Frameworks Guide](file:///c:/kartheek/Krish/Data%20Quality/docs/integration_frameworks.md).
* **Governance and SLAs**: Policy-to-closure workflows, issue priority rules, and medallion certification levels are detailed in the [Governance Policies & Lifecycles Guide](file:///c:/kartheek/Krish/Data%20Quality/docs/governance_policies_lifecycles.md).
* **ADRs**: Key architectural trade-offs and approved designs are recorded in the [Architecture Decision Records](file:///c:/kartheek/Krish/Data%20Quality/docs/architecture_decision_records.md).
* **Scale, DR & Operations**: Read about high-availability replication, partitioning, and interview strategies in the [Architect Operations Guide](file:///c:/kartheek/Krish/Data%20Quality/docs/architect_interview_guide.md).
* **ER Diagram**: Visual relationships are modeled in the [ER Diagram](file:///c:/kartheek/Krish/Data%20Quality/docs/er_diagram.mermaid).
