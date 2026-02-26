"""
Company and product rankings for annuity market analysis.

Provides rankings by rate, spread, and other metrics.
Supports market share analysis and competitor tracking.

See: METHODOLOGY.md Section 5
See: docs/knowledge/domain/competitive_analysis.md
"""

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class CompanyRanking:
    """
    Company ranking result.

    Attributes
    ----------
    company : str
        Company name
    rank : int
        Overall rank (1 = best)
    best_rate : float
        Best rate offered
    avg_rate : float
        Average rate across products
    product_count : int
        Number of products
    duration_coverage : list[int]
        Durations covered
    """

    company: str
    rank: int
    best_rate: float
    avg_rate: float
    product_count: int
    duration_coverage: tuple[int, ...]


@dataclass(frozen=True)
class ProductRanking:
    """
    Product ranking result.

    Attributes
    ----------
    company : str
        Company name
    product : str
        Product name
    rank : int
        Rank among comparable products
    rate : float
        Product rate
    duration : int
        Guarantee duration
    """

    company: str
    product: str
    rank: int
    rate: float
    duration: int


class RankingAnalyzer:
    """
    Company and product ranking analyzer.

    Provides rankings by rate, spread, and product count.
    Supports filtering by product type and duration.

    [T2] Based on WINK competitive data patterns.

    Examples
    --------
    >>> analyzer = RankingAnalyzer()
    >>> rankings = analyzer.rank_companies(
    ...     market_data=wink_df,
    ...     product_group="MYGA",
    ...     guarantee_duration=5
    ... )
    >>> rankings[0].company
    'Top Life Insurance'
    """

    def __init__(
        self,
        rate_column: str = "fixedRate",
        duration_column: str = "guaranteeDuration",
        product_group_column: str = "productGroup",
        status_column: str = "status",
        company_column: str = "companyName",
        product_column: str = "productName",
    ):
        """
        Initialize ranking analyzer.

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
        company_column : str
            Column containing company name
        product_column : str
            Column containing product name
        """
        self.rate_column = rate_column
        self.duration_column = duration_column
        self.product_group_column = product_group_column
        self.status_column = status_column
        self.company_column = company_column
        self.product_column = product_column

    def rank_companies(
        self,
        market_data: pd.DataFrame,
        product_group: str | None = None,
        guarantee_duration: int | None = None,
        duration_tolerance: int = 1,
        status: str = "current",
        rank_by: str = "best_rate",
        top_n: int | None = None,
    ) -> list[CompanyRanking]:
        """
        Rank companies by rate performance.

        Parameters
        ----------
        market_data : pd.DataFrame
            Market data
        product_group : str, optional
            Filter to product group
        guarantee_duration : int, optional
            Filter to duration
        duration_tolerance : int, default 1
            Years tolerance
        status : str, default "current"
            Filter to status
        rank_by : str, default "best_rate"
            Ranking criterion: 'best_rate', 'avg_rate', 'product_count'
        top_n : int, optional
            Limit to top N companies

        Returns
        -------
        list[CompanyRanking]
            Ranked list of companies
        """
        df = self._filter_data(
            market_data=market_data,
            product_group=product_group,
            guarantee_duration=guarantee_duration,
            duration_tolerance=duration_tolerance,
            status=status,
        )

        if df.empty:
            raise ValueError(
                "CRITICAL: No products found for company ranking."
            )

        # Aggregate by company
        company_stats = (
            df.groupby(self.company_column)
            .agg({
                self.rate_column: ["max", "mean", "count"],
                self.duration_column: lambda x: tuple(sorted(x.dropna().unique())),
            })
        )

        company_stats.columns = [
            "best_rate",
            "avg_rate",
            "product_count",
            "duration_coverage",
        ]

        # Sort by ranking criterion
        if rank_by == "best_rate":
            company_stats = company_stats.sort_values("best_rate", ascending=False)
        elif rank_by == "avg_rate":
            company_stats = company_stats.sort_values("avg_rate", ascending=False)
        elif rank_by == "product_count":
            company_stats = company_stats.sort_values("product_count", ascending=False)
        else:
            raise ValueError(f"CRITICAL: Invalid rank_by value: {rank_by}")

        # Build rankings
        rankings = []
        for i, row in enumerate(company_stats.itertuples(), 1):
            if top_n and i > top_n:
                break

            rankings.append(
                CompanyRanking(
                    company=str(row.Index),
                    rank=i,
                    best_rate=float(row.best_rate),
                    avg_rate=float(row.avg_rate),
                    product_count=int(row.product_count),
                    duration_coverage=tuple(int(d) for d in row.duration_coverage),
                )
            )

        return rankings

    def rank_products(
        self,
        market_data: pd.DataFrame,
        product_group: str | None = None,
        guarantee_duration: int | None = None,
        duration_tolerance: int = 1,
        status: str = "current",
        top_n: int | None = None,
    ) -> list[ProductRanking]:
        """
        Rank individual products by rate.

        Parameters
        ----------
        market_data : pd.DataFrame
            Market data
        product_group : str, optional
            Filter to product group
        guarantee_duration : int, optional
            Filter to duration
        duration_tolerance : int, default 1
            Years tolerance
        status : str, default "current"
            Filter to status
        top_n : int, optional
            Limit to top N products

        Returns
        -------
        list[ProductRanking]
            Ranked list of products
        """
        df = self._filter_data(
            market_data=market_data,
            product_group=product_group,
            guarantee_duration=guarantee_duration,
            duration_tolerance=duration_tolerance,
            status=status,
        )

        if df.empty:
            raise ValueError(
                "CRITICAL: No products found for product ranking."
            )

        # Sort by rate
        df = df.sort_values(self.rate_column, ascending=False)

        # Build rankings
        rankings = []
        for i, row in enumerate(df.itertuples(), 1):
            if top_n and i > top_n:
                break

            rankings.append(
                ProductRanking(
                    company=getattr(row, self.company_column, "Unknown"),
                    product=getattr(row, self.product_column, "Unknown"),
                    rank=i,
                    rate=float(getattr(row, self.rate_column)),
                    duration=int(getattr(row, self.duration_column, 0)),
                )
            )

        return rankings

    def get_company_rank(
        self,
        company: str,
        market_data: pd.DataFrame,
        product_group: str | None = None,
        guarantee_duration: int | None = None,
        duration_tolerance: int = 1,
        status: str = "current",
    ) -> CompanyRanking | None:
        """
        Get ranking for a specific company.

        Parameters
        ----------
        company : str
            Company name to look up
        market_data : pd.DataFrame
            Market data
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
        CompanyRanking or None
            Company ranking if found
        """
        rankings = self.rank_companies(
            market_data=market_data,
            product_group=product_group,
            guarantee_duration=guarantee_duration,
            duration_tolerance=duration_tolerance,
            status=status,
        )

        for ranking in rankings:
            if ranking.company.lower() == company.lower():
                return ranking

        return None

    def market_summary(
        self,
        market_data: pd.DataFrame,
        product_group: str | None = None,
        status: str = "current",
    ) -> dict[str, Any]:
        """
        Get market summary statistics.

        Parameters
        ----------
        market_data : pd.DataFrame
            Market data
        product_group : str, optional
            Filter to product group
        status : str, default "current"
            Filter to status

        Returns
        -------
        dict
            Market summary with counts and statistics
        """
        df = self._filter_data(
            market_data=market_data,
            product_group=product_group,
            status=status,
        )

        if df.empty:
            raise ValueError("CRITICAL: No products found for market summary.")

        return {
            "total_products": len(df),
            "total_companies": df[self.company_column].nunique(),
            "rate_min": float(df[self.rate_column].min()),
            "rate_max": float(df[self.rate_column].max()),
            "rate_mean": float(df[self.rate_column].mean()),
            "rate_median": float(df[self.rate_column].median()),
            "durations_available": sorted(df[self.duration_column].unique().tolist()),
        }

    def rate_leaders_by_duration(
        self,
        market_data: pd.DataFrame,
        product_group: str | None = None,
        status: str = "current",
    ) -> pd.DataFrame:
        """
        Get rate leaders for each duration.

        Parameters
        ----------
        market_data : pd.DataFrame
            Market data
        product_group : str, optional
            Filter to product group
        status : str, default "current"
            Filter to status

        Returns
        -------
        pd.DataFrame
            Leaders by duration with company, rate, rank columns
        """
        df = self._filter_data(
            market_data=market_data,
            product_group=product_group,
            status=status,
        )

        if df.empty:
            raise ValueError("CRITICAL: No products found for rate leaders.")

        # Get top rate for each duration
        leaders = []
        for duration in sorted(df[self.duration_column].unique()):
            duration_df = df[df[self.duration_column] == duration]
            top = duration_df.nlargest(3, self.rate_column)

            for rank, row in enumerate(top.itertuples(), 1):
                leaders.append({
                    "duration": int(duration),
                    "rank": rank,
                    "company": getattr(row, self.company_column, "Unknown"),
                    "product": getattr(row, self.product_column, "Unknown"),
                    "rate": float(getattr(row, self.rate_column)),
                })

        return pd.DataFrame(leaders)

    def competitive_landscape(
        self,
        market_data: pd.DataFrame,
        product_group: str | None = None,
        guarantee_duration: int | None = None,
        duration_tolerance: int = 1,
        status: str = "current",
    ) -> pd.DataFrame:
        """
        Generate competitive landscape summary.

        Parameters
        ----------
        market_data : pd.DataFrame
            Market data
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
        pd.DataFrame
            Landscape with company stats and positioning
        """
        df = self._filter_data(
            market_data=market_data,
            product_group=product_group,
            guarantee_duration=guarantee_duration,
            duration_tolerance=duration_tolerance,
            status=status,
        )

        if df.empty:
            raise ValueError("CRITICAL: No products found for competitive landscape.")

        # Aggregate by company
        landscape = (
            df.groupby(self.company_column)
            .agg({
                self.rate_column: ["max", "mean", "min", "count"],
            })
        )

        landscape.columns = ["best_rate", "avg_rate", "min_rate", "product_count"]
        landscape = landscape.reset_index()

        # Calculate market percentiles
        all_best_rates = landscape["best_rate"]
        landscape["rate_percentile"] = landscape["best_rate"].apply(
            lambda x: (all_best_rates <= x).sum() / len(all_best_rates) * 100
        )

        # Add rank
        landscape = landscape.sort_values("best_rate", ascending=False)
        landscape["rank"] = range(1, len(landscape) + 1)

        # Calculate competitive tier
        landscape["tier"] = landscape["rate_percentile"].apply(
            lambda p: "Leader" if p >= 75 else "Competitive" if p >= 50 else "Follower"
        )

        return landscape.round(4)

    def _filter_data(
        self,
        market_data: pd.DataFrame,
        product_group: str | None = None,
        guarantee_duration: int | None = None,
        duration_tolerance: int = 1,
        status: str | None = None,
    ) -> pd.DataFrame:
        """Filter market data to relevant products."""
        df = market_data.copy()

        # Remove null rates
        df = df[df[self.rate_column].notna()]

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

        return df
