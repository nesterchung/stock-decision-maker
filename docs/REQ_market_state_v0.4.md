# Market State (v0.4) — Config-driven Rules (Requirement)

## Objective
Replace hardcoded market_state logic (v0.3) with a config-driven evaluator (v0.4) using a minimal YAML rule schema.
Must be backward compatible and easy to rollback via config.

## Context
Current pipeline produces `signals` per date and computes `state` with hardcoded required signals: tech, utilities, rates.
We want to move required signals and label rules into config (signals.yaml) so that changes do not require code updates.

## In-Scope
1. Add `market_state` section to the YAML config (same file as existing signals config).
2. Implement `compute_market_state_v04(signals: dict, config: dict) -> dict` (minimal DSL: AND of equality checks).
3. Wire it into `compute_signals_v2()` with a version switch:
   - If `config.market_state.version == "0.4"` → use v0.4 evaluator
   - Else → fallback to existing v0.3 hardcoded evaluator
4. Add minimal schema validation (fail-fast) for market_state config.
5. Add pytest unit tests covering: RISK_ON, RISK_OFF, MIXED(default), NA(missing), disabled.

## Out-of-Scope (for v0.4)
- Complex DSL (any/not/thresholds)
- ML/statistical regime detection
- Multi-layer states (volatility/breadth/etc)

## Config Schema (YAML)
Add this at root level of the config file:

market_state:
  version: "0.4"
  enabled: true
  required_signals: ["tech", "utilities", "rates"]
  labels_order: ["RISK_ON", "RISK_OFF", "MIXED"]
  labels:
    RISK_ON:
      all:
        - signal: tech
          is: "UP"
        - signal: utilities
          is: "DOWN"
        - signal: rates
          is: "DOWN"
    RISK_OFF:
      all:
        - signal: tech
          is: "DOWN"
        - signal: utilities
          is: "UP"
        - signal: rates
          is: "UP"
    MIXED:
      default: true
  output:
    field: "state"
    include_debug: false
    na_label: "NA"

## Inputs
- `signals`: dict keyed by signal name; each signal must expose `signals[name]["signal"]` string value.
  Example:
  signals = {
    "tech": {"signal": "UP", ...},
    "utilities": {"signal": "DOWN", ...},
    "rates": {"signal": "DOWN", ...}
  }

- `config`: dict loaded from YAML, containing the `market_state` section above.

## Output Contract
Return object assigned into row field `market_state.output.field` (default "state"):

Minimum output:
{
  "label": "<RISK_ON|RISK_OFF|MIXED|NA>",
  "rule": "v0.4_config"
}

Special cases:
- If market_state.enabled == false:
  { "label": "<na_label>", "rule": "disabled" }

- If required signals are missing (missing key or missing ["signal"] field):
  { "label": "<na_label>", "rule": "v0.4_config", "missing": ["rates", ...] }

## Evaluation Rules
- Build `actual[name] = signals[name]["signal"]` for each required signal.
- Iterate labels in `labels_order` (first-match wins):
  - For a label with `all`, all conditions must match:
    - condition passes iff `actual[cond.signal] == cond.is`
  - If matches → return label
- If none matched:
  - If any label has `default: true` → return that label
  - Else return "MIXED"
- If output.include_debug == true (optional in v0.4):
  - include "matched" and "reasons" fields (not required unless implemented)

## Minimal Schema Validation (Fail-fast)
Validate at runtime when loading/using config:
- market_state.required_signals is list[str] and non-empty
- market_state.labels_order is list[str] and non-empty
- market_state.labels is dict
- For each label in labels_order that is not default-only:
  - labels[label].all is list of objects with keys: signal, is
If invalid → raise ValueError with an actionable message.

## Tests (pytest)
Add tests for:
1. RISK_ON match
2. RISK_OFF match
3. MIXED default when no match
4. NA when missing required signals
5. disabled behavior

## Rollback Strategy
- Remove or change config `market_state.version` away from "0.4" OR set `market_state.enabled=false`
- Code must fallback to v0.3 evaluator without modification.
