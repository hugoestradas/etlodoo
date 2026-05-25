import os
import duckdb
import pandas as pd
from typing import List, Dict, Any
import logging

from .socrata_client import SocrataClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataLoader:
    """Load data from Socrata API into DuckDB with idempotency."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.client = SocrataClient()
    
    def load_basic_info(self, min_funding_year: int) -> None:
        """Load Basic Information data into raw_basic table."""
        logger.info("Loading Basic Information data...")
        
        records = self.client.fetch_all("jp7a-89nd", min_funding_year)
        
        if not records:
            logger.warning("No Basic Information records found")
            return
        
        df = pd.DataFrame(records)
        
        con = duckdb.connect(self.db_path)
        try:
            # Register the dataframe
            con.register("basic_df", df)
            
            # Check if table exists and get existing funding years
            table_exists = con.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = 'raw_basic'
            """).fetchone()[0] > 0
            
            if table_exists:
                # Idempotent: delete existing data for these funding years
                funding_years = df["funding_year"].unique()
                funding_years_list = funding_years.tolist()
                con.execute(f"""
                    DELETE FROM raw_basic 
                    WHERE funding_year IN ({','.join(map(str, funding_years_list))})
                """)
                con.execute("""
                    INSERT INTO raw_basic 
                    SELECT * FROM basic_df
                """)
            else:
                # Create table from dataframe
                con.execute("""
                    CREATE TABLE raw_basic AS 
                    SELECT * FROM basic_df
                """)
            
            logger.info(f"Loaded {len(df)} rows into raw_basic")
        finally:
            con.close()
    
    def load_services_requested(self, min_funding_year: int) -> None:
        """Load Services Requested data into raw_services table."""
        logger.info("Loading Services Requested data...")
        
        records = self.client.fetch_all("39tn-hjzv", min_funding_year)
        
        if not records:
            logger.warning("No Services Requested records found")
            return
        
        df = pd.DataFrame(records)
        
        con = duckdb.connect(self.db_path)
        try:
            # Register the dataframe
            con.register("services_df", df)
            
            # Check if table exists
            table_exists = con.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = 'raw_services'
            """).fetchone()[0] > 0
            
            if table_exists:
                # Idempotent: delete existing data for these funding years
                funding_years = df["funding_year"].unique()
                funding_years_list = funding_years.tolist()
                con.execute(f"""
                    DELETE FROM raw_services 
                    WHERE funding_year IN ({','.join(map(str, funding_years_list))})
                """)
                con.execute("""
                    INSERT INTO raw_services 
                    SELECT * FROM services_df
                """)
            else:
                # Create table from dataframe
                con.execute("""
                    CREATE TABLE raw_services AS 
                    SELECT * FROM services_df
                """)
            
            logger.info(f"Loaded {len(df)} rows into raw_services")
        finally:
            con.close()
    
    def initialize_db(self) -> None:
        """Initialize database with raw tables if they don't exist."""
        # Tables are created automatically with CREATE OR REPLACE in load methods
        # This method is kept for future initialization needs
        logger.info("Database initialization handled in load methods")
