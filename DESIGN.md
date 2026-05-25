# E-Rate Pipeline Design Document

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USAC Socrata API                        │
│  (jp7a-89nd: Basic Info, 39tn-hjzv: Services Requested)        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ingest/ Module                             │
│  ┌─────────────────┐    ┌──────────────────────────────────┐  │
│  │ SocrataClient   │───▶│ DataLoader (DuckDB)               │  │
│  │ - Pagination    │    │ - Idempotent DELETE+INSERT        │  │
│  │ - Retries       │    │ - raw_basic, raw_services         │  │
│  └─────────────────┘    └──────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DuckDB Database                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ raw_* Tables (exact API data)                            │  │
│  │  - raw_basic                                              │  │
│  │  - raw_services                                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ stg_* Tables (cleaning + dedup)                          │  │
│  │  - stg_basic (form_version dedup: Current > Original)   │  │
│  │  - stg_services (type casting)                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ mart_* Tables (analytical layer)                         │  │
│  │  - mart_form_470 (joined basic + services)               │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      tests/ Module                              │
│  - PK uniqueness check                                          │
│  - Referential integrity check                                  │
│  - Critical nulls check                                         │
│  - Form version distribution                                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    analysis.py                                   │
│  - 6 analytical questions against mart layer                    │
│  - Each with explicit form_version handling documentation      │
└─────────────────────────────────────────────────────────────────┘
```

## Stack Rationale

**Python 3.11+**: Mature ecosystem, excellent data libraries (pandas, requests), familiar to data engineers.

**DuckDB**: 
- Zero-config local file database (no server to manage)
- Excellent SQL support with analytical functions
- Fast columnar storage
- Python-native integration
- Perfect for mid-sized datasets (E-Rate data fits comfortably)

**Requests**: Simple, reliable HTTP client with built-in session support for retries.

**Pandas**: Efficient data manipulation for API response handling and type conversion.

**SQL for modeling**: 
- Declarative and readable transformations
- Easy to audit and version control
- Portable across database systems
- Industry standard for data engineering

## Timebox Trade-offs

**What was cut or simplified:**

1. **Incremental loading**: Current implementation does full refresh per funding year. An incremental loader using `$where` and `$order` would be more efficient for frequent runs but requires tracking high-water marks.

2. **Advanced error handling**: Basic retry logic is implemented, but dead letter queues or detailed error logging were not included.

3. **Data profiling**: Only basic data quality checks (4 checks) rather than comprehensive profiling (statistics, distributions, outlier detection).

4. **Metadata tracking**: No separate table tracking load timestamps, row counts, or data lineage.

5. **API token management**: Optional app token is supported but not required (API is anonymous). No token rotation logic.

6. **Parallel ingestion**: Sequential loading of basic info and services. Could parallelize for faster initial load.

7. **Historical version tracking**: Staging layer keeps only the deduplicated "current" view. Raw layer preserves all versions but no dedicated history table.

**Why these cuts:**

- Focused on core functionality: reliable ingestion, correct deduplication, analytical answers
- Kept implementation simple enough to complete in a single session
- DuckDB's performance makes full refresh acceptable for this dataset size
- Basic data quality checks catch critical issues without over-engineering

## Incremental Loader Design

To build an incremental loader (not implemented):

1. **Track high-water marks**: Store the last `:id` value fetched for each resource in a metadata table.

2. **Use SoQL for incremental fetch**:
   ```python
   params = {
       "$where": f":id > '{last_id}'",
       "$order": ":id",
       "$limit": PAGE_SIZE
   }
   ```
   Note: The USAC Socrata API does not support `$where` clauses with `funding_year` filtering, so filtering is done in Python after fetching.

3. **Append-only inserts**: Use INSERT instead of DELETE+INSERT for new records.

4. **Handle updates**: For updated records (same :id, different content), use upsert logic or periodic full refresh of recent years.

5. **Backfill strategy**: Periodically re-fetch older funding years to catch any late-arriving amendments.

This approach minimizes API calls and data transfer while ensuring eventual consistency.

## What Would Be Different With a Week

1. **Orchestration**: Add Airflow or Dagster for scheduled runs, monitoring, and alerting.

2. **Incremental loading**: Implement the high-water mark tracking described above.

3. **Data quality**: Expand to 10+ checks including statistical profiling, outlier detection, and trend analysis.

4. **Testing**: Add unit tests for ingest logic, integration tests for models, and synthetic data fixtures.

5. **Documentation**: Add dbt-style documentation for each column and table.

6. **Performance**: Benchmark and optimize queries, add indexes if needed (though DuckDB handles this well).

7. **Monitoring**: Add logging to external system (e.g., CloudWatch, DataDog) with metrics on row counts, timing, and error rates.

8. **Data lineage**: Track source-to-target column mappings and transformation logic.

9. **API reliability**: Add circuit breaker pattern, more sophisticated backoff, and fallback caching.

10. **User interface**: Simple web dashboard (Streamlit or FastAPI) for exploring data and viewing results.

11. **Historical analysis**: Preserve historical snapshots to enable trend analysis over time.

12. **Geospatial analysis**: Leverage DuckDB's spatial extensions for better geographic analysis.
