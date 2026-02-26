"""
RILA (Registered Index-Linked Annuity) Pricer.

Prices RILA products with partial downside protection:
- Buffer: Insurer absorbs FIRST X% of losses
- Floor: Insurer covers losses BEYOND X%

[T1] RILAs can have negative returns (unlike FIA with 0% floor).
[T1] Buffer = Long ATM put - Short OTM put (put spread)
[T1] Floor = Long OTM put

See: METHODOLOGY.md Section 3.2
See: docs/knowledge/domain/buffer_floor.md
"""

import logging
from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)
# brentq removed - using analytical breakeven values instead

from annuity_pricing.data.schemas import RILAProduct
from annuity_pricing.options.payoffs.base import OptionType
from annuity_pricing.options.payoffs.rila import (
    BufferPayoff,
    FloorPayoff,
)
from annuity_pricing.options.pricing.black_scholes import (
    black_scholes_call,
    black_scholes_greeks,
    black_scholes_put,
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
class RILAPricingResult(PricingResult):
    """
    Extended pricing result for RILA products.

    Attributes
    ----------
    protection_value : float
        Value of downside protection (buffer or floor)
    protection_type : str
        'buffer' or 'floor'
    upside_value : float
        Value of capped upside
    expected_return : float
        Expected return from product
    max_loss : float
        Maximum possible loss
    breakeven_return : Optional[float]
        Index return needed to break even (None if not yet implemented)
    """

    protection_value: float = 0.0
    protection_type: str = ""
    upside_value: float = 0.0
    expected_return: float = 0.0
    max_loss: float = 0.0
    breakeven_return: float | None = None


@dataclass(frozen=True)
class MarketParams:
    """
    Market parameters for RILA pricing.

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


@dataclass(frozen=True)
class RILAGreeks:
    """
    Hedge Greeks for RILA product from option replication.

    [T1] Buffer = Long ATM put - Short OTM put (put spread)
    [T1] Floor = Long OTM put

    The Greeks represent the sensitivities of the embedded option
    position, useful for hedging the insurer's liability.

    Attributes
    ----------
    protection_type : str
        'buffer' or 'floor'
    delta : float
        Position delta (dV/dS), sum across all options
    gamma : float
        Position gamma (d²V/dS²)
    vega : float
        Position vega (dV/dσ) per 1% vol change
    theta : float
        Position theta (dV/dt) per day
    rho : float
        Position rho (dV/dr) per 1% rate change
    atm_put_delta : float
        Delta of ATM put component (buffer only)
    otm_put_delta : float
        Delta of OTM put component
    dollar_delta : float
        Dollar delta (delta * spot * notional)
    """

    protection_type: str
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float
    atm_put_delta: float
    otm_put_delta: float
    dollar_delta: float


class RILAPricer(BasePricer):
    """
    Pricer for Registered Index-Linked Annuity products.

    [T1] RILA = Index participation + Downside protection
    - Buffer: Absorbs first X% of losses (put spread)
    - Floor: Limits max loss to X% (long OTM put)

    Parameters
    ----------
    market_params : MarketParams
        Market parameters for option pricing
    n_mc_paths : int, default 100000
        Number of Monte Carlo paths for simulation
    seed : int, optional
        Random seed for reproducibility

    Examples
    --------
    >>> market = MarketParams(spot=100, risk_free_rate=0.05, dividend_yield=0.02, volatility=0.20)
    >>> pricer = RILAPricer(market_params=market)
    >>> product = RILAProduct(company_name="Test", product_name="10% Buffer", product_group="RILA", status="current", buffer_rate=0.10, buffer_modifier="Losses Covered Up To", cap_rate=0.15)
    >>> result = pricer.price(product, term_years=1)
    """

    def __init__(
        self,
        market_params: MarketParams,
        n_mc_paths: int = 100000,
        seed: int | None = None,
    ):
        self.market_params = market_params
        self.n_mc_paths = n_mc_paths
        self.seed = seed

        # Initialize MC engine
        self.mc_engine = MonteCarloEngine(
            n_paths=n_mc_paths, antithetic=True, seed=seed
        )

    def price(  # type: ignore[override]  # Subclass has specific params
        self,
        product: RILAProduct,
        as_of_date: date | None = None,
        term_years: float | None = None,
        premium: float = 100.0,
    ) -> RILAPricingResult:
        """
        Price RILA product.

        [T3] Modeling Assumptions:
        - Risk-neutral pricing (no real-world drift)
        - Single-period (no interim crediting)
        - No fees, hedging frictions, or surrender charges
        - Constant volatility (GBM)

        Parameters
        ----------
        product : RILAProduct
            RILA product to price
        as_of_date : date, optional
            Valuation date
        term_years : float, optional
            Investment term in years. If None, uses product.term_years.
            CRITICAL: Must be explicitly provided or available from product.
        premium : float, default 100.0
            Premium amount for scaling

        Returns
        -------
        RILAPricingResult
            Present value and protection metrics

        Raises
        ------
        ValueError
            If term_years is not provided and product.term_years is None
        """
        if not isinstance(product, RILAProduct):
            raise ValueError(
                f"CRITICAL: Expected RILAProduct, got {type(product).__name__}"
            )

        # [F.1] Resolve term_years: require explicit value or from product
        if term_years is None:
            term_years = getattr(product, 'term_years', None)
            if term_years is not None:
                term_years = float(term_years)
        if term_years is None or term_years <= 0:
            raise ValueError(
                f"CRITICAL: term_years required and must be > 0, got {term_years}. "
                f"Specify term_years parameter or set product.term_years."
            )

        # Determine protection type
        is_buffer = product.is_buffer()
        protection_type = "buffer" if is_buffer else "floor"

        # [NEVER FAIL SILENTLY] Validate buffer/floor rate separately
        if is_buffer:
            if product.buffer_rate is None:
                raise ValueError(
                    f"Buffer RILA '{product.product_name}' missing buffer_rate. "
                    "Specify buffer_rate (e.g., 0.10 for 10% buffer)."
                )
            buffer_rate = product.buffer_rate
        else:
            # Floor product - buffer_rate field represents floor level
            if product.buffer_rate is None:
                raise ValueError(
                    f"Floor RILA '{product.product_name}' missing floor_rate (buffer_rate field). "
                    "Specify buffer_rate as floor level (e.g., 0.10 for -10% floor)."
                )
            buffer_rate = product.buffer_rate
        cap_rate = product.cap_rate

        # Calculate max loss
        if is_buffer:
            max_loss = 1.0 - buffer_rate  # Dollar-for-dollar after buffer exhausted
        else:
            max_loss = buffer_rate  # Floor is the max loss

        # Price protection component
        protection_value = self._price_protection(
            is_buffer, buffer_rate, term_years, premium
        )

        # Price upside component (capped call)
        upside_value = self._price_upside(cap_rate, term_years, premium)

        # Calculate expected return via Monte Carlo
        expected_return = self._calculate_expected_return(
            is_buffer, buffer_rate, cap_rate, term_years
        )

        # Calculate breakeven return
        breakeven_return = self._calculate_breakeven(
            is_buffer, buffer_rate, cap_rate
        )

        # [T1] Risk-neutral PV: discount the full maturity payoff (principal + return)
        # At maturity, policyholder receives: premium * (1 + expected_return)
        # PV = e^(-rT) * premium * (1 + expected_return)
        discount_factor = np.exp(-self.market_params.risk_free_rate * term_years)
        present_value = discount_factor * premium * (1 + expected_return)
        # Note: PV clipping removed - negative PV now surfaced to validation gates

        return RILAPricingResult(
            present_value=present_value,
            duration=term_years,
            as_of_date=as_of_date or date.today(),
            protection_value=protection_value,
            protection_type=protection_type,
            upside_value=upside_value,
            expected_return=expected_return,
            max_loss=max_loss,
            breakeven_return=breakeven_return,
            details={
                "buffer_rate": buffer_rate,
                "cap_rate": cap_rate,
                "is_buffer": is_buffer,
                "term_years": term_years,
                "premium": premium,
                "discount_factor": discount_factor,
            },
        )

    def competitive_position(
        self,
        product: RILAProduct,
        market_data: pd.DataFrame,
        **kwargs: Any,
    ) -> CompetitivePosition:
        """
        Determine competitive position of RILA product.

        Parameters
        ----------
        product : RILAProduct
            RILA product to analyze
        market_data : pd.DataFrame
            Comparable RILA products from WINK
        **kwargs : Any
            Additional filters (e.g., buffer_modifier, index_used)

        Returns
        -------
        CompetitivePosition
            Percentile rank based on cap rate
        """
        # Filter to RILA products
        comparables = market_data[market_data["productGroup"] == "RILA"].copy()

        # Filter by protection type if specified
        if product.is_buffer():
            comparables = comparables[
                comparables["bufferModifier"].str.lower().str.contains("up to", na=False)
            ]
        else:
            comparables = comparables[
                comparables["bufferModifier"].str.lower().str.contains("after", na=False)
            ]

        # Filter by buffer rate (similar protection level)
        if product.buffer_rate is not None:
            tolerance = 0.02  # 2% tolerance
            comparables = comparables[
                (comparables["bufferRate"] >= product.buffer_rate - tolerance)
                & (comparables["bufferRate"] <= product.buffer_rate + tolerance)
            ]

        # Apply additional filters
        if kwargs.get("index_used"):
            comparables = comparables[comparables["indexUsed"] == kwargs["index_used"]]

        if comparables.empty:
            raise ValueError(
                "CRITICAL: No comparable RILA products found. "
                "Check filters and market data."
            )

        # Use cap rate for comparison
        if product.cap_rate is None:
            raise ValueError(
                "CRITICAL: RILA product must have cap_rate for competitive analysis"
            )

        rate = product.cap_rate
        distribution = comparables["capRate"].dropna()

        if distribution.empty:
            raise ValueError("CRITICAL: No comparable products with capRate found")

        percentile = self._calculate_percentile(rate, distribution)
        rank = int((distribution > rate).sum() + 1)

        return CompetitivePosition(
            rate=rate,
            percentile=percentile,
            rank=rank,
            total_products=len(distribution),
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
            return black_scholes_call(
                m.spot, strike, m.risk_free_rate, m.dividend_yield, m.volatility, term_years
            )

        elif model_type == VolatilityModelType.HESTON:
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
                method="cos",
            )

        elif model_type == VolatilityModelType.SABR:
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
            raise ValueError(f"CRITICAL: Unknown volatility model type: {model_type}")

    def _price_put_option(
        self,
        strike: float,
        term_years: float,
    ) -> float:
        """
        Price a put option using the appropriate volatility model.

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
            Put option price
        """
        m = self.market_params
        model_type = m.get_vol_model_type()

        if model_type == VolatilityModelType.BLACK_SCHOLES:
            return black_scholes_put(
                m.spot, strike, m.risk_free_rate, m.dividend_yield, m.volatility, term_years
            )

        elif model_type == VolatilityModelType.HESTON:
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
                option_type=OptionType.PUT,
                method="cos",
            )

        elif model_type == VolatilityModelType.SABR:
            from annuity_pricing.options.pricing.sabr import sabr_price_put

            sabr_vol = m.vol_model
            if not isinstance(sabr_vol, SABRVolatility):
                raise TypeError(
                    f"CRITICAL: Expected SABRVolatility for SABR model, "
                    f"got {type(sabr_vol).__name__}"
                )

            return sabr_price_put(
                spot=m.spot,
                strike=strike,
                rate=m.risk_free_rate,
                dividend=m.dividend_yield,
                time=term_years,
                params=sabr_vol.params,
            )

        else:
            raise ValueError(f"CRITICAL: Unknown volatility model type: {model_type}")

    def _price_protection(
        self,
        is_buffer: bool,
        buffer_rate: float,
        term_years: float,
        premium: float,
    ) -> float:
        """
        Price the downside protection component.

        [T1] Uses pricing dispatcher for consistent volatility model handling.

        Parameters
        ----------
        is_buffer : bool
            True if buffer, False if floor
        buffer_rate : float
            Protection level
        term_years : float
            Option term
        premium : float
            Notional amount

        Returns
        -------
        float
            Protection value
        """
        m = self.market_params

        if is_buffer:
            # [T1] 100% buffer edge case: economically equivalent to 0% floor (full protection)
            # When buffer_rate >= 1.0, OTM strike would be 0, which is invalid for BS.
            # A 100% buffer means insurer absorbs ALL losses = full ATM put protection.
            # See: docs/knowledge/domain/buffer_floor.md
            if buffer_rate >= 1.0 - 1e-10:
                atm_put = self._price_put_option(m.spot, term_years)
                protection = atm_put  # Full put protection, no short position
            else:
                # Buffer = Long ATM put - Short OTM put
                # [T1] Put spread with strikes K1=S (ATM) and K2=S*(1-buffer)
                atm_put = self._price_put_option(m.spot, term_years)
                otm_strike = m.spot * (1 - buffer_rate)
                otm_put = self._price_put_option(otm_strike, term_years)
                protection = atm_put - otm_put
        else:
            # Floor = Long OTM put at floor strike
            # [T1] Put with strike K = S*(1 - floor_rate)
            floor_strike = m.spot * (1 - buffer_rate)
            protection = self._price_put_option(floor_strike, term_years)

        return (protection / m.spot) * premium

    def _price_upside(
        self,
        cap_rate: float | None,
        term_years: float,
        premium: float,
    ) -> float:
        """
        Price the capped upside component.

        [T1] Uses pricing dispatcher for consistent volatility model handling.

        Parameters
        ----------
        cap_rate : float, optional
            Cap rate (None = uncapped)
        term_years : float
            Option term
        premium : float
            Notional amount

        Returns
        -------
        float
            Upside value
        """
        m = self.market_params

        # ATM call for full upside
        atm_call = self._price_call_option(m.spot, term_years)

        if cap_rate is not None and cap_rate > 0:
            # Capped call = ATM call - OTM call at cap
            cap_strike = m.spot * (1 + cap_rate)
            otm_call = self._price_call_option(cap_strike, term_years)
            upside = atm_call - otm_call
        else:
            # Uncapped (or participation)
            upside = atm_call

        return (upside / m.spot) * premium

    def _calculate_expected_return(
        self,
        is_buffer: bool,
        buffer_rate: float,
        cap_rate: float | None,
        term_years: float,
    ) -> float:
        """
        Calculate expected return via Monte Carlo.

        [T1] Uses GBM or Heston paths based on vol_model configuration.
        Dispatches to appropriate MC method for path generation.

        Parameters
        ----------
        is_buffer : bool
            True if buffer protection
        buffer_rate : float
            Protection level
        cap_rate : float, optional
            Cap rate
        term_years : float
            Investment term

        Returns
        -------
        float
            Expected return (decimal)
        """
        # Create payoff object (BufferPayoff or FloorPayoff based on protection type)
        payoff: BufferPayoff | FloorPayoff
        if is_buffer:
            payoff = BufferPayoff(buffer_rate=buffer_rate, cap_rate=cap_rate)
        else:
            # Floor rate is negative for FloorPayoff
            payoff = FloorPayoff(floor_rate=-buffer_rate, cap_rate=cap_rate)

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
                n_steps=252,  # Daily steps for RILA
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
            mc_result = self.mc_engine.price_with_payoff(gbm_params, payoff)

        # Convert back to return
        expected_return = mc_result.payoffs.mean() / self.market_params.spot

        return expected_return

    def _calculate_breakeven(
        self,
        is_buffer: bool,
        buffer_rate: float,
        cap_rate: float | None,
    ) -> float | None:
        """
        Calculate breakeven index return.

        [T1] Find index return R where payoff = 1.0 (principal returned).

        For buffers:
        - Gain side: min(R, cap) if R > 0
        - Loss side: max(R + buffer, -1) if R < -buffer
        - Breakeven is where 1 + net_return = 1

        For floors:
        - Gain side: min(R, cap) if R > 0
        - Loss side: max(R, floor) (floor is typically negative, e.g., -0.10)
        - Breakeven is where 1 + net_return = 1

        Parameters
        ----------
        is_buffer : bool
            True if buffer protection
        buffer_rate : float
            Protection level (buffer absorbs first X% loss; floor = minimum return)
        cap_rate : float, optional
            Cap rate (None = uncapped)

        Returns
        -------
        Optional[float]
            Breakeven return (decimal), or None if no breakeven exists in range

        Examples
        --------
        >>> pricer = RILAPricer(market_params=MarketParams(spot=100, risk_free_rate=0.05, dividend_yield=0.02, volatility=0.20))
        >>> # 10% buffer: breakeven at -10% (first 10% absorbed)
        >>> pricer._calculate_breakeven(True, 0.10, 0.15)
        -0.1
        >>> # 10% floor: breakeven at 0% (any negative return = loss, floor only limits max loss)
        >>> pricer._calculate_breakeven(False, 0.10, 0.15)
        0.0
        """
        # [FIX] Return analytical breakeven values instead of numerical solver
        # The payoff function has a flat region where many points are technically
        # "breakeven", but conceptually:
        #
        # Buffer: breakeven = -buffer_rate
        #   At exactly -buffer_rate, the buffer fully absorbs the loss,
        #   returning principal. This is the boundary of the loss region.
        #
        # Floor: breakeven = 0
        #   Any negative index return results in a loss (floor only limits
        #   maximum loss, doesn't prevent loss). Breakeven requires R >= 0.
        #
        # See: codex-audit-report.md Finding 4 (floor docstring fix)

        if is_buffer:
            # Buffer absorbs first buffer_rate% of losses
            # At exactly -buffer_rate, investor gets back principal
            return -buffer_rate
        else:
            # Floor product: any negative return = loss
            # Must have R >= 0 to break even
            return 0.0

    def compare_buffer_vs_floor(
        self,
        buffer_rate: float,
        floor_rate: float,
        cap_rate: float,
        term_years: float,
    ) -> pd.DataFrame:
        """
        Compare buffer vs floor protection for same protection level.

        Parameters
        ----------
        buffer_rate : float
            Buffer protection level (e.g., 0.10 for 10%)
        floor_rate : float
            Floor protection level (e.g., 0.10 for -10% floor)
        cap_rate : float
            Cap rate for both
        term_years : float
            Investment term (required)

        Returns
        -------
        pd.DataFrame
            Comparison of buffer vs floor metrics

        Raises
        ------
        ValueError
            If term_years is not provided or <= 0
        """
        if term_years is None or term_years <= 0:
            raise ValueError(
                f"CRITICAL: term_years required and must be > 0, got {term_years}"
            )

        # Create dummy products with explicit term_years
        buffer_product = RILAProduct(
            company_name="Compare",
            product_name="Buffer",
            product_group="RILA",
            status="current",
            buffer_rate=buffer_rate,
            buffer_modifier="Losses Covered Up To",
            cap_rate=cap_rate,
            term_years=int(term_years),
        )

        floor_product = RILAProduct(
            company_name="Compare",
            product_name="Floor",
            product_group="RILA",
            status="current",
            buffer_rate=floor_rate,
            buffer_modifier="Losses Covered After",
            cap_rate=cap_rate,
            term_years=int(term_years),
        )

        # Price both
        buffer_result = self.price(buffer_product, term_years=term_years)
        floor_result = self.price(floor_product, term_years=term_years)

        return pd.DataFrame(
            {
                "metric": [
                    "protection_type",
                    "protection_value",
                    "upside_value",
                    "expected_return",
                    "max_loss",
                    "present_value",
                ],
                "buffer": [
                    "buffer",
                    buffer_result.protection_value,
                    buffer_result.upside_value,
                    buffer_result.expected_return,
                    buffer_result.max_loss,
                    buffer_result.present_value,
                ],
                "floor": [
                    "floor",
                    floor_result.protection_value,
                    floor_result.upside_value,
                    floor_result.expected_return,
                    floor_result.max_loss,
                    floor_result.present_value,
                ],
            }
        )

    def price_multiple(
        self,
        products: list[RILAProduct],
        term_years: float | None = None,
        premium: float = 100.0,
    ) -> pd.DataFrame:
        """
        Price multiple RILA products.

        Parameters
        ----------
        products : list[RILAProduct]
            RILA products to price
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
                        "protection_type": result.protection_type,
                        "buffer_rate": product.buffer_rate,
                        "cap_rate": product.cap_rate,
                        "present_value": result.present_value,
                        "protection_value": result.protection_value,
                        "upside_value": result.upside_value,
                        "expected_return": result.expected_return,
                        "max_loss": result.max_loss,
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

    def calculate_greeks(
        self,
        product: RILAProduct,
        term_years: float | None = None,
        notional: float = 100.0,
    ) -> RILAGreeks:
        """
        Calculate hedge Greeks for RILA protection.

        [T1] Buffer = Long ATM put - Short OTM put (put spread)
        [T1] Floor = Long OTM put

        Greeks are computed from the option replication and represent
        the insurer's hedging exposure.

        Parameters
        ----------
        product : RILAProduct
            RILA product to analyze
        term_years : float, optional
            Investment term in years. If None, uses product.term_years.
            CRITICAL: Must be explicitly provided or available from product.
        notional : float
            Notional amount (for dollar Greeks)

        Returns
        -------
        RILAGreeks
            Position Greeks for hedging

        Raises
        ------
        ValueError
            If term_years is not provided and product.term_years is None

        Examples
        --------
        >>> market = MarketParams(spot=100, risk_free_rate=0.05, dividend_yield=0.02, volatility=0.20)
        >>> pricer = RILAPricer(market_params=market)
        >>> product = RILAProduct(
        ...     company_name="Test", product_name="10% Buffer",
        ...     product_group="RILA", status="current",
        ...     buffer_rate=0.10, buffer_modifier="Losses Covered Up To", cap_rate=0.15,
        ...     term_years=1
        ... )
        >>> greeks = pricer.calculate_greeks(product)
        >>> greeks.delta < 0  # Short delta from put spread
        True
        """
        if not isinstance(product, RILAProduct):
            raise ValueError(f"Expected RILAProduct, got {type(product).__name__}")

        # [F.1] Resolve term_years: require explicit value or from product
        if term_years is None:
            term_years = getattr(product, 'term_years', None)
            if term_years is not None:
                term_years = float(term_years)
        if term_years is None or term_years <= 0:
            raise ValueError(
                f"CRITICAL: term_years required and must be > 0, got {term_years}. "
                f"Specify term_years parameter or set product.term_years."
            )

        # Determine protection type
        is_buffer = product.buffer_modifier in [
            "Losses Covered Up To",
            "Losses Covered Up to",
            "Buffer",
        ]
        buffer_rate = product.buffer_rate or 0.10
        protection_type = "buffer" if is_buffer else "floor"

        # Get market params
        spot = self.market_params.spot
        r = self.market_params.risk_free_rate
        q = self.market_params.dividend_yield
        sigma = self.market_params.volatility

        # Calculate option Greeks
        if is_buffer:
            # [T1] 100% buffer edge case: economically equivalent to 0% floor (full protection)
            # When buffer_rate >= 1.0, OTM strike would be 0, which is invalid.
            # A 100% buffer = ATM put only (full downside protection)
            if buffer_rate >= 1.0 - 1e-10:
                # ATM put Greeks only (no short position)
                atm_greeks = black_scholes_greeks(
                    spot=spot,
                    strike=spot,
                    rate=r,
                    dividend=q,
                    volatility=sigma,
                    time_to_expiry=term_years,
                    option_type=OptionType.PUT,
                )

                # Position Greeks = ATM put only
                delta = atm_greeks.delta
                gamma = atm_greeks.gamma
                vega = atm_greeks.vega
                theta = atm_greeks.theta
                rho = atm_greeks.rho
                atm_put_delta = atm_greeks.delta
                otm_put_delta = 0.0  # No OTM put for 100% buffer
            else:
                # Buffer = Long ATM put - Short OTM put
                atm_strike = spot  # ATM strike
                otm_strike = spot * (1 - buffer_rate)  # OTM strike

                # ATM put Greeks (long position)
                atm_greeks = black_scholes_greeks(
                    spot=spot,
                    strike=atm_strike,
                    rate=r,
                    dividend=q,
                    volatility=sigma,
                    time_to_expiry=term_years,
                    option_type=OptionType.PUT,
                )

                # OTM put Greeks (short position)
                otm_greeks = black_scholes_greeks(
                    spot=spot,
                    strike=otm_strike,
                    rate=r,
                    dividend=q,
                    volatility=sigma,
                    time_to_expiry=term_years,
                    option_type=OptionType.PUT,
                )

                # Net position: Long ATM - Short OTM
                delta = atm_greeks.delta - otm_greeks.delta
                gamma = atm_greeks.gamma - otm_greeks.gamma
                vega = atm_greeks.vega - otm_greeks.vega
                theta = atm_greeks.theta - otm_greeks.theta
                rho = atm_greeks.rho - otm_greeks.rho
                atm_put_delta = atm_greeks.delta
                otm_put_delta = -otm_greeks.delta  # Negative since short

        else:
            # Floor = Long OTM put
            floor_strike = spot * (1 - buffer_rate)

            # OTM put Greeks (long position)
            otm_greeks = black_scholes_greeks(
                spot=spot,
                strike=floor_strike,
                rate=r,
                dividend=q,
                volatility=sigma,
                time_to_expiry=term_years,
                option_type=OptionType.PUT,
            )

            # Position Greeks
            delta = otm_greeks.delta
            gamma = otm_greeks.gamma
            vega = otm_greeks.vega
            theta = otm_greeks.theta
            rho = otm_greeks.rho
            atm_put_delta = 0.0  # No ATM put for floor
            otm_put_delta = otm_greeks.delta

        # Dollar delta
        dollar_delta = delta * spot * notional

        return RILAGreeks(
            protection_type=protection_type,
            delta=delta,
            gamma=gamma,
            vega=vega,
            theta=theta,
            rho=rho,
            atm_put_delta=atm_put_delta,
            otm_put_delta=otm_put_delta,
            dollar_delta=dollar_delta,
        )
