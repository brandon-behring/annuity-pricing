"""
FIA (Fixed Indexed Annuity) Pricer.

Prices FIA products with embedded index-linked options:
- Cap: Point-to-point with maximum return cap
- Participation: Partial participation in index returns
- Spread: Index return minus spread/margin
- Trigger: Performance triggered bonus

[T1] FIA products have 0% floor (principal protection).

See: CONSTITUTION.md Section 3.2
See: docs/knowledge/domain/crediting_methods.md
"""

from dataclasses import dataclass
from datetime import date
from typing import Any, Optional

import numpy as np
import pandas as pd

from annuity_pricing.data.schemas import FIAProduct
from annuity_pricing.options.payoffs.fia import (
    CappedCallPayoff,
    ParticipationPayoff,
    SpreadPayoff,
    TriggerPayoff,
    create_fia_payoff,
)
from annuity_pricing.options.pricing.black_scholes import (
    black_scholes_call,
    price_capped_call,
    _calculate_d1_d2,
)
from scipy.stats import norm
from annuity_pricing.options.simulation.gbm import GBMParams
from annuity_pricing.options.simulation.monte_carlo import MonteCarloEngine
from annuity_pricing.products.base import BasePricer, CompetitivePosition, PricingResult


@dataclass(frozen=True)
class FIAPricingResult(PricingResult):
    """
    Extended pricing result for FIA products.

    Attributes
    ----------
    embedded_option_value : float
        Value of embedded index-linked option
    option_budget : float
        Option budget available for crediting
    fair_cap : float, optional
        Fair cap rate given option budget
    fair_participation : float, optional
        Fair participation rate given option budget
    expected_credit : float
        Expected crediting rate
    """

    embedded_option_value: float = 0.0
    option_budget: float = 0.0
    fair_cap: Optional[float] = None
    fair_participation: Optional[float] = None
    expected_credit: float = 0.0


@dataclass(frozen=True)
class MarketParams:
    """
    Market parameters for FIA pricing.

    Attributes
    ----------
    spot : float
        Current index level
    risk_free_rate : float
        Risk-free rate (annualized, decimal)
    dividend_yield : float
        Index dividend yield (annualized, decimal)
    volatility : float
        Index volatility (annualized, decimal)
    """

    spot: float
    risk_free_rate: float
    dividend_yield: float
    volatility: float

    def __post_init__(self) -> None:
        """Validate market params."""
        if self.spot <= 0:
            raise ValueError(f"CRITICAL: spot must be > 0, got {self.spot}")
        if self.volatility < 0:
            raise ValueError(f"CRITICAL: volatility must be >= 0, got {self.volatility}")


class FIAPricer(BasePricer):
    """
    Pricer for Fixed Indexed Annuity products.

    [T1] FIA = Bond + Call Option portfolio
    - Bond component provides principal protection (0% floor)
    - Option component provides index-linked upside

    Parameters
    ----------
    market_params : MarketParams
        Market parameters for option pricing
    option_budget_pct : float, default 0.03
        [T3] Option budget as percentage of premium (e.g., 0.03 = 3%)
    n_mc_paths : int, default 100000
        Number of Monte Carlo paths for simulation
    seed : int, optional
        Random seed for reproducibility

    Examples
    --------
    >>> market = MarketParams(spot=100, risk_free_rate=0.05, dividend_yield=0.02, volatility=0.20)
    >>> pricer = FIAPricer(market_params=market)
    >>> product = FIAProduct(company_name="Test", product_name="Test FIA", product_group="FIA", status="current", cap_rate=0.10)
    >>> result = pricer.price(product, term_years=1)
    """

    def __init__(
        self,
        market_params: MarketParams,
        option_budget_pct: float = 0.03,
        n_mc_paths: int = 100000,
        seed: Optional[int] = None,
    ):
        if option_budget_pct < 0:
            raise ValueError(
                f"CRITICAL: option_budget_pct must be >= 0, got {option_budget_pct}"
            )

        self.market_params = market_params
        self.option_budget_pct = option_budget_pct
        self.n_mc_paths = n_mc_paths
        self.seed = seed

        # Initialize MC engine
        self.mc_engine = MonteCarloEngine(
            n_paths=n_mc_paths, antithetic=True, seed=seed
        )

    def price(
        self,
        product: FIAProduct,
        as_of_date: Optional[date] = None,
        term_years: float = 1.0,
        premium: float = 100.0,
        **kwargs: Any,
    ) -> FIAPricingResult:
        """
        Price FIA product.

        Parameters
        ----------
        product : FIAProduct
            FIA product to price
        as_of_date : date, optional
            Valuation date
        term_years : float, default 1.0
            Investment term in years
        premium : float, default 100.0
            Premium amount for scaling

        Returns
        -------
        FIAPricingResult
            Present value and embedded option metrics
        """
        if not isinstance(product, FIAProduct):
            raise ValueError(
                f"CRITICAL: Expected FIAProduct, got {type(product).__name__}"
            )

        # Determine crediting method
        method, params = self._determine_crediting_method(product)

        # Calculate option budget
        option_budget = premium * self.option_budget_pct

        # Price embedded option using Black-Scholes
        embedded_option_value = self._price_embedded_option(
            method, params, term_years, premium
        )

        # Calculate expected credit via Monte Carlo
        expected_credit = self._calculate_expected_credit(
            method, params, term_years
        )

        # Calculate fair terms given option budget
        fair_cap = self._solve_fair_cap(term_years, option_budget, premium)
        fair_participation = self._solve_fair_participation(term_years, option_budget, premium)

        # [T1] Risk-neutral PV: discount the full maturity payoff (principal + credit)
        # At maturity, policyholder receives: premium * (1 + expected_credit)
        # PV = e^(-rT) * premium * (1 + expected_credit)
        discount_factor = np.exp(-self.market_params.risk_free_rate * term_years)
        present_value = discount_factor * premium * (1 + expected_credit)

        return FIAPricingResult(
            present_value=present_value,
            duration=term_years,  # Simplified duration
            as_of_date=as_of_date or date.today(),
            embedded_option_value=embedded_option_value,
            option_budget=option_budget,
            fair_cap=fair_cap,
            fair_participation=fair_participation,
            expected_credit=expected_credit,
            details={
                "method": method,
                "params": params,
                "term_years": term_years,
                "premium": premium,
                "discount_factor": discount_factor,
            },
        )

    def competitive_position(
        self,
        product: FIAProduct,
        market_data: pd.DataFrame,
        **kwargs: Any,
    ) -> CompetitivePosition:
        """
        Determine competitive position of FIA product.

        Parameters
        ----------
        product : FIAProduct
            FIA product to analyze
        market_data : pd.DataFrame
            Comparable FIA products from WINK
        **kwargs : Any
            Additional filters (e.g., index_used, indexing_method)

        Returns
        -------
        CompetitivePosition
            Percentile rank based on cap/participation
        """
        # Filter to FIA products
        comparables = market_data[market_data["productGroup"] == "FIA"].copy()

        # Apply additional filters
        if kwargs.get("index_used"):
            comparables = comparables[comparables["indexUsed"] == kwargs["index_used"]]
        if kwargs.get("indexing_method"):
            comparables = comparables[
                comparables["indexingMethod"] == kwargs["indexing_method"]
            ]

        if comparables.empty:
            raise ValueError(
                "CRITICAL: No comparable FIA products found. "
                "Check filters and market data."
            )

        # Determine which metric to use
        if product.cap_rate is not None:
            rate = product.cap_rate
            rate_col = "capRate"
        elif product.participation_rate is not None:
            rate = product.participation_rate
            rate_col = "participationRate"
        else:
            raise ValueError(
                "CRITICAL: FIA product must have cap_rate or participation_rate"
            )

        # Get distribution of comparable rates
        distribution = comparables[rate_col].dropna()

        if distribution.empty:
            raise ValueError(
                f"CRITICAL: No comparable products with {rate_col} found"
            )

        percentile = self._calculate_percentile(rate, distribution)
        rank = int((distribution > rate).sum() + 1)

        return CompetitivePosition(
            rate=rate,
            percentile=percentile,
            rank=rank,
            total_products=len(distribution),
        )

    def _determine_crediting_method(
        self, product: FIAProduct
    ) -> tuple[str, dict]:
        """
        Determine crediting method and extract parameters.

        Returns
        -------
        tuple[str, dict]
            (method_name, method_params)
        """
        if product.cap_rate is not None:
            return "cap", {"cap_rate": product.cap_rate}
        elif product.participation_rate is not None:
            params = {"participation_rate": product.participation_rate}
            if product.cap_rate is not None:
                params["cap_rate"] = product.cap_rate
            return "participation", params
        elif product.spread_rate is not None:
            params = {"spread_rate": product.spread_rate}
            if product.cap_rate is not None:
                params["cap_rate"] = product.cap_rate
            return "spread", params
        elif product.performance_triggered_rate is not None:
            return "trigger", {"trigger_rate": product.performance_triggered_rate}
        else:
            # [NEVER FAIL SILENTLY] No crediting method specified - raise explicit error
            raise ValueError(
                f"FIA product '{product.product_name}' has no crediting method. "
                "Expected one of: cap_rate, participation_rate, spread_rate, or performance_triggered_rate. "
                "Check WINK data or product configuration."
            )

    def _price_embedded_option(
        self,
        method: str,
        params: dict,
        term_years: float,
        premium: float,
    ) -> float:
        """
        Price the embedded option using Black-Scholes.

        Parameters
        ----------
        method : str
            Crediting method
        params : dict
            Method parameters
        term_years : float
            Option term
        premium : float
            Notional amount

        Returns
        -------
        float
            Option value
        """
        m = self.market_params

        if method == "cap":
            # Capped call = ATM call - OTM call at cap level
            cap_rate = params["cap_rate"]

            # ATM call
            atm_call = black_scholes_call(
                m.spot, m.spot, m.risk_free_rate, m.dividend_yield, m.volatility, term_years
            )

            # OTM call at cap strike (S * (1 + cap))
            if cap_rate > 0:
                cap_strike = m.spot * (1 + cap_rate)
                otm_call = black_scholes_call(
                    m.spot, cap_strike, m.risk_free_rate, m.dividend_yield, m.volatility, term_years
                )
                capped_call_value = atm_call - otm_call
            else:
                capped_call_value = 0.0

            return (capped_call_value / m.spot) * premium

        elif method == "participation":
            # Participation = par_rate × ATM call
            par_rate = params["participation_rate"]
            atm_call = black_scholes_call(
                m.spot, m.spot, m.risk_free_rate, m.dividend_yield, m.volatility, term_years
            )
            return par_rate * (atm_call / m.spot) * premium

        elif method == "spread":
            # Spread: approximately ATM call with adjusted strike
            spread_rate = params["spread_rate"]
            effective_strike = m.spot * (1 + spread_rate)
            spread_call = black_scholes_call(
                m.spot, effective_strike, m.risk_free_rate, m.dividend_yield, m.volatility, term_years
            )
            return (spread_call / m.spot) * premium

        elif method == "trigger":
            # [T1] Digital option pricing using risk-neutral probability
            # PV(digital) = e^(-rT) * N(d2) * trigger_rate * notional
            # where N(d2) is the risk-neutral probability of finishing ITM
            trigger_rate = params["trigger_rate"]

            # Calculate d1, d2 for ATM option (strike = spot)
            d1, d2 = _calculate_d1_d2(
                m.spot, m.spot, m.risk_free_rate, m.dividend_yield,
                m.volatility, term_years
            )

            # N(d2) = risk-neutral probability of S_T > K
            prob_itm = norm.cdf(d2)
            discount_factor = np.exp(-m.risk_free_rate * term_years)

            return discount_factor * trigger_rate * premium * prob_itm

        else:
            return 0.0

    def _calculate_expected_credit(
        self,
        method: str,
        params: dict,
        term_years: float,
    ) -> float:
        """
        Calculate expected credited return via Monte Carlo.

        Parameters
        ----------
        method : str
            Crediting method
        params : dict
            Method parameters
        term_years : float
            Investment term

        Returns
        -------
        float
            Expected credited return (decimal)
        """
        # Handle no crediting method case (cap_rate=0 means no upside)
        if method == "cap" and params.get("cap_rate", 0) == 0:
            return 0.0

        # Create payoff object
        payoff = create_fia_payoff(method, **params)

        # Set up GBM parameters
        gbm_params = GBMParams(
            spot=self.market_params.spot,
            rate=self.market_params.risk_free_rate,
            dividend=self.market_params.dividend_yield,
            volatility=self.market_params.volatility,
            time_to_expiry=term_years,
        )

        # Price using MC engine
        mc_result = self.mc_engine.price_with_payoff(gbm_params, payoff)

        # Convert back to return (MC gives dollar payoff)
        expected_credit = mc_result.payoffs.mean() / self.market_params.spot

        return expected_credit

    def _solve_fair_cap(
        self,
        term_years: float,
        option_budget: float,
        premium: float,
    ) -> float:
        """
        Solve for fair cap rate given option budget.

        [T1] Find cap such that capped_call_value = option_budget

        Parameters
        ----------
        term_years : float
            Option term
        option_budget : float
            Available option budget
        premium : float
            Notional amount

        Returns
        -------
        float
            Fair cap rate
        """
        m = self.market_params

        # ATM call value
        atm_call = black_scholes_call(
            m.spot, m.spot, m.risk_free_rate, m.dividend_yield, m.volatility, term_years
        )
        atm_call_pct = atm_call / m.spot

        # Budget as percentage of premium
        budget_pct = option_budget / premium

        # If budget >= ATM call, can offer unlimited cap
        if budget_pct >= atm_call_pct:
            return 1.0  # 100% cap = effectively unlimited

        # Binary search for cap rate
        low, high = 0.01, 1.0
        target = budget_pct

        for _ in range(50):  # Max iterations
            mid = (low + high) / 2
            cap_strike = m.spot * (1 + mid)

            otm_call = black_scholes_call(
                m.spot, cap_strike, m.risk_free_rate, m.dividend_yield, m.volatility, term_years
            )
            capped_value = (atm_call - otm_call) / m.spot

            if abs(capped_value - target) < 1e-6:
                return mid
            elif capped_value > target:
                high = mid
            else:
                low = mid

        return mid

    def _solve_fair_participation(
        self,
        term_years: float,
        option_budget: float,
        premium: float,
    ) -> float:
        """
        Solve for fair participation rate given option budget.

        [T1] Participation = option_budget / ATM_call_value

        Parameters
        ----------
        term_years : float
            Option term
        option_budget : float
            Available option budget
        premium : float
            Notional amount

        Returns
        -------
        float
            Fair participation rate
        """
        m = self.market_params

        # ATM call value as percentage
        atm_call = black_scholes_call(
            m.spot, m.spot, m.risk_free_rate, m.dividend_yield, m.volatility, term_years
        )
        atm_call_pct = atm_call / m.spot

        if atm_call_pct < 1e-10:
            return 0.0

        # Budget as percentage
        budget_pct = option_budget / premium

        # Participation = budget / ATM call
        participation = budget_pct / atm_call_pct

        return participation

    def price_multiple(
        self,
        products: list[FIAProduct],
        term_years: float = 1.0,
        premium: float = 100.0,
    ) -> pd.DataFrame:
        """
        Price multiple FIA products.

        Parameters
        ----------
        products : list[FIAProduct]
            FIA products to price
        term_years : float
            Investment term
        premium : float
            Premium amount

        Returns
        -------
        pd.DataFrame
            Pricing results for all products
        """
        results = []
        for product in products:
            try:
                result = self.price(product, term_years=term_years, premium=premium)
                results.append(
                    {
                        "company_name": product.company_name,
                        "product_name": product.product_name,
                        "cap_rate": product.cap_rate,
                        "participation_rate": product.participation_rate,
                        "spread_rate": product.spread_rate,
                        "present_value": result.present_value,
                        "embedded_option_value": result.embedded_option_value,
                        "expected_credit": result.expected_credit,
                        "fair_cap": result.fair_cap,
                        "fair_participation": result.fair_participation,
                    }
                )
            except ValueError as e:
                results.append(
                    {
                        "company_name": product.company_name,
                        "product_name": product.product_name,
                        "error": str(e),
                    }
                )

        return pd.DataFrame(results)
