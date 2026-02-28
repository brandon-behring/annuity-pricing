"""
Competitive positioning analysis for annuity products.

Determines where a product's rate falls within the market distribution.
Supports filtering by product type, duration, and other attributes.

See: METHODOLOGY.md Section 5
See: docs/knowledge/domain/competitive_analysis.md
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PositionResult:
    """
    Immutable competitive position result.

    Attributes
    ----------
    rate : float
        Product rate being analyzed
    percentile : float
        Percentile rank (0-100, higher = more competitive)
    rank : int
        Absolute rank (1 = highest rate)
    total_products : int
        Total comparable products in analysis
    quartile : int
        Quartile (1=top 25%, 2=25-50%, 3=50-75%, 4=bottom 25%)
    position_label : str
        Human-readable position ('Top Quartile', 'Above Median', etc.)
    """

    rate: float
    percentile: float
    rank: int
    total_products: int
    quartile: int
    position_label: str

    def __post_init__(self) -> None:
        """Validate position result."""
        if not 0 <= self.percentile <= 100:
            raise ValueError(f"CRITICAL: percentile must be 0-100, got {self.percentile}")
        if self.rank < 1:
            raise ValueError(f"CRITICAL: rank must be >= 1, got {self.rank}")
        if self.quartile not in (1, 2, 3, 4):
            raise ValueError(f"CRITICAL: quartile must be 1-4, got {self.quartile}")


@dataclass(frozen=True)
class DistributionStats:
    """
    Distribution statistics for rate analysis.

    Attributes
    ----------
    min : float
        Minimum rate
    max : float
        Maximum rate
    mean : float
        Mean rate
    median : float
        Median rate
    std : float
        Standard deviation
    q1 : float
        25th percentile
    q3 : float
        75th percentile
    count : int
        Number of products
    """

    min: float
    max: float
    mean: float
    median: float
    std: float
    q1: float
    q3: float
    count: int


class PositioningAnalyzer:
    """
    Competitive positioning analyzer for annuity products.

    Analyzes rate positioning relative to market, supporting
    filtering by product type, duration, company, and other attributes.

    [T2] Based on WINK competitive data patterns.

    Examples
    --------
    >>> analyzer = PositioningAnalyzer()
    >>> position = analyzer.analyze_position(
    ...     rate=0.045,
    ...     market_data=wink_df,
    ...     product_group="MYGA",
    ...     guarantee_duration=5
    ... )
    >>> position.percentile
    65.0
    """

    def __init__(
        self,
        rate_column: str = "fixedRate",
        duration_column: str = "guaranteeDuration",
        product_group_column: str = "productGroup",
        status_column: str = "status",
        company_column: str = "companyName",
    ):
        """
        Initialize positioning analyzer.

        Parameters
        ----------
        rate_column : str
            Column containing product rates
        duration_column : str
            Column containing guarantee duration
        product_group_column : str
            Column containing product group (MYGA, FIA, RILA)
        status_column : str
            Column containing product status
        company_column : str
            Column containing company name
        """
        self.rate_column = rate_column
        self.duration_column = duration_column
        self.product_group_column = product_group_column
        self.status_column = status_column
        self.company_column = company_column

    def analyze_position(
        self,
        rate: float,
        market_data: pd.DataFrame,
        product_group: str | None = None,
        guarantee_duration: int | None = None,
        duration_tolerance: int = 1,
        status: str = "current",
        exclude_company: str | None = None,
    ) -> PositionResult:
        """
        Analyze competitive position of a rate.

        Parameters
        ----------
        rate : float
            Rate to analyze (decimal)
        market_data : pd.DataFrame
            Market data with rate and attribute columns
        product_group : str, optional
            Filter to specific product group (MYGA, FIA, RILA)
        guarantee_duration : int, optional
            Filter to similar duration products
        duration_tolerance : int, default 1
            Years tolerance for duration matching
        status : str, default "current"
            Filter to specific status
        exclude_company : str, optional
            Exclude a specific company from analysis

        Returns
        -------
        PositionResult
            Complete position analysis

        Raises
        ------
        ValueError
            If no comparable products found
        """
        # Filter to comparable products
        comparables = self._filter_comparables(
            market_data=market_data,
            product_group=product_group,
            guarantee_duration=guarantee_duration,
            duration_tolerance=duration_tolerance,
            status=status,
            exclude_company=exclude_company,
        )

        rates = comparables[self.rate_column].dropna()

        if rates.empty:
            raise ValueError(
                "CRITICAL: No comparable products found for positioning analysis. "
                f"Filters: product_group={product_group}, duration={guarantee_duration}, "
                f"status={status}"
            )

        # Calculate percentile
        percentile = self._calculate_percentile(rate, rates)

        # Calculate rank (1 = highest rate)
        rank = int((rates > rate).sum() + 1)

        # Calculate quartile
        quartile = self._calculate_quartile(percentile)

        # Generate position label
        position_label = self._get_position_label(percentile, quartile)

        return PositionResult(
            rate=rate,
            percentile=percentile,
            rank=rank,
            total_products=len(rates),
            quartile=quartile,
            position_label=position_label,
        )

    def get_distribution_stats(
        self,
        market_data: pd.DataFrame,
        product_group: str | None = None,
        guarantee_duration: int | None = None,
        duration_tolerance: int = 1,
        status: str = "current",
    ) -> DistributionStats:
        """
        Get distribution statistics for rate analysis.

        Parameters
        ----------
        market_data : pd.DataFrame
            Market data
        product_group : str, optional
            Filter to specific product group
        guarantee_duration : int, optional
            Filter to similar duration
        duration_tolerance : int, default 1
            Years tolerance for duration matching
        status : str, default "current"
            Filter to specific status

        Returns
        -------
        DistributionStats
            Summary statistics for the distribution
        """
        comparables = self._filter_comparables(
            market_data=market_data,
            product_group=product_group,
            guarantee_duration=guarantee_duration,
            duration_tolerance=duration_tolerance,
            status=status,
        )

        rates = comparables[self.rate_column].dropna()

        if rates.empty:
            raise ValueError("CRITICAL: No comparable products found for distribution analysis.")

        return DistributionStats(
            min=float(rates.min()),
            max=float(rates.max()),
            mean=float(rates.mean()),
            median=float(rates.median()),
            std=float(rates.std()),
            q1=float(np.percentile(rates, 25)),
            q3=float(np.percentile(rates, 75)),
            count=len(rates),
        )

    def get_percentile_thresholds(
        self,
        market_data: pd.DataFrame,
        percentiles: list[float] | None = None,
        product_group: str | None = None,
        guarantee_duration: int | None = None,
        duration_tolerance: int = 1,
        status: str = "current",
    ) -> dict[float, float]:
        """
        Get rate thresholds for specific percentiles.

        Parameters
        ----------
        market_data : pd.DataFrame
            Market data
        percentiles : list[float], optional
            Percentiles to calculate. Default: [25, 50, 75, 90, 95]
        product_group : str, optional
            Filter to specific product group
        guarantee_duration : int, optional
            Filter to similar duration
        duration_tolerance : int, default 1
            Years tolerance
        status : str, default "current"
            Filter to status

        Returns
        -------
        dict[float, float]
            Mapping of percentile → rate threshold
        """
        if percentiles is None:
            percentiles = [25.0, 50.0, 75.0, 90.0, 95.0]

        comparables = self._filter_comparables(
            market_data=market_data,
            product_group=product_group,
            guarantee_duration=guarantee_duration,
            duration_tolerance=duration_tolerance,
            status=status,
        )

        rates = comparables[self.rate_column].dropna()

        if rates.empty:
            raise ValueError("CRITICAL: No comparable products found for percentile calculation.")

        return {p: float(np.percentile(rates, p)) for p in percentiles}

    def compare_to_peers(
        self,
        rate: float,
        company: str,
        market_data: pd.DataFrame,
        product_group: str | None = None,
        guarantee_duration: int | None = None,
        duration_tolerance: int = 1,
        top_n: int = 10,
    ) -> pd.DataFrame:
        """
        Compare rate to peer companies.

        Parameters
        ----------
        rate : float
            Rate to compare
        company : str
            Company name (will be highlighted in results)
        market_data : pd.DataFrame
            Market data
        product_group : str, optional
            Filter to product group
        guarantee_duration : int, optional
            Filter to duration
        duration_tolerance : int, default 1
            Years tolerance
        top_n : int, default 10
            Number of top competitors to show

        Returns
        -------
        pd.DataFrame
            Peer comparison with columns: company, rate, rank, vs_target
        """
        comparables = self._filter_comparables(
            market_data=market_data,
            product_group=product_group,
            guarantee_duration=guarantee_duration,
            duration_tolerance=duration_tolerance,
        )

        if comparables.empty:
            raise ValueError("CRITICAL: No comparable products found for peer comparison.")

        # Group by company and get max rate
        company_rates = (
            comparables.groupby(self.company_column)[self.rate_column]
            .max()
            .sort_values(ascending=False)
        )

        # Build comparison DataFrame
        results = []
        for i, (comp_name, comp_rate) in enumerate(company_rates.head(top_n).items(), 1):
            results.append(
                {
                    "company": comp_name,
                    "rate": comp_rate,
                    "rank": i,
                    "vs_target_bps": (comp_rate - rate) * 10000,
                    "is_target": comp_name == company,
                }
            )

        # Add target company if not in top N
        if company not in company_rates.head(top_n).index:
            if company in company_rates.index:
                target_rate = company_rates[company]
                target_rank = (company_rates > target_rate).sum() + 1
                results.append(
                    {
                        "company": company,
                        "rate": target_rate,
                        "rank": int(target_rank),
                        "vs_target_bps": (target_rate - rate) * 10000,
                        "is_target": True,
                    }
                )

        return pd.DataFrame(results)

    def _filter_comparables(
        self,
        market_data: pd.DataFrame,
        product_group: str | None = None,
        guarantee_duration: int | None = None,
        duration_tolerance: int = 1,
        status: str | None = None,
        exclude_company: str | None = None,
    ) -> pd.DataFrame:
        """Filter market data to comparable products."""
        df = market_data.copy()

        # Filter by status
        if status and self.status_column in df.columns:
            df = df[df[self.status_column] == status]

        # Filter by product group
        if product_group and self.product_group_column in df.columns:
            df = df[df[self.product_group_column] == product_group]

        # Filter by duration
        if guarantee_duration is not None and self.duration_column in df.columns:
            df = df[
                (df[self.duration_column] >= guarantee_duration - duration_tolerance)
                & (df[self.duration_column] <= guarantee_duration + duration_tolerance)
            ]

        # Exclude specific company
        if exclude_company and self.company_column in df.columns:
            df = df[df[self.company_column] != exclude_company]

        return df

    def _calculate_percentile(self, value: float, distribution: pd.Series) -> float:
        """Calculate percentile of value within distribution."""
        count_le = (distribution <= value).sum()
        return float((count_le / len(distribution)) * 100)

    def _calculate_quartile(self, percentile: float) -> int:
        """Calculate quartile from percentile."""
        if percentile >= 75:
            return 1
        elif percentile >= 50:
            return 2
        elif percentile >= 25:
            return 3
        else:
            return 4

    def _get_position_label(self, percentile: float, quartile: int) -> str:
        """Get human-readable position label."""
        if percentile >= 90:
            return "Top 10%"
        elif percentile >= 75:
            return "Top Quartile"
        elif percentile >= 50:
            return "Above Median"
        elif percentile >= 25:
            return "Below Median"
        else:
            return "Bottom Quartile"
