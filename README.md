# FCC Form 470 Data Pipeline

A production-minded data pipeline for ingesting, modeling, and analyzing E-Rate FCC Form 470 data from USAC's Socrata API.

## Stack

- **Python 3.11+**
- **DuckDB** (local file storage)
- **Requests** (HTTP client with retries)
- **Pandas** (data manipulation)
- **python-dotenv** (configuration management)

## Architecture

The pipeline follows a layered architecture in DuckDB:

1. **raw_* tables**: Exact data as received from the API (raw_basic, raw_services)
2. **stg_* tables**: Cleaning, type casting, and form_version deduplication logic
3. **mart_* tables**: Analytical layer joining both datasets for easy querying

## Setup

1. Clone or navigate to the project directory
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env to set MIN_FUNDING_YEAR (default: 2024)
   # SOCRATA_APP_TOKEN is optional (API is anonymous)
   ```

## Run the Pipeline

Single command to run everything end-to-end:

```bash
python main.py
```

This will:
1. Ingest data from USAC's Socrata API (with pagination and retries)
2. Load into raw_* tables in DuckDB (idempotent)
3. Build stg_* and mart_* models
4. Run data quality checks
5. Execute analytical queries and print results

## Configuration

Edit `.env` to customize:

- `MIN_FUNDING_YEAR`: Minimum funding year to ingest (default: 2024)
- `DATABASE_URL`: Path to DuckDB database file (default: ./data/erate.duckdb)
- `SOCRATA_APP_TOKEN`: Optional Socrata app token for higher rate limits

**Note**: By default, the pipeline ingests only the last 2 funding years (configurable via MIN_FUNDING_YEAR). The pipeline is designed to handle the full dataset if needed.

## Data Quality Checks

The pipeline automatically runs these checks after modeling:

1. **Primary Key Uniqueness**: Verifies stg_basic has unique application_number (form_version dedup)
2. **Referential Integrity**: Ensures all services have matching basic info records
3. **Critical Nulls**: Checks for NULL application_number or funding_year
4. **Form Version Distribution**: Reports distribution of form_version values

The pipeline will fail if critical checks do not pass.

## Analytical Questions & Results

The pipeline answers 6 analytical questions. Results are printed after a successful run.

### Q1: Volume by Funding Year
How many UNIQUE Form 470 applications per year and the average number of line items per application.

**form_version handling**: Uses stg_basic which deduplicates to ONE row per application (Current when present, otherwise Original).

| funding_year | unique_applications | avg_line_items_per_application |
|--------------|---------------------|--------------------------------|
| 2026         | 23,704              | 10.33                          |
| 2025         | 23,767              | 9.09                           |
| 2024         | 22,932              | 8.31                           |

### Q2: Top 10 Service Types
Top 10 most-requested service types in the most recent funding year.

**form_version handling**: Uses mart_form_470 which joins to stg_basic (deduplicated).

| service_type                                | request_count | percentage |
|---------------------------------------------|---------------|------------|
| Internal Connections                        | 118,929       | 48.56%     |
| Basic Maintenance Of Internal Connections   | 79,627        | 32.51%     |
| Data Transmission And/Or Internet Access    | 31,482        | 12.85%     |
| Managed Internal Broadband Services         | 14,885        | 6.08%      |

### Q3: Category Comparison
Category One (data/internet) vs Category Two (internal connections / managed broadband / basic maintenance) comparison by funding year.

**form_version handling**: Uses stg_basic (deduplicated) to avoid double-counting.

| funding_year | category_one_count | category_two_count | category_one_pct | category_two_pct |
|--------------|-------------------|-------------------|------------------|------------------|
| 2026         | 31,482            | 213,441           | 12.85%           | 87.15%           |
| 2025         | 36,080            | 180,004           | 16.70%           | 83.30%           |
| 2024         | 37,697            | 152,942           | 19.77%           | 80.23%           |

### Q4: Geography
Top 10 states by number of filings.

**form_version handling**: Uses stg_basic (deduplicated).

**Data quality issues identified**:
1. form_version deduplication (handled in stg_basic)
2. NULL state codes (0 applications with NULL state in current dataset)

| billed_entity_state | application_count |
|---------------------|-------------------|
| CA                  | 5,154             |
| NY                  | 4,694             |
| IL                  | 4,593             |
| TX                  | 4,457             |
| OH                  | 3,742             |
| MI                  | 2,839             |
| NJ                  | 2,747             |
| WI                  | 2,636             |
| FL                  | 2,559             |
| IA                  | 2,305             |

### Q5: Amendment Rate
Percentage of applications that have both an Original and a Current row.

**form_version handling**: Uses raw_basic (NOT deduplicated) to count both versions. This is necessary to calculate the amendment rate.

| funding_year | total_applications | amended_applications | amendment_rate_pct |
|--------------|-------------------|----------------------|-------------------|
| 2026         | 23,704            | 4,217                | 17.79%            |
| 2025         | 23,767            | 4,151                | 17.47%            |
| 2024         | 22,932            | 4,044                | 17.63%            |

### Q6: Top Billed Entities
Top 10 billed entities by total line items in the most recent year.

**form_version handling**: Uses mart_form_470 (stg_basic deduplicated).

| billed_entity_name                                   | state | total_line_items |
|-------------------------------------------------------|-------|------------------|
| San Bernardino City Unif S D                          | CA    | 4,864            |
| Hendry County School District                         | FL    | 2,592            |
| Pa State Peppm Consortium (Central Susquehanna IU)     | PA    | 2,000            |
| Chaffey Union High Sch Dist                           | CA    | 1,412            |
| Corona-Norco Unif Sch District                        | CA    | 1,392            |
| Capital Region Boces                                   | NY    | 1,391            |
| Socorro Indep School District                         | TX    | 1,137            |
| Stevensville School District 2 (Stevensville Public) | MT    | 872              |
| Onondaga-Cortland-Madison Boces                       | NY    | 872              |
| Northwest R-1 School District                         | MO    | 822              |

## Project Structure

```
.
├── ingest/
│   ├── __init__.py
│   ├── socrata_client.py    # API client with pagination and retries
│   └── loader.py             # DuckDB loader with idempotency
├── models/
│   ├── __init__.py
│   ├── stg_basic.sql         # Staging: Basic Information with dedup
│   ├── stg_services.sql      # Staging: Services Requested
│   └── mart_form_470.sql     # Mart: Joined analytical layer
├── tests/
│   ├── __init__.py
│   ├── data_quality.sql      # Data quality check queries
│   └── run_tests.py          # Test runner
├── data/
│   └── erate.duckdb          # DuckDB database (created on first run)
├── analysis.py               # Analytical queries
├── main.py                   # Pipeline orchestrator
├── requirements.txt
├── .env.example
├── README.md
└── DESIGN.md
```

## Key Engineering Practices

- **Idempotency**: Running ingestion twice does not duplicate rows (DELETE+INSERT per funding year)
- **Pagination**: Handles $limit/$offset with $order=:id for stable ordering
- **Retries**: Exponential backoff on HTTP errors and rate limits
- **Configuration**: No secrets in repo; uses .env (gitignored)
- **Data Quality**: Automated SQL checks that run and report on each execution
