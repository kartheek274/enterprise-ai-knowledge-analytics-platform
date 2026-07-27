# Metadata Architect Interview & Operations Guide

This guide details the architectural decisions, scaling considerations, operational strategies, and best practices for the Enterprise Data Trust Framework (EDTF).

---

## 1. Architectural Rationale: "Why this design?"

In global banking migration projects (handling hundreds of millions of records across legacy DB2 and Oracle systems), classical data validation patterns fail. 

Common points of failure include:
* **Hardcoded Validation Scripts**: Validation checks written in PySpark or dbt SQL models lead to code bloat and require a full CI/CD deployment cycle to update simple thresholds.
* **Database Bottlenecks**: Spark executors querying the metadata database directly can overwhelm transactional systems, leading to connection exhaustion.
* **Catalog Disconnects**: Cataloging tools like Collibra and Microsoft Purview often drift from actual database schemas because validation is separate from metadata collection.

This architecture addresses these issues by decoupling **Metadata Definition** (via the API Layer), **Data Validation** (via the PySpark dynamic execution engine), and **Data Cataloging** (via Collibra sync webhooks).

```text
[ Collibra SoR ]  <---(Inbound/Outbound Sync)---> [ Metadata API Layer ]
                                                            |
                                                   (Serves Configuration)
                                                            v
[ Delta Lakes ]   <====(Read/Write Engine)====== [ Spark / dbt Runners ]
```

---

## 2. Common Enterprise Metadata Mistakes to Avoid

1. **Treating Collibra as a Real-time Cache Engine**: Sending dynamic data quality requests from Spark executors directly to Collibra APIs creates latency issues. Collibra is not designed for sub-second query execution.
2. **Missing a Physical API Decoupling Layer**: Allowing Spark runners to query the metadata SQL database directly bypasses security controls and exposes database credentials.
3. **Hardcoding Exception Remediation Routing**: Hand-routing data errors without linking them to owners or stewards in the metadata glossary leads to orphaned quarantine tables.
4. **Neglecting Lineage Versioning**: Mapping lineage statically without version controls results in lineage graphs that do not match historical schema states after migrations.

---

## 3. Scalability Considerations (Volume & Throughput)

### 3.1 Database Reads & Write Scale
* **Master DB Scaling**: Read traffic to `/rules` and `/columns` is cached using **Redis** at the API layer. This reduces read workloads on the Master DB to near-zero.
* **Runtime Logging Volume**: High-volume write traffic to `runtime.validation_results` is handled by write-buffering. Spark engines write logs to a staging table, which is periodically merged into the Metadata DB using a background worker.

### 3.2 Partitioning & Indexing Strategy
* **`runtime.validation_run_history` & `runtime.validation_results`**: Partitioned by month using PG range partitioning (`start_timestamp`). Indexes are placed on `dataset_id` and `validation_run_id`.
* **`runtime.exception_repository`**: Hash partitioned by `remediation_status`. This keeps active (`OPEN`) quarantine entries in distinct physical partitions, accelerating lookup queries.
* **`audit.metadata_changes`**: Range partitioned by quarter (`modified_at`).

---

## 4. Performance Considerations

### 4.1 Caching Latency
* **Redis API Caching**: Cache hit latency is kept under 5 milliseconds.
* **Spark Broadcast Overhead**: Broadcast variables are serialized and distributed to executors only once per pipeline run. This minimizes network traffic across the Spark cluster.

### 4.2 Query Optimization
All relational join columns (such as `dataset_id`, `column_id`, `rule_id`, and `pipeline_run_id`) are indexed. Text searching on glossary tables uses GIN indexes to support fast, regex-based keyword searches.

---

## 5. Disaster Recovery (DR) & High Availability (HA)

To support critical banking migrations, the Metadata API and DB must achieve a Recovery Time Objective (RTO) of less than 30 minutes and a Recovery Point Objective (RPO) of less than 1 minute.

```text
[ Primary Region (Azure East US) ]                 [ Secondary Region (Azure West US) ]
Active API Services <--> Primary SQL DB  ===(Replication)===> Active API Services <--> Replica SQL DB
```

1. **Active-Active API Routing**: The API layer is deployed to multi-region clusters (Azure AKS / Fabric containers) behind a global load balancer (Azure Front Door).
2. **Active-Passive Database Failover**: The PostgreSQL database is deployed in a high-availability configuration with active-passive replication.
3. **Point-In-Time Recovery (PITR)**: Transaction logs are backed up to write-once-read-many (WORM) storage every 5 minutes. This allows rollbacks to precise points in time in the event of database corruption.
