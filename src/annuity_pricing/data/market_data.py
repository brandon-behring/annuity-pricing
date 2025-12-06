"""
Market data loaders for Treasury curves, equity indices, and volatility.

Sources:
- FRED: Treasury yields, SOFR, VIX
- Yahoo Finance: Equity index levels
- Stooq: Backup for equity indices

See: codex-pricing-resources-rila-fia-myga.md Section 2
"""

import os
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

from annuity_pricing.config.settings import SETTINGS


class MarketDataError(Exception):
    """Raised when market data fetching fails."""

    pass


# =============================================================================
# FRED Data (Treasury Curves, VIX)
# =============================================================================

def fetch_fred_series(
    series_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    api_key: Optional[str] = None,
) -> pd.Series:
    """
    Fetch a single FRED series.

    Parameters
    ----------
    series_id : str
        FRED series ID (e.g., 'DGS10', 'VIXCLS')
    start_date : str, optional
        Start date in 'YYYY-MM-DD' format
    end_date : str, optional
        End date in 'YYYY-MM-DD' format
    api_key : str, optional
        FRED API key. If not provided, uses FRED_API_KEY env var.

    Returns
    -------
    pd.Series
        Time series with date index

    Raises
    ------
    MarketDataError
        If fetching fails
    """
    try:
        from fredapi import Fred
    except ImportError:
        raise MarketDataError(
            "CRITICAL: fredapi not installed. Run: pip install fredapi"
        )

    key = api_key or os.environ.get("FRED_API_KEY")
    if not key:
        raise MarketDataError(
            "CRITICAL: FRED API key required. Set FRED_API_KEY environment "
            "variable or pass api_key parameter. "
            "Get free key at: https://fred.stlouisfed.org/docs/api/api_key.html"
        )

    try:
        fred = Fred(api_key=key)
        data = fred.get_series(
            series_id,
            observation_start=start_date,
            observation_end=end_date,
        )

        if data is None or data.empty:
            raise MarketDataError(
                f"CRITICAL: No data returned for FRED series '{series_id}'"
            )

        return data

    except Exception as e:
        raise MarketDataError(
            f"CRITICAL: Failed to fetch FRED series '{series_id}': {e}"
        ) from e


def fetch_treasury_curve(
    as_of_date: Optional[str] = None,
    api_key: Optional[str] = None,
) -> pd.DataFrame:
    """
    Fetch Treasury yield curve from FRED.

    Parameters
    ----------
    as_of_date : str, optional
        Date for curve snapshot ('YYYY-MM-DD'). If None, uses latest.
    api_key : str, optional
        FRED API key

    Returns
    -------
    pd.DataFrame
        DataFrame with columns: tenor (years), yield (decimal)

    Examples
    --------
    >>> curve = fetch_treasury_curve('2024-01-15')
    >>> curve
       tenor   yield
    0    0.25  0.0535
    1    1.00  0.0498
    2    2.00  0.0432
    ...
    """
    # Treasury series and their tenors in years
    treasury_series = {
        "DTB3": 0.25,    # 3-month
        "DGS1": 1.0,     # 1-year
        "DGS2": 2.0,     # 2-year
        "DGS5": 5.0,     # 5-year
        "DGS10": 10.0,   # 10-year
        "DGS30": 30.0,   # 30-year
    }

    # Determine date range
    if as_of_date:
        end = as_of_date
        start = (datetime.strptime(as_of_date, "%Y-%m-%d") - timedelta(days=7)).strftime(
            "%Y-%m-%d"
        )
    else:
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    results = []
    for series_id, tenor in treasury_series.items():
        try:
            data = fetch_fred_series(series_id, start, end, api_key)
            # Get most recent non-null value
            latest = data.dropna().iloc[-1] if not data.dropna().empty else None
            if latest is not None:
                results.append({
                    "tenor": tenor,
                    "yield": latest / 100.0,  # Convert from percent to decimal
                    "series": series_id,
                })
        except MarketDataError:
            # Skip missing series but continue
            pass

    if not results:
        raise MarketDataError(
            "CRITICAL: Could not fetch any Treasury yields from FRED"
        )

    return pd.DataFrame(results)


def fetch_vix(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    api_key: Optional[str] = None,
) -> pd.Series:
    """
    Fetch VIX (implied volatility proxy) from FRED.

    Parameters
    ----------
    start_date : str, optional
        Start date
    end_date : str, optional
        End date
    api_key : str, optional
        FRED API key

    Returns
    -------
    pd.Series
        VIX values (already in percentage points, e.g., 20 = 20%)
    """
    return fetch_fred_series("VIXCLS", start_date, end_date, api_key)


# =============================================================================
# Yahoo Finance Data (Equity Indices)
# =============================================================================

def fetch_yahoo_index(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Fetch equity index data from Yahoo Finance.

    Parameters
    ----------
    ticker : str
        Yahoo Finance ticker (e.g., '^GSPC' for S&P 500)
    start_date : str, optional
        Start date ('YYYY-MM-DD')
    end_date : str, optional
        End date ('YYYY-MM-DD')

    Returns
    -------
    pd.DataFrame
        OHLCV data with date index

    Raises
    ------
    MarketDataError
        If fetching fails
    """
    try:
        import yfinance as yf
    except ImportError:
        raise MarketDataError(
            "CRITICAL: yfinance not installed. Run: pip install yfinance"
        )

    try:
        ticker_obj = yf.Ticker(ticker)
        data = ticker_obj.history(start=start_date, end=end_date)

        if data is None or data.empty:
            raise MarketDataError(
                f"CRITICAL: No data returned for Yahoo ticker '{ticker}'"
            )

        return data

    except Exception as e:
        raise MarketDataError(
            f"CRITICAL: Failed to fetch Yahoo ticker '{ticker}': {e}"
        ) from e


def fetch_sp500(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Fetch S&P 500 index data.

    Parameters
    ----------
    start_date : str, optional
        Start date
    end_date : str, optional
        End date

    Returns
    -------
    pd.DataFrame
        S&P 500 OHLCV data
    """
    return fetch_yahoo_index("^GSPC", start_date, end_date)


def fetch_russell2000(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Fetch Russell 2000 index data.

    Parameters
    ----------
    start_date : str, optional
        Start date
    end_date : str, optional
        End date

    Returns
    -------
    pd.DataFrame
        Russell 2000 OHLCV data
    """
    return fetch_yahoo_index("^RUT", start_date, end_date)


def fetch_nasdaq100(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Fetch NASDAQ-100 index data.

    Parameters
    ----------
    start_date : str, optional
        Start date
    end_date : str, optional
        End date

    Returns
    -------
    pd.DataFrame
        NASDAQ-100 OHLCV data
    """
    return fetch_yahoo_index("^NDX", start_date, end_date)


# =============================================================================
# Stooq Backup (Fallback for Yahoo)
# =============================================================================

def fetch_stooq_index(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Fetch index data from Stooq (backup source).

    Parameters
    ----------
    symbol : str
        Stooq symbol (e.g., '^SPX' for S&P 500)
    start_date : str, optional
        Start date
    end_date : str, optional
        End date

    Returns
    -------
    pd.DataFrame
        OHLCV data

    Notes
    -----
    Stooq is a free backup source if Yahoo Finance is unavailable.
    URL format: https://stooq.com/q/d/l/?s={symbol}&d1={start}&d2={end}
    """
    # Build URL
    base_url = SETTINGS.market.stooq_base_url

    params = [f"s={symbol}"]
    if start_date:
        params.append(f"d1={start_date.replace('-', '')}")
    if end_date:
        params.append(f"d2={end_date.replace('-', '')}")

    url = base_url + "?" + "&".join(params)

    try:
        data = pd.read_csv(url)

        if data.empty:
            raise MarketDataError(
                f"CRITICAL: No data returned from Stooq for '{symbol}'"
            )

        # Parse date column
        data["Date"] = pd.to_datetime(data["Date"])
        data = data.set_index("Date").sort_index()

        return data

    except Exception as e:
        raise MarketDataError(
            f"CRITICAL: Failed to fetch Stooq data for '{symbol}': {e}"
        ) from e


# =============================================================================
# Convenience Functions
# =============================================================================

def get_risk_free_rate(
    tenor_years: float = 1.0,
    as_of_date: Optional[str] = None,
    api_key: Optional[str] = None,
) -> float:
    """
    Get risk-free rate for a given tenor.

    Parameters
    ----------
    tenor_years : float
        Desired tenor in years
    as_of_date : str, optional
        Date for rate ('YYYY-MM-DD')
    api_key : str, optional
        FRED API key

    Returns
    -------
    float
        Risk-free rate as decimal (e.g., 0.045 = 4.5%)

    Examples
    --------
    >>> rate = get_risk_free_rate(1.0)  # 1-year rate
    >>> 0.0 < rate < 0.20  # Sanity check
    True
    """
    curve = fetch_treasury_curve(as_of_date, api_key)

    # Find closest tenor
    curve["tenor_diff"] = abs(curve["tenor"] - tenor_years)
    closest = curve.loc[curve["tenor_diff"].idxmin()]

    return float(closest["yield"])


def calculate_index_return(
    prices: pd.Series,
    start_date: str,
    end_date: str,
) -> float:
    """
    Calculate price return between two dates.

    [T1] FIA/RILA typically use price return (not total return).

    Parameters
    ----------
    prices : pd.Series
        Price series with date index
    start_date : str
        Start date
    end_date : str
        End date

    Returns
    -------
    float
        Return as decimal (e.g., 0.10 = 10%)

    Raises
    ------
    ValueError
        If dates not found in prices
    """
    try:
        start_price = prices.loc[start_date]
        end_price = prices.loc[end_date]
    except KeyError as e:
        raise ValueError(
            f"CRITICAL: Date not found in price series: {e}"
        ) from e

    return (end_price - start_price) / start_price
