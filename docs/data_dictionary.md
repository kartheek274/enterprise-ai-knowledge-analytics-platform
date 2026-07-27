# Enterprise Data Trust Framework (EDTF) - Data Dictionary

This document represents the logical and physical data dictionary of the Metadata Repository (`metadata_db`).

---

## 1. Domain: Metadata Master Repository (`master` Schema)

### 1.1 Table: `business_domains`
* **Business Purpose**: Organizes banking data assets into distinct functional domains (e.g., Retail Deposits, Wealth, Commercial Lending) to align ownership.
* **Normalization Level**: 3NF
* **Partition Strategy**: Unpartitioned (low volume, < 1,000 rows).
* **Retention Policy**: Indefinite.

| Column Name | Business Name | Business Definition | Datatype | Nullable | Allowed Values | Sample Value | CDE | Classification | Sensitivity | Masking | Encryption |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `domain_id` | Domain ID | Unique alphanumeric identifier for a banking domain | `VARCHAR(50)` | No | `^[A-Z_]{3,50}$` | `RETAIL_DEPOSITS` | No | INTERNAL | LOW | No | No |
| `domain_name` | Domain Name | Human-readable name of the domain | `VARCHAR(100)` | No | Free text | `Retail Deposits` | No | INTERNAL | LOW | No | No |
| `description` | Description | Functional description of the domain scope | `TEXT` | No | Free text | `Savings, Checking accounts` | No | INTERNAL | LOW | No | No |
| `parent_domain_id` | Parent Domain ID | Relational pointer to a parent domain | `VARCHAR(50)` | Yes | Valid `domain_id` | `RETAIL_BANKING` | No | INTERNAL | LOW | No | No |

---

### 1.2 Table: `data_products`
* **Business Purpose**: Registers logical packages of data assets consumed by business workflows, establishing SLA metrics.
* **Normalization Level**: 3NF
* **Partition Strategy**: Unpartitioned.
* **Retention Policy**: Indefinite.

| Column Name | Business Name | Business Definition | Datatype | Nullable | Allowed Values | Sample Value | CDE | Classification | Sensitivity | Masking | Encryption |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `product_id` | Product ID | Unique alphanumeric key for the data product | `VARCHAR(50)` | No | `^[A-Z_]{3,50}$` | `DP_CUSTOMER_360` | No | INTERNAL | LOW | No | No |
| `product_name` | Product Name | Name of the business data product | `VARCHAR(100)` | No | Free text | `Customer 360 Profile` | No | INTERNAL | LOW | No | No |
| `description` | Description | Target business objective of the product | `TEXT` | No | Free text | `Consolidated customer profile` | No | INTERNAL | LOW | No | No |
| `domain_id` | Domain ID | Primary domain hosting this product | `VARCHAR(50)` | No | Valid `domain_id` | `RETAIL_DEPOSITS` | No | INTERNAL | LOW | No | No |
| `sla_definition` | SLA Definition | JSON specifying data availability SLAs | `JSONB` | Yes | Valid JSON | `{"delivery_cutoff": "06:00 EST"}` | No | INTERNAL | LOW | No | No |
| `kpi_definitions` | KPI Definitions | JSON of quality threshold KPIs | `JSONB` | Yes | Valid JSON | `{"min_quality_score": 99.50}` | No | INTERNAL | LOW | No | No |
| `quality_score_target`| DQ Score Target | Minimum target overall quality score percentage | `NUMERIC(5,2)` | Yes | `0.00` to `100.00` | `99.90` | No | INTERNAL | LOW | No | No |
| `lifecycle_status` | Lifecycle Status | Current operational state of the product | `VARCHAR(30)` | No | `DRAFT`, `ACTIVE`, `DEPRECATED`, `RETIRED` | `ACTIVE` | No | INTERNAL | LOW | No | No |

---

### 1.3 Table: `business_glossary`
* **Business Purpose**: Hosts collections of standardized business terms to guarantee semantic consistency across legacy databases.

| Column Name | Business Name | Business Definition | Datatype | Nullable | Allowed Values | Sample Value | CDE | Classification | Sensitivity | Masking | Encryption |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `glossary_id` | Glossary ID | Unique key representing a glossary book | `VARCHAR(50)` | No | Alphanumeric | `BG_CORE_RETAIL` | No | INTERNAL | LOW | No | No |
| `glossary_name` | Glossary Name | Title of the business glossary | `VARCHAR(100)` | No | Free text | `Retail Core Banking Glossary` | No | INTERNAL | LOW | No | No |
| `description` | Description | Core business scope definition | `TEXT` | No | Free text | `Terms relating to core accounts` | No | INTERNAL | LOW | No | No |
| `domain_id` | Domain ID | Parent domain associated with the glossary | `VARCHAR(50)` | No | Valid `domain_id` | `RETAIL_DEPOSITS` | No | INTERNAL | LOW | No | No |

---

### 1.4 Table: `business_terms`
* **Business Purpose**: Canonical glossary definitions for data columns, mapped to owners and stewards.

| Column Name | Business Name | Business Definition | Datatype | Nullable | Allowed Values | Sample Value | CDE | Classification | Sensitivity | Masking | Encryption |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `term_id` | Term ID | Alphanumeric identity key of the business term | `VARCHAR(50)` | No | Alphanumeric | `BT_ACCT_BAL` | No | INTERNAL | LOW | No | No |
| `glossary_id` | Glossary ID | Parent glossary mapping reference | `VARCHAR(50)` | No | Valid `glossary_id` | `BG_CORE_RETAIL` | No | INTERNAL | LOW | No | No |
| `term_name` | Term Name | Standardization business label | `VARCHAR(100)` | No | Free text | `Account Balance` | No | INTERNAL | LOW | No | No |
| `definition` | Definition | Exact description of how term value is calculated | `TEXT` | No | Free text | `Total ledger balance minus holds` | No | INTERNAL | LOW | No | No |
| `synonyms` | Synonyms | List of equivalent naming conventions | `TEXT[]` | Yes | Array of text | `{"Ledger Bal", "Current Balance"}` | No | INTERNAL | LOW | No | No |
| `aliases` | Aliases | Shortened names or secondary system tags | `TEXT[]` | Yes | Array of text | `{"acct_bal", "bal_amt"}` | No | INTERNAL | LOW | No | No |
| `formula` | Formula | Explicit mathematical definition of term calculations | `TEXT` | Yes | Mathematical text | `ledger_balance - hold_amount` | No | INTERNAL | LOW | No | No |
| `approval_status` | Approval Status | Workflow approval state for governance auditing | `VARCHAR(30)` | No | `DRAFT`, `SUBMITTED`, `APPROVED`, `REJECTED` | `APPROVED` | No | INTERNAL | LOW | No | No |
| `lifecycle_status` | Lifecycle Status | Operational deployment status of the term | `VARCHAR(30)` | No | `ACTIVE`, `DEPRECATED`, `RETIRED` | `ACTIVE` | No | INTERNAL | LOW | No | No |
| `owner_id` | Owner ID | Business owner responsible for term accuracy | `VARCHAR(50)` | Yes | Valid `owner_id` | `OWN_FIN_RETAIL` | No | INTERNAL | LOW | No | No |
| `steward_id` | Steward ID | Data steward assigned to define the term | `VARCHAR(50)` | Yes | Valid `steward_id` | `STW_FIN_RETAIL` | No | INTERNAL | LOW | No | No |

---

### 1.5 Table: `dataset_registry`
* **Business Purpose**: Registers physical datasets (e.g., Delta tables in ADLS / OneLake) to bind them to metadata validations.

| Column Name | Business Name | Business Definition | Datatype | Nullable | Allowed Values | Sample Value | CDE | Classification | Sensitivity | Masking | Encryption |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `dataset_id` | Dataset ID | Unique physical identity string of dataset | `VARCHAR(50)` | No | Alphanumeric | `DS_RETAIL_ACCT` | No | INTERNAL | LOW | No | No |
| `dataset_name` | Dataset Name | Fully qualified physical database table name | `VARCHAR(100)` | No | Free text | `silver.retail_accounts` | No | INTERNAL | LOW | No | No |
| `data_product_id` | Data Product ID| Optional linkage to data product schema | `VARCHAR(50)` | Yes | Valid `product_id` | `DP_CUSTOMER_360` | No | INTERNAL | LOW | No | No |
| `domain_id` | Domain ID | Owner domain directory reference | `VARCHAR(50)` | No | Valid `domain_id` | `RETAIL_DEPOSITS` | No | INTERNAL | LOW | No | No |
| `physical_format` | Physical Format | Storage serialization format of the files | `VARCHAR(20)` | No | `DELTA`, `PARQUET`, `AVRO`, `CSV`, `ORC` | `DELTA` | No | INTERNAL | LOW | No | No |
| `layer` | Layer | Medallion architectural layer mapping | `VARCHAR(20)` | No | `BRONZE`, `SILVER`, `GOLD`, `SANDBOX` | `SILVER` | No | INTERNAL | LOW | No | No |
| `storage_path` | Storage Path | Complete ADLS Gen2 path / URL to directory | `VARCHAR(500)` | No | URI String | `abfss://silver@onelake.dfs.core...` | No | INTERNAL | LOW | No | No |
| `onelake_shortcut_path`| Shortcut Path | Path link inside Fabric OneLake workspace | `VARCHAR(500)` | Yes | URI String | `onelake://workspace/shortcuts/acct` | No | INTERNAL | LOW | No | No |
| `is_pii` | Is PII | Indicates presence of PII data elements | `BOOLEAN` | No | `true`, `false` | `true` | No | INTERNAL | LOW | No | No |
| `certification_status` | Certification | Logical quality tier ranking of this table | `VARCHAR(30)` | No | `BRONZE`, `SILVER`, `GOLD`, `CERTIFIED` | `CERTIFIED` | No | INTERNAL | LOW | No | No |
| `owner_id` | Owner ID | Data owner accountability key | `VARCHAR(50)` | No | Valid `owner_id` | `OWN_FIN_RETAIL` | No | INTERNAL | LOW | No | No |
| `steward_id` | Steward ID | Data steward custodian key | `VARCHAR(50)` | No | Valid `steward_id` | `STW_FIN_RETAIL` | No | INTERNAL | LOW | No | No |

---

### 1.6 Table: `column_metadata`
* **Business Purpose**: Field-by-field index of registers schema, mapping columns to classification constraints.

| Column Name | Business Name | Business Definition | Datatype | Nullable | Allowed Values | Sample Value | CDE | Classification | Sensitivity | Masking | Encryption |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `column_id` | Column ID | Unique UUID or alphanumeric index value | `VARCHAR(50)` | No | Alphanumeric | `COL_RETAIL_SSN` | Yes | CONFIDENTIAL | HIGH | Yes | Yes |
| `dataset_id` | Dataset ID | Target dataset directory pointer | `VARCHAR(50)` | No | Valid `dataset_id` | `DS_RETAIL_ACCT` | No | INTERNAL | LOW | No | No |
| `column_name` | Column Name | Physical column name in Delta table | `VARCHAR(100)` | No | Alphanumeric | `customer_ssn` | Yes | CONFIDENTIAL | HIGH | Yes | Yes |
| `business_name` | Business Name | Human-readable business name of the column | `VARCHAR(100)` | Yes | Free text | `Customer Social Security Number` | Yes | CONFIDENTIAL | HIGH | Yes | Yes |
| `data_type` | Data Type | Physical SQL datatype matching schema | `VARCHAR(50)` | No | `STRING`, `INT`, `DECIMAL`, `DATE`, etc.| `STRING` | Yes | CONFIDENTIAL | HIGH | Yes | Yes |
| `is_nullable` | Is Nullable | Can value contain SQL Null | `BOOLEAN` | No | `true`, `false` | `false` | Yes | CONFIDENTIAL | HIGH | Yes | Yes |
| `is_primary_key` | Is Primary Key| Indicates unique record identity index field | `BOOLEAN` | No | `true`, `false` | `false` | Yes | CONFIDENTIAL | HIGH | Yes | Yes |
| `is_foreign_key` | Is Foreign Key| Indicates relational join key field | `BOOLEAN` | No | `true`, `false` | `false` | Yes | CONFIDENTIAL | HIGH | Yes | Yes |
| `classification_id` | Classification | Link to security classification register | `VARCHAR(50)` | No | Valid `classification_id` | `CLASS_CONFIDENTIAL` | Yes | CONFIDENTIAL | HIGH | Yes | Yes |
| `term_id` | Term ID | link to Glossary business definition mapping | `VARCHAR(50)` | Yes | Valid `term_id` | `BT_CUST_SSN` | Yes | CONFIDENTIAL | HIGH | Yes | Yes |

---

### 1.7 Table: `critical_data_elements`
* **Business Purpose**: Flags column structures subject to audit reviews (e.g., Basel Committee compliance columns).

| Column Name | Business Name | Business Definition | Datatype | Nullable | Allowed Values | Sample Value | CDE | Classification | Sensitivity | Masking | Encryption |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `cde_id` | CDE ID | Unique audit identity key | `VARCHAR(50)` | No | Alphanumeric | `CDE_BCBS_001` | Yes | INTERNAL | LOW | No | No |
| `column_id` | Column ID | Column metadata mapping reference | `VARCHAR(50)` | No | Valid `column_id` | `COL_RETAIL_BAL` | Yes | CONFIDENTIAL | HIGH | No | No |
| `regulatory_mandate`| Mandate | Compliance rules forcing strict auditing | `VARCHAR(100)` | No | `BCBS-239`, `GDPR`, `SOX`, etc. | `BCBS-239` | Yes | INTERNAL | LOW | No | No |
| `justification` | Justification | Explanation for marking column as critical | `TEXT` | No | Free text | `Used in tier 1 Capital reports` | Yes | INTERNAL | LOW | No | No |
| `cde_status` | CDE Status | Status of critical monitoring enforcement | `VARCHAR(30)` | No | `ACTIVE`, `DEPRECATED` | `ACTIVE` | Yes | INTERNAL | LOW | No | No |

---

### 1.8 Table: `data_quality_rules`
* **Business Purpose**: Central configuration register for rule metrics dynamically executed by Spark engines.

| Column Name | Business Name | Business Definition | Datatype | Nullable | Allowed Values | Sample Value | CDE | Classification | Sensitivity | Masking | Encryption |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `rule_id` | Rule ID | Unique configuration rule identity key | `VARCHAR(50)` | No | Alphanumeric | `R_BAL_NON_NEG` | No | INTERNAL | LOW | No | No |
| `rule_name` | Rule Name | Short descriptive name of validation check | `VARCHAR(100)` | No | Free text | `Account Balance Non-Negative` | No | INTERNAL | LOW | No | No |
| `business_rule_id` | Business Rule | Logical business rule definition | `VARCHAR(50)` | Yes | Valid `business_rule_id` | `BR_BAL_092` | No | INTERNAL | LOW | No | No |
| `template_id` | Template ID | Spark validation template pointer | `VARCHAR(50)` | Yes | Valid `template_id` | `T_MIN_VAL` | No | INTERNAL | LOW | No | No |
| `group_id` | Group ID | Logical package groupings for batch runs | `VARCHAR(50)` | Yes | Valid `group_id` | `G_RETAIL_NIGHT` | No | INTERNAL | LOW | No | No |
| `column_id` | Column ID | Column subject to validation rule | `VARCHAR(50)` | No | Valid `column_id` | `COL_RETAIL_BAL` | No | INTERNAL | LOW | No | No |
| `expression_override`| SQL Override | Custom raw SQL rule bypass filter | `TEXT` | Yes | SQL expressions | `account_status <> 'CLOSED'` | No | INTERNAL | LOW | No | No |
| `rule_parameters` | Rule Parameters | Parameters parsed by Spark (e.g. thresholds)| `JSONB` | No | Valid JSON | `{"min_val": 0.00}` | No | INTERNAL | LOW | No | No |
| `severity` | Severity | Alert/Fail escalation path for run errors | `VARCHAR(20)` | No | `CRITICAL`, `WARNING`, `INFO` | `CRITICAL` | No | INTERNAL | LOW | No | No |
| `active_status` | Active Status | Flag to enable or disable rule parsing | `BOOLEAN` | No | `true`, `false` | `true` | No | INTERNAL | LOW | No | No |
| `version` | Version | Semantic version control index tracking | `VARCHAR(20)` | No | Semantic versioning | `1.1.0` | No | INTERNAL | LOW | No | No |

---

## 2. Domain: Metadata Runtime Repository (`runtime` Schema)

### 2.1 Table: `validation_run_history`
* **Business Purpose**: Tracks top-level execution metrics for validation jobs.
* **Normalization Level**: 3NF
* **Partition Strategy**: Range partition on `start_timestamp` (monthly intervals).
* **Retention Policy**: 1 year.

| Column Name | Business Name | Business Definition | Datatype | Nullable | Allowed Values | Sample Value | CDE | Classification | Sensitivity | Masking | Encryption |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `validation_run_id` | Run ID | Unique run transaction ID | `VARCHAR(50)` | No | UUID/Alphanumeric | `RUN_20260713_001` | No | INTERNAL | LOW | No | No |
| `pipeline_run_id` | Pipeline Run ID| Parent pipeline orchestrator tracking ID | `VARCHAR(50)` | No | Valid `run_id` | `PL_RUN_9823472` | No | INTERNAL | LOW | No | No |
| `dataset_id` | Dataset ID | Dataset undergoing validation | `VARCHAR(50)` | No | Valid `dataset_id` | `DS_RETAIL_ACCT` | No | INTERNAL | LOW | No | No |
| `execution_engine` | Engine Type | Running execution framework engine type | `VARCHAR(20)` | No | `PYSPARK`, `DBT` | `PYSPARK` | No | INTERNAL | LOW | No | No |
| `total_records_processed`| Total Processed | Count of records scanned in table | `BIGINT` | No | `>= 0` | `15000000` | No | INTERNAL | LOW | No | No |
| `passed_records_count` | Records Passed | Count of clean rows passing checks | `BIGINT` | No | `>= 0` | `14999850` | No | INTERNAL | LOW | No | No |
| `failed_records_count` | Records Failed | Count of rows failing validation checks | `BIGINT` | No | `>= 0` | `150` | No | INTERNAL | LOW | No | No |
| `start_timestamp` | Start Time | Epoch timestamp of execution launch | `TIMESTAMPTZ`| No | Date-Time | `2026-07-13 13:00:00+00`| No | INTERNAL | LOW | No | No |
| `end_timestamp` | End Time | Epoch timestamp of validation termination | `TIMESTAMPTZ`| Yes | Date-Time | `2026-07-13 13:05:22+00`| No | INTERNAL | LOW | No | No |
| `status` | Run Status | Terminal exit state of run execution | `VARCHAR(30)` | No | `RUNNING`, `COMPLETED`, `FAILED` | `COMPLETED` | No | INTERNAL | LOW | No | No |

---

### 2.2 Table: `exception_repository`
* **Business Purpose**: Central repository mapping quarantined records to steward remediation workflows.
* **Normalization Level**: 3NF
* **Partition Strategy**: Hash partition on `remediation_status`.
* **Retention Policy**: 7 years (regulatory audit trail for banking migration adjustments).

| Column Name | Business Name | Business Definition | Datatype | Nullable | Allowed Values | Sample Value | CDE | Classification | Sensitivity | Masking | Encryption |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `exception_id` | Exception ID | Autoincrement surrogate primary key | `BIGINT` | No | Integers | `540938` | No | INTERNAL | LOW | No | No |
| `validation_run_id` | Validation Run ID| Validation run audit link | `VARCHAR(50)` | No | Valid `validation_run_id`| `RUN_20260713_001` | No | INTERNAL | LOW | No | No |
| `rule_id` | Rule ID | Failed validation rule identifier | `VARCHAR(50)` | No | Valid `rule_id` | `R_BAL_NON_NEG` | No | INTERNAL | LOW | No | No |
| `quarantine_table_fqn`| Quarantine Path | Delta table location housing failed rows | `VARCHAR(255)` | No | Path string | `quarantine.err_retail_acct` | No | INTERNAL | LOW | No | No |
| `record_natural_key` | Natural Key | Unique business key of row (e.g. Account No) | `VARCHAR(255)` | No | Free text | `ACC_9082348` | No | INTERNAL | LOW | No | No |
| `failed_column_name` | Column Name | Column containing invalid value | `VARCHAR(100)` | No | Alphanumeric | `account_balance` | No | INTERNAL | LOW | No | No |
| `invalid_value` | Invalid Value | Value string that caused validation failure | `TEXT` | Yes | Free text | `-1500.45` | Yes | CONFIDENTIAL | HIGH | No | No |
| `remediation_status` | Status | Steward investigation status | `VARCHAR(30)` | No | `OPEN`, `RESOLVED`, `CLOSED` | `OPEN` | No | INTERNAL | LOW | No | No |
| `data_steward_notes` | Notes | Audit log text written by investigating steward| `TEXT` | Yes | Free text | `Negative balance caused by ledger test`| No | INTERNAL | LOW | No | No |

---

## 3. Domain: Metadata Security Repository (`security` Schema)

### 3.1 Table: `masking_policies`
* **Business Purpose**: Encapsulates data masking logic for dynamic execution in database views.

| Column Name | Business Name | Business Definition | Datatype | Nullable | Allowed Values | Sample Value | CDE | Classification | Sensitivity | Masking | Encryption |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `masking_policy_id` | Policy ID | Alphanumeric key of masking strategy | `VARCHAR(50)` | No | Alphanumeric | `MSK_SSN_LAST4` | No | INTERNAL | LOW | No | No |
| `policy_name` | Policy Name | Descriptive name of mask policy | `VARCHAR(100)` | No | Free text | `SSN Last 4 Masking` | No | INTERNAL | LOW | No | No |
| `masking_type` | Masking Type | Mask methodology executed by system | `VARCHAR(30)` | No | `REDACT`, `HASH_SHA256`, `PARTIAL_MASK` | `PARTIAL_MASK` | No | INTERNAL | LOW | No | No |
| `masking_expression` | Expression | Logical masking formula parsed in views | `TEXT` | No | Free text | `concat('***-**-', substr(val, 8,4))` | No | INTERNAL | LOW | No | No |

---

### 3.2 Table: `encryption_policies`
* **Business Purpose**: Encrypts sensitive target columns using designated algorithms and vaults.

| Column Name | Business Name | Business Definition | Datatype | Nullable | Allowed Values | Sample Value | CDE | Classification | Sensitivity | Masking | Encryption |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `encryption_policy_id`| Policy ID | Alphanumeric encryption key pointer | `VARCHAR(50)` | No | Alphanumeric | `ENC_AES256` | No | INTERNAL | LOW | No | No |
| `policy_name` | Policy Name | Name of the encryption control | `VARCHAR(100)` | No | Free text | `PII AES-256 Tokenization` | No | INTERNAL | LOW | No | No |
| `encryption_algorithm`| Algorithm | Cryptographic standard used | `VARCHAR(50)` | No | `AES_256_GCM`, `FPE_AES_256` | `AES_256_GCM` | No | INTERNAL | LOW | No | No |
| `key_vault_reference_id`| Vault Key URI | Logical reference path to KMS secret URI | `VARCHAR(150)` | No | Key Vault URI | `vault://prod/keys/db-crypt-key`| No | INTERNAL | LOW | No | No |

---

## 4. Domain: Metadata Reference Repository (`reference` Schema)

### 4.1 Table: `currencies`
* **Business Purpose**: Global list of ISO currencies used to validate financial values.

| Column Name | Business Name | Business Definition | Datatype | Nullable | Allowed Values | Sample Value | CDE | Classification | Sensitivity | Masking | Encryption |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `currency_code` | Currency Code | ISO 4217 standard alpha currency code | `CHAR(3)` | No | `^[A-Z]{3}$` | `USD` | No | PUBLIC | LOW | No | No |
| `currency_name` | Currency Name | Name of the legal currency | `VARCHAR(100)` | No | Free text | `United States Dollar` | No | PUBLIC | LOW | No | No |
| `symbol` | Symbol | Short typographic representation | `VARCHAR(10)` | Yes | Free text | `$` | No | PUBLIC | LOW | No | No |
| `decimal_places` | Decimals | Number of fractional values allowed in ledger | `INT` | No | `0`, `2`, `3`, `4` | `2` | No | PUBLIC | LOW | No | No |

---

## 5. Domain: Metadata Audit Repository (`audit` Schema)

### 5.1 Table: `metadata_changes`
* **Business Purpose**: Compliance audit trail showing prior and new states of rules and schemas.
* **Normalization Level**: 3NF
* **Partition Strategy**: Range partition on `modified_at` (quarterly intervals).
* **Retention Policy**: Indefinite (Non-deletable compliance logging).

| Column Name | Business Name | Business Definition | Datatype | Nullable | Allowed Values | Sample Value | CDE | Classification | Sensitivity | Masking | Encryption |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `change_id` | Change ID | Auto-increment sequence identifier | `BIGINT` | No | Integers | `49203` | No | INTERNAL | LOW | No | No |
| `request_id` | Request ID | Reference ticket ID enabling change | `VARCHAR(50)` | Yes | Valid `request_id` | `REQ_98234` | No | INTERNAL | LOW | No | No |
| `target_table` | Target Table | Target metadata table modified | `VARCHAR(100)` | No | Alphanumeric | `master.data_quality_rules` | No | INTERNAL | LOW | No | No |
| `primary_key_val` | PK Value | Value of key identifier modified | `VARCHAR(100)` | No | Free text | `R_BAL_NON_NEG` | No | INTERNAL | LOW | No | No |
| `operation_type` | Operation Type| SQL operation type performed | `VARCHAR(20)` | No | `INSERT`, `UPDATE`, `DELETE` | `UPDATE` | No | INTERNAL | LOW | No | No |
| `pre_change_state` | Old JSON | JSON dump of record before modification | `JSONB` | Yes | Valid JSON | `{"active_status": false}` | No | INTERNAL | LOW | No | No |
| `post_change_state` | New JSON | JSON dump of record after modification | `JSONB` | Yes | Valid JSON | `{"active_status": true}` | No | INTERNAL | LOW | No | No |
| `modified_by` | Modified By | Corporate email/username of operator | `VARCHAR(100)` | No | Free text | `admin@bank.com` | No | INTERNAL | LOW | No | No |
| `modified_at` | Modified At | Epoch timestamp of modification | `TIMESTAMPTZ`| No | Date-time | `2026-07-13 13:10:00+00`| No | INTERNAL | LOW | No | No |
