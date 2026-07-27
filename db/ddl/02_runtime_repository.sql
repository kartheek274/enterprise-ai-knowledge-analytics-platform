-- ============================================================================
-- Enterprise Data Trust Framework (EDTF)
-- Component: Metadata Runtime Repository DDL
-- Database: metadata_db (Schema: runtime)
-- RDBMS Target: PostgreSQL / Azure Database for PostgreSQL
-- Version: 1.0.0
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS runtime;

-- 1. Pipeline and Notebook Executions
CREATE TABLE runtime.pipeline_runs (
    run_id VARCHAR(50) PRIMARY KEY,
    pipeline_id VARCHAR(50) NOT NULL, -- references master.pipeline_registry(pipeline_id) logically
    run_status VARCHAR(30) NOT NULL CHECK (run_status IN ('RUNNING', 'SUCCESS', 'FAILED', 'CANCELLED')),
    triggered_by VARCHAR(100) NOT NULL,
    start_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    end_timestamp TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    execution_environment VARCHAR(10) CHECK (execution_environment IN ('DEV', 'UAT', 'PROD'))
);

CREATE INDEX idx_pipeline_runs_status ON runtime.pipeline_runs(run_status);

CREATE TABLE runtime.notebook_runs (
    notebook_run_id VARCHAR(50) PRIMARY KEY,
    pipeline_run_id VARCHAR(50) NOT NULL REFERENCES runtime.pipeline_runs(run_id),
    notebook_id VARCHAR(50) NOT NULL, -- references master.notebook_registry(notebook_id)
    run_status VARCHAR(30) NOT NULL CHECK (run_status IN ('RUNNING', 'SUCCESS', 'FAILED')),
    start_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    end_timestamp TIMESTAMP WITH TIME ZONE,
    spark_job_id VARCHAR(100),
    error_log TEXT
);

CREATE INDEX idx_notebook_runs_parent ON runtime.notebook_runs(pipeline_run_id);

-- 2. Validation Run History (PySpark and dbt Executions)
CREATE TABLE runtime.validation_run_history (
    validation_run_id VARCHAR(50) PRIMARY KEY,
    pipeline_run_id VARCHAR(50) NOT NULL REFERENCES runtime.pipeline_runs(run_id),
    dataset_id VARCHAR(50) NOT NULL, -- references master.dataset_registry(dataset_id)
    execution_engine VARCHAR(20) NOT NULL CHECK (execution_engine IN ('PYSPARK', 'DBT', 'GREAT_EXPECTATIONS')),
    total_records_processed BIGINT NOT NULL CHECK (total_records_processed >= 0),
    passed_records_count BIGINT NOT NULL CHECK (passed_records_count >= 0),
    failed_records_count BIGINT NOT NULL CHECK (failed_records_count >= 0),
    start_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    end_timestamp TIMESTAMP WITH TIME ZONE,
    status VARCHAR(30) NOT NULL CHECK (status IN ('RUNNING', 'COMPLETED', 'FAILED'))
);

CREATE INDEX idx_val_run_dataset ON runtime.validation_run_history(dataset_id);
CREATE INDEX idx_val_run_pipeline ON runtime.validation_run_history(pipeline_run_id);

-- 3. Detailed Validation Results (Rule level)
CREATE TABLE runtime.validation_results (
    result_id BIGSERIAL PRIMARY KEY,
    validation_run_id VARCHAR(50) NOT NULL REFERENCES runtime.validation_run_history(validation_run_id),
    rule_id VARCHAR(50) NOT NULL, -- references master.data_quality_rules(rule_id)
    records_evaluated BIGINT NOT NULL,
    records_failed BIGINT NOT NULL,
    pass_percentage NUMERIC(5, 2),
    execution_status VARCHAR(30) NOT NULL CHECK (execution_status IN ('PASSED', 'WARNING', 'FAILED', 'ERROR')),
    execution_duration_ms BIGINT,
    error_message TEXT
);

CREATE INDEX idx_val_res_run ON runtime.validation_results(validation_run_id);
CREATE INDEX idx_val_res_rule ON runtime.validation_results(rule_id);

-- 4. Exception & Quarantine Repository (Rows that failed checks)
CREATE TABLE runtime.exception_repository (
    exception_id BIGSERIAL PRIMARY KEY,
    validation_run_id VARCHAR(50) NOT NULL REFERENCES runtime.validation_run_history(validation_run_id),
    rule_id VARCHAR(50) NOT NULL, -- references master.data_quality_rules(rule_id)
    quarantine_table_fqn VARCHAR(255) NOT NULL, -- Location where actual record data is saved (Delta path)
    record_natural_key VARCHAR(255) NOT NULL, -- Unique identity key for lookup in quarantine table
    failed_column_name VARCHAR(100) NOT NULL,
    invalid_value TEXT,
    remediation_status VARCHAR(30) DEFAULT 'OPEN' CHECK (remediation_status IN ('OPEN', 'INVESTIGATING', 'SUPPRESSED', 'RESOLVED', 'CLOSED')),
    data_steward_notes TEXT,
    resolved_by VARCHAR(100),
    resolved_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_exception_run ON runtime.exception_repository(validation_run_id);
CREATE INDEX idx_exception_status ON runtime.exception_repository(remediation_status);

-- 5. Data Reconciliation Results (Balance Sheet Ledger Controls)
CREATE TABLE runtime.reconciliation_results (
    recon_run_id VARCHAR(50) PRIMARY KEY,
    pipeline_run_id VARCHAR(50) NOT NULL REFERENCES runtime.pipeline_runs(run_id),
    source_system VARCHAR(50) NOT NULL,
    target_system VARCHAR(50) NOT NULL,
    recon_key_field VARCHAR(100) NOT NULL, -- e.g. "ledger_account_no"
    source_checksum_val NUMERIC(20, 4) NOT NULL,
    target_checksum_val NUMERIC(20, 4) NOT NULL,
    variance_val NUMERIC(20, 4) NOT NULL,
    variance_percentage NUMERIC(5, 2) NOT NULL,
    recon_status VARCHAR(30) NOT NULL CHECK (recon_status IN ('RECONCILED', 'OUT_OF_BALANCE', 'WARNING')),
    recon_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_recon_pipeline ON runtime.reconciliation_results(pipeline_run_id);

-- 6. Audit & Governance Logging
CREATE TABLE runtime.audit_logs (
    audit_id BIGSERIAL PRIMARY KEY,
    user_identity VARCHAR(100) NOT NULL,
    action_type VARCHAR(50) NOT NULL, -- e.g. READ_PII, UPDATE_RULE, CERTIFY_DATASET
    entity_type VARCHAR(50) NOT NULL, -- e.g. TABLE, RULE, GLOSSARY
    entity_id VARCHAR(100) NOT NULL,
    action_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    client_ip VARCHAR(45),
    request_payload JSONB
);

CREATE INDEX idx_audit_timestamp ON runtime.audit_logs(action_timestamp);
CREATE INDEX idx_audit_entity ON runtime.audit_logs(entity_type, entity_id);

-- 7. High-Level Data Quality Metrics
CREATE TABLE runtime.dq_metrics (
    metric_id BIGSERIAL PRIMARY KEY,
    validation_run_id VARCHAR(50) NOT NULL REFERENCES runtime.validation_run_history(validation_run_id),
    completeness_score NUMERIC(5, 2),
    accuracy_score NUMERIC(5, 2),
    consistency_score NUMERIC(5, 2),
    validity_score NUMERIC(5, 2),
    uniqueness_score NUMERIC(5, 2),
    freshness_score NUMERIC(5, 2),
    composite_dq_score NUMERIC(5, 2) NOT NULL,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 8. Execution & Performance Statistics
CREATE TABLE runtime.execution_statistics (
    stat_id BIGSERIAL PRIMARY KEY,
    pipeline_run_id VARCHAR(50) NOT NULL REFERENCES runtime.pipeline_runs(run_id),
    bytes_read BIGINT,
    bytes_written BIGINT,
    io_duration_ms BIGINT,
    cpu_utilization_avg NUMERIC(5, 2),
    spark_executors_count INT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 9. Certification History
CREATE TABLE runtime.certification_history (
    cert_history_id BIGSERIAL PRIMARY KEY,
    dataset_id VARCHAR(50) NOT NULL, -- references master.dataset_registry(dataset_id)
    previous_cert_status VARCHAR(30) NOT NULL,
    new_cert_status VARCHAR(30) NOT NULL,
    approved_by VARCHAR(100) NOT NULL,
    certification_notes TEXT,
    workflow_id VARCHAR(100),
    certified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cert_history_dataset ON runtime.certification_history(dataset_id);

-- 10. Pipeline Notifications Queue
CREATE TABLE runtime.notifications (
    notification_id BIGSERIAL PRIMARY KEY,
    pipeline_run_id VARCHAR(50) REFERENCES runtime.pipeline_runs(run_id),
    channel VARCHAR(30) NOT NULL CHECK (channel IN ('TEAMS', 'SLACK', 'EMAIL', 'PAGERDUTY', 'WEBHOOK')),
    recipient_address VARCHAR(255) NOT NULL,
    subject VARCHAR(200) NOT NULL,
    message_body TEXT NOT NULL,
    send_status VARCHAR(20) DEFAULT 'PENDING' CHECK (send_status IN ('PENDING', 'SENT', 'FAILED')),
    retry_count INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP WITH TIME ZONE
);

-- 11. Run & Performance Telemetry
CREATE TABLE runtime.run_metrics (
    run_metric_id BIGSERIAL PRIMARY KEY,
    run_id VARCHAR(50) NOT NULL REFERENCES runtime.pipeline_runs(run_id),
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC(15, 4) NOT NULL,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE runtime.performance_metrics (
    perf_metric_id BIGSERIAL PRIMARY KEY,
    notebook_run_id VARCHAR(50) NOT NULL REFERENCES runtime.notebook_runs(notebook_run_id),
    stage_name VARCHAR(100) NOT NULL,
    records_per_second NUMERIC(12, 2) NOT NULL,
    duration_ms BIGINT NOT NULL,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 12. Issue Tracking Lifecycle (Mapped to policy framework)
CREATE TABLE runtime.issue_history (
    issue_id VARCHAR(50) PRIMARY KEY,
    issue_title VARCHAR(150) NOT NULL,
    category VARCHAR(50) NOT NULL CHECK (category IN ('DATA_QUALITY', 'COMPLIANCE', 'RECONCILIATION_FAIL', 'SCHEMA_DRIFT')),
    priority VARCHAR(10) NOT NULL CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    severity VARCHAR(10) NOT NULL CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    assignee_steward_id VARCHAR(50), -- references master.data_stewards(steward_id)
    assignee_team VARCHAR(100) NOT NULL,
    sla_due_date DATE NOT NULL,
    current_status VARCHAR(30) NOT NULL CHECK (current_status IN ('OPEN', 'ASSIGNED', 'IN_INVESTIGATION', 'REMEDIATING', 'PENDING_APPROVAL', 'CLOSED')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE runtime.findings (
    finding_id VARCHAR(50) PRIMARY KEY,
    issue_id VARCHAR(50) NOT NULL REFERENCES runtime.issue_history(issue_id),
    validation_run_id VARCHAR(50) REFERENCES runtime.validation_run_history(validation_run_id),
    finding_details TEXT NOT NULL,
    root_cause_analysis TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE runtime.remediation_history (
    remediation_id BIGSERIAL PRIMARY KEY,
    issue_id VARCHAR(50) NOT NULL REFERENCES runtime.issue_history(issue_id),
    remediation_action TEXT NOT NULL,
    remediated_by VARCHAR(100) NOT NULL,
    remediation_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    approval_status VARCHAR(30) NOT NULL CHECK (approval_status IN ('PENDING_REVIEW', 'APPROVED', 'REJECTED')),
    approver VARCHAR(100),
    closure_date TIMESTAMP WITH TIME ZONE
);
