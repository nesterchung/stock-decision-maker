# AGENTS.md

## Overview

This is the Market State Engine v0.1 - a hybrid Python/Node.js financial signal processing engine that computes daily binary market state indicators (UP/DOWN) from sector ETFs using simple moving average (SMA) relative strength.

**Architecture Pattern:**
- Python (canonical compute) → generates NDJSON output
- Node.js validator → recomputes and diffs against Python output
- CI ensures both implementations produce identical results

## Build/Test Commands

### Python Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run all Python unit tests
pytest tests/python/ -v

# Run specific test class
pytest tests/python/test_compute.py::TestSignalComputation -v

# Run single test method
pytest tests/python/test_compute.py::TestSignalComputation::test_basic_signals -v

# Run canonical compute (core functionality)
python -m src.python_mse.compute --input tests/sample/prices.csv --out data/canonical.ndjson

# Run with custom window size
python -m src.python_mse.compute --input tests/sample/prices.csv --out data/canonical.ndjson --window 50
```

### Node.js Commands

```bash
# Install Node dependencies (run from src/node_validator/)
npm install

# Run Node unit tests
node tests/node/test_validator.js

# Run validator against Python canonical output
node src/node_validator/validator.js --prices tests/sample/prices.csv --canonical data/canonical.ndjson --window 20

# Run validation script from package.json (from src/node_validator/)
npm run validate
```

### Full Pipeline (CI Commands)

```bash
# Complete Python pipeline
python -m pytest tests/python/ -v && python -m src.python_mse.compute --input tests/sample/prices.csv --out data/canonical.ndjson

# Complete Node validation pipeline
python -m src.python_mse.compute --input tests/sample/prices.csv --out data/canonical.ndjson && node tests/node/test_validator.js && node src/node_validator/validator.js --prices tests/sample/prices.csv --canonical data/canonical.ndjson --window 20
```

## Code Style Guidelines

### Python (Primary Implementation)

**Naming Conventions:**
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE` (rare)
- Classes: `PascalCase` (unittest classes only)
- Files: `snake_case.py`

**Import Style:**
```python
import unittest
import pandas as pd
import sys
from pathlib import Path

# Local imports after standard library
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from python_mse.compute import compute_signals
```

**Function Documentation:**
- Use docstrings (not type hints)
- Clear parameter descriptions
- Return value documentation
- Include usage examples when helpful

**Code Patterns:**
- Use pandas for data manipulation
- Prefer `.loc` for DataFrame indexing
- Handle NaN values explicitly with `pd.isna()`
- Date handling with `pd.to_datetime().strftime("%Y-%m-%d")`
- File I/O using `pathlib.Path`

**Error Handling:**
- Raise `ValueError` for data validation issues
- Include clear error messages with expected vs actual
- Use print() for runtime warnings (as seen in compute.py)

### Node.js (Validator Implementation)

**Naming Conventions:**
- Functions/variables: `camelCase`
- Constants: `UPPER_SNAKE_CASE` (rare)
- Files: `camelCase.js`

**Code Style:**
```javascript
const assert = require('assert');

// Functions with clear single responsibility
function movingAverage(arr, window) {
  // Implementation with null handling
  const res = new Array(arr.length).fill(null);
  // ...
}

// Test functions should be descriptive
function testMovingAverage() {
  // Arrange
  const arr = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
  const ma = movingAverage(arr, 3);
  
  // Assert
  assert.strictEqual(ma[0], null);
  assert.strictEqual(ma[2], 2);
  console.log('✓ testMovingAverage');
}
```

**Testing Pattern:**
- Use native `assert` module only (no external test frameworks)
- Test functions should console.log success with checkmark prefix
- Wrap test execution in try/catch with `process.exit(1)` on failure
- Follow: Arrange → Act → Assert pattern

**Error Handling:**
- Validate input arrays for length/validity
- Return `null` for undefined SMA calculations (window not filled)
- Use descriptive error messages in assertions

## Architecture Guidelines

### Dual Implementation Pattern
Python implementation is canonical source. Node.js validator must produce identical output. CI validates consistency. Signal logic: Energy/ Tech/Utilities use RS ratio > SMA, Rates uses TLT < SMA. First (window-1) days must be "NA". Input: CSV with date + tickers. Output: NDJSON with date, signals, inputs, version fields.

### Testing Requirements
Test NA policy, UP/DOWN logic with known datasets, schema completeness, rates semantics. Both implementations must handle edge cases identically. Window calculation exact, date handling identical YYYY-MM-DD strings, output schema must match exactly.

### File Organization
```
src/
├── python_mse/           # Python canonical implementation
│   ├── compute.py        # Core signal logic
│   ├── __main__.py       # CLI interface
│   └── __init__.py
└── node_validator/        # Node.js validation implementation
    ├── validator.js      # Validation logic
    └── package.json      # Node dependencies

tests/
├── python/
│   └── test_compute.py   # Python unit tests
└── node/
    └── test_validator.js # Node unit tests

data/
└── canonical.ndjson     # Generated by Python, consumed by Node
```

## Development Workflow

1. Modify Python compute.py first, validate with tests
2. Port exact logic to Node validator.js  
3. Run Python tests, then Node tests separately
4. Run full pipeline with canonical output
5. Push to trigger full cross-language validation

## Important Notes

- No linting/formatting tools configured
- Python 3.11 Required, Node.js 18 Required
- Version number "0.1" appears in both implementations
- Uses pytest for discovery, unittest for structure