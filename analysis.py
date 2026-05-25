import duckdb
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Analyzer:
    """Run analytical queries against the mart layer."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def run_all(self):
        """Run all analytical questions and print results."""
        
        print("\n" + "="*80)
        print("ANALYTICAL QUESTIONS")
        print("="*80 + "\n")
        
        self.q1_volume_by_funding_year()
        self.q2_top_service_types()
        self.q3_category_comparison()
        self.q4_geography()
        self.q5_amendment_rate()
        self.q6_top_billed_entities()
    
    def q1_volume_by_funding_year(self):
        """
        Q1: Volume by funding year
        How many UNIQUE Form 470 applications per year and the average number of line items per application.
        
        form_version handling: Uses stg_basic which deduplicates to ONE row per application
        (Current when present, otherwise Original), so no double-counting.
        """
        print("\nQ1: Volume by Funding Year")
        print("-" * 80)
        print("form_version handling: Uses stg_basic (deduplicated: Current > Original)")
        print()
        
        sql = """
        SELECT
            funding_year,
            COUNT(DISTINCT application_number) AS unique_applications,
            ROUND(AVG(line_item_count), 2) AS avg_line_items_per_application
        FROM (
            SELECT
                b.application_number,
                b.funding_year,
                COUNT(s.application_number) AS line_item_count
            FROM stg_basic b
            LEFT JOIN stg_services s 
                ON b.application_number = s.application_number 
                AND b.funding_year = s.funding_year
            GROUP BY b.application_number, b.funding_year
        ) app_counts
        GROUP BY funding_year
        ORDER BY funding_year DESC
        """
        
        con = duckdb.connect(self.db_path)
        try:
            result = con.execute(sql).fetchdf()
            print(result.to_string(index=False))
        finally:
            con.close()
    
    def q2_top_service_types(self):
        """
        Q2: Top 10 most-requested service types in the most recent funding year.
        
        form_version handling: Uses mart_form_470 which joins to stg_basic (deduplicated),
        so each application is counted once regardless of amendments.
        """
        print("\nQ2: Top 10 Service Types (Most Recent Funding Year)")
        print("-" * 80)
        print("form_version handling: Uses mart_form_470 (stg_basic deduplicated)")
        print()
        
        sql = """
        WITH latest_year AS (
            SELECT MAX(funding_year) AS max_year FROM stg_basic
        )
        SELECT
            service_type,
            COUNT(*) AS request_count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage
        FROM mart_form_470, latest_year
        WHERE funding_year = latest_year.max_year
            AND service_type IS NOT NULL
        GROUP BY service_type
        ORDER BY request_count DESC
        LIMIT 10
        """
        
        con = duckdb.connect(self.db_path)
        try:
            result = con.execute(sql).fetchdf()
            print(result.to_string(index=False))
        finally:
            con.close()
    
    def q3_category_comparison(self):
        """
        Q3: Category One vs Category Two comparison by funding year.
        
        form_version handling: Uses stg_basic (deduplicated) to avoid double-counting applications.
        """
        print("\nQ3: Category One vs Category Two by Funding Year")
        print("-" * 80)
        print("form_version handling: Uses stg_basic (deduplicated)")
        print()
        
        sql = """
        SELECT
            funding_year,
            SUM(CASE WHEN service_category = 'Category 1' THEN 1 ELSE 0 END) AS category_one_count,
            SUM(CASE WHEN service_category = 'Category 2' THEN 1 ELSE 0 END) AS category_two_count,
            ROUND(
                SUM(CASE WHEN service_category = 'Category 1' THEN 1 ELSE 0 END) * 100.0 / 
                NULLIF(SUM(CASE WHEN service_category IN ('Category 1', 'Category 2') THEN 1 ELSE 0 END), 0), 
                2
            ) AS category_one_pct,
            ROUND(
                SUM(CASE WHEN service_category = 'Category 2' THEN 1 ELSE 0 END) * 100.0 / 
                NULLIF(SUM(CASE WHEN service_category IN ('Category 1', 'Category 2') THEN 1 ELSE 0 END), 0), 
                2
            ) AS category_two_pct
        FROM mart_form_470
        WHERE service_category IN ('Category 1', 'Category 2')
        GROUP BY funding_year
        ORDER BY funding_year DESC
        """
        
        con = duckdb.connect(self.db_path)
        try:
            result = con.execute(sql).fetchdf()
            print(result.to_string(index=False))
        finally:
            con.close()
    
    def q4_geography(self):
        """
        Q4: Top 10 states by number of filings.
        
        form_version handling: Uses stg_basic (deduplicated) to count each application once.
        Data quality issues identified:
        1. form_version deduplication - handled in stg_basic
        2. NULL state codes - some applications have missing state information
        """
        print("\nQ4: Top 10 States by Number of Filings")
        print("-" * 80)
        print("form_version handling: Uses stg_basic (deduplicated)")
        print("Data quality issues: 1) form_version dedup, 2) NULL state codes")
        print()
        
        sql = """
        SELECT
            billed_entity_state,
            COUNT(DISTINCT application_number) AS application_count
        FROM stg_basic
        WHERE billed_entity_state IS NOT NULL
        GROUP BY billed_entity_state
        ORDER BY application_count DESC
        LIMIT 10
        """
        
        con = duckdb.connect(self.db_path)
        try:
            result = con.execute(sql).fetchdf()
            print(result.to_string(index=False))
            
            # Show data quality issue: NULL states
            print("\nData Quality Issue: NULL State Codes")
            print("-" * 40)
            null_check_sql = """
            SELECT
                COUNT(*) AS applications_with_null_state,
                ROUND(COUNT(*) * 100.0 / COUNT(*), 2) AS percentage
            FROM stg_basic
            WHERE billed_entity_state IS NULL
            """
            null_result = con.execute(null_check_sql).fetchdf()
            print(null_result.to_string(index=False))
            
        finally:
            con.close()
    
    def q5_amendment_rate(self):
        """
        Q5: Amendment rate - % of applications that have both an Original and a Current row.
        
        form_version handling: Uses raw_basic (NOT deduplicated) to count both versions.
        We need both versions to calculate the amendment rate.
        """
        print("\nQ5: Amendment Rate (Applications with Both Original and Current)")
        print("-" * 80)
        print("form_version handling: Uses raw_basic (keeps both Original and Current)")
        print("Reason: Need both versions to calculate amendment rate")
        print()
        
        sql = """
        WITH version_counts AS (
            SELECT
                application_number,
                funding_year,
                COUNT(CASE WHEN form_version = 'Original' THEN 1 END) AS has_original,
                COUNT(CASE WHEN form_version = 'Current' THEN 1 END) AS has_current
            FROM raw_basic
            GROUP BY application_number, funding_year
        )
        SELECT
            funding_year,
            COUNT(*) AS total_applications,
            SUM(CASE WHEN has_original > 0 AND has_current > 0 THEN 1 ELSE 0 END) AS amended_applications,
            ROUND(
                SUM(CASE WHEN has_original > 0 AND has_current > 0 THEN 1 ELSE 0 END) * 100.0 / 
                NULLIF(COUNT(*), 0), 
                2
            ) AS amendment_rate_pct
        FROM version_counts
        GROUP BY funding_year
        ORDER BY funding_year DESC
        """
        
        con = duckdb.connect(self.db_path)
        try:
            result = con.execute(sql).fetchdf()
            print(result.to_string(index=False))
        finally:
            con.close()
    
    def q6_top_billed_entities(self):
        """
        Q6: Top 10 billed entities by total line items in the most recent year.
        
        form_version handling: Uses mart_form_470 (stg_basic deduplicated) to count
        each application once per entity.
        """
        print("\nQ6: Top 10 Billed Entities by Total Line Items (Most Recent Year)")
        print("-" * 80)
        print("form_version handling: Uses mart_form_470 (stg_basic deduplicated)")
        print()
        
        sql = """
        WITH latest_year AS (
            SELECT MAX(funding_year) AS max_year FROM stg_basic
        )
        SELECT
            billed_entity_name,
            billed_entity_state,
            COUNT(service_type) AS total_line_items
        FROM mart_form_470, latest_year
        WHERE funding_year = latest_year.max_year
            AND billed_entity_name IS NOT NULL
        GROUP BY billed_entity_name, billed_entity_state
        ORDER BY total_line_items DESC
        LIMIT 10
        """
        
        con = duckdb.connect(self.db_path)
        try:
            result = con.execute(sql).fetchdf()
            print(result.to_string(index=False))
        finally:
            con.close()


if __name__ == "__main__":
    db_path = os.getenv("DATABASE_URL", "./data/erate.duckdb")
    
    if not os.path.exists(db_path):
        logger.error(f"Database not found at {db_path}")
        exit(1)
    
    analyzer = Analyzer(db_path)
    analyzer.run_all()
