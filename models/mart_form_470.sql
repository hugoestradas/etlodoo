-- Analytical mart: joins Basic Information with Services Requested
-- This is the primary table for answering analytical questions
-- Uses stg_basic (deduplicated) as the base to avoid double-counting applications

CREATE OR REPLACE TABLE mart_form_470 AS
SELECT
    b.application_number,
    b.funding_year,
    b.form_nickname,
    b.f470_status,
    b.billed_entity_name,
    b.billed_entity_state,
    b.applicant_type,
    b.organization_type,
    b.latitude,
    b.longitude,
    b.number_of_eligible_entities,
    b.form_version,
    s.service_category,
    s.service_type,
    s.function,
    s.entities,
    s.quantity,
    s.unit,
    s.manufacturer
FROM stg_basic b
LEFT JOIN stg_services s 
    ON b.application_number = s.application_number 
    AND b.funding_year = s.funding_year;
