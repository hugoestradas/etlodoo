-- Staging layer for Services Requested
-- Handles type casting
-- Note: We do NOT deduplicate by form_version here because:
-- 1. Services are line items that should be preserved for analysis
-- 2. The join to stg_basic (which is deduplicated) handles the relationship
-- 3. For amendment analysis, we need to see services across all versions

CREATE OR REPLACE TABLE stg_services AS
SELECT
    application_number,
    CAST(funding_year AS INTEGER) AS funding_year,
    service_category,
    service_type,
    function,
    entities,
    quantity,
    unit,
    installation_initial_configuration,
    manufacturer,
    rfp_identifier,
    form_version
FROM raw_services;
