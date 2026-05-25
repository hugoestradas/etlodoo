-- Staging layer for Basic Information
-- Handles type casting and form_version deduplication
-- For application-level questions, we keep ONE row per application:
-- - 'Current' version when present
-- - 'Original' version when 'Current' is not present
-- This prevents double-counting applications that have been amended

CREATE OR REPLACE TABLE stg_basic AS
WITH ranked AS (
    SELECT
        *,
        -- Rank form_version within each application_number
        -- 'Current' gets rank 1, 'Original' gets rank 2, others get rank 3
        ROW_NUMBER() OVER (
            PARTITION BY application_number 
            ORDER BY 
                CASE 
                    WHEN form_version = 'Current' THEN 1
                    WHEN form_version = 'Original' THEN 2
                    ELSE 3
                END
        ) as version_rank
    FROM raw_basic
)
SELECT
    application_number,
    form_nickname,
    CAST(funding_year AS INTEGER) AS funding_year,
    f470_status,
    allowable_contract_date,
    created_datetime,
    created_by,
    certified_datetime,
    certified_by,
    last_modified_datetime,
    last_modified_by,
    ben,
    billed_entity_name,
    organization_status,
    organization_type,
    applicant_type,
    website_url,
    latitude,
    longitude,
    ben_fcc_registration_number,
    billed_entity_address1,
    billed_entity_address2,
    billed_entity_city,
    billed_entity_state,
    billed_entity_zip,
    billed_entity_email,
    billed_entity_phone,
    number_of_eligible_entities,
    contact_name,
    contact_address1,
    contact_city,
    contact_state,
    contact_zip,
    contact_phone,
    contact_email,
    technical_contact_name,
    technical_contact_title,
    technical_contact_phone,
    technical_contact_email,
    authorized_person_name,
    authorized_person_address,
    authorized_person_city,
    authorized_person_state,
    authorized_person_zip,
    authorized_person_phone,
    authorized_person_email,
    authorized_person_title,
    authorized_person_employer,
    category_one_description,
    rfp_identifier,
    state_or_local_restrictions,
    all_public_schools_districts,
    all_non_public_schools,
    all_libraries,
    form_version
FROM ranked
WHERE version_rank = 1;
