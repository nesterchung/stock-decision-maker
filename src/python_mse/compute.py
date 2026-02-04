import argparse
import json
from pathlib import Path
import pandas as pd
import yaml


def load_signals_config(config_path: Path = None):
    """Load signal configuration from YAML file.

    If config_path is not provided, looks for signals.yaml in repo root.
    """
    if config_path is None:
        # Look for signals.yaml in repo root (parent of src/)
        config_path = Path(__file__).parent.parent.parent / "signals.yaml"

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    return config


def compute_signal(value_series: pd.Series, sma_series: pd.Series, rule: str):
    """Compute signal based on value and SMA series.

    Args:
        value_series: Series of values
        sma_series: Series of SMA values
        rule: "gt_sma" (UP if value > SMA) or "lt_sma" (UP if value < SMA)

    Returns:
        Tuple of (signal, value, sma) where signal is "UP", "DOWN", or "NA"
    """
    val = value_series.iloc[-1] if len(value_series) > 0 else None
    sma = sma_series.iloc[-1] if len(sma_series) > 0 else None

    if pd.isna(sma):
        return "NA", val, None

    if rule == "gt_sma":
        signal = "UP" if val > sma else "DOWN"
    elif rule == "lt_sma":
        signal = "UP" if val < sma else "DOWN"
    else:
        raise ValueError(f"Unknown rule: {rule}")

    return signal, val, sma


def validate_market_state_config(config: dict):
    """Validate market_state configuration for v0.4."""
    market_state = config.get("market_state")
    if not isinstance(market_state, dict):
        raise ValueError("market_state config is required and must be a dict")

    required_signals = market_state.get("required_signals")
    if not isinstance(required_signals, list) or not required_signals:
        raise ValueError("market_state.required_signals must be a non-empty list")
    if not all(isinstance(name, str) for name in required_signals):
        raise ValueError("market_state.required_signals must contain only strings")

    labels_order = market_state.get("labels_order")
    if not isinstance(labels_order, list) or not labels_order:
        raise ValueError("market_state.labels_order must be a non-empty list")
    if not all(isinstance(name, str) for name in labels_order):
        raise ValueError("market_state.labels_order must contain only strings")

    labels = market_state.get("labels")
    if not isinstance(labels, dict):
        raise ValueError("market_state.labels must be a dict")

    for label in labels_order:
        label_def = labels.get(label)
        if not isinstance(label_def, dict):
            raise ValueError(f"market_state.labels.{label} must be a dict")

        has_default = label_def.get("default") is True
        has_all = "all" in label_def

        if has_default and not has_all:
            continue

        conditions = label_def.get("all")
        if not isinstance(conditions, list) or not conditions:
            raise ValueError(
                f"market_state.labels.{label}.all must be a non-empty list"
            )
        for condition in conditions:
            if not isinstance(condition, dict):
                raise ValueError(
                    f"market_state.labels.{label}.all entries must be dicts"
                )
            if "signal" not in condition or "is" not in condition:
                message = (
                    "market_state.labels."
                    f"{label}.all entries require 'signal' and 'is'"
                )
                raise ValueError(message)


def compute_market_state_v04(signals: dict, config: dict):
    """Compute v0.4 market state label from config-driven rules."""
    validate_market_state_config(config)
    market_state = config.get("market_state", {})
    output_config = market_state.get("output", {})
    na_label = output_config.get("na_label", "NA")

    if market_state.get("enabled", True) is False:
        return {"label": na_label, "rule": "disabled"}

    required_signals = market_state.get("required_signals", [])
    missing = []
    for name in required_signals:
        if name not in signals:
            missing.append(name)
            continue
        signal_value = signals[name].get("signal") if name in signals else None
        if "signal" not in signals[name] or signal_value == "NA":
            missing.append(name)

    if missing:
        return {"label": na_label, "rule": "v0.4_config", "missing": missing}

    actual = {name: signals[name]["signal"] for name in required_signals}
    labels_order = market_state.get("labels_order", [])
    labels = market_state.get("labels", {})

    for label in labels_order:
        label_def = labels.get(label, {})
        conditions = label_def.get("all")
        if not conditions:
            continue
        matches = all(actual.get(cond["signal"]) == cond["is"] for cond in conditions)
        if matches:
            return {"label": label, "rule": "v0.4_config"}

    default_label = None
    for label, label_def in labels.items():
        if label_def.get("default") is True:
            default_label = label
            break

    if default_label is not None:
        return {"label": default_label, "rule": "v0.4_config"}

    return {"label": "MIXED", "rule": "v0.4_config"}


def compute_signals_v2(prices_wide: pd.DataFrame, config: dict):
    """Compute signals based on config-driven logic (v0.2).

    Args:
        prices_wide: DataFrame with date index and ticker columns
        config: Loaded signals.yaml configuration

    Returns:
        List of records with date, signals, metrics, inputs, version
    """
    df = prices_wide.sort_index().copy()
    out = []

    price_field = config.get("price_field", "adj_close")
    window = config.get("window", 20)
    bench = config.get("bench", "SPY")
    signals_config = config.get("signals", {})
    version = config.get("version", "0.2")

    market_state_config = config.get("market_state", {})
    market_state_version = market_state_config.get("version")
    if market_state_version == "0.4":
        validate_market_state_config(config)

    # Pre-compute all signal values and SMAs
    signal_data = {}
    for signal_name, signal_def in signals_config.items():
        kind = signal_def["kind"]
        rule = signal_def["rule"]

        if kind == "relative_strength":
            a_ticker = signal_def["a"]
            b_ticker = signal_def["b"]
            value_series = df[a_ticker] / df[b_ticker]
        elif kind == "price_proxy":
            ticker = signal_def["ticker"]
            value_series = df[ticker]
        else:
            raise ValueError(f"Unknown signal kind: {kind}")

        sma_series = value_series.rolling(window=window).mean()
        signal_data[signal_name] = {
            "value": value_series,
            "sma": sma_series,
            "rule": rule,
        }

    # Collect all tickers used
    all_tickers = set([bench])
    for signal_def in signals_config.values():
        if "a" in signal_def:
            all_tickers.add(signal_def["a"])
        if "b" in signal_def:
            all_tickers.add(signal_def["b"])
        if "ticker" in signal_def:
            all_tickers.add(signal_def["ticker"])

    # Generate records for each date
    for date in df.index:
        row = {"date": pd.to_datetime(date).strftime("%Y-%m-%d")}

        signals = {}
        metrics = {}

        for signal_name, data in signal_data.items():
            value = data["value"].loc[date]
            sma = data["sma"].loc[date]
            rule = data["rule"]

            if pd.isna(sma):
                signal = "NA"
                metrics[signal_name] = {
                    "value": float(value) if not pd.isna(value) else None,
                    "sma": None,
                }
            else:
                if rule == "gt_sma":
                    signal = "UP" if value > sma else "DOWN"
                elif rule == "lt_sma":
                    signal = "UP" if value < sma else "DOWN"
                else:
                    raise ValueError(f"Unknown rule: {rule}")

                metrics[signal_name] = {
                    "value": float(value),
                    "sma": float(sma),
                }

            signals[signal_name] = signal

        row["signals"] = signals
        if market_state_version == "0.4":
            field = market_state_config.get("output", {}).get(
                "field",
                "state",
            )
            signals_for_state = {
                name: {"signal": signal} for name, signal in signals.items()
            }
            row[field] = compute_market_state_v04(
                signals_for_state,
                config,
            )
        else:
            row["state"] = compute_market_state(signals)
        row["metrics"] = metrics
        row["inputs"] = {
            "price_field": price_field,
            "window": window,
            "tickers": sorted(list(all_tickers)),
        }
        row["version"] = version

        out.append(row)

    return out


def compute_market_state(signals: dict):
    """Compute v0.3 market state label from signals."""
    required = ["tech", "utilities", "rates"]
    if any(signals.get(name) == "NA" for name in required):
        label = "NA"
    elif (
        signals.get("tech") == "UP"
        and signals.get("utilities") == "DOWN"
        and signals.get("rates") == "DOWN"
    ):
        label = "RISK_ON"
    elif (
        signals.get("tech") == "DOWN"
        and signals.get("utilities") == "UP"
        and signals.get("rates") == "UP"
    ):
        label = "RISK_OFF"
    else:
        label = "MIXED"

    return {"label": label, "rule": "v0.3_basic"}


def compute_signals(prices_wide: pd.DataFrame, window: int = 20, config: dict = None):
    """Compute signals with v0.1 compatibility.

    If config is provided, uses v0.2 config-driven logic.
    If config is None, falls back to v0.1 hardcoded logic for backward compatibility.
    """
    if config is not None:
        return compute_signals_v2(prices_wide, config)

    # v0.1 fallback - hardcoded logic for backward compatibility
    df = prices_wide.sort_index().copy()
    out = []

    rs_energy = df["XLE"] / df["SPY"]
    ma_energy = rs_energy.rolling(window=window).mean()

    rs_tech = df["XLK"] / df["SPY"]
    ma_tech = rs_tech.rolling(window=window).mean()

    rs_util = df["XLU"] / df["SPY"]
    ma_util = rs_util.rolling(window=window).mean()

    ma_tlt = df["TLT"].rolling(window=window).mean()

    for date in df.index:
        row = {"date": pd.to_datetime(date).strftime("%Y-%m-%d")}

        # Energy
        re = rs_energy.loc[date]
        me = ma_energy.loc[date]
        if pd.isna(me):
            energy = "NA"
        else:
            energy = "UP" if re > me else "DOWN"

        # Rates (Rates = UP means yields up -> TLT < MA)
        tlt = df["TLT"].loc[date]
        mt = ma_tlt.loc[date]
        if pd.isna(mt):
            rates = "NA"
        else:
            rates = "UP" if tlt < mt else "DOWN"

        # Tech
        rt = rs_tech.loc[date]
        mtc = ma_tech.loc[date]
        if pd.isna(mtc):
            tech = "NA"
        else:
            tech = "UP" if rt > mtc else "DOWN"

        # Utilities
        ru = rs_util.loc[date]
        mu = ma_util.loc[date]
        if pd.isna(mu):
            utilities = "NA"
        else:
            utilities = "UP" if ru > mu else "DOWN"

        row["signals"] = {
            "energy": energy,
            "rates": rates,
            "tech": tech,
            "utilities": utilities,
        }

        row["inputs"] = {
            "bench": "SPY",
            "tickers": ["XLE", "TLT", "XLK", "XLU", "SPY"],
            "window": window,
            "price_field": "adj_close",
        }
        row["version"] = "0.1"

        out.append(row)

    return out


def read_wide_csv(path: Path, price_field: str = "adj_close"):
    """Read a wide CSV where each ticker is a column.

    Expected column formats (in order of preference):
    - <TICKER>_<price_field> (e.g. XLE_adj_close)
    - <TICKER> (plain column name; assumed to already be adj_close)

    For v0.1 we require the CSV to represent adjusted close prices. If the
    file uses plain ticker column names (no suffix), a WARNING is emitted but
    the file is accepted to preserve backward-compatibility with the sample
    data. For stricter enforcement, callers should ensure columns use the
    "_<price_field>" suffix and/or validate upstream data source.
    """
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.set_index("date")

    required_tickers = ["XLE", "TLT", "XLK", "XLU", "SPY"]

    # Detect columns with suffix, prefer <TICKER>_<price_field>
    resolved_cols = {}
    suffixed = [f"{t}_{price_field}" for t in required_tickers]
    if all(c in df.columns for c in suffixed):
        for t, c in zip(required_tickers, suffixed):
            resolved_cols[t] = c
    else:
        # Fallback to plain ticker columns
        missing_plain = [t for t in required_tickers if t not in df.columns]
        if missing_plain:
            message = (
                f"Missing required columns in prices CSV: {missing_plain}.\n"
                "Expected either plain tickers "
                f"{required_tickers} or suffixed columns {suffixed} where "
                "suffixed means the price_field (e.g. adj_close) is included."
            )
            raise ValueError(message)
        # Issue a warning if plain columns are used (ask to use adj_close explicitly)
        print(
            "WARNING: Input CSV uses plain ticker columns (no '_adj_close' "
            "suffix). Please ensure these values are adjusted close prices "
            "(adj_close). For strict enforcement, provide files with "
            "'<TICKER>_adj_close' columns.)"
        )
        for t in required_tickers:
            resolved_cols[t] = t

    # Reindex dataframe to required columns in canonical order
    df2 = df[[resolved_cols[t] for t in required_tickers]].copy()
    df2.columns = required_tickers
    return df2


def main():
    p = argparse.ArgumentParser(
        description="Compute Market State Engine v0.2 canonical signals"
    )
    p.add_argument(
        "--input",
        "-i",
        required=True,
        help="Input wide CSV with date + ticker columns",
    )
    p.add_argument("--window", "-w", type=int, default=20, help="SMA window")
    p.add_argument(
        "--out",
        "-o",
        default="data/canonical.ndjson",
        help="Output ndjson file",
    )
    p.add_argument(
        "--config",
        "-c",
        default=None,
        help="Path to signals.yaml config file",
    )
    p.add_argument(
        "--legacy",
        action="store_true",
        help="Use v0.1 hardcoded logic (for testing)",
    )
    args = p.parse_args()

    prices = read_wide_csv(Path(args.input))

    if args.legacy:
        # Use v0.1 hardcoded logic
        records = compute_signals(prices, window=args.window, config=None)
    else:
        # Use v0.2 config-driven logic
        config_path = Path(args.config) if args.config else None
        config = load_signals_config(config_path)
        records = compute_signals_v2(prices, config)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Wrote {len(records)} canonical records to {out_path}")


if __name__ == "__main__":
    main()
