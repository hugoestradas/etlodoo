#!/usr/bin/env python3
"""
E-Rate FCC Form 470 Data Pipeline
Orchestrates the entire pipeline: ingest -> model -> test -> analyze
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from ingest.loader import DataLoader
from analysis import Analyzer
from tests.run_tests import run_data_quality_checks

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_models(db_path: str):
    """Run SQL models to create staging and mart layers."""
    import duckdb
    
    logger.info("Running SQL models...")
    
    model_files = [
        "models/stg_basic.sql",
        "models/stg_services.sql",
        "models/mart_form_470.sql"
    ]
    
    con = duckdb.connect(db_path)
    try:
        for model_file in model_files:
            logger.info(f"Running {model_file}...")
            with open(model_file, "r") as f:
                sql = f.read()
            con.execute(sql)
            logger.info(f"Completed {model_file}")
    finally:
        con.close()
    
    logger.info("All models completed successfully")


def main():
    """Main orchestration function."""
    
    # Get configuration
    db_path = os.getenv("DATABASE_URL", "./data/erate.duckdb")
    min_funding_year = int(os.getenv("MIN_FUNDING_YEAR", "2024"))
    
    # Ensure data directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    logger.info("="*80)
    logger.info("E-RATE FCC FORM 470 DATA PIPELINE")
    logger.info("="*80)
    logger.info(f"Database: {db_path}")
    logger.info(f"Min Funding Year: {min_funding_year}")
    logger.info("")
    
    try:
        # Step 1: Ingest
        logger.info("STEP 1: INGESTION")
        logger.info("-"*80)
        loader = DataLoader(db_path)
        loader.initialize_db()
        loader.load_basic_info(min_funding_year)
        loader.load_services_requested(min_funding_year)
        logger.info("Ingestion completed successfully")
        logger.info("")
        
        # Step 2: Model
        logger.info("STEP 2: MODELING")
        logger.info("-"*80)
        run_models(db_path)
        logger.info("")
        
        # Step 3: Test
        logger.info("STEP 3: DATA QUALITY TESTS")
        logger.info("-"*80)
        tests_passed = run_data_quality_checks(db_path)
        if not tests_passed:
            logger.error("Data quality tests failed. Aborting.")
            sys.exit(1)
        logger.info("")
        
        # Step 4: Analyze
        logger.info("STEP 4: ANALYTICAL QUESTIONS")
        logger.info("-"*80)
        analyzer = Analyzer(db_path)
        analyzer.run_all()
        logger.info("")
        
        logger.info("="*80)
        logger.info("PIPELINE COMPLETED SUCCESSFULLY")
        logger.info("="*80)
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
