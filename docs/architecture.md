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

