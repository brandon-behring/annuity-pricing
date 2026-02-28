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

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, cast

import numpy as np

from ..behavioral import (
    DynamicLapseModel,
    ExpenseAssumptions,
    ExpenseModel,
    LapseAssumptions,
    WithdrawalAssumptions,
    WithdrawalModel,
)
from ..loaders.mortality import MortalityLoader, MortalityTable
from .gwb_tracker import GWBConfig, GWBTracker


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
    prob_lapse : float
        Probability of lapse before death/ruin
    mean_lapse_year : float
        Average year of lapse (if lapse occurs)
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
    prob_lapse: float
    mean_lapse_year: float
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
    pv_expenses : float
        Present value of insurer expenses
    ruin_year : int
        Year AV exhausted (-1 if never)
    lapse_year : int
        Year of lapse (-1 if never)
    final_av : float
        Account value at end of simulation
    final_gwb : float
        GWB at end of simulation
    death_year : int
        Year of death (-1 if survived)
    """

    pv_insurer_payments: float
    pv_withdrawals: float
    pv_expenses: float
    ruin_year: int
    lapse_year: int
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
        seed: int | None = None,
        lapse_assumptions: LapseAssumptions | None = None,
        withdrawal_assumptions: WithdrawalAssumptions | None = None,
        expense_assumptions: ExpenseAssumptions | None = None,
        steps_per_year: int = 1,
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
        lapse_assumptions : LapseAssumptions, optional
            Dynamic lapse parameters. If None, uses defaults.
        withdrawal_assumptions : WithdrawalAssumptions, optional
            Withdrawal utilization parameters. If None, uses defaults.
        expense_assumptions : ExpenseAssumptions, optional
            Expense parameters. If None, uses defaults.
        steps_per_year : int
            Number of timesteps per year. Default 1 (annual).
            Use 12 for monthly timesteps (Round 6 decision for Julia port).
        """
        if steps_per_year < 1:
            raise ValueError(f"steps_per_year must be >= 1, got {steps_per_year}")

        self.gwb_config = gwb_config
        self.n_paths = n_paths
        self.seed = seed
        self.steps_per_year = steps_per_year
        self._rng = np.random.default_rng(seed)
        self._mortality_loader = MortalityLoader()

        # Behavioral models with defaults
        self._lapse_model = DynamicLapseModel(lapse_assumptions or LapseAssumptions())
        self._withdrawal_model = WithdrawalModel(withdrawal_assumptions or WithdrawalAssumptions())
        self._expense_model = ExpenseModel(expense_assumptions or ExpenseAssumptions())

    def price(
        self,
        premium: float,
        age: int,
        r: float,
        sigma: float,
        max_age: int = 100,
        mortality_table: Callable[[int], float] | MortalityTable | None = None,
        utilization_rate: float | None = None,
        gender: str = "male",
        surrender_period_years: int = 7,
        use_behavioral_models: bool = True,
        deferral_years: int = 0,
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
        mortality_table : callable or MortalityTable, optional
            Function age -> qx or MortalityTable object. If None, uses SOA 2012 IAM.
        utilization_rate : float, optional
            Fixed utilization rate (overrides behavioral model if set).
            If None, uses WithdrawalModel for age-dependent utilization.
        gender : str
            Gender for default mortality table ("male" or "female")
        surrender_period_years : int
            Years until surrender period ends (affects lapse rates)
        use_behavioral_models : bool
            If True, uses lapse/withdrawal/expense models. If False, simple mode.
        deferral_years : int
            Years before withdrawals begin. During deferral, rollup applies
            to benefit base. After deferral, withdrawals begin and rollup stops.

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

        # Convert mortality table to callable
        # [T1] Default to SOA 2012 IAM (industry-standard table)
        if mortality_table is None:
            mortality_table = self._mortality_loader.soa_2012_iam(
                gender=cast(Literal["male", "female"], gender)
            )

        # Convert MortalityTable to callable if needed
        mortality_func: Callable[[int], float]
        if isinstance(mortality_table, MortalityTable):
            _table = mortality_table

            def _mortality_func(age: int) -> float:
                return _table.get_qx(age)

            mortality_func = _mortality_func
        else:
            mortality_func = mortality_table

        n_years = max_age - age
        path_results = []
        ruin_years = []
        lapse_years = []

        for _ in range(self.n_paths):
            result = self.simulate_single_path(
                premium=premium,
                age=age,
                r=r,
                sigma=sigma,
                n_years=n_years,
                mortality_func=mortality_func,
                utilization_rate=utilization_rate,
                surrender_period_years=surrender_period_years,
                use_behavioral_models=use_behavioral_models,
                deferral_years=deferral_years,
            )
            path_results.append(result)
            if result.ruin_year >= 0:
                ruin_years.append(result.ruin_year)
            if result.lapse_year >= 0:
                lapse_years.append(result.lapse_year)

        # Aggregate results
        pv_payoffs = np.array([r.pv_insurer_payments for r in path_results])
        mean_payoff = np.mean(pv_payoffs)
        std_payoff = np.std(pv_payoffs)
        standard_error = std_payoff / np.sqrt(self.n_paths)

        prob_ruin = len(ruin_years) / self.n_paths
        mean_ruin_year = np.mean(ruin_years) if ruin_years else -1.0
        prob_lapse = len(lapse_years) / self.n_paths
        mean_lapse_year = np.mean(lapse_years) if lapse_years else -1.0

        return GLWBPricingResult(
            price=mean_payoff,
            guarantee_cost=mean_payoff / premium,
            mean_payoff=mean_payoff,
            std_payoff=std_payoff,
            standard_error=standard_error,
            prob_ruin=prob_ruin,
            mean_ruin_year=float(mean_ruin_year),
            prob_lapse=prob_lapse,
            mean_lapse_year=float(mean_lapse_year),
            n_paths=self.n_paths,
        )

    def simulate_single_path(
        self,
        premium: float,
        age: int,
        r: float,
        sigma: float,
        n_years: int,
        mortality_func: Callable[[int], float],
        utilization_rate: float | None = None,
        surrender_period_years: int = 7,
        use_behavioral_models: bool = True,
        deferral_years: int = 0,
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
            Risk-free rate (annual)
        sigma : float
            Volatility (annual)
        n_years : int
            Maximum years to simulate
        mortality_func : callable
            Function age -> qx (annual mortality rate)
        utilization_rate : float, optional
            Fixed utilization rate. If None, uses WithdrawalModel.
        surrender_period_years : int
            Years until surrender period ends (for lapse model)
        use_behavioral_models : bool
            Whether to use lapse/withdrawal/expense models
        deferral_years : int
            Years before withdrawals begin (rollup applies during deferral)

        Returns
        -------
        PathResult
            Path simulation result

        Notes
        -----
        Timestep granularity is controlled by self.steps_per_year:
        - steps_per_year=1: Annual timesteps (dt=1.0)
        - steps_per_year=12: Monthly timesteps (dt=1/12)

        Monthly timesteps provide more realistic fee accrual and market dynamics
        but require 12x more computational steps.
        """
        tracker = GWBTracker(self.gwb_config, premium)
        state = tracker.initial_state()

        # Timestep parameters
        dt = 1.0 / self.steps_per_year  # e.g., 1/12 for monthly
        n_steps = n_years * self.steps_per_year

        pv_insurer_payments = 0.0
        pv_withdrawals = 0.0
        pv_expenses = 0.0
        ruin_year = -1
        lapse_year = -1
        death_year = -1
        current_age = age
        first_withdrawal_step = deferral_years * self.steps_per_year

        # GBM parameters scaled to timestep
        drift_per_step = (r - 0.5 * sigma**2) * dt
        diffusion_per_step = sigma * np.sqrt(dt)

        # Annual mortality scaled to timestep: qx_step ≈ 1 - (1 - qx)^dt
        # For small dt, this is approximately qx * dt

        for step in range(n_steps):
            # Current time in years (for discounting and events)
            t_years = (step + 1) * dt

            # Check mortality (annual rate converted to step rate)
            # Use conditional probability: P(death in step | alive at start of step)
            # For step k in year, P(death) = qx / steps_per_year (approximation)
            # More accurate: 1 - (1 - qx)^(1/steps_per_year)
            if step % self.steps_per_year == 0:  # New year, get new qx
                qx_annual = mortality_func(current_age)
                # Convert annual qx to per-step probability
                qx_step = 1 - (1 - qx_annual) ** dt

            if self._rng.random() < qx_step:
                death_year = int(t_years)
                break

            # Check dynamic lapse (at annual frequency for stability)
            if use_behavioral_models and state.av > 0 and step % self.steps_per_year == 0:
                surrender_complete = t_years >= surrender_period_years
                lapse_result = self._lapse_model.calculate_lapse(
                    gwb=state.gwb,
                    av=state.av,
                    surrender_period_complete=surrender_complete,
                )
                if self._rng.random() < lapse_result.lapse_rate:
                    lapse_year = int(t_years)
                    break  # Policy lapses, no further payments

            # Generate return (risk-neutral GBM at timestep granularity)
            # [T1] Under risk-neutral measure: drift = r - 0.5*sigma^2
            z = self._rng.standard_normal()
            av_return = drift_per_step + diffusion_per_step * z

            # Discount factor to this point in time
            df = np.exp(-r * t_years)

            # Calculate expenses (if behavioral models enabled)
            if use_behavioral_models and state.av > 0:
                expense_result = self._expense_model.calculate_period_expense(
                    av=state.av,
                    period_years=dt,
                    years_from_issue=int(t_years),
                )
                pv_expenses += expense_result.total_expense * df

            # Calculate withdrawal (only after deferral period)
            # Scale max withdrawal to timestep (annual withdrawal spread across steps)
            max_withdrawal_annual = tracker.calculate_max_withdrawal(state)
            max_withdrawal_step = max_withdrawal_annual * dt

            if step < first_withdrawal_step:
                # During deferral period - no withdrawals, rollup applies
                withdrawal = 0.0
            elif utilization_rate is not None:
                # Use fixed utilization rate
                withdrawal = max_withdrawal_step * utilization_rate
            elif use_behavioral_models:
                # Use behavioral model for withdrawal utilization (at annual equivalent)
                years_since = (step - first_withdrawal_step) / self.steps_per_year
                withdrawal_result = self._withdrawal_model.calculate_withdrawal(
                    gwb=state.gwb,
                    withdrawal_rate=self.gwb_config.withdrawal_rate,
                    age=current_age,
                    years_since_first_withdrawal=int(years_since),
                )
                # Scale withdrawal to timestep
                withdrawal = withdrawal_result.withdrawal_amount * dt
            else:
                # Default to 100% utilization
                withdrawal = max_withdrawal_step

            # Step forward with appropriate dt
            result = tracker.step(state, av_return, dt=dt, withdrawal=withdrawal)
            state = result.new_state

            # Track withdrawals
            pv_withdrawals += result.withdrawal_taken * df

            # Check for ruin (AV exhausted)
            if state.av <= 0 and ruin_year < 0:
                ruin_year = int(t_years) + 1

            # If ruined, insurer pays guaranteed amount
            if state.av <= 0:
                insurer_payment = max_withdrawal_step  # Guaranteed payment this step
                pv_insurer_payments += insurer_payment * df

            # Age increments annually (on anniversary)
            if (step + 1) % self.steps_per_year == 0:
                current_age += 1

        return PathResult(
            pv_insurer_payments=pv_insurer_payments,
            pv_withdrawals=pv_withdrawals,
            pv_expenses=pv_expenses,
            ruin_year=ruin_year,
            lapse_year=lapse_year,
            final_av=state.av,
            final_gwb=state.gwb,
            death_year=death_year,
        )

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
