#!/usr/bin/env python3
"""
fetch_market_data.py - Download market data for annuity pricing.

Usage:
    python scripts/fetch_market_data.py [--output-dir data/market] [--start 2020-01-01]

Data sources:
    - Treasury yields: FRED API (DGS1, DGS2, DGS5, DGS10, DGS30)
    - VIX: Yahoo Finance (^VIX)
    - S&P 500: Yahoo Finance (^GSPC)

Requires:
    - FRED_API_KEY environment variable (get free key at https://fred.stlouisfed.org/docs/api/api_key.html)
    - yfinance, fredapi packages

Output:
    - treasury_yields.parquet
    - vix.parquet
    - sp500.parquet
    - combined_market_data.parquet
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

# Color output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"


def fetch_treasury_yields(
    start_date: str = "2010-01-01",
    end_date: Optional[str] = None
) -> Optional[pd.DataFrame]:
    """
    Fetch Treasury yield curve from FRED.

    Series:
        DGS1, DGS2, DGS3, DGS5, DGS7, DGS10, DGS20, DGS30

    Returns
    -------
    pd.DataFrame
        Daily Treasury yields with columns for each maturity.
    """
    try:
        from fredapi import Fred
    except ImportError:
        print(f"{RED}Error: fredapi not installed. Run: pip install fredapi{RESET}")
        return None

    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        print(f"{YELLOW}Warning: FRED_API_KEY not set. Get free key at:{RESET}")
        print("  https://fred.stlouisfed.org/docs/api/api_key.html")
        print("  Then: export FRED_API_KEY=your_key_here")
        return None

    fred = Fred(api_key=api_key)

    series_ids = {
        "DGS1": "1Y",
        "DGS2": "2Y",
        "DGS3": "3Y",
        "DGS5": "5Y",
        "DGS7": "7Y",
        "DGS10": "10Y",
        "DGS20": "20Y",
        "DGS30": "30Y",
    }

    end_date = end_date or datetime.now().strftime("%Y-%m-%d")

    print(f"Fetching Treasury yields from FRED ({start_date} to {end_date})...")

    dfs = []
    for series_id, label in series_ids.items():
        try:
            data = fred.get_series(series_id, start_date, end_date)
            df = pd.DataFrame({label: data})
            dfs.append(df)
            print(f"  {GREEN}✓{RESET} {series_id} ({label}): {len(data)} observations")
        except Exception as e:
            print(f"  {RED}✗{RESET} {series_id}: {e}")

    if not dfs:
        return None

    result = pd.concat(dfs, axis=1)
    result.index.name = "date"

    # Convert to decimal (FRED gives percent)
    result = result / 100.0

    return result


def fetch_vix(
    start_date: str = "2010-01-01",
    end_date: Optional[str] = None
) -> Optional[pd.DataFrame]:
    """
    Fetch VIX (CBOE Volatility Index) from Yahoo Finance.

    Returns
    -------
    pd.DataFrame
        Daily VIX levels.
    """
    try:
        import yfinance as yf
    except ImportError:
        print(f"{RED}Error: yfinance not installed. Run: pip install yfinance{RESET}")
        return None

    end_date = end_date or datetime.now().strftime("%Y-%m-%d")

    print(f"Fetching VIX from Yahoo Finance ({start_date} to {end_date})...")

    try:
        vix = yf.download("^VIX", start=start_date, end=end_date, progress=False)
        if vix.empty:
            print(f"  {RED}✗{RESET} No data returned")
            return None

        result = vix[["Close"]].rename(columns={"Close": "VIX"})
        result.index.name = "date"

        # Convert to decimal (VIX is in percent)
        result["VIX"] = result["VIX"] / 100.0

        print(f"  {GREEN}✓{RESET} VIX: {len(result)} observations")
        return result

    except Exception as e:
        print(f"  {RED}✗{RESET} Error: {e}")
        return None


def fetch_sp500(
    start_date: str = "2010-01-01",
    end_date: Optional[str] = None
) -> Optional[pd.DataFrame]:
    """
    Fetch S&P 500 index from Yahoo Finance.

    Returns
    -------
    pd.DataFrame
        Daily S&P 500 levels and returns.
    """
    try:
        import yfinance as yf
    except ImportError:
        print(f"{RED}Error: yfinance not installed. Run: pip install yfinance{RESET}")
        return None

    end_date = end_date or datetime.now().strftime("%Y-%m-%d")

    print(f"Fetching S&P 500 from Yahoo Finance ({start_date} to {end_date})...")

    try:
        sp500 = yf.download("^GSPC", start=start_date, end=end_date, progress=False)
        if sp500.empty:
            print(f"  {RED}✗{RESET} No data returned")
            return None

        result = sp500[["Close"]].rename(columns={"Close": "SP500"})
        result["SP500_Return"] = result["SP500"].pct_change()
        result.index.name = "date"

        print(f"  {GREEN}✓{RESET} S&P 500: {len(result)} observations")
        return result

    except Exception as e:
        print(f"  {RED}✗{RESET} Error: {e}")
        return None


def main():
    """Fetch all market data and save to parquet files."""
    import argparse

    parser = argparse.ArgumentParser(description="Fetch market data for annuity pricing")
    parser.add_argument("--output-dir", default="data/market", help="Output directory")
    parser.add_argument("--start", default="2010-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default=None, help="End date (YYYY-MM-DD)")
    args = parser.parse_args()

    # Setup output directory
    project_root = Path(__file__).parent.parent
    output_dir = project_root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  Market Data Fetch")
    print(f"  Output: {output_dir}")
    print("=" * 60)
    print()

    datasets = {}

    # Treasury yields
    treasury = fetch_treasury_yields(args.start, args.end)
    if treasury is not None:
        treasury.to_parquet(output_dir / "treasury_yields.parquet")
        datasets["treasury"] = treasury
        print(f"  Saved: treasury_yields.parquet ({len(treasury)} rows)")
    print()

    # VIX
    vix = fetch_vix(args.start, args.end)
    if vix is not None:
        vix.to_parquet(output_dir / "vix.parquet")
        datasets["vix"] = vix
        print(f"  Saved: vix.parquet ({len(vix)} rows)")
    print()

    # S&P 500
    sp500 = fetch_sp500(args.start, args.end)
    if sp500 is not None:
        sp500.to_parquet(output_dir / "sp500.parquet")
        datasets["sp500"] = sp500
        print(f"  Saved: sp500.parquet ({len(sp500)} rows)")
    print()

    # Combined dataset
    if datasets:
        print("Creating combined dataset...")
        combined = pd.concat(datasets.values(), axis=1)
        combined = combined.ffill()  # Forward fill missing values
        combined.to_parquet(output_dir / "combined_market_data.parquet")
        print(f"  Saved: combined_market_data.parquet ({len(combined)} rows)")
        print()

        # Summary
        print("=" * 60)
        print(f"{GREEN}✓ Market data fetch complete{RESET}")
        print(f"  Files saved to: {output_dir}")
        print()
        print("Columns in combined dataset:")
        for col in combined.columns:
            non_null = combined[col].notna().sum()
            print(f"  - {col}: {non_null} observations")
    else:
        print(f"{RED}✗ No data fetched{RESET}")
        print("  Check FRED_API_KEY and network connection")
        sys.exit(1)


if __name__ == "__main__":
    main()
