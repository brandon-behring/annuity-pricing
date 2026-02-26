"""
Rate recommendation engine for MYGA products.

Provides rate recommendations based on:
- Target competitive percentile
- Treasury spread targets
- Margin/profitability constraints

See: METHODOLOGY.md Section 5
See: docs/knowledge/domain/competitive_analysis.md
"""

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class RateRecommendation:
    """
    Immutable rate recommendation result.

    Attributes
    ----------
    recommended_rate : float
        Recommended rate (decimal)
    target_percentile : float
        Target competitive percentile achieved
    spread_over_treasury : float
        Spread over matched-duration Treasury (bps)
    margin_estimate : float
        Estimated margin (bps) after option/hedge costs
    confidence : str
        Confidence level: 'high', 'medium', 'low'
    rationale : str
        Explanation of recommendation
    comparable_count : int
        Number of comparable products in analysis
    """

    recommended_rate: float
    target_percentile: float
    spread_over_treasury: float | None = None
    margin_estimate: float | None = None
    confidence: str = "medium"
    rationale: str = ""
    comparable_count: int = 0

    def __post_init__(self) -> None:
        """Validate recommendation."""
        if self.recommended_rate < 0:
            raise ValueError(
                f"CRITICAL: recommended_rate must be >= 0, got {self.recommended_rate}"
            )
        if not 0 <= self.target_percentile <= 100:
            raise ValueError(
                f"CRITICAL: target_percentile must be 0-100, got {self.target_percentile}"
            )


@dataclass(frozen=True)
class MarginAnalysis:
    """
    Margin breakdown for a given rate.

    Attributes
    ----------
    gross_spread : float
        Spread over Treasury (bps)
    option_cost : float
        Estimated hedging/option cost (bps)
    expense_load : float
        Operating expense load (bps)
    net_margin : float
        Net margin after costs (bps)
    """

    gross_spread: float
    option_cost: float
    expense_load: float
    net_margin: float


class RateRecommender:
    """
    Rate recommendation engine for MYGA products.

    Provides rate recommendations based on competitive positioning,
    Treasury spreads, and margin targets.

    [T1] Rate positioning is relative to duration-matched comparables.
    [T2] Typical MYGA spreads over Treasury: 100-200 bps (from WINK data).

    Examples
    --------
    >>> recommender = RateRecommender()
    >>> rec = recommender.recommend_rate(
    ...     guarantee_duration=5,
    ...     target_percentile=75,
    ...     market_data=wink_df,
    ...     treasury_rate=0.04
    ... )
    >>> rec.recommended_rate
    0.048
    """

    def __init__(
        self,
        default_expense_load: float = 0.0050,  # 50 bps
        duration_tolerance: int = 1,
    ):
        """
        Initialize rate recommender.

        Parameters
        ----------
        default_expense_load : float, default 0.0050
            Default expense load (50 bps)
        duration_tolerance : int, default 1
            Years tolerance for duration matching
        """
        self.default_expense_load = default_expense_load
        self.duration_tolerance = duration_tolerance

    def recommend_rate(
        self,
        guarantee_duration: int,
        target_percentile: float,
        market_data: pd.DataFrame,
        treasury_rate: float | None = None,
        min_margin_bps: float = 50.0,
        **kwargs: Any,
    ) -> RateRecommendation:
        """
        Recommend rate to achieve target competitive percentile.

        Parameters
        ----------
        guarantee_duration : int
            Product duration in years
        target_percentile : float
            Target percentile (0-100, higher = more competitive)
        market_data : pd.DataFrame
            Comparable MYGA products (must have 'fixedRate', 'guaranteeDuration')
        treasury_rate : float, optional
            Treasury yield for matching duration (decimal)
        min_margin_bps : float, default 50
            Minimum acceptable margin in basis points

        Returns
        -------
        RateRecommendation
            Complete recommendation with rationale

        Raises
        ------
        ValueError
            If no comparable products found or invalid inputs
        """
        # Validate inputs
        if not 0 <= target_percentile <= 100:
            raise ValueError(
                f"CRITICAL: target_percentile must be 0-100, got {target_percentile}"
            )
        if guarantee_duration <= 0:
            raise ValueError(
                f"CRITICAL: guarantee_duration must be > 0, got {guarantee_duration}"
            )

        # Filter to comparable products
        comparables = self._get_comparables(market_data, guarantee_duration)

        if comparables.empty:
            raise ValueError(
                f"CRITICAL: No comparable MYGA products found for "
                f"duration {guarantee_duration} ± {self.duration_tolerance} years. "
                f"Check market_data filters."
            )

        rates = comparables["fixedRate"].dropna()

        if rates.empty:
            raise ValueError(
                "CRITICAL: All fixedRate values are null in comparable products."
            )

        # Calculate rate at target percentile
        recommended_rate = float(np.percentile(rates, target_percentile))

        # Calculate spread over Treasury
        spread_bps = None
        if treasury_rate is not None:
            spread_bps = (recommended_rate - treasury_rate) * 10000

        # Estimate margin (simplified - MYGA has no option cost)
        margin_bps = None
        if spread_bps is not None:
            expense_bps = self.default_expense_load * 10000
            margin_bps = spread_bps - expense_bps

        # Determine confidence
        confidence = self._assess_confidence(len(rates), target_percentile, margin_bps)

        # Build rationale
        rationale = self._build_rationale(
            recommended_rate=recommended_rate,
            target_percentile=target_percentile,
            spread_bps=spread_bps,
            margin_bps=margin_bps,
            min_margin_bps=min_margin_bps,
            comparable_count=len(rates),
        )

        return RateRecommendation(
            recommended_rate=recommended_rate,
            target_percentile=target_percentile,
            spread_over_treasury=spread_bps,
            margin_estimate=margin_bps,
            confidence=confidence,
            rationale=rationale,
            comparable_count=len(rates),
        )

    def recommend_for_spread(
        self,
        guarantee_duration: int,
        treasury_rate: float,
        target_spread_bps: float,
        market_data: pd.DataFrame,
    ) -> RateRecommendation:
        """
        Recommend rate to achieve target spread over Treasury.

        Parameters
        ----------
        guarantee_duration : int
            Product duration in years
        treasury_rate : float
            Treasury yield for matching duration (decimal)
        target_spread_bps : float
            Target spread in basis points
        market_data : pd.DataFrame
            Comparable MYGA products

        Returns
        -------
        RateRecommendation
            Complete recommendation
        """
        if treasury_rate < 0:
            raise ValueError(
                f"CRITICAL: treasury_rate must be >= 0, got {treasury_rate}"
            )

        # Calculate rate from spread target
        recommended_rate = treasury_rate + (target_spread_bps / 10000)

        # Get comparables to determine percentile
        comparables = self._get_comparables(market_data, guarantee_duration)

        if comparables.empty:
            raise ValueError(
                f"CRITICAL: No comparable products for duration {guarantee_duration}"
            )

        rates = comparables["fixedRate"].dropna()

        # Calculate percentile for this rate
        percentile = self._calculate_percentile(recommended_rate, rates)

        # Estimate margin
        expense_bps = self.default_expense_load * 10000
        margin_bps = target_spread_bps - expense_bps

        confidence = self._assess_confidence(len(rates), percentile, margin_bps)

        rationale = (
            f"Rate {recommended_rate:.3%} achieves {target_spread_bps:.0f}bps spread "
            f"over {guarantee_duration}-year Treasury ({treasury_rate:.3%}). "
            f"Positions at {percentile:.0f}th percentile among {len(rates)} comparables."
        )

        return RateRecommendation(
            recommended_rate=recommended_rate,
            target_percentile=percentile,
            spread_over_treasury=target_spread_bps,
            margin_estimate=margin_bps,
            confidence=confidence,
            rationale=rationale,
            comparable_count=len(rates),
        )

    def analyze_margin(
        self,
        rate: float,
        treasury_rate: float,
        expense_load: float | None = None,
    ) -> MarginAnalysis:
        """
        Analyze margin breakdown for a given rate.

        Parameters
        ----------
        rate : float
            Product rate (decimal)
        treasury_rate : float
            Treasury yield (decimal)
        expense_load : float, optional
            Expense load (decimal). Defaults to default_expense_load.

        Returns
        -------
        MarginAnalysis
            Breakdown of gross spread, costs, net margin
        """
        if expense_load is None:
            expense_load = self.default_expense_load

        gross_spread_bps = (rate - treasury_rate) * 10000
        option_cost_bps = 0.0  # MYGA has no option cost
        expense_bps = expense_load * 10000
        net_margin_bps = gross_spread_bps - option_cost_bps - expense_bps

        return MarginAnalysis(
            gross_spread=gross_spread_bps,
            option_cost=option_cost_bps,
            expense_load=expense_bps,
            net_margin=net_margin_bps,
        )

    def sensitivity_analysis(
        self,
        guarantee_duration: int,
        market_data: pd.DataFrame,
        treasury_rate: float,
        percentile_range: list[float] | None = None,
    ) -> pd.DataFrame:
        """
        Perform sensitivity analysis across percentile targets.

        Parameters
        ----------
        guarantee_duration : int
            Product duration
        market_data : pd.DataFrame
            Comparable products
        treasury_rate : float
            Treasury yield
        percentile_range : list[float], optional
            Percentiles to analyze. Default: [25, 50, 75, 90]

        Returns
        -------
        pd.DataFrame
            Analysis with columns: percentile, rate, spread_bps, margin_bps
        """
        if percentile_range is None:
            percentile_range = [25.0, 50.0, 75.0, 90.0]

        results = []

        for pct in percentile_range:
            try:
                rec = self.recommend_rate(
                    guarantee_duration=guarantee_duration,
                    target_percentile=pct,
                    market_data=market_data,
                    treasury_rate=treasury_rate,
                )
                results.append(
                    {
                        "percentile": pct,
                        "rate": rec.recommended_rate,
                        "spread_bps": rec.spread_over_treasury,
                        "margin_bps": rec.margin_estimate,
                        "comparable_count": rec.comparable_count,
                    }
                )
            except ValueError as e:
                # Log but continue with other percentiles
                results.append(
                    {
                        "percentile": pct,
                        "rate": None,
                        "spread_bps": None,
                        "margin_bps": None,
                        "comparable_count": 0,
                        "error": str(e),  # type: ignore[dict-item]
                    }
                )

        return pd.DataFrame(results)

    def _get_comparables(
        self,
        market_data: pd.DataFrame,
        guarantee_duration: int,
    ) -> pd.DataFrame:
        """
        Filter market data to comparable products.

        Parameters
        ----------
        market_data : pd.DataFrame
            Full market data
        guarantee_duration : int
            Target duration

        Returns
        -------
        pd.DataFrame
            Filtered to comparable products
        """
        df = market_data.copy()

        # Filter to current MYGA products
        if "status" in df.columns:
            df = df[df["status"] == "current"]

        if "productGroup" in df.columns:
            df = df[df["productGroup"] == "MYGA"]

        # Duration matching
        if "guaranteeDuration" in df.columns:
            df = df[
                (df["guaranteeDuration"] >= guarantee_duration - self.duration_tolerance)
                & (df["guaranteeDuration"] <= guarantee_duration + self.duration_tolerance)
            ]

        return df

    def _calculate_percentile(self, value: float, distribution: pd.Series) -> float:
        """Calculate percentile of value within distribution."""
        if distribution.empty:
            raise ValueError(
                "CRITICAL: Cannot calculate percentile with empty distribution"
            )
        count_le = (distribution <= value).sum()
        return float((count_le / len(distribution)) * 100)

    def _assess_confidence(
        self,
        sample_size: int,
        percentile: float,
        margin_bps: float | None,
    ) -> str:
        """
        Assess confidence level of recommendation.

        Parameters
        ----------
        sample_size : int
            Number of comparable products
        percentile : float
            Target percentile
        margin_bps : float, optional
            Estimated margin

        Returns
        -------
        str
            'high', 'medium', or 'low'
        """
        # Start with medium confidence
        score = 2

        # Sample size factors
        if sample_size >= 50:
            score += 1
        elif sample_size < 10:
            score -= 1

        # Extreme percentiles are less reliable
        if percentile > 95 or percentile < 5:
            score -= 1

        # Margin factors
        if margin_bps is not None:
            if margin_bps < 0:
                score -= 1
            elif margin_bps > 100:
                score += 1

        # Convert to confidence level
        if score >= 3:
            return "high"
        elif score <= 1:
            return "low"
        else:
            return "medium"

    def _build_rationale(
        self,
        recommended_rate: float,
        target_percentile: float,
        spread_bps: float | None,
        margin_bps: float | None,
        min_margin_bps: float,
        comparable_count: int,
    ) -> str:
        """Build human-readable rationale for recommendation."""
        parts = [
            f"Recommended rate: {recommended_rate:.3%} "
            f"(targets {target_percentile:.0f}th percentile among {comparable_count} comparables)"
        ]

        if spread_bps is not None:
            parts.append(f"Spread over Treasury: {spread_bps:.0f}bps")

        if margin_bps is not None:
            if margin_bps >= min_margin_bps:
                parts.append(
                    f"Estimated margin: {margin_bps:.0f}bps (meets {min_margin_bps:.0f}bps target)"
                )
            else:
                parts.append(
                    f"WARNING: Estimated margin {margin_bps:.0f}bps "
                    f"below {min_margin_bps:.0f}bps target"
                )

        return ". ".join(parts)
