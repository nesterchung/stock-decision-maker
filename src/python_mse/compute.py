import argparse
import json
from pathlib import Path
import pandas as pd


def compute_signals(prices_wide: pd.DataFrame, window: int = 20):
    # Expect prices_wide: index=date (datetime or string), columns = tickers: XLE, TLT, XLK, XLU, SPY
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
            raise ValueError(
                f"Missing required columns in prices CSV: {missing_plain}.\n"
                f"Expected either plain tickers {required_tickers} or suffixed columns {suffixed} where suffixed means the price_field (e.g. adj_close) is included."
            )
        # Issue a warning if plain columns are used (ask to use adj_close explicitly)
        print(
            "WARNING: Input CSV uses plain ticker columns (no '_adj_close' suffix). Please ensure these values are adjusted close prices (adj_close). For strict enforcement, provide files with '<TICKER>_adj_close' columns.)"
        )
        for t in required_tickers:
            resolved_cols[t] = t

    # Reindex dataframe to required columns in canonical order
    df2 = df[[resolved_cols[t] for t in required_tickers]].copy()
    df2.columns = required_tickers
    return df2


def main():
    p = argparse.ArgumentParser(
        description="Compute Market State Engine v0.1 canonical signals"
    )
    p.add_argument(
        "--input", "-i", required=True, help="Input wide CSV with date + ticker columns"
    )
    p.add_argument("--window", "-w", type=int, default=20, help="SMA window")
    p.add_argument(
        "--out", "-o", default="data/canonical.ndjson", help="Output ndjson file"
    )
    args = p.parse_args()

    prices = read_wide_csv(Path(args.input))
    records = compute_signals(prices, window=args.window)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Wrote {len(records)} canonical records to {out_path}")


if __name__ == "__main__":
    main()
