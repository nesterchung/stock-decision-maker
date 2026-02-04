# Extracted Requirements — Market State Engine v0.1

Summary of key requirements and implementation notes extracted from PRD.md.

- Frequency: daily (end-of-day close)
- Output: four binary signals (`UP` / `DOWN`) per date
- Canonical implementation: Python (produces canonical JSON/NDJSON)
- Validator: Node must recompute same logic and fail CI on any mismatch
- Price field: `adj_close` (fallback to `close` if unavailable) — must be consistent across Python/Node
- Window: 20-day SMA; dates with fewer than 20 days -> output `NA` (or skip) to avoid diff churn

Signals (v0.1):
- Energy: `RS_energy = close(XLE)/close(SPY)`; Energy = `UP` if `RS_energy > SMA(RS_energy,20)` else `DOWN`
- Rates: intent = yields up (tightening). Use `TLT` as proxy. Rates = `UP` if `close(TLT) < SMA(close(TLT),20)` else `DOWN`
- Tech: `RS_tech = close(XLK)/close(SPY)`; Tech = `UP` if `RS_tech > SMA(RS_tech,20)` else `DOWN`
- Utilities: `RS_util = close(XLU)/close(SPY)`; Utilities = `UP` if `RS_util > SMA(RS_util,20)` else `DOWN`

Canonical output schema (example):

```
{
  "date": "YYYY-MM-DD",
  "signals": { "energy": "UP", "rates": "DOWN", "tech": "UP", "utilities": "DOWN" },
  "inputs": { "bench": "SPY", "tickers": ["XLE","TLT","XLK","XLU","SPY"], "window": 20, "price_field": "adj_close" },
  "version": "0.1"
}
```

Validator rules:
- Use same date set and same price field across implementations
- Recompute signals per spec and diff against Python canonical output
- Any mismatch -> non-zero exit (CI fail)

Next actions (implementation-oriented):
1. Define technical architecture (data ingestion, canonical compute, storage format, validator flow)
2. Scaffold project structure (python module, node validator, CI workflow)
3. Implement Python canonical generator + small runner
4. Implement Node validator and CI gate
5. Add tests, sample data, and README

