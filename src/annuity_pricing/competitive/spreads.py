"""
Spread analysis over Treasury for annuity products.

Calculates spreads over duration-matched Treasury yields.
Supports historical spread analysis and market comparison.

See: METHODOLOGY.md Section 5
See: docs/knowledge/domain/competitive_analysis.md
"""

from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SpreadResult:
    """
    Immutable spread analysis result.

    Attributes
    ----------
    product_rate : float
        Product rate (decimal)
    treasury_rate : float
        Matched-duration Treasury rate (decimal)
    spread_bps : float
        Spread in basis points
    spread_pct : float
        Spread as percentage of Treasury
    duration : int
        Duration used for matching
    as_of_date : date
        Date of analysis
    """

    product_rate: float
    treasury_rate: float
    spread_bps: float
    spread_pct: float
    duration: int
    as_of_date: date


@dataclass(frozen=True)
class SpreadDistribution:
    """
    Distribution of spreads in the market.

    Attributes
    ----------
    min_bps : float
        Minimum spread
    max_bps : float
        Maximum spread
    mean_bps : float
        Mean spread
    median_bps : float
        Median spread
    std_bps : float
        Standard deviation
    q1_bps : float
        25th percentile
    q3_bps : float
        75th percentile
    count : int
        Number of products
    """

    min_bps: float
    max_bps: float
    mean_bps: float
    median_bps: float
    std_bps: float
    q1_bps: float
    q3_bps: float
    count: int


# Treasury duration mapping (years to FRED series)
TREASURY_SERIES = {
    1: "DGS1",  # 1-Year Treasury
    2: "DGS2",  # 2-Year Treasury
    3: "DGS3",  # 3-Year Treasury (interpolate if not available)
    5: "DGS5",  # 5-Year Treasury
    7: "DGS7",  # 7-Year Treasury
    10: "DGS10",  # 10-Year Treasury
}


class SpreadAnalyzer:
    """
    Treasury spread analyzer for annuity products.

    Calculates spreads over duration-matched Treasury yields
    and provides market spread distribution analysis.

    [T1] Spread = Product Rate - Treasury Rate
    [T2] Typical MYGA spreads: 100-200 bps over matched Treasury

    Examples
    --------
    >>> analyzer = SpreadAnalyzer()
    >>> spread = analyzer.calculate_spread(
    ...     product_rate=0.045,
    ...     treasury_rate=0.04,
    ...     duration=5
    ... )
    >>> spread.spread_bps
    50.0
    """

    def __init__(
        self,
        rate_column: str = "fixedRate",
        duration_column: str = "guaranteeDuration",
        product_group_column: str = "productGroup",
        status_column: str = "status",
    ):
        """
        Initialize spread analyzer.

        Parameters
        ----------
        rate_column : str
            Column containing product rates
        duration_column : str
            Column containing guarantee duration
        product_group_column : str
            Column containing product group
        status_column : str
            Column containing product status
        """
        self.rate_column = rate_column
        self.duration_column = duration_column
        self.product_group_column = product_group_column
        self.status_column = status_column

    def calculate_spread(
        self,
        product_rate: float,
        treasury_rate: float,
        duration: int,
        as_of_date: date | None = None,
    ) -> SpreadResult:
        """
        Calculate spread over Treasury.

        Parameters
        ----------
        product_rate : float
            Product rate (decimal)
        treasury_rate : float
            Treasury rate for matched duration (decimal)
        duration : int
            Duration in years
        as_of_date : date, optional
            Date of analysis

        Returns
        -------
        SpreadResult
            Complete spread analysis
        """
        if treasury_rate <= 0:
            raise ValueError(f"CRITICAL: treasury_rate must be > 0, got {treasury_rate}")

        spread_decimal = product_rate - treasury_rate
        spread_bps = spread_decimal * 10000
        spread_pct = (spread_decimal / treasury_rate) * 100

        return SpreadResult(
            product_rate=product_rate,
            treasury_rate=treasury_rate,
            spread_bps=spread_bps,
            spread_pct=spread_pct,
            duration=duration,
            as_of_date=as_of_date or date.today(),
        )

    def calculate_market_spreads(
        self,
        market_data: pd.DataFrame,
        treasury_curve: dict[int, float],
        product_group: str | None = None,
        status: str = "current",
    ) -> pd.DataFrame:
        """
        Calculate spreads for all products in market data.

        Parameters
        ----------
        market_data : pd.DataFrame
            Market data with rate and duration columns
        treasury_curve : dict[int, float]
            Mapping of duration → Treasury rate
        product_group : str, optional
            Filter to specific product group
        status : str, default "current"
            Filter to specific status

        Returns
        -------
        pd.DataFrame
            Original data with spread_bps column added
        """
        df = market_data.copy()

        # Apply filters
        if status and self.status_column in df.columns:
            df = df[df[self.status_column] == status]

        if product_group and self.product_group_column in df.columns:
            df = df[df[self.product_group_column] == product_group]

        if df.empty:
            raise ValueError("CRITICAL: No products found after filtering.")

        # Calculate spreads
        def get_spread(row: pd.Series) -> float | None:
            duration = row.get(self.duration_column)
            rate = row.get(self.rate_column)

            if pd.isna(duration) or pd.isna(rate):
                return None

            # Find closest Treasury rate
            treasury_rate = self._interpolate_treasury(int(duration), treasury_curve)
            if treasury_rate is None:
                return None

            return (rate - treasury_rate) * 10000

        df["spread_bps"] = df.apply(get_spread, axis=1)

        return df

    def get_spread_distribution(
        self,
        market_data: pd.DataFrame,
        treasury_curve: dict[int, float],
        product_group: str | None = None,
        guarantee_duration: int | None = None,
        duration_tolerance: int = 1,
        status: str = "current",
    ) -> SpreadDistribution:
        """
        Get distribution of spreads in the market.

        Parameters
        ----------
        market_data : pd.DataFrame
            Market data
        treasury_curve : dict[int, float]
            Treasury curve
        product_group : str, optional
            Filter to product group
        guarantee_duration : int, optional
            Filter to duration
        duration_tolerance : int, default 1
            Years tolerance
        status : str, default "current"
            Filter to status

        Returns
        -------
        SpreadDistribution
            Spread distribution statistics
        """
        # Calculate spreads
        df = self.calculate_market_spreads(
            market_data=market_data,
            treasury_curve=treasury_curve,
            product_group=product_group,
            status=status,
        )

        # Apply duration filter
        if guarantee_duration is not None and self.duration_column in df.columns:
            df = df[
                (df[self.duration_column] >= guarantee_duration - duration_tolerance)
                & (df[self.duration_column] <= guarantee_duration + duration_tolerance)
            ]

        spreads = df["spread_bps"].dropna()

        if spreads.empty:
            raise ValueError("CRITICAL: No valid spreads calculated for distribution analysis.")

        return SpreadDistribution(
            min_bps=float(spreads.min()),
            max_bps=float(spreads.max()),
            mean_bps=float(spreads.mean()),
            median_bps=float(spreads.median()),
            std_bps=float(spreads.std()),
            q1_bps=float(np.percentile(spreads, 25)),
            q3_bps=float(np.percentile(spreads, 75)),
            count=len(spreads),
        )

    def analyze_spread_position(
        self,
        spread_bps: float,
        market_data: pd.DataFrame,
        treasury_curve: dict[int, float],
        product_group: str | None = None,
        guarantee_duration: int | None = None,
        duration_tolerance: int = 1,
    ) -> dict[str, Any]:
        """
        Analyze where a spread falls within the market distribution.

        Parameters
        ----------
        spread_bps : float
            Spread to analyze (basis points)
        market_data : pd.DataFrame
            Market data
        treasury_curve : dict[int, float]
            Treasury curve
        product_group : str, optional
            Filter to product group
        guarantee_duration : int, optional
            Filter to duration
        duration_tolerance : int, default 1
            Years tolerance

        Returns
        -------
        dict
            Analysis with percentile, rank, and distribution stats
        """
        # Get market spreads
        df = self.calculate_market_spreads(
            market_data=market_data,
            treasury_curve=treasury_curve,
            product_group=product_group,
        )

        # Apply duration filter
        if guarantee_duration is not None and self.duration_column in df.columns:
            df = df[
                (df[self.duration_column] >= guarantee_duration - duration_tolerance)
                & (df[self.duration_column] <= guarantee_duration + duration_tolerance)
            ]

        spreads = df["spread_bps"].dropna()

        if spreads.empty:
            raise ValueError("CRITICAL: No valid spreads for position analysis.")

        # Calculate percentile
        percentile = float((spreads <= spread_bps).sum() / len(spreads) * 100)

        # Calculate rank (higher spread = lower rank number)
        rank = int((spreads > spread_bps).sum() + 1)

        return {
            "spread_bps": spread_bps,
            "percentile": percentile,
            "rank": rank,
            "total_products": len(spreads),
            "market_median_bps": float(spreads.median()),
            "vs_median_bps": spread_bps - float(spreads.median()),
        }

    def spread_by_duration(
        self,
        market_data: pd.DataFrame,
        treasury_curve: dict[int, float],
        product_group: str | None = None,
        status: str = "current",
    ) -> pd.DataFrame:
        """
        Analyze average spreads by duration.

        Parameters
        ----------
        market_data : pd.DataFrame
            Market data
        treasury_curve : dict[int, float]
            Treasury curve
        product_group : str, optional
            Filter to product group
        status : str, default "current"
            Filter to status

        Returns
        -------
        pd.DataFrame
            Summary by duration with mean/median spreads
        """
        df = self.calculate_market_spreads(
            market_data=market_data,
            treasury_curve=treasury_curve,
            product_group=product_group,
            status=status,
        )

        # Group by duration
        summary = (
            df.groupby(self.duration_column)["spread_bps"]
            .agg(["count", "mean", "median", "std", "min", "max"])
            .round(1)
        )

        summary.columns = [
            "count",
            "mean_spread_bps",
            "median_spread_bps",
            "std_bps",
            "min_bps",
            "max_bps",
        ]

        return summary.reset_index()

    def _interpolate_treasury(
        self,
        duration: int,
        treasury_curve: dict[int, float],
    ) -> float | None:
        """
        Interpolate Treasury rate for a given duration.

        Uses linear interpolation between available maturities.
        """
        if not treasury_curve:
            return None

        # Exact match
        if duration in treasury_curve:
            return treasury_curve[duration]

        # Find surrounding maturities
        available = sorted(treasury_curve.keys())

        if duration < min(available):
            return treasury_curve[min(available)]

        if duration > max(available):
            return treasury_curve[max(available)]

        # Linear interpolation
        lower = max(d for d in available if d < duration)
        upper = min(d for d in available if d > duration)

        lower_rate = treasury_curve[lower]
        upper_rate = treasury_curve[upper]

        # Linear interpolation
        weight = (duration - lower) / (upper - lower)
        return lower_rate + weight * (upper_rate - lower_rate)


def build_treasury_curve(
    rates: dict[str, float],
) -> dict[int, float]:
    """
    Build Treasury curve from FRED series rates.

    Parameters
    ----------
    rates : dict[str, float]
        Mapping of FRED series → rate (e.g., {'DGS5': 0.04})

    Returns
    -------
    dict[int, float]
        Mapping of duration → rate
    """
    # Reverse mapping
    series_to_duration = {v: k for k, v in TREASURY_SERIES.items()}

    curve = {}
    for series, rate in rates.items():
        if series in series_to_duration:
            duration = series_to_duration[series]
            curve[duration] = rate

    return curve
