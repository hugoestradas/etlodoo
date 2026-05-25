-- Data Quality Checks
-- These checks verify critical data integrity assumptions
-- Returns results that should be reviewed after each run

-- Check 1: Primary Key uniqueness in stg_basic
-- After deduplication, application_number should be unique
-- If this fails, the form_version dedup logic has a bug
SELECT
    'stg_basic_pk_uniqueness' AS check_name,
    COUNT(*) AS duplicate_count,
    CASE 
        WHEN COUNT(*) = 0 THEN 'PASS'
        ELSE 'FAIL'
    END AS status
FROM (
    SELECT application_number, COUNT(*) as cnt
    FROM stg_basic
    GROUP BY application_number
    HAVING COUNT(*) > 1
) duplicates;

-- Check 2: Referential integrity between stg_basic and stg_services
-- All services should have a matching basic info record
-- If this fails, there are orphaned service records
SELECT
    'referential_integrity' AS check_name,
    COUNT(*) AS orphaned_services_count,
    CASE 
        WHEN COUNT(*) = 0 THEN 'PASS'
        ELSE 'FAIL'
    END AS status
FROM stg_services s
LEFT JOIN stg_basic b 
    ON s.application_number = b.application_number 
    AND s.funding_year = b.funding_year
WHERE b.application_number IS NULL;

-- Check 3: Null rate on critical columns
-- application_number and funding_year should never be null
SELECT
    'critical_nulls' AS check_name,
    SUM(CASE WHEN application_number IS NULL THEN 1 ELSE 0 END) AS null_application_numbers,
    SUM(CASE WHEN funding_year IS NULL THEN 1 ELSE 0 END) AS null_funding_years,
    CASE 
        WHEN SUM(CASE WHEN application_number IS NULL THEN 1 ELSE 0 END) = 0 
         AND SUM(CASE WHEN funding_year IS NULL THEN 1 ELSE 0 END) = 0 
        THEN 'PASS'
        ELSE 'FAIL'
    END AS status
FROM stg_basic;

-- Check 4: form_version distribution sanity check
-- We expect mostly 'Original' and 'Current' versions
-- A high count of other versions might indicate data issues
SELECT
    'form_version_distribution' AS check_name,
    form_version,
    COUNT(*) AS count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage
FROM raw_basic
GROUP BY form_version
ORDER BY count DESC;
