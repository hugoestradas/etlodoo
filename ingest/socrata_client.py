import os
import time
import requests
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SocrataClient:
    """Client for fetching data from USAC's Socrata API with pagination and retries."""
    
    BASE_URL = "https://opendata.usac.org/resource"
    PAGE_SIZE = 50000
    MAX_RETRIES = 5
    INITIAL_RETRY_DELAY = 1.0
    
    def __init__(self, app_token: str = None):
        self.app_token = app_token or os.getenv("SOCRATA_APP_TOKEN")
        self.session = requests.Session()
        if self.app_token:
            self.session.headers.update({"X-App-Token": self.app_token})
    
    def fetch_all(
        self,
        resource_id: str,
        min_funding_year: int = None,
        select: str = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all records for a resource with pagination.
        
        Args:
            resource_id: Socrata resource ID
            min_funding_year: Minimum funding year to filter (filtered in Python, not API)
            select: Optional SoQL select clause (e.g., "count(*)")
        
        Returns:
            List of records
        """
        offset = 0
        all_records = []
        
        while True:
            params = {
                "$limit": self.PAGE_SIZE,
                "$offset": offset,
                "$order": ":id"
            }
            if select:
                params["$select"] = select
            
            records = self._fetch_with_retry(resource_id, params)
            
            if not records:
                break
            
            all_records.extend(records)
            
            if len(records) < self.PAGE_SIZE:
                break
            
            offset += self.PAGE_SIZE
            logger.info(f"Fetched {len(all_records)} records so far...")
        
        # Filter by funding_year in Python (API doesn't support $where clause)
        if min_funding_year:
            filtered_records = [
                r for r in all_records 
                if r.get('funding_year') and int(r['funding_year']) >= min_funding_year
            ]
            logger.info(f"Filtered to {len(filtered_records)} records (funding_year >= {min_funding_year})")
            return filtered_records
        
        logger.info(f"Total records fetched: {len(all_records)}")
        return all_records
    
    def _fetch_with_retry(
        self,
        resource_id: str,
        params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Fetch with exponential backoff retry logic."""
        url = f"{self.BASE_URL}/{resource_id}.json"
        retry_delay = self.INITIAL_RETRY_DELAY
        
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.session.get(url, params=params, timeout=60)
                response.raise_for_status()
                
                data = response.json()
                
                # Handle count(*) queries which return a single dict
                if isinstance(data, dict):
                    return [data]
                return data
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code in (429, 500, 502, 503, 504):
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.MAX_RETRIES} failed: {e}. "
                        f"Retrying in {retry_delay}s..."
                    )
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise
            except (requests.exceptions.RequestException, ValueError) as e:
                logger.warning(
                    f"Attempt {attempt + 1}/{self.MAX_RETRIES} failed: {e}. "
                    f"Retrying in {retry_delay}s..."
                )
                time.sleep(retry_delay)
                retry_delay *= 2
        
        raise Exception(f"Max retries exceeded for {url}")
