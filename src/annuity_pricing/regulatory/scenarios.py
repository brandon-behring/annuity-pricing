"""
Scenario Generation - Phase 9.

Generates economic scenarios for VM-21/AG43 calculations:
- Interest rate scenarios (Vasicek mean-reversion)
- Equity return scenarios (GBM)
- Correlated multi-asset scenarios

Theory
------
[T1] Interest rates: Vasicek dr = κ(θ - r)dt + σ_r dW
[T1] Equity: GBM dS/S = μdt + σ dW
[T1] Correlation: Use Cholesky decomposition for correlated shocks

See: docs/knowledge/domain/vm21_vm22.md
"""

from dataclasses import dataclass
from typing import Optional, List, Tuple
import numpy as np


@dataclass(frozen=True)
class EconomicScenario:
    """
    Single economic scenario.

    Attributes
    ----------
    rates : ndarray
        Interest rate path (shape: [n_years])
    equity_returns : ndarray
        Equity return path (shape: [n_years])
    scenario_id : int
        Scenario identifier
    """

    rates: np.ndarray
    equity_returns: np.ndarray
    scenario_id: int

    def __post_init__(self) -> None:
        """Validate scenario data."""
        if len(self.rates) != len(self.equity_returns):
            raise ValueError(
                f"Rate path length ({len(self.rates)}) must match "
                f"equity path length ({len(self.equity_returns)})"
            )


@dataclass(frozen=True)
class AG43Scenarios:
    """
    AG43/VM-21 prescribed scenarios.

    [T1] AG43 requires stochastic scenarios for CTE calculation.

    Attributes
    ----------
    scenarios : List[EconomicScenario]
        List of economic scenarios
    n_scenarios : int
        Number of scenarios
    projection_years : int
        Years in each scenario
    """

    scenarios: List[EconomicScenario]
    n_scenarios: int
    projection_years: int

    def get_rate_matrix(self) -> np.ndarray:
        """
        Get all rate paths as matrix.

        Returns
        -------
        ndarray
            Shape: [n_scenarios, projection_years]
        """
        return np.array([s.rates for s in self.scenarios])

    def get_equity_matrix(self) -> np.ndarray:
        """
        Get all equity return paths as matrix.

        Returns
        -------
        ndarray
            Shape: [n_scenarios, projection_years]
        """
        return np.array([s.equity_returns for s in self.scenarios])


@dataclass(frozen=True)
class VasicekParams:
    """
    Vasicek interest rate model parameters.

    [T1] dr = κ(θ - r)dt + σ dW

    Attributes
    ----------
    kappa : float
        Mean reversion speed
    theta : float
        Long-run mean rate
    sigma : float
        Rate volatility
    """

    kappa: float = 0.20  # Reversion speed
    theta: float = 0.04  # Long-run mean (4%)
    sigma: float = 0.01  # Rate volatility (1%)


@dataclass(frozen=True)
class EquityParams:
    """
    Equity model parameters (GBM).

    [T1] dS/S = μdt + σ dW

    Attributes
    ----------
    mu : float
        Drift (expected return)
    sigma : float
        Volatility
    """

    mu: float = 0.07  # 7% expected return
    sigma: float = 0.18  # 18% volatility


class ScenarioGenerator:
    """
    Economic scenario generator for VM-21/AG43.

    Generates correlated interest rate and equity scenarios
    using Vasicek (rates) and GBM (equity) models.

    Examples
    --------
    >>> gen = ScenarioGenerator(n_scenarios=1000, seed=42)
    >>> scenarios = gen.generate_ag43_scenarios()
    >>> scenarios.n_scenarios
    1000

    See: docs/knowledge/domain/vm21_vm22.md
    """

    def __init__(
        self,
        n_scenarios: int = 1000,
        projection_years: int = 30,
        seed: Optional[int] = None,
    ):
        """
        Initialize scenario generator.

        Parameters
        ----------
        n_scenarios : int
            Number of scenarios to generate
        projection_years : int
            Years to project in each scenario
        seed : int, optional
            Random seed for reproducibility
        """
        if n_scenarios <= 0:
            raise ValueError(f"n_scenarios must be positive, got {n_scenarios}")
        if projection_years <= 0:
            raise ValueError(f"projection_years must be positive, got {projection_years}")

        self.n_scenarios = n_scenarios
        self.projection_years = projection_years
        self.seed = seed
        self._rng = np.random.default_rng(seed)

    def generate_ag43_scenarios(
        self,
        initial_rate: float = 0.04,
        initial_equity: float = 100.0,
        rate_params: Optional[VasicekParams] = None,
        equity_params: Optional[EquityParams] = None,
        correlation: float = -0.20,
    ) -> AG43Scenarios:
        """
        Generate AG43-compliant scenarios.

        [T1] AG43 requires correlated interest rate and equity scenarios.

        Parameters
        ----------
        initial_rate : float
            Starting interest rate (e.g., 0.04 for 4%)
        initial_equity : float
            Starting equity index level
        rate_params : VasicekParams, optional
            Interest rate model parameters
        equity_params : EquityParams, optional
            Equity model parameters
        correlation : float
            Correlation between rate and equity shocks
            Typically negative (rates down → equities up)

        Returns
        -------
        AG43Scenarios
            Collection of economic scenarios

        Examples
        --------
        >>> gen = ScenarioGenerator(n_scenarios=100, seed=42)
        >>> scenarios = gen.generate_ag43_scenarios()
        >>> len(scenarios.scenarios)
        100
        """
        if not -1 <= correlation <= 1:
            raise ValueError(f"Correlation must be in [-1, 1], got {correlation}")

        rate_params = rate_params or VasicekParams()
        equity_params = equity_params or EquityParams()

        # Generate correlated shocks
        rate_shocks, equity_shocks = self._generate_correlated_shocks(correlation)

        # Generate rate and equity paths
        rate_paths = self._generate_vasicek_paths(
            initial_rate, rate_params, rate_shocks
        )
        equity_paths = self._generate_gbm_returns(
            equity_params, equity_shocks
        )

        # Build scenario objects
        scenarios = []
        for i in range(self.n_scenarios):
            scenario = EconomicScenario(
                rates=rate_paths[i],
                equity_returns=equity_paths[i],
                scenario_id=i,
            )
            scenarios.append(scenario)

        return AG43Scenarios(
            scenarios=scenarios,
            n_scenarios=self.n_scenarios,
            projection_years=self.projection_years,
        )

    def generate_rate_scenarios(
        self,
        initial_rate: float = 0.04,
        params: Optional[VasicekParams] = None,
    ) -> np.ndarray:
        """
        Generate interest rate scenarios using Vasicek model.

        [T1] dr = κ(θ - r)dt + σ dW

        Parameters
        ----------
        initial_rate : float
            Starting interest rate
        params : VasicekParams, optional
            Model parameters

        Returns
        -------
        ndarray
            Rate scenarios (shape: [n_scenarios, projection_years])

        Examples
        --------
        >>> gen = ScenarioGenerator(n_scenarios=100, seed=42)
        >>> rates = gen.generate_rate_scenarios()
        >>> rates.shape
        (100, 30)
        """
        if initial_rate < 0:
            raise ValueError(f"Initial rate cannot be negative, got {initial_rate}")

        params = params or VasicekParams()
        shocks = self._rng.standard_normal((self.n_scenarios, self.projection_years))
        return self._generate_vasicek_paths(initial_rate, params, shocks)

    def generate_equity_scenarios(
        self,
        mu: float = 0.07,
        sigma: float = 0.18,
    ) -> np.ndarray:
        """
        Generate equity return scenarios using GBM.

        [T1] Log returns: ln(S_t/S_{t-1}) ~ N(μ - σ²/2, σ²)

        Parameters
        ----------
        mu : float
            Expected return (drift)
        sigma : float
            Volatility

        Returns
        -------
        ndarray
            Equity return scenarios (shape: [n_scenarios, projection_years])

        Examples
        --------
        >>> gen = ScenarioGenerator(n_scenarios=100, seed=42)
        >>> returns = gen.generate_equity_scenarios()
        >>> returns.shape
        (100, 30)
        """
        if sigma < 0:
            raise ValueError(f"Volatility cannot be negative, got {sigma}")

        params = EquityParams(mu=mu, sigma=sigma)
        shocks = self._rng.standard_normal((self.n_scenarios, self.projection_years))
        return self._generate_gbm_returns(params, shocks)

    def _generate_correlated_shocks(
        self,
        correlation: float,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate correlated standard normal shocks.

        [T1] Uses Cholesky decomposition for correlation.

        Parameters
        ----------
        correlation : float
            Correlation coefficient

        Returns
        -------
        Tuple[ndarray, ndarray]
            (rate_shocks, equity_shocks) each shape [n_scenarios, projection_years]
        """
        # Generate independent shocks
        z1 = self._rng.standard_normal((self.n_scenarios, self.projection_years))
        z2 = self._rng.standard_normal((self.n_scenarios, self.projection_years))

        # Apply Cholesky: [z_rate, z_equity] = L @ [z1, z2]
        # L = [[1, 0], [ρ, sqrt(1-ρ²)]]
        rate_shocks = z1
        equity_shocks = correlation * z1 + np.sqrt(1 - correlation**2) * z2

        return rate_shocks, equity_shocks

    def _generate_vasicek_paths(
        self,
        initial_rate: float,
        params: VasicekParams,
        shocks: np.ndarray,
    ) -> np.ndarray:
        """
        Generate Vasicek rate paths.

        [T1] Euler discretization: r_{t+1} = r_t + κ(θ - r_t) + σ * Z

        Parameters
        ----------
        initial_rate : float
            Starting rate
        params : VasicekParams
            Model parameters
        shocks : ndarray
            Standard normal shocks [n_scenarios, n_years]

        Returns
        -------
        ndarray
            Rate paths [n_scenarios, n_years]
        """
        n_scenarios, n_years = shocks.shape
        rates = np.zeros((n_scenarios, n_years))

        # Initialize with first step
        r_prev = initial_rate
        for t in range(n_years):
            # Vasicek: r_{t+1} = r_t + κ(θ - r_t)*dt + σ*sqrt(dt)*Z
            # With dt = 1 year:
            r_new = r_prev + params.kappa * (params.theta - r_prev) + params.sigma * shocks[:, t]
            # Floor at zero (avoid negative rates in this simple model)
            rates[:, t] = np.maximum(r_new, 0.0)
            r_prev = rates[:, t]

        return rates

    def _generate_gbm_returns(
        self,
        params: EquityParams,
        shocks: np.ndarray,
    ) -> np.ndarray:
        """
        Generate GBM returns.

        [T1] Log return = (μ - σ²/2) + σZ

        Parameters
        ----------
        params : EquityParams
            Model parameters
        shocks : ndarray
            Standard normal shocks [n_scenarios, n_years]

        Returns
        -------
        ndarray
            Annual returns [n_scenarios, n_years]
        """
        # Log return: (μ - σ²/2) + σZ
        log_returns = (params.mu - 0.5 * params.sigma**2) + params.sigma * shocks
        # Convert to simple returns: exp(log_return) - 1
        returns = np.exp(log_returns) - 1
        return returns


def generate_deterministic_scenarios(
    n_years: int = 30,
    base_rate: float = 0.04,
    base_equity: float = 0.07,
) -> List[EconomicScenario]:
    """
    Generate deterministic stress scenarios for VM-22.

    [T1] VM-22 deterministic reserve uses prescribed stress scenarios.

    Parameters
    ----------
    n_years : int
        Projection years
    base_rate : float
        Base interest rate
    base_equity : float
        Base equity return

    Returns
    -------
    List[EconomicScenario]
        Deterministic scenarios (base, up, down)

    Examples
    --------
    >>> scenarios = generate_deterministic_scenarios()
    >>> len(scenarios)
    3
    """
    scenarios = []

    # Base scenario
    base = EconomicScenario(
        rates=np.full(n_years, base_rate),
        equity_returns=np.full(n_years, base_equity),
        scenario_id=0,
    )
    scenarios.append(base)

    # Rate up scenario (+2%)
    rate_up = EconomicScenario(
        rates=np.full(n_years, base_rate + 0.02),
        equity_returns=np.full(n_years, base_equity - 0.02),  # Inverse correlation
        scenario_id=1,
    )
    scenarios.append(rate_up)

    # Rate down scenario (-2%)
    rate_down = EconomicScenario(
        rates=np.full(n_years, max(0.0, base_rate - 0.02)),
        equity_returns=np.full(n_years, base_equity + 0.02),
        scenario_id=2,
    )
    scenarios.append(rate_down)

    return scenarios


def calculate_scenario_statistics(
    scenarios: AG43Scenarios,
) -> dict:
    """
    Calculate summary statistics for scenarios.

    Parameters
    ----------
    scenarios : AG43Scenarios
        Generated scenarios

    Returns
    -------
    dict
        Statistics including means, std devs, percentiles

    Examples
    --------
    >>> gen = ScenarioGenerator(n_scenarios=100, seed=42)
    >>> scenarios = gen.generate_ag43_scenarios()
    >>> stats = calculate_scenario_statistics(scenarios)
    >>> 'rate_mean' in stats
    True
    """
    rate_matrix = scenarios.get_rate_matrix()
    equity_matrix = scenarios.get_equity_matrix()

    # Terminal values (last year)
    terminal_rates = rate_matrix[:, -1]
    cumulative_equity = np.prod(1 + equity_matrix, axis=1) - 1

    return {
        # Rate statistics
        "rate_mean": float(np.mean(rate_matrix)),
        "rate_std": float(np.std(rate_matrix)),
        "rate_min": float(np.min(rate_matrix)),
        "rate_max": float(np.max(rate_matrix)),
        "terminal_rate_mean": float(np.mean(terminal_rates)),
        "terminal_rate_5pct": float(np.percentile(terminal_rates, 5)),
        "terminal_rate_95pct": float(np.percentile(terminal_rates, 95)),
        # Equity statistics
        "equity_return_mean": float(np.mean(equity_matrix)),
        "equity_return_std": float(np.std(equity_matrix)),
        "cumulative_return_mean": float(np.mean(cumulative_equity)),
        "cumulative_return_5pct": float(np.percentile(cumulative_equity, 5)),
        "cumulative_return_95pct": float(np.percentile(cumulative_equity, 95)),
        # Counts
        "n_scenarios": scenarios.n_scenarios,
        "projection_years": scenarios.projection_years,
    }
