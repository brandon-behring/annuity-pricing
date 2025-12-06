"""
Base pricer abstract class for all annuity products.

All product pricers inherit from BasePricer and implement the common API.
See: CONSTITUTION.md Section 4
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Any, Optional

import pandas as pd


@dataclass(frozen=True)
class PricingResult:
    """
    Immutable result from pricing calculation.

    Attributes
    ----------
    present_value : float
        Present value of the product/liability
    duration : float, optional
        Macaulay or modified duration
    convexity : float, optional
        Convexity measure
    details : dict, optional
        Additional pricing details
    as_of_date : date, optional
        Valuation date
    """

    present_value: float
    duration: Optional[float] = None
    convexity: Optional[float] = None
    details: Optional[dict] = None
    as_of_date: Optional[date] = None

    def __post_init__(self) -> None:
        """Validate pricing result."""
        if self.present_value < 0:
            raise ValueError(
                f"CRITICAL: present_value must be >= 0, got {self.present_value}. "
                f"Negative PV indicates calculation error."
            )


@dataclass(frozen=True)
class CompetitivePosition:
    """
    Competitive positioning result.

    Attributes
    ----------
    rate : float
        The product's rate
    percentile : float
        Percentile rank (0-100) among comparable products
    spread_over_treasury : float, optional
        Spread over matched-duration Treasury
    rank : int, optional
        Absolute rank (1 = highest rate)
    total_products : int, optional
        Total comparable products
    """

    rate: float
    percentile: float
    spread_over_treasury: Optional[float] = None
    rank: Optional[int] = None
    total_products: Optional[int] = None

    def __post_init__(self) -> None:
        """Validate position."""
        if not 0 <= self.percentile <= 100:
            raise ValueError(
                f"CRITICAL: percentile must be 0-100, got {self.percentile}"
            )


class BasePricer(ABC):
    """
    Abstract base class for all product pricers.

    All pricers implement:
    - price(): Calculate present value and risk metrics
    - competitive_position(): Rank against market

    Subclasses: MYGAPricer, FIAPricer, RILAPricer
    """

    @abstractmethod
    def price(
        self,
        product: Any,
        as_of_date: Optional[date] = None,
        **kwargs: Any,
    ) -> PricingResult:
        """
        Price the product.

        Parameters
        ----------
        product : Product dataclass
            Product to price (MYGAProduct, FIAProduct, etc.)
        as_of_date : date, optional
            Valuation date. Defaults to today.
        **kwargs : Any
            Additional pricing parameters

        Returns
        -------
        PricingResult
            Present value and risk metrics

        Raises
        ------
        ValueError
            If product is invalid or missing required fields
        """
        pass

    @abstractmethod
    def competitive_position(
        self,
        product: Any,
        market_data: pd.DataFrame,
        **kwargs: Any,
    ) -> CompetitivePosition:
        """
        Determine competitive position of product.

        Parameters
        ----------
        product : Product dataclass
            Product to analyze
        market_data : pd.DataFrame
            Comparable products from WINK
        **kwargs : Any
            Additional parameters (e.g., filter criteria)

        Returns
        -------
        CompetitivePosition
            Percentile rank and spread metrics
        """
        pass

    def validate_product(self, product: Any, required_fields: list[str]) -> None:
        """
        Validate that product has required fields.

        Parameters
        ----------
        product : Any
            Product to validate
        required_fields : list[str]
            Fields that must be present and non-null

        Raises
        ------
        ValueError
            If any required field is missing or null
        """
        for field in required_fields:
            value = getattr(product, field, None)
            if value is None:
                raise ValueError(
                    f"CRITICAL: Product missing required field '{field}'. "
                    f"Cannot price without this value."
                )

    def _calculate_percentile(
        self,
        value: float,
        distribution: pd.Series,
    ) -> float:
        """
        Calculate percentile of value within distribution.

        Parameters
        ----------
        value : float
            Value to rank
        distribution : pd.Series
            Distribution to compare against

        Returns
        -------
        float
            Percentile (0-100)
        """
        if distribution.empty:
            raise ValueError(
                "CRITICAL: Cannot calculate percentile with empty distribution"
            )

        # Count values less than or equal to our value
        count_le = (distribution <= value).sum()
        percentile = (count_le / len(distribution)) * 100

        return float(percentile)
