"""
MYGA (Multi-Year Guaranteed Annuity) pricer.

MYGA is the simplest product: fixed rate locked for entire term.
See: docs/knowledge/domain/mgsv_mva.md
See: wink-research-archive/product-guides/ANNUITY_PRODUCT_GUIDE.md
"""

import logging
import warnings
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

from annuity_pricing.config.settings import SETTINGS
from annuity_pricing.data.schemas import MYGAProduct
from annuity_pricing.products.base import (
    BasePricer,
    CompetitivePosition,
    PricingResult,
)


class MYGAPricer(BasePricer):
    """
    Pricer for Multi-Year Guaranteed Annuities.

    MYGA pricing is deterministic:
    - Fixed rate for entire term
    - Principal 100% protected
    - Value = PV of guaranteed cash flows

    Examples
    --------
    >>> pricer = MYGAPricer()
    >>> product = MYGAProduct(
    ...     company_name="Example Life",
    ...     product_name="5-Year MYGA",
    ...     product_group="MYGA",
    ...     status="current",
    ...     fixed_rate=0.045,
    ...     guarantee_duration=5
    ... )
    >>> result = pricer.price(product, principal=100000, discount_rate=0.04)
    >>> result.present_value > 100000  # Worth more than principal at lower discount
    True
    """

    def price(  # type: ignore[override]  # Subclass has specific params
        self,
        product: MYGAProduct,
        as_of_date: date | None = None,
        principal: float = 100_000.0,
        discount_rate: float | None = None,
        include_mgsv: bool = True,
        premium: float | None = None,  # DEPRECATED: use principal
    ) -> PricingResult:
        """
        Price MYGA product.

        Parameters
        ----------
        product : MYGAProduct
            MYGA product to price
        as_of_date : date, optional
            Valuation date
        principal : float, default 100_000
            Initial premium amount
        discount_rate : float, optional
            Discount rate for PV calculation. If None, uses product rate.
        include_mgsv : bool, default True
            Whether to include MGSV floor in result details
        premium : float, optional
            DEPRECATED: Use 'principal' instead. Will be removed in v0.4.0.

        Returns
        -------
        PricingResult
            Present value, duration, convexity

        Raises
        ------
        ValueError
            If product missing required fields
        """
        # Handle deprecated premium parameter
        if premium is not None:
            warnings.warn(
                "DEPRECATION: 'premium' is deprecated for MYGA, use 'principal'. "
                "Will be removed in v0.4.0.",
                DeprecationWarning,
                stacklevel=2,
            )
            principal = premium

        # Validate required fields
        self.validate_product(product, ["fixed_rate", "guarantee_duration"])

        if product.guarantee_duration <= 0:
            raise ValueError(
                f"CRITICAL: guarantee_duration must be > 0, got {product.guarantee_duration}"
            )

        rate = product.fixed_rate
        years = product.guarantee_duration
        disc = discount_rate if discount_rate is not None else rate

        # Calculate maturity value (single payment at end)
        # FV = Principal * (1 + rate)^years
        maturity_value = principal * (1 + rate) ** years

        # Present value at discount rate
        # PV = FV / (1 + disc)^years
        present_value = maturity_value / (1 + disc) ** years

        # Duration (Macaulay) for zero-coupon bond = time to maturity
        # [T1] For single cash flow at T, duration = T
        duration = float(years)

        # Modified duration = Macaulay duration / (1 + disc)
        modified_duration = duration / (1 + disc)

        # Convexity for zero-coupon bond
        # [T1] Convexity = T * (T + 1) / (1 + disc)^2
        convexity = years * (years + 1) / (1 + disc) ** 2

        # Calculate MGSV floor
        mgsv = None
        if include_mgsv:
            mgsv = self._calculate_mgsv(principal, years)

        details = {
            "principal": principal,
            "fixed_rate": rate,
            "guarantee_duration": years,
            "discount_rate": disc,
            "maturity_value": maturity_value,
            "modified_duration": modified_duration,
            "mgsv": mgsv,
            "effective_yield": rate,  # For MYGA, effective yield = stated rate
        }

        return PricingResult(
            present_value=present_value,
            duration=duration,
            convexity=convexity,
            details=details,
            as_of_date=as_of_date or date.today(),
        )

    def competitive_position(
        self,
        product: MYGAProduct,
        market_data: pd.DataFrame,
        duration_match: bool = True,
        duration_tolerance: int = 1,
        **kwargs: Any,
    ) -> CompetitivePosition:
        """
        Determine competitive position of MYGA product.

        Parameters
        ----------
        product : MYGAProduct
            Product to analyze
        market_data : pd.DataFrame
            Comparable MYGA products from WINK (must have 'fixedRate',
            'guaranteeDuration', 'status' columns)
        duration_match : bool, default True
            Whether to filter to similar duration products
        duration_tolerance : int, default 1
            Years tolerance for duration matching

        Returns
        -------
        CompetitivePosition
            Percentile rank among comparable products
        """
        self.validate_product(product, ["fixed_rate", "guarantee_duration"])

        # Filter to current MYGA products
        df = market_data.copy()

        if "status" in df.columns:
            df = df[df["status"] == "current"]

        if "productGroup" in df.columns:
            df = df[df["productGroup"] == "MYGA"]

        # Duration matching
        if duration_match and "guaranteeDuration" in df.columns:
            target_duration = product.guarantee_duration
            df = df[
                (df["guaranteeDuration"] >= target_duration - duration_tolerance)
                & (df["guaranteeDuration"] <= target_duration + duration_tolerance)
            ]

        # Get rate distribution
        if "fixedRate" not in df.columns or df.empty:
            raise ValueError(
                "CRITICAL: No comparable MYGA products found in market_data. "
                "Check filters and data."
            )

        rates = df["fixedRate"].dropna()

        if rates.empty:
            raise ValueError("CRITICAL: All fixedRate values are null in comparable products.")

        # Calculate percentile (higher rate = higher percentile)
        percentile = self._calculate_percentile(product.fixed_rate, rates)

        # Calculate rank (1 = highest rate)
        rank = int((rates > product.fixed_rate).sum() + 1)

        return CompetitivePosition(
            rate=product.fixed_rate,
            percentile=percentile,
            spread_over_treasury=None,  # Will be added when treasury curve available
            rank=rank,
            total_products=len(rates),
        )

    def _calculate_mgsv(self, principal: float, years: int) -> float:
        """
        Calculate Minimum Guaranteed Surrender Value.

        [T1] MGSV = Base_Factor × Principal × (1 + MGSV_Rate)^Years

        Parameters
        ----------
        principal : float
            Initial premium
        years : int
            Years held

        Returns
        -------
        float
            MGSV floor value
        """
        base = SETTINGS.myga.mgsv_base_rate  # 87.5%
        rate = SETTINGS.myga.mgsv_rate_default  # 1%

        return base * principal * (1 + rate) ** years

    def calculate_spread_over_treasury(
        self,
        product: MYGAProduct,
        treasury_rate: float,
    ) -> float:
        """
        Calculate spread over matched-duration Treasury.

        Parameters
        ----------
        product : MYGAProduct
            MYGA product
        treasury_rate : float
            Treasury yield for matching duration (decimal)

        Returns
        -------
        float
            Spread in basis points (e.g., 50 = 0.50%)
        """
        self.validate_product(product, ["fixed_rate"])

        spread_decimal = product.fixed_rate - treasury_rate
        spread_bps = spread_decimal * 10000  # Convert to basis points

        return spread_bps

    def recommend_rate(
        self,
        target_percentile: float,
        market_data: pd.DataFrame,
        guarantee_duration: int,
        duration_tolerance: int = 1,
    ) -> float:
        """
        Recommend rate to achieve target competitive percentile.

        Parameters
        ----------
        target_percentile : float
            Desired percentile (0-100, higher = more competitive)
        market_data : pd.DataFrame
            Comparable MYGA products
        guarantee_duration : int
            Target product duration
        duration_tolerance : int, default 1
            Years tolerance for duration matching

        Returns
        -------
        float
            Recommended rate to achieve target percentile

        Examples
        --------
        >>> pricer = MYGAPricer()
        >>> rate = pricer.recommend_rate(75, market_df, 5)  # 75th percentile
        >>> rate
        0.048  # Example: 4.8% needed for 75th percentile
        """
        if not 0 <= target_percentile <= 100:
            raise ValueError(f"CRITICAL: target_percentile must be 0-100, got {target_percentile}")

        # Filter to comparable products
        df = market_data.copy()

        if "status" in df.columns:
            df = df[df["status"] == "current"]

        if "productGroup" in df.columns:
            df = df[df["productGroup"] == "MYGA"]

        if "guaranteeDuration" in df.columns:
            df = df[
                (df["guaranteeDuration"] >= guarantee_duration - duration_tolerance)
                & (df["guaranteeDuration"] <= guarantee_duration + duration_tolerance)
            ]

        if "fixedRate" not in df.columns or df.empty:
            raise ValueError("CRITICAL: No comparable MYGA products found for rate recommendation.")

        rates = df["fixedRate"].dropna()

        if rates.empty:
            raise ValueError("CRITICAL: All fixedRate values are null in comparable products.")

        # Calculate rate at target percentile
        recommended_rate = float(np.percentile(rates, target_percentile))

        return recommended_rate
