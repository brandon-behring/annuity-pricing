"""
Heston stochastic volatility path generation.

Implements Andersen (2008) Quadratic-Exponential (QE) scheme for Heston paths:
- Exact moments of CIR variance process
- Quadratic approximation for large variance (psi <= 1.5)
- Exponential approximation for small variance (psi > 1.5)
- Correlated Brownian motions via Cholesky decomposition

[T1] Heston SDEs:
  dS = (r - q)S dt + sqrt(v) S dW1
  dv = kappa(theta - v) dt + sigma sqrt(v) dW2
  dW1 dW2 = rho dt

References
----------
[T1] Heston, S. L. (1993). A closed-form solution for options with stochastic
     volatility with applications to bond and currency options.
[T1] Andersen, L. B. G. (2008). Simple and efficient simulation of the Heston
     stochastic volatility model. Journal of Computational Finance, 11(3), 1-42.

Validation: tests/validation/test_heston_vs_quantlib.py (MC validated to <1% error)
"""

from dataclasses import dataclass

import numpy as np

from annuity_pricing.options.pricing.heston import HestonParams


@dataclass(frozen=True)
class HestonPathResult:
    """
    Result of Heston path generation.

    Attributes
    ----------
    spot_paths : np.ndarray
        Simulated spot paths, shape (n_paths, n_steps + 1)
    variance_paths : np.ndarray
        Simulated variance paths, shape (n_paths, n_steps + 1)
    times : np.ndarray
        Time points, shape (n_steps + 1,)
    params : HestonParams
        Heston parameters used
    spot : float
        Initial spot price
    rate : float
        Risk-free rate
    dividend : float
        Dividend yield
    time_to_expiry : float
        Total time simulated
    seed : int, optional
        Random seed used
    """

    spot_paths: np.ndarray
    variance_paths: np.ndarray
    times: np.ndarray
    params: HestonParams
    spot: float
    rate: float
    dividend: float
    time_to_expiry: float
    seed: int | None = None

    @property
    def n_paths(self) -> int:
        """Number of paths."""
        return self.spot_paths.shape[0]

    @property
    def n_steps(self) -> int:
        """Number of time steps."""
        return self.spot_paths.shape[1] - 1

    @property
    def terminal_spots(self) -> np.ndarray:
        """Terminal spot values of all paths."""
        return self.spot_paths[:, -1]

    @property
    def terminal_variances(self) -> np.ndarray:
        """Terminal variance values of all paths."""
        return self.variance_paths[:, -1]

    @property
    def returns(self) -> np.ndarray:
        """Total returns for all paths."""
        return (self.spot_paths[:, -1] - self.spot_paths[:, 0]) / self.spot_paths[:, 0]


def generate_heston_paths(
    spot: float,
    time: float,
    steps: int,
    paths: int,
    rate: float,
    dividend: float,
    params: HestonParams,
    seed: int | None = None,
) -> HestonPathResult:
    """
    Generate Heston paths using Andersen QE discretization.

    [T1] Implements Andersen (2008) Quadratic-Exponential (QE) scheme:
    - Quadratic approximation for large variance (psi <= 1.5)
    - Exponential approximation for small variance (psi > 1.5)
    - More accurate than Euler-Maruyama with truncation/reflection

    Parameters
    ----------
    spot : float
        Initial spot price (S(0) > 0)
    time : float
        Time to expiry in years (T > 0)
    steps : int
        Number of time steps (> 0)
    paths : int
        Number of paths to simulate (> 0)
    rate : float
        Risk-free rate (annualized, decimal)
    dividend : float
        Dividend yield (annualized, decimal)
    params : HestonParams
        Heston model parameters (v0, kappa, theta, sigma, rho)
    seed : int, optional
        Random seed for reproducibility

    Returns
    -------
    HestonPathResult
        Simulated spot and variance paths with metadata

    Examples
    --------
    >>> params = HestonParams(v0=0.04, kappa=2.0, theta=0.04, sigma=0.3, rho=-0.7)
    >>> result = generate_heston_paths(
    ...     spot=100.0, time=1.0, steps=252, paths=10000,
    ...     rate=0.05, dividend=0.02, params=params, seed=42
    ... )
    >>> result.terminal_spots.mean()  # Close to forward price
    """
    if spot <= 0:
        raise ValueError(f"CRITICAL: spot must be > 0. Got: spot={spot}")
    if time <= 0:
        raise ValueError(f"CRITICAL: time must be > 0. Got: time={time}")
    if steps <= 0:
        raise ValueError(f"CRITICAL: steps must be > 0. Got: steps={steps}")
    if paths <= 0:
        raise ValueError(f"CRITICAL: paths must be > 0. Got: paths={paths}")

    rng = np.random.default_rng(seed)

    dt = time / steps
    times = np.linspace(0, time, steps + 1)

    v0 = params.v0
    kappa = params.kappa
    theta = params.theta
    sigma = params.sigma
    rho = params.rho

    # Initialize paths
    S = np.full((paths, steps + 1), spot)
    v = np.full((paths, steps + 1), v0)

    # Generate correlated Brownian motions [T1]
    Z1 = rng.standard_normal((paths, steps))
    Z2_indep = rng.standard_normal((paths, steps))
    Z2 = rho * Z1 + np.sqrt(1 - rho**2) * Z2_indep

    # Andersen QE scheme threshold
    psi_c = 1.5

    for i in range(steps):
        v_curr = v[:, i]

        # Variance update using Andersen QE scheme [T1]
        # Step 1: Compute moments of v(t+dt) | v(t)
        m = theta + (v_curr - theta) * np.exp(-kappa * dt)
        s2 = (
            v_curr * sigma**2 * np.exp(-kappa * dt) / kappa * (1 - np.exp(-kappa * dt))
            + theta * sigma**2 / (2 * kappa) * (1 - np.exp(-kappa * dt)) ** 2
        )

        # Step 2: Compute psi = s^2 / m^2
        psi = s2 / (m**2 + 1e-10)

        # Step 3: Choose scheme based on psi
        # Quadratic scheme (for large variance)
        b2 = 2 / psi - 1 + np.sqrt(2 / psi) * np.sqrt(2 / psi - 1)
        a = m / (1 + b2)

        # Exponential scheme (for small variance)
        p = (psi - 1) / (psi + 1)
        beta = (1 - p) / m

        # Uniform random for exponential scheme
        U = rng.uniform(0, 1, paths)

        # Apply appropriate scheme [T1]
        v_next = np.where(
            psi <= psi_c,
            a * (np.sqrt(b2) + Z2[:, i]) ** 2,
            np.where(p >= U, 0.0, np.log((1 - p) / (1 - U)) / beta),
        )

        v[:, i + 1] = v_next

        # Spot update [T1]
        drift = (rate - dividend - 0.5 * v_curr) * dt
        diffusion = np.sqrt(np.maximum(v_curr * dt, 0)) * Z1[:, i]
        S[:, i + 1] = S[:, i] * np.exp(drift + diffusion)

    return HestonPathResult(
        spot_paths=S,
        variance_paths=v,
        times=times,
        params=params,
        spot=spot,
        rate=rate,
        dividend=dividend,
        time_to_expiry=time,
        seed=seed,
    )


def generate_heston_terminal_spots(
    spot: float,
    time: float,
    steps: int,
    paths: int,
    rate: float,
    dividend: float,
    params: HestonParams,
    seed: int | None = None,
) -> np.ndarray:
    """
    Generate only terminal spot values (faster for European options).

    Uses Andersen QE scheme but returns only S(T) without storing paths.
    More memory-efficient for European option pricing via Monte Carlo.

    Parameters
    ----------
    spot : float
        Initial spot price
    time : float
        Time to expiry in years
    steps : int
        Number of time steps
    paths : int
        Number of paths
    rate : float
        Risk-free rate (annualized, decimal)
    dividend : float
        Dividend yield (annualized, decimal)
    params : HestonParams
        Heston model parameters
    seed : int, optional
        Random seed

    Returns
    -------
    np.ndarray
        Terminal spot values, shape (paths,)
    """
    if paths <= 0:
        raise ValueError(f"CRITICAL: paths must be > 0, got {paths}")
    if steps <= 0:
        raise ValueError(f"CRITICAL: steps must be > 0, got {steps}")

    rng = np.random.default_rng(seed)

    dt = time / steps

    v0 = params.v0
    kappa = params.kappa
    theta = params.theta
    sigma = params.sigma
    rho = params.rho

    # Current values (start)
    S_curr = np.full(paths, spot)
    v_curr = np.full(paths, v0)

    # Andersen QE scheme threshold
    psi_c = 1.5

    for _ in range(steps):
        # Generate correlated randoms
        Z1 = rng.standard_normal(paths)
        Z2_indep = rng.standard_normal(paths)
        Z2 = rho * Z1 + np.sqrt(1 - rho**2) * Z2_indep

        # Variance update using Andersen QE scheme [T1]
        m = theta + (v_curr - theta) * np.exp(-kappa * dt)
        s2 = (
            v_curr * sigma**2 * np.exp(-kappa * dt) / kappa * (1 - np.exp(-kappa * dt))
            + theta * sigma**2 / (2 * kappa) * (1 - np.exp(-kappa * dt)) ** 2
        )
        psi = s2 / (m**2 + 1e-10)

        # Quadratic and exponential schemes
        b2 = 2 / psi - 1 + np.sqrt(2 / psi) * np.sqrt(2 / psi - 1)
        a = m / (1 + b2)
        p = (psi - 1) / (psi + 1)
        beta = (1 - p) / m
        U = rng.uniform(0, 1, paths)

        # Apply scheme
        v_next = np.where(
            psi <= psi_c,
            a * (np.sqrt(b2) + Z2) ** 2,
            np.where(p >= U, 0.0, np.log((1 - p) / (1 - U)) / beta),
        )

        # Spot update (use v_curr BEFORE updating)
        drift = (rate - dividend - 0.5 * v_curr) * dt
        diffusion = np.sqrt(np.maximum(v_curr * dt, 0)) * Z1
        S_curr = S_curr * np.exp(drift + diffusion)

        # Update variance
        v_curr = np.asarray(v_next).ravel()

    return S_curr


def validate_heston_simulation(
    spot: float,
    time: float,
    params: HestonParams,
    rate: float,
    dividend: float,
    n_paths: int = 100000,
    n_steps: int = 252,
    seed: int = 42,
) -> dict:
    """
    Validate Heston simulation against theoretical moments.

    [T1] Under Heston model:
    - E[S(T)] = S(0) * exp((r-q)*T) (forward price, risk-neutral)
    - E[v(T)] = v0*exp(-kappa*T) + theta*(1 - exp(-kappa*T)) (mean reversion)

    Parameters
    ----------
    spot : float
        Initial spot price
    time : float
        Time to expiry
    params : HestonParams
        Heston parameters
    rate : float
        Risk-free rate
    dividend : float
        Dividend yield
    n_paths : int, default 100000
        Number of paths for validation
    n_steps : int, default 252
        Number of time steps
    seed : int, default 42
        Random seed

    Returns
    -------
    dict
        Validation results with theoretical vs simulated values
    """
    result = generate_heston_paths(spot, time, n_steps, n_paths, rate, dividend, params, seed)

    # Theoretical values
    expected_spot_mean = spot * np.exp((rate - dividend) * time)
    expected_var_mean = params.v0 * np.exp(-params.kappa * time) + params.theta * (
        1 - np.exp(-params.kappa * time)
    )

    # Simulated values
    simulated_spot_mean = result.terminal_spots.mean()
    simulated_var_mean = result.terminal_variances.mean()

    # Standard errors
    se_spot = result.terminal_spots.std() / np.sqrt(n_paths)
    se_var = result.terminal_variances.std() / np.sqrt(n_paths)

    return {
        "n_paths": n_paths,
        "n_steps": n_steps,
        "feller_condition_satisfied": params.satisfies_feller(),
        "theoretical_spot_mean": expected_spot_mean,
        "simulated_spot_mean": simulated_spot_mean,
        "spot_error_pct": abs(simulated_spot_mean - expected_spot_mean) / expected_spot_mean * 100,
        "spot_se": se_spot,
        "spot_z_score": (simulated_spot_mean - expected_spot_mean) / se_spot,
        "theoretical_var_mean": expected_var_mean,
        "simulated_var_mean": simulated_var_mean,
        "var_error_pct": abs(simulated_var_mean - expected_var_mean) / expected_var_mean * 100,
        "var_se": se_var,
        "spot_validation_passed": abs(simulated_spot_mean - expected_spot_mean) / expected_spot_mean
        < 0.02,
        "var_validation_passed": abs(simulated_var_mean - expected_var_mean) / expected_var_mean
        < 0.05,
    }
