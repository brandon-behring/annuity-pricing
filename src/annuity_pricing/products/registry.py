"""
Product Registry - Unified dispatch for all annuity product types.

Provides a single entry point for pricing any product type (MYGA, FIA, RILA).
Automatically detects product type and routes to appropriate pricer.

See: METHODOLOGY.md Section 4
"""

from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd

from annuity_pricing.data.schemas import (
    FIAProduct,
    GLWBProduct,
    MYGAProduct,
    RILAProduct,
    create_fia_from_row,
    create_myga_from_row,
    create_rila_from_row,
)
from annuity_pricing.products.base import BasePricer, CompetitivePosition, PricingResult
from annuity_pricing.products.fia import FIAPricer, FIAPricingResult
from annuity_pricing.products.fia import MarketParams as FIAMarketParams
from annuity_pricing.products.glwb import GLWBPricer, GLWBPricingResult
from annuity_pricing.products.myga import MYGAPricer
from annuity_pricing.products.rila import MarketParams as RILAMarketParams
from annuity_pricing.products.rila import RILAPricer, RILAPricingResult
from annuity_pricing.validation.gates import ValidationEngine

# Type alias for any product type
AnyProduct = MYGAProduct | FIAProduct | RILAProduct | GLWBProduct
AnyPricingResult = PricingResult | FIAPricingResult | RILAPricingResult | GLWBPricingResult


@dataclass(frozen=True)
class MarketEnvironment:
    """
    Unified market environment for all pricers.

    Attributes
    ----------
    risk_free_rate : float
        Risk-free rate (annualized, decimal)
    spot : float
        Current index level (for FIA/RILA)
    dividend_yield : float
        Index dividend yield (for FIA/RILA)
    volatility : float
        Index volatility (for FIA/RILA)
    option_budget_pct : float
        FIA option budget as percentage of premium
    """

    risk_free_rate: float = 0.05
    spot: float = 100.0
    dividend_yield: float = 0.02
    volatility: float = 0.20
    option_budget_pct: float = 0.03

    def __post_init__(self) -> None:
        """Validate market environment."""
        if self.risk_free_rate < -0.10 or self.risk_free_rate > 0.50:
            raise ValueError(
                f"CRITICAL: risk_free_rate {self.risk_free_rate} outside "
                f"reasonable bounds [-0.10, 0.50]"
            )
        if self.spot <= 0:
            raise ValueError(f"CRITICAL: spot must be > 0, got {self.spot}")
        if self.volatility < 0:
            raise ValueError(f"CRITICAL: volatility must be >= 0, got {self.volatility}")
        if self.option_budget_pct < 0:
            raise ValueError(
                f"CRITICAL: option_budget_pct must be >= 0, got {self.option_budget_pct}"
            )

    def to_fia_market_params(self) -> FIAMarketParams:
        """Convert to FIA market parameters."""
        return FIAMarketParams(
            spot=self.spot,
            risk_free_rate=self.risk_free_rate,
            dividend_yield=self.dividend_yield,
            volatility=self.volatility,
        )

    def to_rila_market_params(self) -> RILAMarketParams:
        """Convert to RILA market parameters."""
        return RILAMarketParams(
            spot=self.spot,
            risk_free_rate=self.risk_free_rate,
            dividend_yield=self.dividend_yield,
            volatility=self.volatility,
        )


class ProductRegistry:
    """
    Unified registry for pricing any annuity product type.

    Automatically detects product type and routes to the appropriate pricer.
    Provides consistent interface across MYGA, FIA, and RILA products.

    Parameters
    ----------
    market_env : MarketEnvironment
        Market parameters for all pricers
    n_mc_paths : int, default 100000
        Number of Monte Carlo paths for FIA/RILA pricing
    seed : int, optional
        Random seed for reproducibility

    Examples
    --------
    >>> market = MarketEnvironment(risk_free_rate=0.05)
    >>> registry = ProductRegistry(market_env=market)
    >>> myga = MYGAProduct(company_name="Test", product_name="5Y MYGA",
    ...                    product_group="MYGA", status="current",
    ...                    fixed_rate=0.045, guarantee_duration=5)
    >>> result = registry.price(myga)
    >>> result.present_value
    122.628...
    """

    # Supported product types
    SUPPORTED_TYPES = {"MYGA", "FIA", "RILA", "GLWB"}

    def __init__(
        self,
        market_env: MarketEnvironment,
        n_mc_paths: int = 100000,
        seed: int | None = None,
        validation_engine: ValidationEngine | None = None,
    ):
        self.market_env = market_env
        self.n_mc_paths = n_mc_paths
        self.seed = seed

        # Validation engine (uses default gates if not provided)
        self._validation_engine = validation_engine or ValidationEngine()

        # Initialize pricers
        self._myga_pricer = MYGAPricer()
        self._fia_pricer = FIAPricer(
            market_params=market_env.to_fia_market_params(),
            option_budget_pct=market_env.option_budget_pct,
            n_mc_paths=n_mc_paths,
            seed=seed,
        )
        self._rila_pricer = RILAPricer(
            market_params=market_env.to_rila_market_params(),
            n_mc_paths=n_mc_paths,
            seed=seed,
        )
        # GLWB pricer is lazy-initialized (has stricter validation, e.g., no negative rates)
        self._glwb_pricer: GLWBPricer | None = None

    def price(
        self,
        product: AnyProduct,
        as_of_date: date | None = None,
        validate: bool = True,
        **kwargs: Any,
    ) -> AnyPricingResult:
        """
        Price any product type.

        Automatically detects product type and routes to appropriate pricer.
        Runs validation by default; raises ValueError on HALT.

        Parameters
        ----------
        product : AnyProduct
            Product to price (MYGAProduct, FIAProduct, or RILAProduct)
        as_of_date : date, optional
            Valuation date
        validate : bool, default True
            Whether to run validation gates after pricing.
            On HALT: raises ValueError (fail-fast per CLAUDE.md).
            Set to False only for performance testing or debugging.
        **kwargs : Any
            Additional pricing parameters (term_years, premium, etc.)

        Returns
        -------
        AnyPricingResult
            Pricing result appropriate to product type

        Raises
        ------
        ValueError
            If product type is not supported, or if validation HALTs

        Examples
        --------
        >>> result = registry.price(myga_product)
        >>> result = registry.price(fia_product, term_years=1.0)
        >>> result = registry.price(rila_product, term_years=6.0, premium=100.0)
        >>> result = registry.price(myga_product, validate=False)  # Skip validation
        """
        pricer = self._get_pricer(product)

        # Filter kwargs to only those accepted by each pricer type
        # MYGAPricer: principal, discount_rate, include_mgsv
        # FIA/RILAPricer: term_years, premium
        # GLWBPricer: premium, age, max_age, gender
        if isinstance(product, MYGAProduct):
            # Inject discount_rate for MYGA if not provided
            if "discount_rate" not in kwargs:
                kwargs["discount_rate"] = self.market_env.risk_free_rate
            # Filter to only MYGA-accepted params
            myga_params = {"principal", "discount_rate", "include_mgsv", "premium"}
            kwargs = {k: v for k, v in kwargs.items() if k in myga_params}
        elif isinstance(product, GLWBProduct):
            # GLWB accepts premium, age, max_age, gender
            glwb_params = {"premium", "age", "max_age", "gender"}
            kwargs = {k: v for k, v in kwargs.items() if k in glwb_params}
        else:
            # FIA/RILA accept term_years, premium
            fia_rila_params = {"term_years", "premium"}
            kwargs = {k: v for k, v in kwargs.items() if k in fia_rila_params}

        result = pricer.price(product, as_of_date=as_of_date, **kwargs)

        # Run validation if enabled
        if validate:
            validation_context = self._build_validation_context(product, **kwargs)
            result = self._validation_engine.validate_and_raise(result, **validation_context)

        return result

    def _build_validation_context(
        self,
        product: AnyProduct,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Build validation context from product and kwargs.

        Extracts premium, cap_rate, buffer_rate for validation gates.

        Parameters
        ----------
        product : AnyProduct
            The product being priced
        **kwargs : Any
            Additional pricing parameters

        Returns
        -------
        dict[str, Any]
            Context for validation gates
        """
        context: dict[str, Any] = {}

        # Premium from kwargs or default (use realistic default for validation)
        context["premium"] = kwargs.get("premium", 100_000.0)

        # FIA-specific context
        if isinstance(product, FIAProduct):
            if product.cap_rate is not None:
                context["cap_rate"] = product.cap_rate
            if product.participation_rate is not None:
                context["participation_rate"] = product.participation_rate
            # [FIX] Include spread_rate for validation (codex-audit Finding 2)
            if product.spread_rate is not None:
                context["spread_rate"] = product.spread_rate

        # RILA-specific context
        elif isinstance(product, RILAProduct):
            if product.buffer_rate is not None:
                context["buffer_rate"] = product.buffer_rate
            if product.cap_rate is not None:
                context["cap_rate"] = product.cap_rate

        return context

    def competitive_position(
        self,
        product: AnyProduct,
        market_data: pd.DataFrame,
        **kwargs: Any,
    ) -> CompetitivePosition:
        """
        Determine competitive position of any product type.

        Parameters
        ----------
        product : AnyProduct
            Product to analyze
        market_data : pd.DataFrame
            Comparable products from WINK
        **kwargs : Any
            Additional filter criteria

        Returns
        -------
        CompetitivePosition
            Percentile rank and related metrics
        """
        pricer = self._get_pricer(product)
        return pricer.competitive_position(product, market_data, **kwargs)

    def price_from_row(
        self,
        row: dict,
        product_group: str,
        **kwargs: Any,
    ) -> AnyPricingResult:
        """
        Price product directly from a WINK DataFrame row.

        Parameters
        ----------
        row : dict
            Dictionary from DataFrame row (e.g., df.iloc[0].to_dict())
        product_group : str
            Product type ("MYGA", "FIA", or "RILA")
        **kwargs : Any
            Additional pricing parameters

        Returns
        -------
        AnyPricingResult
            Pricing result

        Examples
        --------
        >>> row = wink_df.iloc[0].to_dict()
        >>> result = registry.price_from_row(row, "MYGA")
        """
        product = self._create_product(row, product_group)
        return self.price(product, **kwargs)

    def price_multiple(
        self,
        products: list[AnyProduct],
        **kwargs: Any,
    ) -> pd.DataFrame:
        """
        Price multiple products of any type.

        Parameters
        ----------
        products : list[AnyProduct]
            List of products to price
        **kwargs : Any
            Additional pricing parameters

        Returns
        -------
        pd.DataFrame
            Pricing results for all products
        """
        results = []
        for product in products:
            try:
                result = self.price(product, **kwargs)
                result_dict = {
                    "company_name": product.company_name,
                    "product_name": product.product_name,
                    "product_group": product.product_group,
                    "present_value": result.present_value,
                    "duration": result.duration,
                }

                # Add type-specific fields
                if isinstance(result, FIAPricingResult):
                    result_dict.update(
                        {
                            "embedded_option_value": result.embedded_option_value,
                            "expected_credit": result.expected_credit,
                            "fair_cap": result.fair_cap,
                            "fair_participation": result.fair_participation,
                        }
                    )
                elif isinstance(result, RILAPricingResult):
                    result_dict.update(
                        {
                            "protection_value": result.protection_value,
                            "protection_type": result.protection_type,
                            "upside_value": result.upside_value,
                            "expected_return": result.expected_return,
                            "max_loss": result.max_loss,
                        }
                    )
                elif isinstance(result, GLWBPricingResult):
                    result_dict.update(
                        {
                            "guarantee_cost": result.guarantee_cost,
                            "prob_ruin": result.prob_ruin,
                            "mean_ruin_year": result.mean_ruin_year,
                            "prob_lapse": result.prob_lapse,
                            "mean_lapse_year": result.mean_lapse_year,
                            "n_paths": result.n_paths,
                        }
                    )

                results.append(result_dict)
            except ValueError as e:
                results.append(
                    {
                        "company_name": product.company_name,
                        "product_name": product.product_name,
                        "product_group": product.product_group,
                        "error": str(e),
                    }
                )

        return pd.DataFrame(results)

    def _get_pricer(self, product: AnyProduct) -> BasePricer:
        """
        Get appropriate pricer for product type.

        Parameters
        ----------
        product : AnyProduct
            Product to price

        Returns
        -------
        BasePricer
            Appropriate pricer instance

        Raises
        ------
        ValueError
            If product type is not supported
        """
        if isinstance(product, MYGAProduct):
            return self._myga_pricer
        elif isinstance(product, FIAProduct):
            return self._fia_pricer
        elif isinstance(product, RILAProduct):
            return self._rila_pricer
        elif isinstance(product, GLWBProduct):
            # Lazy initialization for GLWB pricer
            if self._glwb_pricer is None:
                self._glwb_pricer = GLWBPricer(
                    risk_free_rate=self.market_env.risk_free_rate,
                    volatility=self.market_env.volatility,
                    n_paths=self.n_mc_paths,
                    seed=self.seed,
                )
            return self._glwb_pricer
        else:
            raise ValueError(
                f"CRITICAL: Unsupported product type {type(product).__name__}. "
                f"Supported types: {self.SUPPORTED_TYPES}"
            )

    def _create_product(self, row: dict, product_group: str) -> AnyProduct:
        """
        Create product from WINK row.

        Parameters
        ----------
        row : dict
            Dictionary from DataFrame row
        product_group : str
            Product type

        Returns
        -------
        AnyProduct
            Appropriate product instance
        """
        product_group = product_group.upper()

        if product_group == "MYGA":
            return create_myga_from_row(row)
        elif product_group == "FIA":
            return create_fia_from_row(row)
        elif product_group == "RILA":
            return create_rila_from_row(row)
        else:
            raise ValueError(
                f"CRITICAL: Unsupported product_group '{product_group}'. "
                f"Supported types: {self.SUPPORTED_TYPES}"
            )

    def get_pricer_info(self) -> dict:
        """
        Get information about registered pricers.

        Returns
        -------
        dict
            Pricer information including market parameters
        """
        return {
            "supported_types": list(self.SUPPORTED_TYPES),
            "market_environment": {
                "risk_free_rate": self.market_env.risk_free_rate,
                "spot": self.market_env.spot,
                "dividend_yield": self.market_env.dividend_yield,
                "volatility": self.market_env.volatility,
                "option_budget_pct": self.market_env.option_budget_pct,
            },
            "n_mc_paths": self.n_mc_paths,
            "seed": self.seed,
        }


# =============================================================================
# Convenience Functions
# =============================================================================


def create_default_registry(
    risk_free_rate: float = 0.05,
    volatility: float = 0.20,
    seed: int | None = None,
) -> ProductRegistry:
    """
    Create a product registry with default market parameters.

    Parameters
    ----------
    risk_free_rate : float, default 0.05
        Risk-free rate (5%)
    volatility : float, default 0.20
        Index volatility (20%)
    seed : int, optional
        Random seed for reproducibility

    Returns
    -------
    ProductRegistry
        Configured registry

    Examples
    --------
    >>> registry = create_default_registry()
    >>> result = registry.price(myga_product)
    """
    market_env = MarketEnvironment(
        risk_free_rate=risk_free_rate,
        spot=100.0,
        dividend_yield=0.02,
        volatility=volatility,
        option_budget_pct=0.03,
    )
    return ProductRegistry(market_env=market_env, seed=seed)


def price_product(
    product: AnyProduct,
    risk_free_rate: float = 0.05,
    volatility: float = 0.20,
    **kwargs: Any,
) -> AnyPricingResult:
    """
    Quick price a single product with default parameters.

    Parameters
    ----------
    product : AnyProduct
        Product to price
    risk_free_rate : float, default 0.05
        Risk-free rate
    volatility : float, default 0.20
        Index volatility
    **kwargs : Any
        Additional pricing parameters

    Returns
    -------
    AnyPricingResult
        Pricing result

    Examples
    --------
    >>> result = price_product(myga_product)
    >>> result = price_product(fia_product, term_years=1.0)
    """
    registry = create_default_registry(
        risk_free_rate=risk_free_rate,
        volatility=volatility,
    )
    return registry.price(product, **kwargs)
