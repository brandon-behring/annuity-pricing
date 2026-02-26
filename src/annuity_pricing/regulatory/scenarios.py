"""
Scenario Generation - Phase 9.

[PROTOTYPE] EDUCATIONAL USE ONLY - NOT FOR NAIC REGULATORY FILING
===========================================================================
This module generates economic scenarios using standard academic models
for educational purposes. It is NOT NAIC-compliant for regulatory filings.

CRITICAL LIMITATION:
This generator uses custom Vasicek + GBM models, NOT the NAIC-prescribed
scenario generators required for VM-21/VM-22 compliance:

- Current requirement: AAA Economic Scenario Generator (ESG)
- Future requirement: GOES (Generator of Economic Scenarios)
  Effective date: December 31, 2026

NAIC-prescribed generators provide:
- Stochastically generated scenarios meeting NAIC calibration criteria
- Deterministic scenarios for DR/SSA calculations
- Pre-packaged scenario files (available from naic.conning.com)
- Regulatory acceptance for reserve calculations

This implementation provides:
- Vasicek interest rate model (mean-reverting)
- GBM equity model (log-normal returns)
- Cholesky correlation structure
- Useful for: education, research, prototype testing

NOT suitable for: regulatory filings, statutory reserves, ORSA

See: docs/regulatory/AG43_COMPLIANCE_GAP.md
===========================================================================

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

import numpy as np

from ..loaders.yield_curve import YieldCurve, YieldCurveLoader


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

    scenarios: list[EconomicScenario]
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
    Equity model parameters (GBM) - real-world measure.

    [T1] dS/S = μdt + σ dW

    Attributes
    ----------
    mu : float
        Drift (expected return) - real-world measure
    sigma : float
        Volatility

    Note: For risk-neutral pricing, use RiskNeutralEquityParams instead.
    """

    mu: float = 0.07  # 7% expected return (real-world)
    sigma: float = 0.18  # 18% volatility


@dataclass(frozen=True)
class RiskNeutralEquityParams:
    """
    Risk-neutral equity model parameters.

    [T1] Under risk-neutral measure: drift = r - q (forward rate minus dividend yield)

    Attributes
    ----------
    risk_free_rate : float
        Risk-free rate (from yield curve)
    dividend_yield : float
        Continuous dividend yield
    sigma : float
        Volatility

    Examples
    --------
    >>> params = RiskNeutralEquityParams(risk_free_rate=0.04, dividend_yield=0.02)
    >>> params.mu
    0.02  # 4% - 2% = 2% risk-neutral drift
    """

    risk_free_rate: float
    dividend_yield: float = 0.02  # ~2% typical S&P 500 dividend yield
    sigma: float = 0.18

    @property
    def mu(self) -> float:
        """
        Risk-neutral drift = r - q.

        [T1] Under risk-neutral measure, expected return equals
        risk-free rate minus dividend yield.
        """
        return self.risk_free_rate - self.dividend_yield

    def to_equity_params(self) -> EquityParams:
        """Convert to EquityParams for compatibility."""
        return EquityParams(mu=self.mu, sigma=self.sigma)


class ScenarioGenerator:
    """
    Economic scenario generator for VM-21/AG43.

    [PROTOTYPE] NOT NAIC-COMPLIANT
    ------------------------------
    This generator uses academic Vasicek + GBM models, NOT the NAIC-prescribed
    AAA ESG or GOES generators required for regulatory compliance.
    Use for education and research only.

    Generates correlated interest rate and equity scenarios
    using Vasicek (rates) and GBM (equity) models.

    Examples
    --------
    >>> gen = ScenarioGenerator(n_scenarios=1000, seed=42)
    >>> scenarios = gen.generate_ag43_scenarios()
    >>> scenarios.n_scenarios
    1000

    See Also
    --------
    docs/regulatory/AG43_COMPLIANCE_GAP.md : Compliance gap analysis
    docs/knowledge/domain/vm21_vm22.md : Theory reference
    """

    def __init__(
        self,
        n_scenarios: int = 1000,
        projection_years: int = 30,
        seed: int | None = None,
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
        rate_params: VasicekParams | None = None,
        equity_params: EquityParams | None = None,
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

    def generate_risk_neutral_scenarios(
        self,
        yield_curve: YieldCurve | None = None,
        dividend_yield: float = 0.02,
        equity_sigma: float = 0.18,
        rate_params: VasicekParams | None = None,
        correlation: float = -0.20,
    ) -> AG43Scenarios:
        """
        Generate scenarios using risk-neutral equity drift.

        [T1] Risk-neutral drift = r - q (forward rate - dividend yield).

        This is the correct approach for pricing purposes (VM-21, GLWB valuation).
        Use generate_ag43_scenarios() for real-world scenarios (stress testing).

        Parameters
        ----------
        yield_curve : YieldCurve, optional
            Yield curve for rate projection and risk-neutral drift.
            If None, uses a flat 4% curve.
        dividend_yield : float
            Continuous dividend yield (default 2%)
        equity_sigma : float
            Equity volatility (default 18%)
        rate_params : VasicekParams, optional
            Interest rate model parameters
        correlation : float
            Correlation between rate and equity shocks

        Returns
        -------
        AG43Scenarios
            Collection of risk-neutral scenarios

        Examples
        --------
        >>> from annuity_pricing.loaders.yield_curve import YieldCurveLoader
        >>> gen = ScenarioGenerator(n_scenarios=100, seed=42)
        >>> curve = YieldCurveLoader().flat_curve(0.04)
        >>> scenarios = gen.generate_risk_neutral_scenarios(yield_curve=curve)
        >>> len(scenarios.scenarios)
        100
        """
        if not -1 <= correlation <= 1:
            raise ValueError(f"Correlation must be in [-1, 1], got {correlation}")

        # Default to flat 4% curve
        if yield_curve is None:
            yield_curve = YieldCurveLoader().flat_curve(0.04)

        rate_params = rate_params or VasicekParams()
        initial_rate = yield_curve.get_rate(1.0)

        # Create risk-neutral equity params using yield curve
        # [T1] Under risk-neutral: mu = r - q
        rn_equity_params = RiskNeutralEquityParams(
            risk_free_rate=initial_rate,
            dividend_yield=dividend_yield,
            sigma=equity_sigma,
        )

        # Generate correlated shocks
        rate_shocks, equity_shocks = self._generate_correlated_shocks(correlation)

        # Generate rate paths from Vasicek
        rate_paths = self._generate_vasicek_paths(
            initial_rate, rate_params, rate_shocks
        )

        # Generate equity returns using risk-neutral drift
        equity_paths = self._generate_gbm_returns(
            rn_equity_params.to_equity_params(), equity_shocks
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
        params: VasicekParams | None = None,
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
    ) -> tuple[np.ndarray, np.ndarray]:
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

        # Initialize with first step (broadcast scalar to array for vectorized loop)
        r_prev: np.ndarray = np.full(n_scenarios, initial_rate)
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
) -> list[EconomicScenario]:
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
