"""
Heston option pricing via COS (Fourier Cosine Expansion) method.

[T1] Implements Fang & Oosterlee (2008) COS method for Heston model pricing.
Superior to Carr-Madan FFT: exponential convergence, no dampening parameter.

References
----------
[T1] Fang, F., & Oosterlee, C. W. (2008). A Novel Pricing Method for European
     Options Based on Fourier-Cosine Series Expansions. SIAM J. Sci. Comput.,
     31(2), 826-848.
[T1] Heston, S. L. (1993). A closed-form solution for options with stochastic
     volatility. Review of Financial Studies, 6(2), 327-343.

Target: <0.1% error vs QuantLib AnalyticHestonEngine
"""

from dataclasses import dataclass

import numpy as np

from annuity_pricing.options.payoffs.base import OptionType
from annuity_pricing.options.pricing.heston import HestonParams


@dataclass(frozen=True)
class COSParams:
    """
    COS method parameters.

    Attributes
    ----------
    N : int
        Number of Fourier terms (default 256, typically 64-512 sufficient)
    L : float
        Truncation range multiplier (default 10, controls [a,b] width)
    """

    N: int = 256
    L: float = 10.0

    def __post_init__(self) -> None:
        if self.N < 16:
            raise ValueError(f"CRITICAL: N must be >= 16. Got: N={self.N}")
        if self.L <= 0:
            raise ValueError(f"CRITICAL: L must be > 0. Got: L={self.L}")


def heston_cumulants(
    time: float,
    rate: float,
    dividend: float,
    params: HestonParams,
) -> tuple[float, float, float, float]:
    """
    Calculate first four cumulants of log-price under Heston.

    [T1] Cumulants from characteristic function expansion.
    Used to determine truncation range [a, b] for COS method.

    Parameters
    ----------
    time : float
        Time to expiry (years)
    rate : float
        Risk-free rate (decimal)
    dividend : float
        Dividend yield (decimal)
    params : HestonParams
        Heston model parameters

    Returns
    -------
    Tuple[float, float, float, float]
        c1, c2, c4: First, second, fourth cumulants (c3 is zero for symmetric)
        w: Martingale correction (for drift)

    Notes
    -----
    [T1] For Heston model:
        c1 = (r - q)*T + (1 - exp(-kappa*T)) * (theta - v0) / (2*kappa)
           - theta*T / 2
        c2 = ... (variance of log-price)
    """
    v0 = params.v0
    kappa = params.kappa
    theta = params.theta
    sigma = params.sigma
    rho = params.rho

    T = time

    # Auxiliary quantities
    exp_kT = np.exp(-kappa * T)
    one_minus_exp = 1 - exp_kT

    # c1: Mean of log-price (minus drift)
    # [T1] Fang & Oosterlee (2008), Appendix A
    c1 = (rate - dividend) * T + (one_minus_exp) * (theta - v0) / (2 * kappa) - theta * T / 2

    # c2: Variance of log-price
    # [T1] From Heston variance of integrated variance
    term1 = sigma**2 * one_minus_exp * (v0 - theta) * (1 - exp_kT) / (kappa**2)
    term2 = theta * sigma**2 * T / kappa
    term3 = theta * sigma**2 * (1 - exp_kT) / (kappa**2)
    term4 = sigma**2 * v0 * one_minus_exp / (2 * kappa)

    # Simplified c2 formula [T1]
    c2 = (1 / (8 * kappa**3)) * (
        sigma * T * kappa * exp_kT * (v0 - theta) * (8 * kappa * rho - 4 * sigma)
        + kappa * rho * sigma * (1 - exp_kT) * (16 * theta - 8 * v0)
        + 2 * theta * kappa * T * (-4 * kappa * rho * sigma + sigma**2 + 4 * kappa**2)
        + sigma**2 * ((theta - 2 * v0) * exp_kT**2 + theta * (6 * exp_kT - 7) + 2 * v0)
        + 8 * kappa**2 * (v0 - theta) * (1 - exp_kT)
    )

    # Ensure c2 is positive
    c2 = max(c2, 1e-10)

    # c4: Fourth cumulant (for higher accuracy truncation)
    # Simplified approximation
    c4 = 0.0  # Zero for symmetric, use L adjustment instead

    # Martingale correction w
    w = -np.log(heston_characteristic_function_cos(-1j, 0.0, time, rate, dividend, params).real)

    return c1, c2, c4, w


def heston_characteristic_function_cos(
    u: complex,
    x: float,
    time: float,
    rate: float,
    dividend: float,
    params: HestonParams,
) -> complex:
    """
    Heston characteristic function for COS method.

    [T1] Characteristic function of log-asset price Y = ln(S_T/K).
    phi(u) = E[exp(i*u*Y)]

    Parameters
    ----------
    u : complex
        Frequency parameter
    x : float
        Current log-moneyness ln(S/K) (pass 0 for forward-starting)
    time : float
        Time to expiry
    rate : float
        Risk-free rate
    dividend : float
        Dividend yield
    params : HestonParams
        Heston parameters

    Returns
    -------
    complex
        Characteristic function value
    """
    # Handle u = 0 case (characteristic function = 1 at u=0)
    if abs(u) < 1e-14:
        return complex(1.0, 0.0)

    v0 = params.v0
    kappa = params.kappa
    theta = params.theta
    sigma = params.sigma
    rho = params.rho

    # Forward drift
    mu = rate - dividend

    # [T1] Heston (1993) characteristic function
    # Using the "little Heston trap" formulation for numerical stability
    # Reference: Albrecher et al. (2007) "The little Heston trap"

    # d^2 = (rho*sigma*i*u - kappa)^2 + sigma^2*(i*u + u^2)
    #     = (kappa - rho*sigma*i*u)^2 + sigma^2*i*u + sigma^2*u^2
    #     = kappa^2 - 2*kappa*rho*sigma*i*u - rho^2*sigma^2*u^2 + sigma^2*i*u + sigma^2*u^2
    #     = kappa^2 + sigma^2*u^2*(1 - rho^2) + i*u*sigma*(sigma - 2*kappa*rho)

    xi = kappa - rho * sigma * 1j * u
    d_squared = xi**2 + sigma**2 * (1j * u + u**2)
    d = np.sqrt(d_squared)

    # Ensure real part of d is positive for numerical stability
    if np.real(d) < 0:
        d = -d

    # Use numerically stable formulation
    # g = (kappa - rho*sigma*i*u - d) / (kappa - rho*sigma*i*u + d)
    g = (xi - d) / (xi + d)

    exp_neg_dt = np.exp(-d * time)

    # A(u, T) and B(u, T) [T1]
    # B = (xi - d) * (1 - exp(-d*T)) / (sigma^2 * (1 - g*exp(-d*T)))
    # A = (kappa*theta/sigma^2) * ((xi - d)*T - 2*ln((1 - g*exp(-d*T))/(1 - g)))

    one_minus_g_exp = 1 - g * exp_neg_dt
    one_minus_g = 1 - g

    # Avoid log of zero/negative
    if abs(one_minus_g_exp) < 1e-14:
        one_minus_g_exp = 1e-14
    if abs(one_minus_g) < 1e-14:
        one_minus_g = 1e-14

    B = (xi - d) / sigma**2 * (1 - exp_neg_dt) / one_minus_g_exp

    A = (kappa * theta / sigma**2) * ((xi - d) * time - 2 * np.log(one_minus_g_exp / one_minus_g))

    # Characteristic function
    phi = np.exp(A + B * v0 + 1j * u * mu * time)

    return phi


def cos_truncation_range(
    c1: float,
    c2: float,
    L: float = 10.0,
) -> tuple[float, float]:
    """
    Calculate COS truncation range [a, b] from cumulants.

    [T1] Fang & Oosterlee recommend [c1 - L*sqrt(c2), c1 + L*sqrt(c2)]
    with L = 10-12 for most cases.

    Parameters
    ----------
    c1 : float
        First cumulant (mean)
    c2 : float
        Second cumulant (variance)
    L : float
        Truncation multiplier (default 10)

    Returns
    -------
    Tuple[float, float]
        (a, b) truncation range
    """
    std = np.sqrt(max(c2, 1e-10))
    a = c1 - L * std
    b = c1 + L * std

    # Ensure sufficient range
    if b - a < 1e-6:
        a = c1 - 0.5
        b = c1 + 0.5

    return a, b


def chi_psi_coefficients(
    a: float,
    b: float,
    c: float,
    d: float,
    k: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Calculate chi and psi coefficients for COS payoff.

    [T1] Fang & Oosterlee (2008), equations for call/put payoff coefficients.

    chi_k(c, d) = [cos(k*pi*(d-a)/(b-a))*exp(d) - cos(k*pi*(c-a)/(b-a))*exp(c)
                   + k*pi/(b-a) * sin(k*pi*(d-a)/(b-a))*exp(d)
                   - k*pi/(b-a) * sin(k*pi*(c-a)/(b-a))*exp(c)]
                  / (1 + (k*pi/(b-a))^2)

    psi_k(c, d) = sin(k*pi*(d-a)/(b-a)) - sin(k*pi*(c-a)/(b-a)) for k != 0
                = d - c for k = 0

    Parameters
    ----------
    a, b : float
        Truncation range
    c, d : float
        Integration limits (payoff-dependent)
    k : np.ndarray
        Fourier indices (0 to N-1)

    Returns
    -------
    chi : np.ndarray
        Chi coefficients
    psi : np.ndarray
        Psi coefficients
    """
    bma = b - a

    # k * pi / (b - a)
    kpi_bma = k * np.pi / bma

    # Arguments for sin/cos
    arg_d = k * np.pi * (d - a) / bma
    arg_c = k * np.pi * (c - a) / bma

    # chi_k [T1]
    denom = 1 + kpi_bma**2
    chi = (
        np.cos(arg_d) * np.exp(d)
        - np.cos(arg_c) * np.exp(c)
        + kpi_bma * np.sin(arg_d) * np.exp(d)
        - kpi_bma * np.sin(arg_c) * np.exp(c)
    ) / denom

    # psi_k [T1]
    psi = np.zeros_like(k, dtype=float)
    psi[0] = d - c  # k = 0 case
    psi[1:] = (np.sin(arg_d[1:]) - np.sin(arg_c[1:])) * bma / (k[1:] * np.pi)

    return chi, psi


def heston_price_cos(
    spot: float,
    strike: float,
    rate: float,
    dividend: float,
    time: float,
    params: HestonParams,
    option_type: OptionType = OptionType.CALL,
    cos_params: COSParams | None = None,
) -> float:
    """
    Price European option using Heston model via COS method.

    [T1] Fang & Oosterlee (2008) COS method with exponential convergence.
    Target: <0.1% error vs QuantLib AnalyticHestonEngine.

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
    time : float
        Time to expiry (years)
    params : HestonParams
        Heston model parameters
    option_type : OptionType, optional
        CALL or PUT (default CALL)
    cos_params : COSParams, optional
        COS method parameters (default N=256, L=10)

    Returns
    -------
    float
        Option price

    Examples
    --------
    >>> params = HestonParams(v0=0.04, kappa=2.0, theta=0.04, sigma=0.3, rho=-0.7)
    >>> price = heston_price_cos(100, 100, 0.05, 0.02, 1.0, params)
    """
    # Validate inputs
    if spot <= 0:
        raise ValueError(f"CRITICAL: spot must be > 0. Got: spot={spot}")
    if strike <= 0:
        raise ValueError(f"CRITICAL: strike must be > 0. Got: strike={strike}")
    if time <= 0:
        raise ValueError(f"CRITICAL: time must be > 0. Got: time={time}")

    # Default COS parameters
    if cos_params is None:
        cos_params = COSParams()

    N = cos_params.N
    L = cos_params.L

    # Log-moneyness
    x = np.log(spot / strike)

    # Get cumulants and truncation range
    c1, c2, c4, w = heston_cumulants(time, rate, dividend, params)
    a, b = cos_truncation_range(c1, c2, L)

    # Fourier indices
    k = np.arange(N)

    # Characteristic function values at u_k = k*pi/(b-a)
    u_k = k * np.pi / (b - a)
    phi_k = np.array(
        [heston_characteristic_function_cos(u, x, time, rate, dividend, params) for u in u_k]
    )

    # Payoff coefficients
    if option_type == OptionType.CALL:
        # Call: payoff is (S_T - K)^+ = K*(exp(Y) - 1)^+ where Y = ln(S_T/K)
        # Integration limits: [0, b] (Y >= 0)
        c_int = 0.0
        d_int = b
        chi, psi = chi_psi_coefficients(a, b, c_int, d_int, k)
        # V_k for call [T1]
        V_k = 2 / (b - a) * (chi - psi)
    else:
        # Put: payoff is (K - S_T)^+ = K*(1 - exp(Y))^+ where Y = ln(S_T/K)
        # Integration limits: [a, 0] (Y <= 0)
        c_int = a
        d_int = 0.0
        chi, psi = chi_psi_coefficients(a, b, c_int, d_int, k)
        # V_k for put [T1]
        V_k = 2 / (b - a) * (-chi + psi)

    # First term has factor 1/2
    V_k[0] *= 0.5

    # COS series summation [T1]
    # exp_term = exp(i * k * pi * (x - a) / (b - a))
    exp_arg = k * np.pi * (x - a) / (b - a)
    exp_term = np.exp(1j * exp_arg)

    # Sum: Re[phi_k * exp_term] * V_k
    summation = np.sum(np.real(phi_k * exp_term) * V_k)

    # Discount and scale
    discount = np.exp(-rate * time)
    price = strike * discount * summation

    return max(price, 0.0)


def heston_price_call_cos(
    spot: float,
    strike: float,
    rate: float,
    dividend: float,
    time: float,
    params: HestonParams,
    cos_params: COSParams | None = None,
) -> float:
    """
    Price European call using Heston COS method.

    [T1] Convenience wrapper for heston_price_cos with option_type=CALL.
    """
    return heston_price_cos(
        spot,
        strike,
        rate,
        dividend,
        time,
        params,
        option_type=OptionType.CALL,
        cos_params=cos_params,
    )


def heston_price_put_cos(
    spot: float,
    strike: float,
    rate: float,
    dividend: float,
    time: float,
    params: HestonParams,
    cos_params: COSParams | None = None,
) -> float:
    """
    Price European put using Heston COS method.

    [T1] Convenience wrapper for heston_price_cos with option_type=PUT.
    """
    return heston_price_cos(
        spot,
        strike,
        rate,
        dividend,
        time,
        params,
        option_type=OptionType.PUT,
        cos_params=cos_params,
    )
