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


def read_wide_csv(path: Path):
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.set_index("date")
    # Ensure required columns exist
    required = ["XLE", "TLT", "XLK", "XLU", "SPY"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in prices CSV: {missing}")
    return df


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
