"""
RILA (Registered Index-Linked Annuity) Pricer.

Prices RILA products with partial downside protection:
- Buffer: Insurer absorbs FIRST X% of losses
- Floor: Insurer covers losses BEYOND X%

[T1] RILAs can have negative returns (unlike FIA with 0% floor).
[T1] Buffer = Long ATM put - Short OTM put (put spread)
[T1] Floor = Long OTM put

See: CONSTITUTION.md Section 3.2
See: docs/knowledge/domain/buffer_floor.md
"""

from dataclasses import dataclass
from datetime import date
from typing import Any, Optional

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from annuity_pricing.data.schemas import RILAProduct
from annuity_pricing.options.payoffs.rila import (
    BufferPayoff,
    FloorPayoff,
    create_rila_payoff,
)
from annuity_pricing.options.payoffs.base import OptionType
from annuity_pricing.options.pricing.black_scholes import (
    black_scholes_call,
    black_scholes_put,
    black_scholes_greeks,
    price_buffer_protection,
)
from annuity_pricing.options.simulation.gbm import GBMParams
from annuity_pricing.options.simulation.monte_carlo import MonteCarloEngine
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
    breakeven_return: Optional[float] = None


@dataclass(frozen=True)
class MarketParams:
    """
    Market parameters for RILA pricing.

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
        seed: Optional[int] = None,
    ):
        self.market_params = market_params
        self.n_mc_paths = n_mc_paths
        self.seed = seed

        # Initialize MC engine
        self.mc_engine = MonteCarloEngine(
            n_paths=n_mc_paths, antithetic=True, seed=seed
        )

    def price(
        self,
        product: RILAProduct,
        as_of_date: Optional[date] = None,
        term_years: Optional[float] = None,
        premium: float = 100.0,
        **kwargs: Any,
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

    def _price_protection(
        self,
        is_buffer: bool,
        buffer_rate: float,
        term_years: float,
        premium: float,
    ) -> float:
        """
        Price the downside protection component.

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
            # Buffer = Long ATM put - Short OTM put
            # [T1] Put spread with strikes K1=S (ATM) and K2=S*(1-buffer)
            atm_put = black_scholes_put(
                m.spot, m.spot, m.risk_free_rate, m.dividend_yield, m.volatility, term_years
            )
            otm_strike = m.spot * (1 - buffer_rate)
            otm_put = black_scholes_put(
                m.spot, otm_strike, m.risk_free_rate, m.dividend_yield, m.volatility, term_years
            )
            protection = atm_put - otm_put
        else:
            # Floor = Long OTM put at floor strike
            # [T1] Put with strike K = S*(1 - floor_rate)
            floor_strike = m.spot * (1 - buffer_rate)
            protection = black_scholes_put(
                m.spot, floor_strike, m.risk_free_rate, m.dividend_yield, m.volatility, term_years
            )

        return (protection / m.spot) * premium

    def _price_upside(
        self,
        cap_rate: Optional[float],
        term_years: float,
        premium: float,
    ) -> float:
        """
        Price the capped upside component.

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
        atm_call = black_scholes_call(
            m.spot, m.spot, m.risk_free_rate, m.dividend_yield, m.volatility, term_years
        )

        if cap_rate is not None and cap_rate > 0:
            # Capped call = ATM call - OTM call at cap
            cap_strike = m.spot * (1 + cap_rate)
            otm_call = black_scholes_call(
                m.spot, cap_strike, m.risk_free_rate, m.dividend_yield, m.volatility, term_years
            )
            upside = atm_call - otm_call
        else:
            # Uncapped (or participation)
            upside = atm_call

        return (upside / m.spot) * premium

    def _calculate_expected_return(
        self,
        is_buffer: bool,
        buffer_rate: float,
        cap_rate: Optional[float],
        term_years: float,
    ) -> float:
        """
        Calculate expected return via Monte Carlo.

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
        # Create payoff object
        if is_buffer:
            payoff = BufferPayoff(buffer_rate=buffer_rate, cap_rate=cap_rate)
        else:
            # Floor rate is negative for FloorPayoff
            payoff = FloorPayoff(floor_rate=-buffer_rate, cap_rate=cap_rate)

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

        # Convert back to return
        expected_return = mc_result.payoffs.mean() / self.market_params.spot

        return expected_return

    def _calculate_breakeven(
        self,
        is_buffer: bool,
        buffer_rate: float,
        cap_rate: Optional[float],
    ) -> Optional[float]:
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
        >>> pricer = RILAPricer()
        >>> # 10% buffer: breakeven at -10% (first 10% absorbed)
        >>> pricer._calculate_breakeven(True, 0.10, 0.15)
        -0.1
        >>> # 10% floor: breakeven at -10% (floor caps losses at -10%)
        >>> pricer._calculate_breakeven(False, 0.10, 0.15)
        -0.1
        """

        def payoff_minus_principal(index_return: float) -> float:
            """Payoff - 1.0 (positive = profit, negative = loss)."""
            if is_buffer:
                # Buffer payoff:
                # - Gains: credited up to cap
                # - Losses: buffer absorbs first buffer_rate%
                if index_return >= 0:
                    # Positive return, apply cap
                    if cap_rate is not None:
                        gain = min(index_return, cap_rate)
                    else:
                        gain = index_return
                    return gain  # payoff - 1 = (1 + gain) - 1 = gain
                else:
                    # Negative return
                    if index_return > -buffer_rate:
                        # Within buffer - no loss
                        return 0.0  # payoff - 1 = 1 - 1 = 0
                    else:
                        # Beyond buffer - client absorbs excess
                        loss = index_return + buffer_rate  # e.g., -15% + 10% = -5%
                        return loss  # payoff - 1 = (1 + loss) - 1 = loss
            else:
                # Floor payoff:
                # - Gains: credited up to cap
                # - Losses: floored at -floor_rate (floor_rate stored in buffer_rate param)
                floor_rate = -buffer_rate  # Floor is negative, e.g., -0.10
                if index_return >= 0:
                    # Positive return, apply cap
                    if cap_rate is not None:
                        gain = min(index_return, cap_rate)
                    else:
                        gain = index_return
                    return gain
                else:
                    # Negative return - floored
                    effective_return = max(index_return, floor_rate)
                    return effective_return  # payoff - 1 = (1 + effective) - 1

        # For buffers: breakeven is exactly at -buffer_rate
        # For floors: breakeven is exactly at -floor_rate
        # But we solve it numerically to handle edge cases

        try:
            # Search for root in reasonable range
            # Minimum return: -99% (can't lose more than invested)
            # Maximum: search up to 100% return
            breakeven = brentq(payoff_minus_principal, -0.99, 1.0, xtol=1e-10)
            return float(breakeven)
        except ValueError:
            # No root found (payoff never equals principal in this range)
            # This can happen with certain cap/floor combinations
            return None

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
        term_years: Optional[float] = None,
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
        term_years: Optional[float] = None,
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
