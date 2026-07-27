-- ============================================================================
-- Enterprise Data Trust Framework (EDTF)
-- Component: Metadata Reference Repository DDL
-- Database: metadata_db (Schema: reference)
-- RDBMS Target: PostgreSQL / Azure Database for PostgreSQL
-- Version: 1.0.0
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS reference;

-- 1. Master Code List Registry (Dynamic Metadata Lookups)
CREATE TABLE reference.master_code_lists (
    code_list_id VARCHAR(50) PRIMARY KEY,
    list_name VARCHAR(100) NOT NULL UNIQUE, -- e.g., GENDER_CODES, ACCOUNT_TYPES
    description TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE reference.allowed_values (
    value_id BIGSERIAL PRIMARY KEY,
    code_list_id VARCHAR(50) NOT NULL REFERENCES reference.master_code_lists(code_list_id),
    code_value VARCHAR(50) NOT NULL, -- e.g., 'M', 'F', 'SAVINGS'
    value_label VARCHAR(100) NOT NULL, -- e.g., 'Male', 'Female', 'Savings Account'
    display_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_list_value UNIQUE (code_list_id, code_value)
);

CREATE INDEX idx_allowed_values_list ON reference.allowed_values(code_list_id);

-- 2. Countries Reference (ISO 3166)
CREATE TABLE reference.countries (
    country_iso_alpha3 CHAR(3) PRIMARY KEY,
    country_iso_alpha2 CHAR(2) NOT NULL UNIQUE,
    country_name VARCHAR(100) NOT NULL,
    region VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

-- 3. Currencies Reference (ISO 4217)
CREATE TABLE reference.currencies (
    currency_code CHAR(3) PRIMARY KEY,
    currency_name VARCHAR(100) NOT NULL,
    symbol VARCHAR(10),
    decimal_places INT NOT NULL DEFAULT 2,
    is_active BOOLEAN DEFAULT TRUE
);

-- 4. SWIFT / BIC Routing Directory (ISO 9362)
CREATE TABLE reference.swift_codes (
    swift_bic VARCHAR(11) PRIMARY KEY,
    bank_name VARCHAR(150) NOT NULL,
    country_iso_alpha3 CHAR(3) NOT NULL REFERENCES reference.countries(country_iso_alpha3),
    city VARCHAR(100) NOT NULL,
    branch_code VARCHAR(3),
    is_active BOOLEAN DEFAULT TRUE
);

-- 5. Indian Financial System Codes (IFSC) Registry
CREATE TABLE reference.ifsc_codes (
    ifsc_code VARCHAR(11) PRIMARY KEY,
    bank_name VARCHAR(150) NOT NULL,
    branch_name VARCHAR(150) NOT NULL,
    address TEXT,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_ifsc_bank ON reference.ifsc_codes(bank_name);

-- 6. Bank Branch Directory (Internal and External Routing)
CREATE TABLE reference.branch_codes (
    branch_id VARCHAR(50) PRIMARY KEY,
    branch_name VARCHAR(150) NOT NULL,
    routing_transit_number VARCHAR(50),
    swift_bic VARCHAR(11) REFERENCES reference.swift_codes(swift_bic),
    ifsc_code VARCHAR(11) REFERENCES reference.ifsc_codes(ifsc_code),
    address TEXT,
    city VARCHAR(100) NOT NULL,
    state_province VARCHAR(100),
    postal_code VARCHAR(20),
    country_iso_alpha3 CHAR(3) REFERENCES reference.countries(country_iso_alpha3),
    is_active BOOLEAN DEFAULT TRUE
);

-- 7. Product Codes Register
CREATE TABLE reference.product_codes (
    product_code VARCHAR(50) PRIMARY KEY,
    product_name VARCHAR(150) NOT NULL,
    product_category VARCHAR(50) NOT NULL CHECK (product_category IN ('LIABILITY', 'ASSET', 'WEALTH_MANAGEMENT', 'TREASURY', 'CREDIT_CARD')),
    product_type VARCHAR(100) NOT NULL, -- e.g., 'TERM_DEPOSIT', 'FIXED_MORTGAGE'
    interest_bearing BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 8. Universal Status Codes (System Run State Machine Enums)
CREATE TABLE reference.status_codes (
    status_code VARCHAR(50) PRIMARY KEY,
    status_group VARCHAR(50) NOT NULL CHECK (status_group IN ('MIGRATION_RUN', 'DATA_QUALITY', 'EXCEPTION_LIFECYCLE', 'APPROVAL_WORKFLOW', 'USER_ACCESS')),
    status_name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL
);

CREATE INDEX idx_status_group ON reference.status_codes(status_group);

-- 9. Dynamic Metadata Column Lookups Link Table
CREATE TABLE reference.reference_lookups (
    lookup_id BIGSERIAL PRIMARY KEY,
    column_id VARCHAR(50) NOT NULL, -- references master.column_metadata(column_id)
    lookup_type VARCHAR(50) NOT NULL CHECK (lookup_type IN ('MASTER_CODE_LIST', 'ISO_COUNTRY', 'ISO_CURRENCY', 'SWIFT_CODE', 'IFSC_CODE', 'INTERNAL_BRANCH')),
    reference_entity_key VARCHAR(100) NOT NULL, -- Points to reference table identifier key
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
