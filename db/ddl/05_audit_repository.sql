-- ============================================================================
-- Enterprise Data Trust Framework (EDTF)
-- Component: Metadata Audit Repository DDL
-- Database: metadata_db (Schema: audit)
-- RDBMS Target: PostgreSQL / Azure Database for PostgreSQL
-- Version: 1.0.0
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS audit;

-- 1. Metadata Schema/Rules Change Requests (Change Management Workflows)
CREATE TABLE audit.change_requests (
    request_id VARCHAR(50) PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL, -- e.g. 'DATA_QUALITY_RULE', 'BUSINESS_TERM', 'DATASET_REGISTRY'
    entity_id VARCHAR(100) NOT NULL,
    request_type VARCHAR(30) NOT NULL CHECK (request_type IN ('CREATE', 'UPDATE', 'RETIRE')),
    proposed_changes JSONB NOT NULL, -- Detailed JSON containing the new configuration fields
    rationale TEXT NOT NULL,
    requester VARCHAR(100) NOT NULL,
    request_status VARCHAR(30) DEFAULT 'PENDING_REVIEW' CHECK (request_status IN ('PENDING_REVIEW', 'APPROVED', 'REJECTED', 'IMPLEMENTED', 'CANCELLED')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_change_req_status ON audit.change_requests(request_status);

-- 2. Change Review Comments (Collaboration Thread)
CREATE TABLE audit.review_comments (
    comment_id BIGSERIAL PRIMARY KEY,
    request_id VARCHAR(50) NOT NULL REFERENCES audit.change_requests(request_id),
    reviewer VARCHAR(100) NOT NULL,
    comment_text TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Approvals and Decom/Retire Signoffs (Compliance Audit Signatures)
CREATE TABLE audit.approvals (
    approval_id BIGSERIAL PRIMARY KEY,
    request_id VARCHAR(50) NOT NULL REFERENCES audit.change_requests(request_id),
    approver_name VARCHAR(100) NOT NULL,
    approver_role VARCHAR(50) NOT NULL CHECK (approver_role IN ('DATA_OWNER', 'DATA_STEWARD', 'COMPLIANCE_OFFICER')),
    signoff_decision VARCHAR(20) NOT NULL CHECK (signoff_decision IN ('APPROVED', 'REJECTED')),
    signature_hash VARCHAR(256) NOT NULL, -- Cryptographic hash of review payload + approver details
    signed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_approval_req ON audit.approvals(request_id);

-- 4. Metadata Change Log (Historical Change Delta Engine)
CREATE TABLE audit.metadata_changes (
    change_id BIGSERIAL PRIMARY KEY,
    request_id VARCHAR(50) REFERENCES audit.change_requests(request_id),
    target_table VARCHAR(100) NOT NULL,
    primary_key_val VARCHAR(100) NOT NULL,
    operation_type VARCHAR(20) NOT NULL CHECK (operation_type IN ('INSERT', 'UPDATE', 'DELETE')),
    pre_change_state JSONB, -- NULL for inserts
    post_change_state JSONB, -- NULL for deletes
    modified_by VARCHAR(100) NOT NULL,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_meta_changes_table ON audit.metadata_changes(target_table, primary_key_val);

-- 5. Version Registry for Rules, Glossary and Mapping configurations
CREATE TABLE audit.version_history (
    version_id BIGSERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL, -- e.g. 'DQ_RULE', 'BUSINESS_GLOSSARY'
    entity_id VARCHAR(100) NOT NULL,
    version_string VARCHAR(20) NOT NULL, -- Semantic Version string: Major.Minor.Patch
    effective_date TIMESTAMP WITH TIME ZONE NOT NULL,
    expiry_date TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    committed_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_version_entity ON audit.version_history(entity_type, entity_id);

-- 6. Workflow Engine Logs (Collibra/Service Bus Integrations tracker)
CREATE TABLE audit.workflow_history (
    instance_id VARCHAR(100) PRIMARY KEY,
    workflow_name VARCHAR(150) NOT NULL,
    current_state VARCHAR(50) NOT NULL,
    triggered_by VARCHAR(100) NOT NULL,
    external_engine VARCHAR(50) DEFAULT 'COLLIBRA' CHECK (external_engine IN ('COLLIBRA', 'SERVICE_BUS', 'AZURE_DURABLE_FUNCTIONS')),
    execution_log TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- 7. Retirements Directory
CREATE TABLE audit.retirements (
    retirement_id BIGSERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(100) NOT NULL,
    decommission_justification TEXT NOT NULL,
    compliance_signoff_ref VARCHAR(100) NOT NULL,
    archival_location VARCHAR(255), -- Where historical entity datasets were stored for compliance
    retired_by VARCHAR(100) NOT NULL,
    retired_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 8. Rollback Operations Audit Trail
CREATE TABLE audit.rollback_history (
    rollback_id BIGSERIAL PRIMARY KEY,
    request_id VARCHAR(50) NOT NULL REFERENCES audit.change_requests(request_id),
    change_id BIGINT NOT NULL REFERENCES audit.metadata_changes(change_id),
    rollback_rationale TEXT NOT NULL,
    executed_by VARCHAR(100) NOT NULL,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
