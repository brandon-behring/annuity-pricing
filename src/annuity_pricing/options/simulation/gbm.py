"""
Geometric Brownian Motion (GBM) path generation.

Implements efficient path simulation for Monte Carlo pricing:
- Standard GBM with Euler discretization
- Antithetic variates for variance reduction
- NumPy vectorized operations for performance

[T1] GBM SDE: dS = (r - q)S dt + σS dW

See: METHODOLOGY.md Section 4
See: docs/knowledge/domain/option_pricing.md
See: Glasserman (2003) "Monte Carlo Methods in Financial Engineering"
"""

from dataclasses import dataclass

import numpy as np

from annuity_pricing.options.payoffs.base import IndexPath


@dataclass(frozen=True)
class GBMParams:
    """
    Parameters for GBM simulation.

    Attributes
    ----------
    spot : float
        Initial spot price
    rate : float
        Risk-free rate (annualized, decimal)
    dividend : float
        Dividend yield (annualized, decimal)
    volatility : float
        Volatility (annualized, decimal)
    time_to_expiry : float
        Time to expiry in years
    """

    spot: float
    rate: float
    dividend: float
    volatility: float
    time_to_expiry: float

    def __post_init__(self) -> None:
        """Validate parameters."""
        if self.spot <= 0:
            raise ValueError(f"CRITICAL: spot must be > 0, got {self.spot}")
        if self.volatility < 0:
            raise ValueError(f"CRITICAL: volatility must be >= 0, got {self.volatility}")
        if self.time_to_expiry <= 0:
            raise ValueError(f"CRITICAL: time_to_expiry must be > 0, got {self.time_to_expiry}")

    @property
    def drift(self) -> float:
        """Risk-neutral drift: r - q - σ²/2."""
        return self.rate - self.dividend - 0.5 * self.volatility**2

    @property
    def forward(self) -> float:
        """Forward price: S * exp((r-q)*T)."""
        return self.spot * np.exp((self.rate - self.dividend) * self.time_to_expiry)


@dataclass(frozen=True)
class PathResult:
    """
    Result of GBM path generation.

    Attributes
    ----------
    paths : np.ndarray
        Simulated paths, shape (n_paths, n_steps + 1)
    times : np.ndarray
        Time points, shape (n_steps + 1,)
    params : GBMParams
        Parameters used for simulation
    seed : int, optional
        Random seed used
    antithetic : bool
        Whether antithetic variates were used
    """

    paths: np.ndarray
    times: np.ndarray
    params: GBMParams
    seed: int | None = None
    antithetic: bool = False

    @property
    def n_paths(self) -> int:
        """Number of paths."""
        return self.paths.shape[0]

    @property
    def n_steps(self) -> int:
        """Number of time steps."""
        return self.paths.shape[1] - 1

    @property
    def terminal_values(self) -> np.ndarray:
        """Terminal values of all paths."""
        return self.paths[:, -1]

    @property
    def returns(self) -> np.ndarray:
        """Total returns for all paths."""
        return (self.paths[:, -1] - self.paths[:, 0]) / self.paths[:, 0]

    def get_index_path(self, path_idx: int) -> IndexPath:
        """
        Get a single path as IndexPath.

        Parameters
        ----------
        path_idx : int
            Index of the path to retrieve

        Returns
        -------
        IndexPath
            Path as IndexPath object for payoff calculation
        """
        if path_idx < 0 or path_idx >= self.n_paths:
            raise ValueError(f"CRITICAL: path_idx must be in [0, {self.n_paths}), got {path_idx}")

        return IndexPath(
            times=tuple(float(t) for t in self.times),
            values=tuple(float(v) for v in self.paths[path_idx]),
            initial_value=float(self.paths[path_idx, 0]),
        )


def generate_gbm_paths(
    params: GBMParams,
    n_paths: int,
    n_steps: int,
    seed: int | None = None,
    antithetic: bool = False,
) -> PathResult:
    """
    Generate GBM paths using Euler discretization.

    [T1] Uses exact log-normal simulation:
    S(t+dt) = S(t) * exp((r - q - σ²/2)dt + σ√dt * Z)

    Parameters
    ----------
    params : GBMParams
        GBM parameters (spot, rate, dividend, volatility, time)
    n_paths : int
        Number of paths to simulate
    n_steps : int
        Number of time steps per path
    seed : int, optional
        Random seed for reproducibility
    antithetic : bool, default False
        Use antithetic variates for variance reduction

    Returns
    -------
    PathResult
        Simulated paths and metadata

    Notes
    -----
    Antithetic variates: For each standard normal Z, also use -Z.
    This reduces variance without additional random numbers.
    When antithetic=True, n_paths must be even and actual paths = n_paths.

    Examples
    --------
    >>> params = GBMParams(spot=100, rate=0.05, dividend=0.02, volatility=0.20, time_to_expiry=1.0)
    >>> result = generate_gbm_paths(params, n_paths=10000, n_steps=252, seed=42)
    >>> result.terminal_values.mean()  # Should be close to forward price
    """
    if n_paths <= 0:
        raise ValueError(f"CRITICAL: n_paths must be > 0, got {n_paths}")
    if n_steps <= 0:
        raise ValueError(f"CRITICAL: n_steps must be > 0, got {n_steps}")
    if antithetic and n_paths % 2 != 0:
        raise ValueError(f"CRITICAL: n_paths must be even for antithetic, got {n_paths}")

    # Set random seed
    rng = np.random.default_rng(seed)

    # Time discretization
    dt = params.time_to_expiry / n_steps
    sqrt_dt = np.sqrt(dt)
    times = np.linspace(0, params.time_to_expiry, n_steps + 1)

    # Drift and diffusion per step
    drift_per_step = params.drift * dt
    vol_per_step = params.volatility * sqrt_dt

    if antithetic:
        # Generate half the paths, use antithetic for other half
        half_paths = n_paths // 2
        z = rng.standard_normal((half_paths, n_steps))

        # Compute log-returns for original and antithetic
        log_returns = drift_per_step + vol_per_step * z
        log_returns_anti = drift_per_step - vol_per_step * z  # -Z

        # Combine
        all_log_returns = np.vstack([log_returns, log_returns_anti])
    else:
        # Generate all random numbers
        z = rng.standard_normal((n_paths, n_steps))
        all_log_returns = drift_per_step + vol_per_step * z

    # Cumulative sum of log-returns
    cum_log_returns = np.cumsum(all_log_returns, axis=1)

    # Build paths: S(t) = S(0) * exp(cumulative log-returns)
    paths = np.zeros((n_paths, n_steps + 1))
    paths[:, 0] = params.spot
    paths[:, 1:] = params.spot * np.exp(cum_log_returns)

    return PathResult(
        paths=paths,
        times=times,
        params=params,
        seed=seed,
        antithetic=antithetic,
    )


def generate_terminal_values(
    params: GBMParams,
    n_paths: int,
    seed: int | None = None,
    antithetic: bool = False,
) -> np.ndarray:
    """
    Generate only terminal values (faster for European options).

    [T1] Direct simulation: S(T) = S(0) * exp((r - q - σ²/2)T + σ√T * Z)

    Parameters
    ----------
    params : GBMParams
        GBM parameters
    n_paths : int
        Number of paths
    seed : int, optional
        Random seed
    antithetic : bool, default False
        Use antithetic variates

    Returns
    -------
    np.ndarray
        Terminal values, shape (n_paths,)

    Notes
    -----
    This is more efficient than generate_gbm_paths when only the terminal
    value is needed (e.g., European option pricing).
    """
    if n_paths <= 0:
        raise ValueError(f"CRITICAL: n_paths must be > 0, got {n_paths}")
    if antithetic and n_paths % 2 != 0:
        raise ValueError(f"CRITICAL: n_paths must be even for antithetic, got {n_paths}")

    rng = np.random.default_rng(seed)

    T = params.time_to_expiry
    sqrt_T = np.sqrt(T)
    total_drift = params.drift * T
    total_vol = params.volatility * sqrt_T

    if antithetic:
        half_paths = n_paths // 2
        z = rng.standard_normal(half_paths)
        z_all = np.concatenate([z, -z])
    else:
        z_all = rng.standard_normal(n_paths)

    log_returns = total_drift + total_vol * z_all
    terminal_values = params.spot * np.exp(log_returns)

    return terminal_values


def generate_paths_with_monthly_observations(
    params: GBMParams,
    n_paths: int,
    n_months: int = 12,
    seed: int | None = None,
    antithetic: bool = False,
) -> PathResult:
    """
    Generate paths with monthly observation dates.

    Useful for monthly averaging crediting methods (FIA).

    Parameters
    ----------
    params : GBMParams
        GBM parameters
    n_paths : int
        Number of paths
    n_months : int, default 12
        Number of monthly observations
    seed : int, optional
        Random seed
    antithetic : bool, default False
        Use antithetic variates

    Returns
    -------
    PathResult
        Paths with monthly observation points
    """
    # Calculate steps needed for monthly observations
    # Assuming 252 trading days per year, ~21 days per month
    steps_per_month = 21
    n_steps = n_months * steps_per_month

    result = generate_gbm_paths(params, n_paths, n_steps, seed, antithetic)

    # Extract monthly observations (every 21 steps)
    monthly_indices = np.arange(0, n_steps + 1, steps_per_month)
    monthly_paths = result.paths[:, monthly_indices]
    monthly_times = result.times[monthly_indices]

    return PathResult(
        paths=monthly_paths,
        times=monthly_times,
        params=params,
        seed=seed,
        antithetic=antithetic,
    )


def validate_gbm_simulation(
    params: GBMParams,
    n_paths: int = 100000,
    seed: int = 42,
) -> dict:
    """
    Validate GBM simulation against theoretical moments.

    [T1] Under risk-neutral measure:
    - E[S(T)] = S(0) * exp((r-q)*T) (forward price)
    - Var[log(S(T)/S(0))] = σ²T

    Parameters
    ----------
    params : GBMParams
        GBM parameters
    n_paths : int, default 100000
        Number of paths for validation
    seed : int, default 42
        Random seed

    Returns
    -------
    dict
        Validation results with theoretical vs simulated values
    """
    terminal = generate_terminal_values(params, n_paths, seed, antithetic=True)

    # Theoretical values
    expected_mean = params.forward
    expected_log_var = params.volatility**2 * params.time_to_expiry

    # Simulated values
    simulated_mean = terminal.mean()
    log_returns = np.log(terminal / params.spot)
    simulated_log_var = log_returns.var()

    # Standard errors (for confidence intervals)
    se_mean = terminal.std() / np.sqrt(n_paths)
    # Chi-squared based SE for variance would be more complex

    return {
        "n_paths": n_paths,
        "theoretical_mean": expected_mean,
        "simulated_mean": simulated_mean,
        "mean_error": abs(simulated_mean - expected_mean),
        "mean_error_pct": abs(simulated_mean - expected_mean) / expected_mean * 100,
        "mean_se": se_mean,
        "mean_z_score": (simulated_mean - expected_mean) / se_mean,
        "theoretical_log_variance": expected_log_var,
        "simulated_log_variance": simulated_log_var,
        "variance_error_pct": abs(simulated_log_var - expected_log_var) / expected_log_var * 100,
        "validation_passed": abs(simulated_mean - expected_mean) / expected_mean < 0.01,
    }
