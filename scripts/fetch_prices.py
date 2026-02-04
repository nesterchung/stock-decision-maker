#!/usr/bin/env python3

import argparse
import sys
from datetime import datetime, date
from pathlib import Path
import yaml
import yfinance as yf
import pandas as pd


def load_signals_config():
    """Load signals.yaml to extract required tickers."""
    config_path = Path(__file__).parent.parent / "signals.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    tickers = set()

    # Add bench ticker if present
    if "bench" in config:
        tickers.add(config["bench"])

    # Add tickers from signal definitions
    for signal_def in config.get("signals", {}).values():
        if "a" in signal_def:
            tickers.add(signal_def["a"])
        if "b" in signal_def:
            tickers.add(signal_def["b"])
        if "ticker" in signal_def:
            tickers.add(signal_def["ticker"])

    return sorted(list(tickers))


def download_prices(tickers, start_date, end_date):
    """Download adjusted close prices for all tickers."""
    print(
        f"Downloading prices for {len(tickers)} tickers from {start_date} to {end_date}"
    )

    data = yf.download(tickers, start=start_date, end=end_date, progress=False)

    # Validate download and extract adjusted close prices
    adj_close_data = {}
    missing_tickers = []

    for ticker in tickers:
        try:
            # Handle different yfinance data structures
            if hasattr(data, "columns") and len(data.columns.levels) > 1:
                # MultiIndex case
                if ("Adj Close", ticker) in data.columns:
                    adj_close_data[ticker] = data[("Adj Close", ticker)]
                elif ("Close", ticker) in data.columns:
                    adj_close_data[ticker] = data[("Close", ticker)]
                else:
                    missing_tickers.append(ticker)
            else:
                # Simple DataFrame case
                if ticker in data.columns:
                    ticker_data = data[ticker]
                    if "Adj Close" in ticker_data.columns:
                        adj_close_data[ticker] = ticker_data["Adj Close"]
                    elif "Close" in ticker_data.columns:
                        adj_close_data[ticker] = ticker_data["Close"]
                    else:
                        missing_tickers.append(ticker)
                else:
                    missing_tickers.append(ticker)

        except Exception as e:
            print(f"Error processing {ticker}: {e}")
            missing_tickers.append(ticker)

    if missing_tickers:
        raise ValueError(f"Failed to download data for tickers: {missing_tickers}")

    return pd.DataFrame(adj_close_data)


def align_trading_days(prices_df):
    """Align trading days across all tickers (inner join on date)."""
    # Remove any rows with NaN values (non-trading days for some tickers)
    clean_df = prices_df.dropna()

    if clean_df.empty:
        raise ValueError("No trading days with complete data found after alignment")

    return clean_df


def normalize_and_save(prices_df, output_path):
    """Convert to wide format and save as CSV for engine consumption."""
    # prices_df is already in wide format: date index, ticker columns
    # We just need to ensure date is a column and save properly

    # Validate output format
    required_tickers = ["XLE", "TLT", "XLK", "XLU", "SPY"]
    missing_tickers = [t for t in required_tickers if t not in prices_df.columns]

    if missing_tickers:
        raise ValueError(f"Missing required tickers: {missing_tickers}")

    if prices_df.isnull().any().any():
        raise ValueError("Output contains missing values")

    # Save to CSV with date as column (not index)
    output_df = prices_df.reset_index()

    # Handle both 'Date' and 'date' column names
    date_col = None
    for col in ["Date", "date"]:
        if col in output_df.columns:
            date_col = col
            break

    if date_col is None:
        raise ValueError(
            f"No date column found after reset_index. Available columns: {list(output_df.columns)}"
        )

    # Rename to lowercase 'date' if needed
    if date_col != "date":
        output_df = output_df.rename(columns={date_col: "date"})

    # Sort by date
    output_df = output_df.sort_values("date")

    # Save in the format engine expects
    output_df.to_csv(output_path, index=False)
    print(f"Saved {len(output_df)} trading days to {output_path}")

    # Save in the format engine expects
    output_df.to_csv(output_path, index=False)
    print(f"Saved {len(output_df)} trading days to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch price data for Market State Engine"
    )
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", help="End date (YYYY-MM-DD, default=today)")
    args = parser.parse_args()

    # Parse dates
    try:
        start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Invalid start date format: {args.start}")

    if args.end:
        try:
            end_date = datetime.strptime(args.end, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"Invalid end date format: {args.end}")
    else:
        end_date = date.today()

    if end_date <= start_date:
        raise ValueError("End date must be after start date")

    # Load tickers from signals.yaml
    tickers = load_signals_config()

    if not tickers:
        raise ValueError("No tickers found in signals.yaml")

    print(f"Required tickers: {tickers}")

    # Download prices
    prices_df = download_prices(tickers, start_date, end_date)

    # Align trading days
    aligned_df = align_trading_days(prices_df)

    # Save normalized output
    output_path = Path(__file__).parent.parent / "data" / "prices.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    normalize_and_save(aligned_df, output_path)


if __name__ == "__main__":
    main()
