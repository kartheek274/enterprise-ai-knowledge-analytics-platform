-- ============================================================================
-- Enterprise Data Trust Framework (EDTF)
-- Component: Metadata Master Repository DDL
-- Database: metadata_db (Schema: master)
-- RDBMS Target: PostgreSQL / Azure Database for PostgreSQL
-- Version: 1.0.0
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS master;

-- 1. Business Domains
CREATE TABLE master.business_domains (
    domain_id VARCHAR(50) PRIMARY KEY,
    domain_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    parent_domain_id VARCHAR(50) REFERENCES master.business_domains(domain_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_domains_parent ON master.business_domains(parent_domain_id);

-- 2. Data Products
CREATE TABLE master.data_products (
    product_id VARCHAR(50) PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    domain_id VARCHAR(50) NOT NULL REFERENCES master.business_domains(domain_id),
    sla_definition JSONB,
    kpi_definitions JSONB,
    quality_score_target NUMERIC(5, 2) CHECK (quality_score_target BETWEEN 0 AND 100),
    lifecycle_status VARCHAR(30) CHECK (lifecycle_status IN ('DRAFT', 'ACTIVE', 'DEPRECATED', 'RETIRED')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_products_domain ON master.data_products(domain_id);

-- 3. Data Owners & Stewards (Part of Governance Roles)
CREATE TABLE master.data_owners (
    owner_id VARCHAR(50) PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    department VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE master.data_stewards (
    steward_id VARCHAR(50) PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    department VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Business Glossary & Terms
CREATE TABLE master.business_glossary (
    glossary_id VARCHAR(50) PRIMARY KEY,
    glossary_name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    domain_id VARCHAR(50) NOT NULL REFERENCES master.business_domains(domain_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE master.business_terms (
    term_id VARCHAR(50) PRIMARY KEY,
    glossary_id VARCHAR(50) NOT NULL REFERENCES master.business_glossary(glossary_id),
    term_name VARCHAR(100) NOT NULL,
    definition TEXT NOT NULL,
    synonyms TEXT[],
    aliases TEXT[],
    formula TEXT,
    approval_status VARCHAR(30) NOT NULL CHECK (approval_status IN ('DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED')),
    lifecycle_status VARCHAR(30) NOT NULL CHECK (lifecycle_status IN ('ACTIVE', 'DEPRECATED', 'RETIRED')),
    owner_id VARCHAR(50) REFERENCES master.data_owners(owner_id),
    steward_id VARCHAR(50) REFERENCES master.data_stewards(steward_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_glossary_term UNIQUE(glossary_id, term_name)
);

CREATE INDEX idx_terms_glossary ON master.business_terms(glossary_id);
CREATE INDEX idx_terms_owner ON master.business_terms(owner_id);
CREATE INDEX idx_terms_steward ON master.business_terms(steward_id);

-- 5. Business Term Relationships (Hierarchical & Semantic Linking)
CREATE TABLE master.business_term_relationships (
    term_id VARCHAR(50) REFERENCES master.business_terms(term_id),
    related_term_id VARCHAR(50) REFERENCES master.business_terms(term_id),
    relationship_type VARCHAR(50) CHECK (relationship_type IN ('BROADER', 'NARROWER', 'SYNONYM', 'RELATED_TO')),
    PRIMARY KEY (term_id, related_term_id, relationship_type)
);

-- 6. Dataset Registry & Environment Configurations
CREATE TABLE master.environment_configuration (
    env_id VARCHAR(30) PRIMARY KEY CHECK (env_id IN ('DEV', 'UAT', 'PROD')),
    spark_warehouse_path VARCHAR(255) NOT NULL,
    onelake_workspace_url VARCHAR(255) NOT NULL,
    metadata_api_endpoint VARCHAR(255) NOT NULL,
    log_level VARCHAR(10) DEFAULT 'INFO'
);

CREATE TABLE master.dataset_registry (
    dataset_id VARCHAR(50) PRIMARY KEY,
    dataset_name VARCHAR(100) NOT NULL UNIQUE,
    data_product_id VARCHAR(50) REFERENCES master.data_products(product_id),
    domain_id VARCHAR(50) NOT NULL REFERENCES master.business_domains(domain_id),
    physical_format VARCHAR(20) NOT NULL CHECK (physical_format IN ('DELTA', 'PARQUET', 'AVRO', 'CSV', 'ORC')),
    layer VARCHAR(20) NOT NULL CHECK (layer IN ('BRONZE', 'SILVER', 'GOLD', 'SANDBOX')),
    storage_path VARCHAR(500) NOT NULL,
    onelake_shortcut_path VARCHAR(500),
    is_pii BOOLEAN DEFAULT FALSE,
    certification_status VARCHAR(30) DEFAULT 'BRONZE' CHECK (certification_status IN ('BRONZE', 'SILVER', 'GOLD', 'CERTIFIED', 'PROVISIONALLY_CERTIFIED', 'DEPRECATED', 'RETIRED')),
    owner_id VARCHAR(50) NOT NULL REFERENCES master.data_owners(owner_id),
    steward_id VARCHAR(50) NOT NULL REFERENCES master.data_stewards(steward_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dataset_product ON master.dataset_registry(data_product_id);
CREATE INDEX idx_dataset_domain ON master.dataset_registry(domain_id);

-- 7. Catalog Assets
CREATE TABLE master.catalog_assets (
    asset_id VARCHAR(50) PRIMARY KEY,
    dataset_id VARCHAR(50) NOT NULL REFERENCES master.dataset_registry(dataset_id),
    collibra_asset_id UUID,
    purview_asset_id VARCHAR(255),
    openmetadata_fqn VARCHAR(500),
    sync_status VARCHAR(30) DEFAULT 'SYNCED' CHECK (sync_status IN ('SYNCED', 'PENDING', 'FAILED')),
    last_synced_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_catalog_dataset ON master.catalog_assets(dataset_id);

-- 8. Data Classification Categories
CREATE TABLE master.data_classification (
    classification_id VARCHAR(50) PRIMARY KEY,
    classification_name VARCHAR(50) NOT NULL UNIQUE CHECK (classification_name IN ('PUBLIC', 'INTERNAL', 'RESTRICTED', 'CONFIDENTIAL', 'SECRET')),
    sensitivity_level VARCHAR(20) NOT NULL CHECK (sensitivity_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    description TEXT NOT NULL
);

-- 9. Column Metadata
CREATE TABLE master.column_metadata (
    column_id VARCHAR(50) PRIMARY KEY,
    dataset_id VARCHAR(50) NOT NULL REFERENCES master.dataset_registry(dataset_id),
    column_name VARCHAR(100) NOT NULL,
    business_name VARCHAR(100),
    data_type VARCHAR(50) NOT NULL,
    is_nullable BOOLEAN DEFAULT TRUE,
    is_primary_key BOOLEAN DEFAULT FALSE,
    is_foreign_key BOOLEAN DEFAULT FALSE,
    classification_id VARCHAR(50) NOT NULL REFERENCES master.data_classification(classification_id),
    term_id VARCHAR(50) REFERENCES master.business_terms(term_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_dataset_column UNIQUE(dataset_id, column_name)
);

CREATE INDEX idx_column_dataset ON master.column_metadata(dataset_id);
CREATE INDEX idx_column_classification ON master.column_metadata(classification_id);

-- 10. Critical Data Elements (CDE) Mapping
CREATE TABLE master.critical_data_elements (
    cde_id VARCHAR(50) PRIMARY KEY,
    column_id VARCHAR(50) NOT NULL REFERENCES master.column_metadata(column_id),
    regulatory_mandate VARCHAR(100) NOT NULL, -- e.g., BCBS-239, GDPR, SOX
    justification TEXT NOT NULL,
    cde_status VARCHAR(30) DEFAULT 'ACTIVE' CHECK (cde_status IN ('ACTIVE', 'DEPRECATED')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cde_column ON master.critical_data_elements(column_id);

-- 11. Policy Definitions (Policy Framework)
CREATE TABLE master.policy_definitions (
    policy_id VARCHAR(50) PRIMARY KEY,
    policy_name VARCHAR(100) NOT NULL UNIQUE,
    policy_type VARCHAR(50) NOT NULL CHECK (policy_type IN ('COMPLIANCE', 'SECURITY', 'RETENTION', 'MASKING', 'ENCRYPTION', 'AUDIT')),
    description TEXT NOT NULL,
    regulatory_authority VARCHAR(100), -- GDPR, Basel Committee
    lifecycle_status VARCHAR(30) DEFAULT 'DRAFT' CHECK (lifecycle_status IN ('DRAFT', 'SUBMITTED', 'APPROVED', 'ACTIVE', 'DEPRECATED', 'RETIRED')),
    owner_id VARCHAR(50) NOT NULL REFERENCES master.data_owners(owner_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 12. Certification Definitions
CREATE TABLE master.certification_definitions (
    cert_def_id VARCHAR(50) PRIMARY KEY,
    certification_level VARCHAR(30) NOT NULL UNIQUE CHECK (certification_level IN ('BRONZE', 'SILVER', 'GOLD', 'CERTIFIED', 'PROVISIONALLY_CERTIFIED')),
    minimum_dq_score NUMERIC(5, 2) CHECK (minimum_dq_score BETWEEN 0 AND 100),
    requirements_description TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 13. Pipeline, Notebook & Report Registry
CREATE TABLE master.pipeline_registry (
    pipeline_id VARCHAR(50) PRIMARY KEY,
    pipeline_name VARCHAR(100) NOT NULL,
    orchestration_tool VARCHAR(50) NOT NULL CHECK (orchestration_tool IN ('ADF', 'AIRFLOW', 'FABRIC', 'DATABRICKS_WORKFLOWS')),
    repository_url VARCHAR(255) NOT NULL,
    branch_name VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE master.notebook_registry (
    notebook_id VARCHAR(50) PRIMARY KEY,
    notebook_path VARCHAR(255) NOT NULL,
    pipeline_id VARCHAR(50) REFERENCES master.pipeline_registry(pipeline_id),
    language VARCHAR(20) NOT NULL CHECK (language IN ('PYTHON', 'SCALA', 'SQL', 'R')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE master.report_registry (
    report_id VARCHAR(50) PRIMARY KEY,
    report_name VARCHAR(100) NOT NULL,
    workspace_id VARCHAR(100) NOT NULL,
    report_type VARCHAR(30) DEFAULT 'POWER_BI' CHECK (report_type IN ('POWER_BI', 'TABLEAU', 'SSR')),
    owner_id VARCHAR(50) REFERENCES master.data_owners(owner_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 14. Rule Engine Configuration: Rule Groups, Categories, Templates & Parameters
CREATE TABLE master.rule_groups (
    group_id VARCHAR(50) PRIMARY KEY,
    group_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE master.rule_categories (
    category_id VARCHAR(50) PRIMARY KEY,
    category_name VARCHAR(50) NOT NULL UNIQUE CHECK (category_name IN (
        'COMPLETENESS', 'ACCURACY', 'CONSISTENCY', 'VALIDITY', 'UNIQUENESS', 
        'INTEGRITY', 'TIMELINESS', 'CONFORMITY', 'PRECISION', 'REASONABLENESS', 
        'REFERENTIAL_INTEGRITY', 'FRESHNESS'
    )),
    description TEXT NOT NULL
);

CREATE TABLE master.rule_templates (
    template_id VARCHAR(50) PRIMARY KEY,
    template_name VARCHAR(100) NOT NULL UNIQUE,
    category_id VARCHAR(50) NOT NULL REFERENCES master.rule_categories(category_id),
    expression_template TEXT NOT NULL, -- e.g. "col(${column}) >= ${min_val}"
    description TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_templates_category ON master.rule_templates(category_id);

CREATE TABLE master.business_rules (
    business_rule_id VARCHAR(50) PRIMARY KEY,
    rule_name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    formula TEXT,
    owner_id VARCHAR(50) NOT NULL REFERENCES master.data_owners(owner_id),
    steward_id VARCHAR(50) NOT NULL REFERENCES master.data_stewards(steward_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE master.data_quality_rules (
    rule_id VARCHAR(50) PRIMARY KEY,
    rule_name VARCHAR(100) NOT NULL,
    business_rule_id VARCHAR(50) REFERENCES master.business_rules(business_rule_id),
    template_id VARCHAR(50) REFERENCES master.rule_templates(template_id),
    group_id VARCHAR(50) REFERENCES master.rule_groups(group_id),
    column_id VARCHAR(50) NOT NULL REFERENCES master.column_metadata(column_id),
    expression_override TEXT, -- Optional direct SQL expression override
    rule_parameters JSONB NOT NULL, -- JSON formatted parameter mapping like {"min_val": 0, "max_val": 1000}
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('CRITICAL', 'WARNING', 'INFO')),
    active_status BOOLEAN DEFAULT TRUE,
    version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dq_rules_column ON master.data_quality_rules(column_id);
CREATE INDEX idx_dq_rules_template ON master.data_quality_rules(template_id);
CREATE INDEX idx_dq_rules_group ON master.data_quality_rules(group_id);

-- 15. Threshold Rules (Schema/Drift threshold & row count drops)
CREATE TABLE master.threshold_rules (
    threshold_id VARCHAR(50) PRIMARY KEY,
    dataset_id VARCHAR(50) NOT NULL REFERENCES master.dataset_registry(dataset_id),
    metric_type VARCHAR(50) NOT NULL CHECK (metric_type IN ('ROW_COUNT_DROP_PCT', 'VALUE_VARIANCE_PCT', 'NULL_PERCENTAGE')),
    max_threshold NUMERIC(5, 2) NOT NULL, -- e.g., 5.00 for 5% drop limit
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('CRITICAL', 'WARNING', 'INFO')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_threshold_dataset ON master.threshold_rules(dataset_id);

-- 16. Reference Lookup Rules
CREATE TABLE master.reference_lookup_rules (
    lookup_rule_id VARCHAR(50) PRIMARY KEY,
    column_id VARCHAR(50) NOT NULL REFERENCES master.column_metadata(column_id),
    lookup_type VARCHAR(30) NOT NULL CHECK (lookup_type IN ('INLINE_VALUES', 'DATABASE_TABLE')),
    allowed_values_array TEXT[], -- Inline array checking e.g., ['USD','EUR']
    reference_table_fqn VARCHAR(255), -- Remote DB reference lookup table e.g. 'reference.currencies'
    reference_key_column VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 17. Source to Target Schema Mapping & Column Lineage
CREATE TABLE master.source_target_mapping (
    mapping_id VARCHAR(50) PRIMARY KEY,
    source_dataset_id VARCHAR(50) NOT NULL REFERENCES master.dataset_registry(dataset_id),
    target_dataset_id VARCHAR(50) NOT NULL REFERENCES master.dataset_registry(dataset_id),
    source_column_id VARCHAR(50) NOT NULL REFERENCES master.column_metadata(column_id),
    target_column_id VARCHAR(50) NOT NULL REFERENCES master.column_metadata(column_id),
    transformation_logic TEXT NOT NULL, -- SQL code snippet or transformation rule description
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_mapping_source ON master.source_target_mapping(source_dataset_id);
CREATE INDEX idx_mapping_target ON master.source_target_mapping(target_dataset_id);

-- 18. Lineage Definitions (Target for dbt, PySpark and Power BI endpoints)
CREATE TABLE master.lineage_definitions (
    lineage_id VARCHAR(50) PRIMARY KEY,
    upstream_asset_id VARCHAR(255) NOT NULL, -- Can be physical table/column or dbt model path
    downstream_asset_id VARCHAR(255) NOT NULL, -- Can be physical table/column or Power BI report item
    asset_type VARCHAR(30) NOT NULL CHECK (asset_type IN ('TABLE', 'COLUMN', 'DBT_MODEL', 'POWER_BI_DATASET', 'POWER_BI_VISUAL')),
    transformation_step_id VARCHAR(50) REFERENCES master.pipeline_registry(pipeline_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
