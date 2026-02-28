"""
FIA (Fixed Indexed Annuity) Pricer.

Prices FIA products with embedded index-linked options:
- Cap: Point-to-point with maximum return cap
- Participation: Partial participation in index returns
- Spread: Index return minus spread/margin
- Trigger: Performance triggered bonus

[T1] FIA products have 0% floor (principal protection).

See: METHODOLOGY.md Section 3.2
See: docs/knowledge/domain/crediting_methods.md
"""

import logging
from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

from scipy.stats import norm

from annuity_pricing.data.schemas import FIAProduct
from annuity_pricing.options.payoffs.fia import (
    MonthlyAveragePayoff,
    create_fia_payoff,
)
from annuity_pricing.options.pricing.black_scholes import (
    _calculate_d1_d2,
    black_scholes_call,
)
from annuity_pricing.options.simulation.gbm import GBMParams
from annuity_pricing.options.simulation.monte_carlo import MonteCarloEngine
from annuity_pricing.options.volatility_models import (
    HestonVolatility,
    SABRVolatility,
    VolatilityModel,
    VolatilityModelType,
)
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
    fair_cap: float | None = None
    fair_participation: float | None = None
    expected_credit: float = 0.0


@dataclass(frozen=True)
class MarketParams:
    """
    Market parameters for FIA pricing.

    [T1] Hybrid architecture for volatility models:
    - volatility: Required scalar field (backward compatible, default BS)
    - vol_model: Optional override for stochastic volatility (Heston/SABR)

    If vol_model is provided, pricing dispatcher uses that model.
    Otherwise, falls back to Black-Scholes with scalar volatility.

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
        Used for Black-Scholes or as fallback when vol_model not provided.
    vol_model : VolatilityModel, optional
        Stochastic volatility model override (Heston or SABR).
        If provided, takes precedence over scalar volatility for option pricing.

    Examples
    --------
    >>> # Standard Black-Scholes (backward compatible)
    >>> market = MarketParams(spot=100, risk_free_rate=0.05, dividend_yield=0.02, volatility=0.20)

    >>> # Heston stochastic volatility
    >>> from annuity_pricing.options.pricing.heston import HestonParams
    >>> from annuity_pricing.options.volatility_models import HestonVolatility
    >>> heston = HestonVolatility(HestonParams(v0=0.04, kappa=2.0, theta=0.04, sigma=0.3, rho=-0.7))
    >>> market = MarketParams(spot=100, risk_free_rate=0.05, dividend_yield=0.02, volatility=0.20, vol_model=heston)
    """

    spot: float
    risk_free_rate: float
    dividend_yield: float
    volatility: float
    vol_model: VolatilityModel | None = None

    def __post_init__(self) -> None:
        """Validate market params."""
        if self.spot <= 0:
            raise ValueError(f"CRITICAL: spot must be > 0, got {self.spot}")
        if self.volatility < 0:
            raise ValueError(f"CRITICAL: volatility must be >= 0, got {self.volatility}")

    def uses_stochastic_vol(self) -> bool:
        """Check if stochastic volatility model is configured."""
        return self.vol_model is not None

    def get_vol_model_type(self) -> VolatilityModelType:
        """
        Get the volatility model type.

        Returns
        -------
        VolatilityModelType
            BLACK_SCHOLES if no vol_model, otherwise the model's type.
        """
        if self.vol_model is None:
            return VolatilityModelType.BLACK_SCHOLES
        return self.vol_model.get_model_type()


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
        seed: int | None = None,
    ):
        if option_budget_pct < 0:
            raise ValueError(f"CRITICAL: option_budget_pct must be >= 0, got {option_budget_pct}")

        self.market_params = market_params
        self.option_budget_pct = option_budget_pct
        self.n_mc_paths = n_mc_paths
        self.seed = seed

        # Initialize MC engine
        self.mc_engine = MonteCarloEngine(n_paths=n_mc_paths, antithetic=True, seed=seed)

    def price(  # type: ignore[override]  # Subclass has specific params
        self,
        product: FIAProduct,
        as_of_date: date | None = None,
        term_years: float | None = None,
        premium: float = 100.0,
    ) -> FIAPricingResult:
        """
        Price FIA product.

        [T3] Modeling Assumptions:
        - Risk-neutral pricing (no real-world drift)
        - Single-period (no interim crediting)
        - No fees, hedging frictions, or surrender charges
        - Constant volatility (GBM)

        Parameters
        ----------
        product : FIAProduct
            FIA product to price
        as_of_date : date, optional
            Valuation date
        term_years : float, optional
            Investment term in years. If None, uses product.term_years.
            CRITICAL: Must be explicitly provided or available from product.
        premium : float, default 100.0
            Premium amount for scaling

        Returns
        -------
        FIAPricingResult
            Present value and embedded option metrics

        Raises
        ------
        ValueError
            If term_years is not provided and product.term_years is None
        """
        if not isinstance(product, FIAProduct):
            raise ValueError(f"CRITICAL: Expected FIAProduct, got {type(product).__name__}")

        # [F.1] Resolve term_years: require explicit value or from product
        if term_years is None:
            term_years = getattr(product, "term_years", None)
            if term_years is not None:
                term_years = float(term_years)
        if term_years is None or term_years <= 0:
            raise ValueError(
                f"CRITICAL: term_years required and must be > 0, got {term_years}. "
                f"Specify term_years parameter or set product.term_years."
            )

        # Determine crediting method
        method, params = self._determine_crediting_method(product)

        # [F.1] Calculate option budget with TIME VALUE OF MONEY
        # Option budget is the present value of annual hedge spend over term.
        # Uses annuity-immediate factor: PV of $1/year for n years at rate r
        #
        # Formula: a_n = (1 - (1 + r)^(-n)) / r
        #
        # [FIX] Previously used linear scaling (budget = pct * term) which
        # ignored time value. Discounted approach is more accurate for
        # multi-year terms. See: codex-audit-report.md Finding 3
        r = self.market_params.risk_free_rate
        if r > 1e-8:  # Avoid division by zero
            annuity_factor = (1 - (1 + r) ** (-term_years)) / r
        else:
            # At r=0, annuity factor equals term (linear case)
            annuity_factor = term_years
        option_budget = premium * self.option_budget_pct * annuity_factor

        # Price embedded option using Black-Scholes
        embedded_option_value = self._price_embedded_option(method, params, term_years, premium)

        # Calculate expected credit via Monte Carlo
        expected_credit = self._calculate_expected_credit(method, params, term_years)

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
            comparables = comparables[comparables["indexingMethod"] == kwargs["indexing_method"]]

        if comparables.empty:
            raise ValueError(
                "CRITICAL: No comparable FIA products found. Check filters and market data."
            )

        # Determine which metric to use
        if product.cap_rate is not None:
            rate = product.cap_rate
            rate_col = "capRate"
        elif product.participation_rate is not None:
            rate = product.participation_rate
            rate_col = "participationRate"
        else:
            raise ValueError("CRITICAL: FIA product must have cap_rate or participation_rate")

        # Get distribution of comparable rates
        distribution = comparables[rate_col].dropna()

        if distribution.empty:
            raise ValueError(f"CRITICAL: No comparable products with {rate_col} found")

        percentile = self._calculate_percentile(rate, distribution)
        rank = int((distribution > rate).sum() + 1)

        return CompetitivePosition(
            rate=rate,
            percentile=percentile,
            rank=rank,
            total_products=len(distribution),
        )

    def _determine_crediting_method(self, product: FIAProduct) -> tuple[str, dict]:
        """
        Determine crediting method and extract parameters.

        [F.3] Detects monthly averaging from indexing_method field.
        Monthly averaging is path-dependent and uses MonthlyAveragePayoff.

        Returns
        -------
        tuple[str, dict]
            (method_name, method_params)
        """
        # [F.3] Check for monthly averaging first (orthogonal to crediting type)
        is_monthly_avg = False
        if product.indexing_method is not None:
            indexing_lower = product.indexing_method.lower()
            if (
                "monthly" in indexing_lower
                or "averaging" in indexing_lower
                or "average" in indexing_lower
            ):
                is_monthly_avg = True

        if is_monthly_avg:
            # Monthly averaging currently only supports cap-style crediting
            if product.cap_rate is not None:
                return "monthly_average", {"cap_rate": product.cap_rate}
            else:
                # [NEVER FAIL SILENTLY] Monthly averaging with participation/spread not yet supported
                raise ValueError(
                    f"FIA product '{product.product_name}' uses monthly averaging "
                    f"(indexing_method='{product.indexing_method}') but monthly averaging "
                    "currently only supports cap_rate crediting. "
                    "Specify cap_rate or use point-to-point indexing."
                )

        # Standard point-to-point crediting methods
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

    def _price_call_option(
        self,
        strike: float,
        term_years: float,
    ) -> float:
        """
        Price a call option using the appropriate volatility model.

        [T1] Dispatcher routes to Black-Scholes, Heston, or SABR based on
        the vol_model configured in market_params.

        Parameters
        ----------
        strike : float
            Strike price
        term_years : float
            Time to expiry in years

        Returns
        -------
        float
            Call option price
        """
        m = self.market_params
        model_type = m.get_vol_model_type()

        if model_type == VolatilityModelType.BLACK_SCHOLES:
            # Standard Black-Scholes with scalar volatility
            return black_scholes_call(
                m.spot, strike, m.risk_free_rate, m.dividend_yield, m.volatility, term_years
            )

        elif model_type == VolatilityModelType.HESTON:
            # Heston stochastic volatility via COS method
            from annuity_pricing.options.payoffs.base import OptionType
            from annuity_pricing.options.pricing.heston import heston_price

            heston_vol = m.vol_model
            if not isinstance(heston_vol, HestonVolatility):
                raise TypeError(
                    f"CRITICAL: Expected HestonVolatility for HESTON model, "
                    f"got {type(heston_vol).__name__}"
                )

            return heston_price(
                spot=m.spot,
                strike=strike,
                rate=m.risk_free_rate,
                dividend=m.dividend_yield,
                time=term_years,
                params=heston_vol.params,
                option_type=OptionType.CALL,
                method="cos",  # COS is most accurate (0% error vs QuantLib)
            )

        elif model_type == VolatilityModelType.SABR:
            # SABR: compute implied vol, then use Black-Scholes
            from annuity_pricing.options.pricing.sabr import sabr_price_call

            sabr_vol = m.vol_model
            if not isinstance(sabr_vol, SABRVolatility):
                raise TypeError(
                    f"CRITICAL: Expected SABRVolatility for SABR model, "
                    f"got {type(sabr_vol).__name__}"
                )

            return sabr_price_call(
                spot=m.spot,
                strike=strike,
                rate=m.risk_free_rate,
                dividend=m.dividend_yield,
                time=term_years,
                params=sabr_vol.params,
            )

        else:
            raise ValueError(
                f"CRITICAL: Unknown volatility model type: {model_type}. "
                f"Supported: BLACK_SCHOLES, HESTON, SABR"
            )

    def _price_embedded_option(
        self,
        method: str,
        params: dict,
        term_years: float,
        premium: float,
    ) -> float:
        """
        Price the embedded option using appropriate volatility model.

        [T1] Uses _price_call_option dispatcher for all option pricing.
        Supports Black-Scholes, Heston, and SABR models.

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
            atm_call = self._price_call_option(m.spot, term_years)

            # OTM call at cap strike (S * (1 + cap))
            if cap_rate > 0:
                cap_strike = m.spot * (1 + cap_rate)
                otm_call = self._price_call_option(cap_strike, term_years)
                capped_call_value = atm_call - otm_call
            else:
                capped_call_value = 0.0

            return (capped_call_value / m.spot) * premium

        elif method == "participation":
            # Participation = par_rate × ATM call
            par_rate = params["participation_rate"]
            atm_call = self._price_call_option(m.spot, term_years)
            return par_rate * (atm_call / m.spot) * premium

        elif method == "spread":
            # Spread: approximately ATM call with adjusted strike
            spread_rate = params["spread_rate"]
            effective_strike = m.spot * (1 + spread_rate)
            spread_call = self._price_call_option(effective_strike, term_years)
            return (spread_call / m.spot) * premium

        elif method == "trigger":
            # [T1] Digital option pricing using risk-neutral probability
            # PV(digital) = e^(-rT) * N(d2) * trigger_rate * notional
            # where N(d2) is the risk-neutral probability of finishing ITM
            #
            # NOTE: For stochastic vol models, digital pricing differs.
            # This currently uses BS-based d2; future enhancement could
            # use model-specific digital pricing.
            trigger_rate = params["trigger_rate"]

            # Calculate d1, d2 for ATM option (strike = spot)
            # Use scalar volatility for d2 (BS approximation)
            d1, d2 = _calculate_d1_d2(
                m.spot, m.spot, m.risk_free_rate, m.dividend_yield, m.volatility, term_years
            )

            # N(d2) = risk-neutral probability of S_T > K
            prob_itm = norm.cdf(d2)
            discount_factor = np.exp(-m.risk_free_rate * term_years)

            return discount_factor * trigger_rate * premium * prob_itm

        elif method == "monthly_average":
            # [F.3] Monthly averaging - use capped call approximation
            # Note: This is an upper bound; actual monthly average option
            # value is typically lower due to averaging reducing volatility.
            # Use MC result (expected_credit) for accurate pricing.
            cap_rate = params["cap_rate"]

            atm_call = self._price_call_option(m.spot, term_years)

            if cap_rate > 0:
                cap_strike = m.spot * (1 + cap_rate)
                otm_call = self._price_call_option(cap_strike, term_years)
                capped_call_value = atm_call - otm_call
            else:
                capped_call_value = 0.0

            return (capped_call_value / m.spot) * premium

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

        [T1] Uses GBM or Heston paths based on vol_model configuration.
        Dispatches to appropriate MC method for path generation.

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

        # Determine n_steps based on payoff type
        # [FIX] Monthly averaging requires 12 observations per year, not 252 daily
        # See: docs/knowledge/derivations/monte_carlo.md (ObservationSchedule design)
        if isinstance(payoff, MonthlyAveragePayoff):
            n_steps = int(12 * term_years)  # 12 monthly observations per year
        else:
            n_steps = 252  # Default daily for other payoffs

        # Dispatch to appropriate MC method based on vol_model
        model_type = self.market_params.get_vol_model_type()

        if model_type == VolatilityModelType.HESTON:
            # Use Heston paths for MC simulation
            heston_vol = self.market_params.vol_model
            assert isinstance(heston_vol, HestonVolatility), "Expected HestonVolatility"

            mc_result = self.mc_engine.price_with_payoff_heston(
                spot=self.market_params.spot,
                rate=self.market_params.risk_free_rate,
                dividend=self.market_params.dividend_yield,
                time_to_expiry=term_years,
                heston_params=heston_vol.params,
                payoff=payoff,
                n_steps=n_steps,
            )
        else:
            # Use GBM paths (default: BS or SABR falls back to GBM paths)
            gbm_params = GBMParams(
                spot=self.market_params.spot,
                rate=self.market_params.risk_free_rate,
                dividend=self.market_params.dividend_yield,
                volatility=self.market_params.volatility,
                time_to_expiry=term_years,
            )
            mc_result = self.mc_engine.price_with_payoff(gbm_params, payoff, n_steps=n_steps)

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
        Uses pricing dispatcher for consistent volatility model handling.

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

        # ATM call value using dispatcher
        atm_call = self._price_call_option(m.spot, term_years)
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

            otm_call = self._price_call_option(cap_strike, term_years)
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
        Uses pricing dispatcher for consistent volatility model handling.

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

        # ATM call value using dispatcher
        atm_call = self._price_call_option(m.spot, term_years)
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
        term_years: float | None = None,
        premium: float = 100.0,
    ) -> pd.DataFrame:
        """
        Price multiple FIA products.

        Parameters
        ----------
        products : list[FIAProduct]
            FIA products to price
        term_years : float, optional
            Investment term. If None, uses each product's term_years.
            Products without term_years will raise ValueError.
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
