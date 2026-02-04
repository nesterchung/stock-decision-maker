# Architecture Draft — Market State Engine v0.1

Goal: provide a minimal, testable architecture to produce daily canonical signals (Python) and validate with Node.

Components

- Data Ingest
  - Responsibility: fetch end-of-day adjusted close for tickers (XLE, TLT, XLK, XLU, SPY)
  - Output: aligned CSV/Parquet with `date` + `adj_close` per ticker, same date index for all tickers
  - Notes: store a snapshot used by both Python and Node to avoid drift

- Canonical Compute (Python)
  - Responsibility: compute RS series, 20-day SMA, produce daily JSON/NDJSON canonical records
  - Output: `data/canonical/YYYY-MM-DD.ndjson` (or single file per run)
  - Implementation: small CLI `python -m mse.compute --input data/prices.csv --out data/canonical.ndjson`

- Validator (Node)
  - Responsibility: read canonical outputs or raw aligned prices, recompute signals per spec, diff against Python output
  - Features: robust CSV parsing with csv-parse library supporting quoted fields and extra columns
  - CI behavior: exit non-zero on any mismatch

- Storage
  - Local project layout for MVP; later S3/remote snapshots
  - Suggested: `data/raw/`, `data/aligned/`, `data/canonical/`, `tests/sample/`

- CI
  - Steps: run python canonical compute -> run node validator -> fail on mismatch
  - Add unit tests for signal logic and SMA edge cases

Project layout (suggested)

- README.md
- PRD.md
- docs/
  - requirements.md
  - architecture.md
- src/python_mse/
  - __main__.py (CLI)
  - compute.py (core logic)
- src/node_validator/
  - package.json
  - package-lock.json
  - validator.js
- data/
  - raw/
  - aligned/
  - canonical/
- tests/
  - python/
  - node/

Next concrete steps (short):
1. Create Python module skeleton and CLI
2. Add a small sample dataset (2 months) in `tests/sample/`
3. Implement Node validator skeleton
4. Add CI job skeleton (GitHub Actions or similar)

Estimated minimal deliverable: runnable Python compute that outputs canonical NDJSON for sample data, plus Node validator that diffs it.

## Implementation Status

✅ **Completed Components:**
- Python canonical compute with signal logic
- Node validator with robust CSV parsing using csv-parse library
- CI/CD pipeline with GitHub Actions
- Unit tests for both Python and Node implementations
- Sample data and documentation

✅ **Enhanced Features:**
- Robust CSV parsing supporting quoted fields and extra columns
- Async CSV parsing with proper error handling
- Backward compatibility maintained with existing CSV formats

## CSV Handling Details

**Node Validator CSV Parsing:**
- Library: csv-parse v6.1.0
- Configuration: `columns: true`, `skip_empty_lines: true`, `trim: true`
- Flexibility: `relax_column_count: true`, `relax_quotes: true`
- Supports: Quoted fields with commas, extra columns, various quote formats

**Supported CSV Formats:**
```csv
date,XLE,TLT,XLK,XLU,SPY,extra_field,notes
2025-12-01,75.0,110.0,150.0,65.0,400.0,extra1,"Note with, comma"
2025-12-02,75.5,109.5,151.0,65.2,401.0,extra2,"Another note"
```

