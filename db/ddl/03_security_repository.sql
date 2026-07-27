-- ============================================================================
-- Enterprise Data Trust Framework (EDTF)
-- Component: Metadata Security Repository DDL
-- Database: metadata_db (Schema: security)
-- RDBMS Target: PostgreSQL / Azure Database for PostgreSQL
-- Version: 1.0.0
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS security;

-- 1. Role-Based Access Control (RBAC) & Group Registries
CREATE TABLE security.rbac_roles (
    role_id VARCHAR(50) PRIMARY KEY,
    role_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE security.user_groups (
    group_id VARCHAR(50) PRIMARY KEY,
    group_name VARCHAR(100) NOT NULL UNIQUE, -- AD/Entra Group Name
    description TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE security.rbac_permissions (
    permission_id VARCHAR(50) PRIMARY KEY,
    permission_name VARCHAR(100) NOT NULL UNIQUE, -- e.g. READ_CONFIDENTIAL, WRITE_METADATA
    description TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE security.role_permissions (
    role_id VARCHAR(50) REFERENCES security.rbac_roles(role_id),
    permission_id VARCHAR(50) REFERENCES security.rbac_permissions(permission_id),
    PRIMARY KEY (role_id, permission_id)
);

-- 2. Data Masking Policies (Tokenization/Anonymization)
CREATE TABLE security.masking_policies (
    masking_policy_id VARCHAR(50) PRIMARY KEY,
    policy_name VARCHAR(100) NOT NULL UNIQUE,
    masking_type VARCHAR(30) NOT NULL CHECK (masking_type IN ('REDACT', 'HASH_SHA256', 'PARTIAL_MASK', 'TOKENIZE', 'DETERMINISTIC_MASK')),
    masking_expression TEXT NOT NULL, -- e.g., "concat(substring(val, 1, 4), '******', substring(val, 11, 4))"
    salt_reference_key VARCHAR(100), -- Reference to Vault Key for salting
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Encryption Policies (Column Cryptographic Control)
CREATE TABLE security.encryption_policies (
    encryption_policy_id VARCHAR(50) PRIMARY KEY,
    policy_name VARCHAR(100) NOT NULL UNIQUE,
    encryption_algorithm VARCHAR(50) NOT NULL DEFAULT 'AES_256_GCM' CHECK (encryption_algorithm IN ('AES_256_GCM', 'RSA_3072_OAEP', 'FPE_AES_256')),
    key_vault_reference_id VARCHAR(150) NOT NULL, -- Logical reference to Key Vault secret URI
    key_rotation_interval_days INT DEFAULT 90,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Access Policies (Dataset Level mapping to Roles/Groups)
CREATE TABLE security.access_policies (
    access_policy_id VARCHAR(50) PRIMARY KEY,
    dataset_id VARCHAR(50) NOT NULL, -- references master.dataset_registry(dataset_id)
    role_id VARCHAR(50) REFERENCES security.rbac_roles(role_id),
    group_id VARCHAR(50) REFERENCES security.user_groups(group_id),
    privilege_type VARCHAR(20) NOT NULL CHECK (privilege_type IN ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'ALL')),
    approval_workflow_ref VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_access_policy_dataset ON security.access_policies(dataset_id);

-- 5. Column-Level Security (CLS) Policies
CREATE TABLE security.column_security (
    column_security_id VARCHAR(50) PRIMARY KEY,
    column_id VARCHAR(50) NOT NULL, -- references master.column_metadata(column_id)
    masking_policy_id VARCHAR(50) REFERENCES security.masking_policies(masking_policy_id),
    encryption_policy_id VARCHAR(50) REFERENCES security.encryption_policies(encryption_policy_id),
    required_permission_id VARCHAR(50) REFERENCES security.rbac_permissions(permission_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_col_sec_column ON security.column_security(column_id);

-- 6. Row-Level Security (RLS) Filter Predicates
CREATE TABLE security.row_level_security (
    rls_policy_id VARCHAR(50) PRIMARY KEY,
    dataset_id VARCHAR(50) NOT NULL, -- references master.dataset_registry(dataset_id)
    policy_name VARCHAR(100) NOT NULL,
    filter_predicate TEXT NOT NULL, -- SQL WHERE clause expression e.g., "customer_region = current_user_region()"
    enforced_group_id VARCHAR(50) REFERENCES security.user_groups(group_id), -- Group subject to this filter
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_rls_dataset ON security.row_level_security(dataset_id);

-- 7. Data Sharing Policies (Delta Sharing and external API consumption)
CREATE TABLE security.data_sharing_policies (
    share_policy_id VARCHAR(50) PRIMARY KEY,
    dataset_id VARCHAR(50) NOT NULL, -- references master.dataset_registry(dataset_id)
    recipient_name VARCHAR(100) NOT NULL, -- External business entity or API Consumer name
    authentication_type VARCHAR(30) NOT NULL CHECK (authentication_type IN ('TOKEN_MUTUAL_TLS', 'DELTA_SHARING_CREDENTIALS', 'OAUTH2')),
    data_agreement_ref VARCHAR(255) NOT NULL, -- Legal link to contract document
    expiration_date TIMESTAMP WITH TIME ZONE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 8. Secrets Vault Reference Metadata (No actual plain secrets allowed)
CREATE TABLE security.secrets_metadata (
    secret_meta_id VARCHAR(50) PRIMARY KEY,
    secret_name VARCHAR(100) NOT NULL UNIQUE, -- Logical name referenced in PySpark e.g. "ADLS_SP_CLIENT_SECRET"
    vault_provider VARCHAR(30) NOT NULL CHECK (vault_provider IN ('AZURE_KEY_VAULT', 'HASHICORP_VAULT', 'AWS_SECRETS_MANAGER')),
    vault_uri VARCHAR(255) NOT NULL,
    secret_key_name VARCHAR(100) NOT NULL,
    last_validated_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
