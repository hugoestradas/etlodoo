import duckdb
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_data_quality_checks(db_path: str) -> bool:
    """Run data quality checks and report results."""
    
    # Read SQL file
    with open("tests/data_quality.sql", "r") as f:
        sql = f.read()
    
    con = duckdb.connect(db_path)
    
    try:
        # Split by SELECT statements (simple approach)
        statements = [s.strip() for s in sql.split(";") if s.strip()]
        
        all_passed = True
        
        for stmt in statements:
            if not stmt.upper().startswith("SELECT"):
                continue
            
            logger.info(f"Running check: {stmt[:50]}...")
            result = con.execute(stmt).fetchdf()
            
            print("\n" + "="*60)
            print(result.to_string(index=False))
            print("="*60 + "\n")
            
            # Check if any FAIL status
            if "status" in result.columns:
                if "FAIL" in result["status"].values:
                    all_passed = False
                    logger.error("Check FAILED!")
                else:
                    logger.info("Check PASSED")
        
        if all_passed:
            logger.info("All data quality checks PASSED")
            return True
        else:
            logger.error("Some data quality checks FAILED")
            return False
            
    finally:
        con.close()


if __name__ == "__main__":
    db_path = os.getenv("DATABASE_URL", "./data/erate.duckdb")
    
    if not os.path.exists(db_path):
        logger.error(f"Database not found at {db_path}")
        sys.exit(1)
    
    success = run_data_quality_checks(db_path)
    sys.exit(0 if success else 1)
