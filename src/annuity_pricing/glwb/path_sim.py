"""
GLWB Path-Dependent Monte Carlo - Phase 8.

Simulates GLWB payoffs using path-dependent MC.
Each path requires:
- AV evolution (GBM + fees)
- GWB tracking (rollup, ratchet)
- Withdrawal and lapse modeling
- Payoff calculation (when AV exhausted)

Theory
------
[T1] GLWB value = E[PV(insurer payments when AV exhausted)]

The insurer pays when:
1. Account value is exhausted (AV = 0)
2. Policyholder is still alive
3. Guaranteed withdrawals continue until death

See: docs/knowledge/domain/glwb_mechanics.md
See: docs/references/L3/bauer_kling_russ_2008.md
"""

from dataclasses import dataclass
from typing import Optional, Callable
import numpy as np

from .gwb_tracker import GWBTracker, GWBConfig, GWBState


@dataclass(frozen=True)
class GLWBPricingResult:
    """
    Result of GLWB pricing.

    Attributes
    ----------
    price : float
        Risk-neutral price of GLWB guarantee
    guarantee_cost : float
        Cost of guarantee as % of premium
    mean_payoff : float
        Average discounted payoff
    std_payoff : float
        Std dev of discounted payoff
    standard_error : float
        Standard error of mean
    prob_ruin : float
        Probability AV exhausted before death
    mean_ruin_year : float
        Average year of ruin (if ruin occurs)
    n_paths : int
        Number of paths simulated
    """

    price: float
    guarantee_cost: float
    mean_payoff: float
    std_payoff: float
    standard_error: float
    prob_ruin: float
    mean_ruin_year: float
    n_paths: int


@dataclass(frozen=True)
class PathResult:
    """
    Result of a single path simulation.

    Attributes
    ----------
    pv_insurer_payments : float
        Present value of payments from insurer (when AV exhausted)
    pv_withdrawals : float
        Present value of all withdrawals
    ruin_year : int
        Year AV exhausted (-1 if never)
    final_av : float
        Account value at end of simulation
    final_gwb : float
        GWB at end of simulation
    death_year : int
        Year of death (-1 if survived)
    """

    pv_insurer_payments: float
    pv_withdrawals: float
    ruin_year: int
    final_av: float
    final_gwb: float
    death_year: int


class GLWBPathSimulator:
    """
    Path-dependent Monte Carlo for GLWB pricing.

    [T1] GLWB guarantee value = E[PV(payments when AV = 0)]

    Examples
    --------
    >>> config = GWBConfig(rollup_rate=0.05, withdrawal_rate=0.05)
    >>> sim = GLWBPathSimulator(config, n_paths=10000)
    >>> result = sim.price(
    ...     premium=100_000, age=65, r=0.04, sigma=0.18
    ... )

    See: docs/knowledge/domain/glwb_mechanics.md
    """

    def __init__(
        self,
        gwb_config: GWBConfig,
        n_paths: int = 10000,
        seed: Optional[int] = None,
    ):
        """
        Initialize GLWB simulator.

        Parameters
        ----------
        gwb_config : GWBConfig
            GWB mechanics configuration
        n_paths : int
            Number of MC paths
        seed : int, optional
            Random seed
        """
        self.gwb_config = gwb_config
        self.n_paths = n_paths
        self.seed = seed
        self._rng = np.random.default_rng(seed)

    def price(
        self,
        premium: float,
        age: int,
        r: float,
        sigma: float,
        max_age: int = 100,
        mortality_table: Optional[Callable[[int], float]] = None,
        utilization_rate: float = 1.0,
    ) -> GLWBPricingResult:
        """
        Price GLWB guarantee using path-dependent MC.

        [T1] Price = E[PV(insurer payments when AV = 0)]

        Parameters
        ----------
        premium : float
            Initial premium
        age : int
            Current age
        r : float
            Risk-free rate
        sigma : float
            Volatility
        max_age : int
            Maximum simulation age
        mortality_table : callable, optional
            Function age -> qx (mortality rate). If None, uses simple table.
        utilization_rate : float
            Fraction of max withdrawal taken (default 1.0)

        Returns
        -------
        GLWBPricingResult
            Pricing result with diagnostics
        """
        if premium <= 0:
            raise ValueError(f"Premium must be positive, got {premium}")
        if age < 0 or age >= max_age:
            raise ValueError(f"Age must be in [0, {max_age}), got {age}")
        if sigma < 0:
            raise ValueError(f"Volatility cannot be negative, got {sigma}")

        # Default mortality table (simplified Gompertz-like)
        if mortality_table is None:
            mortality_table = self._default_mortality

        n_years = max_age - age
        path_results = []
        ruin_years = []

        for _ in range(self.n_paths):
            result = self.simulate_single_path(
                premium=premium,
                age=age,
                r=r,
                sigma=sigma,
                n_years=n_years,
                mortality_table=mortality_table,
                utilization_rate=utilization_rate,
            )
            path_results.append(result)
            if result.ruin_year >= 0:
                ruin_years.append(result.ruin_year)

        # Aggregate results
        pv_payoffs = np.array([r.pv_insurer_payments for r in path_results])
        mean_payoff = np.mean(pv_payoffs)
        std_payoff = np.std(pv_payoffs)
        standard_error = std_payoff / np.sqrt(self.n_paths)

        prob_ruin = len(ruin_years) / self.n_paths
        mean_ruin_year = np.mean(ruin_years) if ruin_years else -1.0

        return GLWBPricingResult(
            price=mean_payoff,
            guarantee_cost=mean_payoff / premium,
            mean_payoff=mean_payoff,
            std_payoff=std_payoff,
            standard_error=standard_error,
            prob_ruin=prob_ruin,
            mean_ruin_year=mean_ruin_year,
            n_paths=self.n_paths,
        )

    def simulate_single_path(
        self,
        premium: float,
        age: int,
        r: float,
        sigma: float,
        n_years: int,
        mortality_table: Callable[[int], float],
        utilization_rate: float = 1.0,
    ) -> PathResult:
        """
        Simulate a single GLWB path.

        Parameters
        ----------
        premium : float
            Initial premium
        age : int
            Starting age
        r : float
            Risk-free rate
        sigma : float
            Volatility
        n_years : int
            Maximum years to simulate
        mortality_table : callable
            Function age -> qx
        utilization_rate : float
            Fraction of max withdrawal taken

        Returns
        -------
        PathResult
            Path simulation result
        """
        tracker = GWBTracker(self.gwb_config, premium)
        state = tracker.initial_state()

        pv_insurer_payments = 0.0
        pv_withdrawals = 0.0
        ruin_year = -1
        death_year = -1
        current_age = age

        for t in range(n_years):
            # Check mortality
            qx = mortality_table(current_age)
            if self._rng.random() < qx:
                death_year = t
                break

            # Generate return (risk-neutral GBM)
            # [T1] Under risk-neutral measure: drift = r - 0.5*sigma^2
            z = self._rng.standard_normal()
            av_return = (r - 0.5 * sigma**2) + sigma * z

            # Calculate withdrawal
            max_withdrawal = tracker.calculate_max_withdrawal(state)
            withdrawal = max_withdrawal * utilization_rate

            # Step forward
            result = tracker.step(state, av_return, dt=1.0, withdrawal=withdrawal)
            state = result.new_state

            # Discount factor
            df = np.exp(-r * (t + 1))

            # Track withdrawals
            pv_withdrawals += result.withdrawal_taken * df

            # Check for ruin (AV exhausted)
            if state.av <= 0 and ruin_year < 0:
                ruin_year = t + 1

            # If ruined, insurer pays guaranteed amount
            if state.av <= 0:
                insurer_payment = max_withdrawal  # Continue guaranteed payment
                pv_insurer_payments += insurer_payment * df

            current_age += 1

        return PathResult(
            pv_insurer_payments=pv_insurer_payments,
            pv_withdrawals=pv_withdrawals,
            ruin_year=ruin_year,
            final_av=state.av,
            final_gwb=state.gwb,
            death_year=death_year,
        )

    def _default_mortality(self, age: int) -> float:
        """
        Default mortality table (simplified Gompertz-like).

        [T2] Approximate US life table.

        Parameters
        ----------
        age : int
            Current age

        Returns
        -------
        float
            Mortality rate qx
        """
        # Simple approximation: qx = 0.0001 * e^(0.08 * age)
        # Caps at 1.0
        qx = 0.0001 * np.exp(0.08 * age)
        return min(qx, 1.0)

    def calculate_fair_fee(
        self,
        premium: float,
        age: int,
        r: float,
        sigma: float,
        max_age: int = 100,
        target_cost: float = 0.0,
        fee_bounds: tuple = (0.001, 0.03),
        tolerance: float = 0.001,
        max_iterations: int = 20,
    ) -> float:
        """
        Calculate fair fee rate for GLWB.

        Find fee such that guarantee cost = target_cost (default 0).

        Parameters
        ----------
        premium : float
            Initial premium
        age : int
            Current age
        r : float
            Risk-free rate
        sigma : float
            Volatility
        max_age : int
            Maximum simulation age
        target_cost : float
            Target guarantee cost as % of premium (default 0 for fair value)
        fee_bounds : tuple
            (min_fee, max_fee) bounds for search
        tolerance : float
            Convergence tolerance
        max_iterations : int
            Maximum iterations

        Returns
        -------
        float
            Fair fee rate
        """
        from dataclasses import replace as dc_replace

        def cost_at_fee(fee: float) -> float:
            """Calculate guarantee cost at given fee."""
            config = GWBConfig(
                rollup_type=self.gwb_config.rollup_type,
                rollup_rate=self.gwb_config.rollup_rate,
                rollup_cap_years=self.gwb_config.rollup_cap_years,
                ratchet_enabled=self.gwb_config.ratchet_enabled,
                ratchet_frequency=self.gwb_config.ratchet_frequency,
                withdrawal_rate=self.gwb_config.withdrawal_rate,
                fee_rate=fee,
                fee_basis=self.gwb_config.fee_basis,
            )
            sim = GLWBPathSimulator(config, n_paths=self.n_paths // 2, seed=self.seed)
            result = sim.price(premium, age, r, sigma, max_age)
            return result.guarantee_cost - target_cost

        # Bisection search
        low, high = fee_bounds

        for _ in range(max_iterations):
            mid = (low + high) / 2
            cost = cost_at_fee(mid)

            if abs(cost) < tolerance:
                return mid

            if cost > 0:
                # Guarantee too expensive, need higher fee
                low = mid
            else:
                # Guarantee too cheap, can lower fee
                high = mid

        return (low + high) / 2

    def sensitivity_analysis(
        self,
        premium: float,
        age: int,
        r: float,
        sigma: float,
        max_age: int = 100,
    ) -> dict:
        """
        Analyze sensitivity of GLWB price to parameters.

        Parameters
        ----------
        premium : float
            Initial premium
        age : int
            Current age
        r : float
            Risk-free rate
        sigma : float
            Volatility
        max_age : int
            Maximum simulation age

        Returns
        -------
        dict
            Sensitivity measures
        """
        base = self.price(premium, age, r, sigma, max_age)

        # Volatility sensitivity (vega-like)
        up_sigma = self.price(premium, age, r, sigma * 1.1, max_age)
        down_sigma = self.price(premium, age, r, sigma * 0.9, max_age)
        sigma_sens = (up_sigma.price - down_sigma.price) / (0.2 * sigma)

        # Rate sensitivity (rho-like)
        up_r = self.price(premium, age, r + 0.01, sigma, max_age)
        down_r = self.price(premium, age, r - 0.01, sigma, max_age)
        rate_sens = (up_r.price - down_r.price) / 0.02

        # Age sensitivity
        if age + 5 < max_age:
            older = self.price(premium, age + 5, r, sigma, max_age)
            age_sens = (older.price - base.price) / 5
        else:
            age_sens = 0.0

        return {
            "base_price": base.price,
            "sigma_sensitivity": sigma_sens,
            "rate_sensitivity": rate_sens,
            "age_sensitivity": age_sens,
            "prob_ruin": base.prob_ruin,
        }
