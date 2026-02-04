# Decision Record: Code Review Follow-ups (2026-02-04)

Status: **Recorded / Deferred**

## Context

This repository implements a **dual-implementation** Market State Engine:

- **Python** produces canonical NDJSON output.
- **Node.js** recomputes signals from the same input data and diffs against the canonical output.
- CI fails on any mismatch.

As of today:

- Python supports **v0.1 legacy** (hardcoded) and **v0.2 config-driven** (`signals.yaml`) compute.
- Node validator computes **v0.1 hardcoded** signals only.

## Scope of review

Reviewed:

- Python: `src/python_mse/compute.py`
- Node: `src/node_validator/validator.js`
- Tests: `tests/python/test_compute.py`, `tests/node/test_validator.js`
- CI: `.github/workflows/ci.yml`
- Docs/spec: `PRD.md`, `docs/architecture.md`, `README.md`, `docs/requirements.md`

## Key findings (summary)

### A) Cross-language drift risk (v0.2 vs validator)

- Python default execution path is **v0.2 config-driven** (loads `signals.yaml`).
- Node validator is **not config-driven** and remains **v0.1 hardcoded**.

**Impact**: CI passes today only because `signals.yaml` currently matches the v0.1 definitions. Any future config change (tickers/rules/window) can cause:

- false failures (validator disagrees)
- or worse: changes ship without being validated if CI execution doesn’t match the intended contract.

### B) CSV contract mismatch (wide vs “preferred”)

- Python `read_wide_csv()` accepts both:
  - preferred: `<TICKER>_adj_close` columns (e.g. `XLE_adj_close`)
  - backward-compatible: plain ticker columns (`XLE`, `SPY`, ...)
- Node validator currently requires **plain** ticker columns only.

**Impact**: the “preferred” suffixed column format cannot be validated by Node as-is.

### C) Strict JSON safety (NaN/Infinity)

- Python v0.2 writes `metrics` floats to JSON.
- If input data introduces `NaN`/`Infinity` (missing values, division-by-zero, etc.), Python may emit non-standard JSON tokens (`NaN`, `Infinity`) that Node’s `JSON.parse` cannot read.

**Impact**: potential runtime parse failures or confusing diffs when data quality degrades.

### D) Validation asymmetry

- Node validates numeric fields strictly (non-numeric => error).
- Python does not fail fast on NaNs/missing; NaNs may propagate into comparisons.

**Impact**: data quality issues can be silently converted into “DOWN” signals in Python, while Node would hard-fail.

### E) Documentation inconsistency

README includes a “v0.2 Data Requirement” section describing a normalized/long CSV contract (`date,ticker,adj_close`), while the implemented code paths use a wide CSV (`date,XLE,TLT,XLK,XLU,SPY`).

**Impact**: onboarding confusion; future contributors may supply the wrong format.

## Decision

These issues are **not urgent** for current usage. We will **record them as known risks** and **defer implementation** until we actively expand v0.2 usage or change data ingestion.

This record exists to prevent re-discovery and to guide future refactors.

## Deferred options (when we revisit)

### Option 1 (Recommended): Make Node validator v0.2 config-driven

- Node reads `signals.yaml` and generically computes:
  - `relative_strength` and `price_proxy`
  - rules `gt_sma` / `lt_sma`
  - window/bench from config

Pros:
- Maintains the “Python canonical, Node validates” architecture for v0.2.

Cons:
- More code in Node; must ensure exact numeric and NA behavior match Python.

### Option 2: Pin CI to v0.1 legacy until Node is upgraded

- Change CI to run Python with `--legacy`.

Pros:
- Zero Node changes.

Cons:
- v0.2 path not validated by CI.

## Suggested follow-up tasks (future)

1. **Contract alignment**
   - Decide: wide CSV vs normalized CSV.
   - Update README/docs to match the chosen contract.

2. **CSV parsing parity**
   - Either add suffixed column support in Node (mirror Python), or drop “preferred” claim.

3. **Strictness & data validation**
   - Add Python input validation (no missing values, no division by zero).
   - Consider `json.dumps(..., allow_nan=False)` and explicit error messages.

4. **Test coverage improvements**
   - Add Python tests for v0.2 config path (YAML parsing + metrics output).
   - Add Node end-to-end tests for `computeSignals`, CSV parsing, and (optional) metrics compare.

## Notes

- Current v0.1 signal semantics appear consistent across Python and Node:
  - Energy/Tech/Utilities: RS ratio > SMA ⇒ UP
  - Rates: `TLT < SMA(TLT)` ⇒ UP (yields up / tightening)
