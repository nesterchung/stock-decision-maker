# Market State Engine v0.2 Implementation Walkthrough

This document provides a comprehensive guide to the v0.2 implementation, explaining the architecture changes, new features, and usage patterns.

## Overview of v0.2 Changes

v0.2 introduces a config-driven architecture while maintaining full backward compatibility with v0.1. The key changes are:

1. **Signal Configuration**: `signals.yaml` defines signal logic declaratively
2. **Enhanced Output**: Per-signal metrics (value + SMA) included in results
3. **Flexible Architecture**: Support for different signal kinds and rules
4. **Backward Compatibility**: v0.1 behavior preserved via `--legacy` flag

## Architecture Changes

### v0.1 Architecture (Legacy)
```
compute.py → hardcoded signal logic → v0.1 output format
```

### v0.2 Architecture (Config-Driven)
```
signals.yaml → config loader → flexible signal engine → v0.2 output format
```

## Signal Configuration (signals.yaml)

The `signals.yaml` file is the heart of v0.2's flexibility:

```yaml
version: "0.2"

price_field: "adj_close"
window: 20
bench: "SPY"

signals:
  energy:
    kind: "relative_strength"
    a: "XLE"
    b: "SPY"
    rule: "gt_sma"

  tech:
    kind: "relative_strength"
    a: "XLK"
    b: "SPY"
    rule: "gt_sma"

  utilities:
    kind: "relative_strength"
    a: "XLU"
    b: "SPY"
    rule: "gt_sma"

  rates:
    kind: "price_proxy"
    ticker: "TLT"
    rule: "lt_sma"
```

### Signal Kinds

1. **relative_strength**: `value = ticker_A / ticker_B`
   - Used for sector performance vs benchmark
   - Example: `XLE/SPY` for Energy relative strength

2. **price_proxy**: `value = ticker_price`
   - Used for direct price analysis
   - Example: `TLT` for rates proxy

### Signal Rules

1. **gt_sma**: Signal = UP if `value > SMA(value, window)`
2. **lt_sma**: Signal = UP if `value < SMA(value, window)`

## Code Implementation Details

### Core Functions

#### `load_signals_config()`
- Loads `signals.yaml` from repo root or custom path
- Uses YAML parsing for configuration
- Returns dict for downstream processing

#### `compute_signals_v2()`
- Main v0.2 entry point
- Pre-computes all signal values and SMAs
- Generates records with enhanced metrics
- Handles all signal kinds and rules

#### Backward Compatibility in `compute_signals()`
- Detects config parameter presence
- Routes to v0.2 or v0.1 accordingly
- Preserves exact v0.1 behavior when needed

### Signal Computation Flow

1. **Load Configuration**: Parse `signals.yaml`
2. **Pre-compute Values**: Calculate raw values for each signal
3. **Calculate SMAs**: Rolling averages for each signal
4. **Apply Rules**: Generate UP/DOWN/NA signals
5. **Package Results**: Create output with metrics

## Output Schema Evolution

### v0.1 Output
```json
{
  "date": "2025-12-20",
  "signals": {"energy": "UP", "rates": "DOWN", "tech": "UP", "utilities": "NA"},
  "inputs": {"bench": "SPY", "tickers": [...], "window": 20, "price_field": "adj_close"},
  "version": "0.1"
}
```

### v0.2 Output
```json
{
  "date": "2025-12-20",
  "signals": {"energy": "UP", "rates": "DOWN", "tech": "UP", "utilities": "NA"},
  "metrics": {
    "energy": {"value": 0.195, "sma": 0.190},
    "rates": {"value": 108.5, "sma": 109.2},
    "tech": {"value": 0.385, "sma": 0.380},
    "utilities": {"value": 0.165, "sma": null}
  },
  "inputs": {"price_field": "adj_close", "window": 20, "tickers": [...]},
  "version": "0.2"
}
```

## Usage Examples

### Basic v0.2 Usage
```bash
# Uses default signals.yaml
python -m src.python_mse.compute --input tests/sample/prices.csv --out data/canonical.ndjson
```

### Custom Configuration
```bash
# Use custom config file
python -m src.python_mse.compute --input prices.csv --out output.ndjson --config my_signals.yaml
```

### v0.1 Legacy Mode
```bash
# Exact v0.1 behavior for backward compatibility
python -m src.python_mse.compute --input prices.csv --out legacy.ndjson --legacy
```

## Testing Strategy

### Backward Compatibility Tests
- Ensure v0.1 legacy mode produces identical output
- Validate v0.2 produces correct signals for same inputs
- Test NA policy consistency across versions

### Configuration Tests
- Validate signal parsing from YAML
- Test all signal kinds and rules
- Verify error handling for invalid configs

### Output Schema Tests
- Confirm metrics inclusion in v0.2
- Validate version field correctness
- Test data type consistency

## Migration Guide

### For Existing Users
1. **No immediate changes needed**: v0.1 behavior preserved
2. **Gradual adoption**: Use `--legacy` flag during transition
3. **Custom configs**: Create `signals.yaml` for custom signals

### For New Implementations
1. **Start with v0.2**: Use config-driven approach
2. **Leverage metrics**: Use enhanced output for analysis
3. **Custom signals**: Define custom signals in YAML

## Advanced Usage

### Custom Signal Examples

#### Sector Rotation Signal
```yaml
sector_rotation:
  kind: "relative_strength"
  a: "XLY"  # Consumer Discretionary
  b: "XLP"  # Consumer Staples
  rule: "gt_sma"
```

#### Volatility Signal
```yaml
volatility:
  kind: "price_proxy"
  ticker: "VIX"
  rule: "gt_sma"
```

### Configuration Validation
The engine validates:
- Required fields presence
- Signal kind validity
- Rule compatibility
- Ticker availability

## Performance Considerations

### Computation Efficiency
- Pre-computation of values and SMAs
- Vectorized pandas operations
- Minimal memory footprint

### Scalability
- Linear scaling with number of signals
- Efficient rolling calculations
- Configurable signal sets

## Troubleshooting

### Common Issues

#### Missing Tickers
```
ValueError: Missing required columns in prices CSV: ['XLE', 'XLK']
```
**Solution**: Ensure all required tickers present in input CSV

#### Invalid Config
```
yaml.scanner.ScannerError: while scanning for the next token
```
**Solution**: Validate YAML syntax and required fields

#### Version Mismatch
```
Validator: Version mismatch (0.2 vs 0.1)
```
**Solution**: Ensure Python and Node versions match

### Debug Mode
Use `--legacy` flag to isolate v0.1 vs v0.2 behavior differences.

## Future Extensibility

The v0.2 architecture enables:
- Additional signal kinds (technical indicators)
- Multiple timeframes
- Custom rules beyond SMA comparisons
- Signal composition and scoring

## Conclusion

v0.2 provides a solid foundation for future enhancements while maintaining the reliability and backward compatibility of v0.1. The config-driven approach makes the system more maintainable and extensible for future requirements.