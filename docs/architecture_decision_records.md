# Architecture Decision Records (ADRs)

This document tracks key architectural decisions, context, and consequences for the Enterprise Data Trust Framework (EDTF).

---

## ADR 01: Decoupling Metadata Storage with a REST API Layer

### Status
**APPROVED**

### Context
Downstream run engines (Databricks Spark executors and dbt models) require frequent access to schema metadata, active validation rules, and lookup values. 

Allowing these systems to query the Metadata Database directly has several drawbacks:
1. **Security Risk**: Exposes database credentials and connection strings to multiple execution environments.
2. **Connection Exhaustion**: High-volume Spark clusters with hundreds of executors can easily exceed database connection limits.
3. **Tight Coupling**: Modifying the database schema requires updating and redeploying code across all downstream engines.

### Decision
Decouple the Metadata Database from execution environments by routing all access through a stateless **REST API Layer** (FastAPI / NestJS). The database is placed in a private network, and API access is secured using OAuth2 and JWT.

### Consequences
* **Pros**:
  * Centralizes logging, request auditing, and authorization.
  * API layer caching (Redis) reduces read workloads on the SQL database.
  * The database schema can be refactored without breaking downstream Spark jobs.
* **Cons**:
  * Adds network overhead (HTTP request/response cycles).
  * Requires deploying and maintaining the API microservice.

---

## ADR 02: PostgreSQL as the Primary Transactional Metadata Store

### Status
**APPROVED**

### Context
The Metadata Store must handle:
1. Complex relationships between datasets, rules, and glossary terms.
2. High-volume write traffic from validation run logs.
3. Semi-structured validation parameters (e.g., regex maps and thresholds).

### Decision
Use **PostgreSQL** (specifically Azure Database for PostgreSQL Flexible Server) as the relational database engine.

### Consequences
* **Pros**:
  * Native support for ACID transactions guarantees audit log integrity.
  * `JSONB` columns allow storing semi-structured validation parameters while supporting indexing.
  * Strong integration with open-source database migration tools (Alembic / Flyway) and infrastructure-as-code (Terraform).
* **Cons**:
  * Vertical scaling limits require careful partitioning of high-volume runtime log tables.

---

## ADR 03: Bidirectional Sync Flow with Collibra as the System of Record

### Status
**APPROVED**

### Context
Collibra is the enterprise governance platform, managing approvals, business terms, and classifications. 

However, Collibra is not designed to support real-time, low-latency queries from execution engines. The Metadata DB acts as a local cache for metadata, but we must prevent the two systems from falling out of sync.

### Decision
Implement a bidirectional synchronization architecture:
1. **Inbound (Collibra → Metadata DB)**: Collibra acts as the System of Record (SoR) for glossary terms, classifications, and mappings. Changes approved in Collibra are synced to the Metadata DB via webhook triggers.
2. **Outbound (Metadata DB → Collibra)**: The Metadata DB acts as the System of Record for execution logs and exceptions. High-volume runs are aggregated, and the resulting quality scores and open quarantine counts are pushed to Collibra using batch APIs.

### Consequences
* **Pros**:
  * Stewards can manage rules and terms in Collibra without worrying about database access.
  * Decoupling queries from Collibra's APIs prevents latency bottlenecks.
* **Cons**:
  * Requires building and maintaining integration pipelines.
  * Temporary sync delays can occur between approval in Collibra and activation in the Metadata DB.
