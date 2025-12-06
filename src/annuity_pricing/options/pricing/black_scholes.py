"""
Black-Scholes option pricing with Greeks.

Implements analytical pricing for European options.
See: CONSTITUTION.md Section 3.1
See: docs/knowledge/domain/option_pricing.md
See: docs/appendix/derivations/black_scholes.md

References
----------
[T1] Black, F., & Scholes, M. (1973). The pricing of options and corporate liabilities.
[T1] Hull, J. C. (2018). Options, Futures, and Other Derivatives (10th ed.).
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import numpy as np
from scipy import stats

from annuity_pricing.options.payoffs.base import OptionType


@dataclass(frozen=True)
class BSResult:
    """
    Immutable Black-Scholes pricing result.

    Attributes
    ----------
    price : float
        Option price
    delta : float
        Delta (dV/dS)
    gamma : float
        Gamma (d²V/dS²)
    vega : float
        Vega (dV/dσ) - per 1% vol change
    theta : float
        Theta (dV/dt) - per day
    rho : float
        Rho (dV/dr) - per 1% rate change
    d1 : float
        d1 parameter
    d2 : float
        d2 parameter
    """

    price: float
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float
    d1: float
    d2: float


def _calculate_d1_d2(
    spot: float,
    strike: float,
    rate: float,
    dividend: float,
    volatility: float,
    time_to_expiry: float,
) -> tuple[float, float]:
    """
    Calculate d1 and d2 parameters.

    [T1] d1 = (ln(S/K) + (r - q + σ²/2)T) / (σ√T)
    [T1] d2 = d1 - σ√T

    Parameters
    ----------
    spot : float
        Current spot price
    strike : float
        Strike price
    rate : float
        Risk-free rate (decimal)
    dividend : float
        Dividend yield (decimal)
    volatility : float
        Volatility (decimal)
    time_to_expiry : float
        Time to expiry (years)

    Returns
    -------
    tuple[float, float]
        (d1, d2)
    """
    sqrt_t = np.sqrt(time_to_expiry)
    vol_sqrt_t = volatility * sqrt_t

    d1 = (
        np.log(spot / strike) + (rate - dividend + 0.5 * volatility**2) * time_to_expiry
    ) / vol_sqrt_t

    d2 = d1 - vol_sqrt_t

    return d1, d2


def black_scholes_call(
    spot: float,
    strike: float,
    rate: float,
    dividend: float,
    volatility: float,
    time_to_expiry: float,
) -> float:
    """
    Price European call option using Black-Scholes.

    [T1] C = S*e^(-qT)*N(d1) - K*e^(-rT)*N(d2)

    Parameters
    ----------
    spot : float
        Current spot price
    strike : float
        Strike price
    rate : float
        Risk-free rate (decimal)
    dividend : float
        Dividend yield (decimal)
    volatility : float
        Volatility (decimal)
    time_to_expiry : float
        Time to expiry (years)

    Returns
    -------
    float
        Call option price

    Examples
    --------
    >>> price = black_scholes_call(100, 100, 0.05, 0.02, 0.20, 1.0)
    >>> round(price, 2)
    9.93
    """
    _validate_inputs(spot, strike, rate, volatility, time_to_expiry)

    if time_to_expiry == 0:
        return max(spot - strike, 0.0)

    d1, d2 = _calculate_d1_d2(spot, strike, rate, dividend, volatility, time_to_expiry)

    call_price = (
        spot * np.exp(-dividend * time_to_expiry) * stats.norm.cdf(d1)
        - strike * np.exp(-rate * time_to_expiry) * stats.norm.cdf(d2)
    )

    return float(call_price)


def black_scholes_put(
    spot: float,
    strike: float,
    rate: float,
    dividend: float,
    volatility: float,
    time_to_expiry: float,
) -> float:
    """
    Price European put option using Black-Scholes.

    [T1] P = K*e^(-rT)*N(-d2) - S*e^(-qT)*N(-d1)

    Parameters
    ----------
    spot : float
        Current spot price
    strike : float
        Strike price
    rate : float
        Risk-free rate (decimal)
    dividend : float
        Dividend yield (decimal)
    volatility : float
        Volatility (decimal)
    time_to_expiry : float
        Time to expiry (years)

    Returns
    -------
    float
        Put option price

    Examples
    --------
    >>> price = black_scholes_put(100, 100, 0.05, 0.02, 0.20, 1.0)
    >>> round(price, 2)
    7.00
    """
    _validate_inputs(spot, strike, rate, volatility, time_to_expiry)

    if time_to_expiry == 0:
        return max(strike - spot, 0.0)

    d1, d2 = _calculate_d1_d2(spot, strike, rate, dividend, volatility, time_to_expiry)

    put_price = (
        strike * np.exp(-rate * time_to_expiry) * stats.norm.cdf(-d2)
        - spot * np.exp(-dividend * time_to_expiry) * stats.norm.cdf(-d1)
    )

    return float(put_price)


def black_scholes_price(
    spot: float,
    strike: float,
    rate: float,
    dividend: float,
    volatility: float,
    time_to_expiry: float,
    option_type: OptionType,
) -> float:
    """
    Price European option using Black-Scholes.

    Parameters
    ----------
    spot : float
        Current spot price
    strike : float
        Strike price
    rate : float
        Risk-free rate (decimal)
    dividend : float
        Dividend yield (decimal)
    volatility : float
        Volatility (decimal)
    time_to_expiry : float
        Time to expiry (years)
    option_type : OptionType
        Call or put

    Returns
    -------
    float
        Option price
    """
    if option_type == OptionType.CALL:
        return black_scholes_call(spot, strike, rate, dividend, volatility, time_to_expiry)
    else:
        return black_scholes_put(spot, strike, rate, dividend, volatility, time_to_expiry)


def black_scholes_greeks(
    spot: float,
    strike: float,
    rate: float,
    dividend: float,
    volatility: float,
    time_to_expiry: float,
    option_type: OptionType,
) -> BSResult:
    """
    Calculate Black-Scholes price and all Greeks.

    [T1] Delta (call) = e^(-qT) * N(d1)
    [T1] Delta (put) = -e^(-qT) * N(-d1)
    [T1] Gamma = e^(-qT) * n(d1) / (S * σ * √T)
    [T1] Vega = S * e^(-qT) * n(d1) * √T
    [T1] Theta (call) = -S*e^(-qT)*n(d1)*σ/(2√T) - r*K*e^(-rT)*N(d2) + q*S*e^(-qT)*N(d1)
    [T1] Rho (call) = K * T * e^(-rT) * N(d2)

    Parameters
    ----------
    spot : float
        Current spot price
    strike : float
        Strike price
    rate : float
        Risk-free rate (decimal)
    dividend : float
        Dividend yield (decimal)
    volatility : float
        Volatility (decimal)
    time_to_expiry : float
        Time to expiry (years)
    option_type : OptionType
        Call or put

    Returns
    -------
    BSResult
        Price and all Greeks
    """
    _validate_inputs(spot, strike, rate, volatility, time_to_expiry)

    if time_to_expiry == 0:
        # At expiry, return intrinsic value with zero Greeks
        if option_type == OptionType.CALL:
            price = max(spot - strike, 0.0)
            delta = 1.0 if spot > strike else 0.0
        else:
            price = max(strike - spot, 0.0)
            delta = -1.0 if spot < strike else 0.0

        return BSResult(
            price=price,
            delta=delta,
            gamma=0.0,
            vega=0.0,
            theta=0.0,
            rho=0.0,
            d1=float("inf") if spot > strike else float("-inf"),
            d2=float("inf") if spot > strike else float("-inf"),
        )

    d1, d2 = _calculate_d1_d2(spot, strike, rate, dividend, volatility, time_to_expiry)

    sqrt_t = np.sqrt(time_to_expiry)
    exp_div = np.exp(-dividend * time_to_expiry)
    exp_rate = np.exp(-rate * time_to_expiry)

    # Standard normal PDF and CDF values
    n_d1 = stats.norm.pdf(d1)
    N_d1 = stats.norm.cdf(d1)
    N_d2 = stats.norm.cdf(d2)
    N_neg_d1 = stats.norm.cdf(-d1)
    N_neg_d2 = stats.norm.cdf(-d2)

    # Price
    if option_type == OptionType.CALL:
        price = spot * exp_div * N_d1 - strike * exp_rate * N_d2
    else:
        price = strike * exp_rate * N_neg_d2 - spot * exp_div * N_neg_d1

    # Delta
    if option_type == OptionType.CALL:
        delta = exp_div * N_d1
    else:
        delta = -exp_div * N_neg_d1

    # Gamma (same for call and put)
    gamma = exp_div * n_d1 / (spot * volatility * sqrt_t)

    # Vega (same for call and put, scaled to 1% vol move)
    vega = spot * exp_div * n_d1 * sqrt_t * 0.01

    # Theta (scaled to per-day)
    if option_type == OptionType.CALL:
        theta = (
            -spot * exp_div * n_d1 * volatility / (2 * sqrt_t)
            - rate * strike * exp_rate * N_d2
            + dividend * spot * exp_div * N_d1
        ) / 365.0
    else:
        theta = (
            -spot * exp_div * n_d1 * volatility / (2 * sqrt_t)
            + rate * strike * exp_rate * N_neg_d2
            - dividend * spot * exp_div * N_neg_d1
        ) / 365.0

    # Rho (scaled to 1% rate move)
    if option_type == OptionType.CALL:
        rho = strike * time_to_expiry * exp_rate * N_d2 * 0.01
    else:
        rho = -strike * time_to_expiry * exp_rate * N_neg_d2 * 0.01

    return BSResult(
        price=float(price),
        delta=float(delta),
        gamma=float(gamma),
        vega=float(vega),
        theta=float(theta),
        rho=float(rho),
        d1=float(d1),
        d2=float(d2),
    )


def put_call_parity_check(
    call_price: float,
    put_price: float,
    spot: float,
    strike: float,
    rate: float,
    dividend: float,
    time_to_expiry: float,
    tolerance: float = 0.01,
) -> tuple[bool, float]:
    """
    Verify put-call parity holds.

    [T1] Put-Call Parity: C - P = S*e^(-qT) - K*e^(-rT)

    Parameters
    ----------
    call_price : float
        Call option price
    put_price : float
        Put option price
    spot : float
        Spot price
    strike : float
        Strike price
    rate : float
        Risk-free rate
    dividend : float
        Dividend yield
    time_to_expiry : float
        Time to expiry
    tolerance : float, default 0.01
        Acceptable error

    Returns
    -------
    tuple[bool, float]
        (parity_holds, error)
    """
    actual_diff = call_price - put_price
    expected_diff = (
        spot * np.exp(-dividend * time_to_expiry)
        - strike * np.exp(-rate * time_to_expiry)
    )

    error = abs(actual_diff - expected_diff)
    parity_holds = error < tolerance

    return parity_holds, error


def implied_volatility(
    market_price: float,
    spot: float,
    strike: float,
    rate: float,
    dividend: float,
    time_to_expiry: float,
    option_type: OptionType,
    initial_guess: float = 0.20,
    max_iterations: int = 100,
    tolerance: float = 1e-6,
) -> Optional[float]:
    """
    Calculate implied volatility using Newton-Raphson.

    Parameters
    ----------
    market_price : float
        Observed market price
    spot : float
        Spot price
    strike : float
        Strike price
    rate : float
        Risk-free rate
    dividend : float
        Dividend yield
    time_to_expiry : float
        Time to expiry
    option_type : OptionType
        Call or put
    initial_guess : float, default 0.20
        Initial volatility guess
    max_iterations : int, default 100
        Maximum iterations
    tolerance : float, default 1e-6
        Convergence tolerance

    Returns
    -------
    float or None
        Implied volatility, or None if not converged
    """
    vol = initial_guess

    for _ in range(max_iterations):
        try:
            result = black_scholes_greeks(
                spot, strike, rate, dividend, vol, time_to_expiry, option_type
            )
        except ValueError:
            return None

        price_diff = result.price - market_price

        if abs(price_diff) < tolerance:
            return vol

        # Vega is scaled to 1% move, need to unscale
        vega_unscaled = result.vega / 0.01

        if abs(vega_unscaled) < 1e-10:
            return None

        vol = vol - price_diff / vega_unscaled

        # Bounds check
        if vol <= 0 or vol > 5.0:
            return None

    return None


def _validate_inputs(
    spot: float,
    strike: float,
    rate: float,
    volatility: float,
    time_to_expiry: float,
) -> None:
    """Validate Black-Scholes inputs."""
    if spot <= 0:
        raise ValueError(f"CRITICAL: spot must be > 0, got {spot}")
    if strike <= 0:
        raise ValueError(f"CRITICAL: strike must be > 0, got {strike}")
    if volatility <= 0:
        raise ValueError(f"CRITICAL: volatility must be > 0, got {volatility}")
    if time_to_expiry < 0:
        raise ValueError(f"CRITICAL: time_to_expiry must be >= 0, got {time_to_expiry}")


# Convenience functions for common scenarios


def price_capped_call(
    spot: float,
    cap_rate: float,
    rate: float,
    dividend: float,
    volatility: float,
    time_to_expiry: float,
) -> float:
    """
    Price capped call option (call spread for FIA cap).

    [T1] Capped call = Long ATM call - Short OTM call at cap

    Parameters
    ----------
    spot : float
        Current spot price
    cap_rate : float
        Cap rate (e.g., 0.10 = 10% cap)
    rate : float
        Risk-free rate
    dividend : float
        Dividend yield
    volatility : float
        Volatility
    time_to_expiry : float
        Time to expiry

    Returns
    -------
    float
        Capped call price (as % of spot)
    """
    # ATM call (strike = spot)
    atm_call = black_scholes_call(spot, spot, rate, dividend, volatility, time_to_expiry)

    # OTM call at cap strike
    cap_strike = spot * (1 + cap_rate)
    otm_call = black_scholes_call(spot, cap_strike, rate, dividend, volatility, time_to_expiry)

    # Capped call = long ATM - short OTM
    capped_call = atm_call - otm_call

    return capped_call / spot  # Return as % of spot


def price_buffer_protection(
    spot: float,
    buffer_rate: float,
    rate: float,
    dividend: float,
    volatility: float,
    time_to_expiry: float,
) -> float:
    """
    Price buffer protection (put spread for RILA buffer).

    [T1] Buffer = Long ATM put - Short OTM put at buffer

    Parameters
    ----------
    spot : float
        Current spot price
    buffer_rate : float
        Buffer rate (e.g., 0.10 = 10% buffer)
    rate : float
        Risk-free rate
    dividend : float
        Dividend yield
    volatility : float
        Volatility
    time_to_expiry : float
        Time to expiry

    Returns
    -------
    float
        Buffer protection cost (as % of spot)
    """
    # ATM put (strike = spot)
    atm_put = black_scholes_put(spot, spot, rate, dividend, volatility, time_to_expiry)

    # OTM put at buffer strike
    buffer_strike = spot * (1 - buffer_rate)
    otm_put = black_scholes_put(spot, buffer_strike, rate, dividend, volatility, time_to_expiry)

    # Buffer = long ATM - short OTM
    buffer_cost = atm_put - otm_put

    return buffer_cost / spot  # Return as % of spot
