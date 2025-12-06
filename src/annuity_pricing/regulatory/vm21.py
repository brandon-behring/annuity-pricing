"""
VM-21 Calculator - Phase 9.

Implements NAIC VM-21 (AG43) for variable annuity reserves.

Theory
------
[T1] VM-21 requires:
- CTE(70) over stochastic scenarios
- Standard Scenario Amount (SSA)
- Reserve = max(CTE70, SSA, CSV floor)

[T1] CTE(α) = E[X | X ≥ VaR(α)]
     = Average of worst (1-α)% of scenarios

See: docs/knowledge/domain/vm21_vm22.md
"""

from dataclasses import dataclass
from typing import Optional, Callable, List
import numpy as np

from .scenarios import ScenarioGenerator, AG43Scenarios, EconomicScenario


@dataclass(frozen=True)
class VM21Result:
    """
    VM-21 calculation result.

    Attributes
    ----------
    cte70 : float
        Conditional Tail Expectation at 70%
    ssa : float
        Standard Scenario Amount
    csv_floor : float
        Cash Surrender Value floor
    reserve : float
        Required reserve = max(CTE70, SSA, CSV)
    scenario_count : int
        Number of scenarios used
    mean_pv : float
        Mean present value across scenarios
    std_pv : float
        Standard deviation of present values
    worst_pv : float
        Worst scenario present value
    """

    cte70: float
    ssa: float
    csv_floor: float
    reserve: float
    scenario_count: int
    mean_pv: float = 0.0
    std_pv: float = 0.0
    worst_pv: float = 0.0


@dataclass(frozen=True)
class PolicyData:
    """
    Policy data for VM-21 calculation.

    Attributes
    ----------
    av : float
        Current account value
    gwb : float
        Guaranteed withdrawal base
    age : int
        Policyholder age
    csv : float
        Cash surrender value
    withdrawal_rate : float
        Annual withdrawal rate (e.g., 0.05 for 5%)
    fee_rate : float
        Annual fee rate (e.g., 0.01 for 1%)
    """

    av: float
    gwb: float
    age: int
    csv: float = 0.0
    withdrawal_rate: float = 0.05
    fee_rate: float = 0.01


class VM21Calculator:
    """
    VM-21 reserve calculator for variable annuities.

    [T1] VM-21 Reserve = max(CTE70, SSA, CSV floor)

    Examples
    --------
    >>> calc = VM21Calculator(n_scenarios=1000, seed=42)
    >>> policy = PolicyData(av=100_000, gwb=110_000, age=70)
    >>> result = calc.calculate_reserve(policy)
    >>> result.reserve > 0
    True

    See: docs/knowledge/domain/vm21_vm22.md
    """

    def __init__(
        self,
        n_scenarios: int = 1000,
        projection_years: int = 30,
        seed: Optional[int] = None,
    ):
        """
        Initialize VM-21 calculator.

        Parameters
        ----------
        n_scenarios : int
            Number of scenarios for CTE calculation
        projection_years : int
            Years to project
        seed : int, optional
            Random seed for reproducibility
        """
        if n_scenarios <= 0:
            raise ValueError(f"n_scenarios must be positive, got {n_scenarios}")

        self.n_scenarios = n_scenarios
        self.projection_years = projection_years
        self.seed = seed
        self._scenario_generator = ScenarioGenerator(
            n_scenarios=n_scenarios,
            projection_years=projection_years,
            seed=seed,
        )

    def calculate_cte(
        self,
        scenario_results: np.ndarray,
        alpha: float = 0.70,
    ) -> float:
        """
        Calculate CTE (Conditional Tail Expectation).

        [T1] CTE(α) = Average of worst (1-α)% of scenarios

        Parameters
        ----------
        scenario_results : ndarray
            PV of liability for each scenario (positive = liability)
        alpha : float
            CTE level (0.70 for CTE70)

        Returns
        -------
        float
            CTE at specified alpha

        Examples
        --------
        >>> calc = VM21Calculator()
        >>> results = np.array([100, 200, 300, 400, 500, 600, 700, 800, 900, 1000])
        >>> calc.calculate_cte(results, alpha=0.70)
        900.0
        """
        if not 0 < alpha < 1:
            raise ValueError(f"Alpha must be in (0, 1), got {alpha}")
        if len(scenario_results) == 0:
            raise ValueError("scenario_results cannot be empty")

        # Sort descending (worst = highest liability first)
        sorted_results = np.sort(scenario_results)[::-1]

        # Take worst (1-α)% of scenarios
        n_tail = max(1, int(len(sorted_results) * (1 - alpha)))
        tail_values = sorted_results[:n_tail]

        return float(np.mean(tail_values))

    def calculate_cte70(
        self,
        scenario_results: np.ndarray,
    ) -> float:
        """
        Calculate CTE(70) from scenario results.

        [T1] CTE70 = Average of worst 30% of scenarios

        Parameters
        ----------
        scenario_results : ndarray
            PV of liability for each scenario

        Returns
        -------
        float
            CTE(70)

        Examples
        --------
        >>> calc = VM21Calculator()
        >>> results = np.array([100, 200, 300, 400, 500, 600, 700, 800, 900, 1000])
        >>> calc.calculate_cte70(results)
        900.0
        """
        return self.calculate_cte(scenario_results, alpha=0.70)

    def calculate_ssa(
        self,
        policy: PolicyData,
        mortality_table: Optional[Callable[[int], float]] = None,
        r: float = 0.04,
    ) -> float:
        """
        Calculate Standard Scenario Amount.

        [T1] SSA uses prescribed deterministic scenarios.

        Parameters
        ----------
        policy : PolicyData
            Policy information
        mortality_table : callable, optional
            Function age -> qx
        r : float
            Discount rate

        Returns
        -------
        float
            Standard Scenario Amount

        Examples
        --------
        >>> calc = VM21Calculator()
        >>> policy = PolicyData(av=100_000, gwb=110_000, age=70)
        >>> calc.calculate_ssa(policy) > 0
        True
        """
        if mortality_table is None:
            mortality_table = self._default_mortality

        # Standard scenario: equity drops 20%, no recovery for 10 years
        # Then gradual 7% return
        max_age = 100
        n_years = max_age - policy.age

        # Project under stress scenario
        av = policy.av
        gwb = policy.gwb
        pv_liability = 0.0

        for t in range(min(n_years, self.projection_years)):
            current_age = policy.age + t

            # Survival probability
            qx = mortality_table(current_age)
            if np.random.random() < qx:
                break

            # Standard scenario: -20% year 1, flat for 10 years, then 7%
            if t == 0:
                equity_return = -0.20
            elif t < 10:
                equity_return = 0.0
            else:
                equity_return = 0.07

            # Update AV
            av = av * (1 + equity_return) * (1 - policy.fee_rate)

            # Guaranteed withdrawal
            guaranteed_wd = gwb * policy.withdrawal_rate

            # If AV < guaranteed withdrawal, liability emerges
            if av <= 0:
                df = np.exp(-r * (t + 1))
                pv_liability += guaranteed_wd * df

            av = max(0, av - guaranteed_wd)

        return pv_liability

    def calculate_reserve(
        self,
        policy: PolicyData,
        scenarios: Optional[AG43Scenarios] = None,
        mortality_table: Optional[Callable[[int], float]] = None,
        r: float = 0.04,
    ) -> VM21Result:
        """
        Calculate VM-21 reserve.

        [T1] Reserve = max(CTE70, SSA, CSV floor)

        Parameters
        ----------
        policy : PolicyData
            Policy information
        scenarios : AG43Scenarios, optional
            Pre-generated scenarios. If None, generates new scenarios.
        mortality_table : callable, optional
            Function age -> qx
        r : float
            Discount rate

        Returns
        -------
        VM21Result
            Complete VM-21 result

        Examples
        --------
        >>> calc = VM21Calculator(n_scenarios=100, seed=42)
        >>> policy = PolicyData(av=100_000, gwb=110_000, age=70)
        >>> result = calc.calculate_reserve(policy)
        >>> result.reserve >= result.csv_floor
        True
        """
        if policy.av < 0:
            raise ValueError(f"Account value cannot be negative, got {policy.av}")
        if policy.gwb < 0:
            raise ValueError(f"GWB cannot be negative, got {policy.gwb}")

        if mortality_table is None:
            mortality_table = self._default_mortality

        # Generate scenarios if not provided
        if scenarios is None:
            scenarios = self._scenario_generator.generate_ag43_scenarios()

        # Calculate PV of liability for each scenario
        scenario_pvs = self._run_scenarios(policy, scenarios, mortality_table, r)

        # Calculate components
        cte70 = self.calculate_cte70(scenario_pvs)
        ssa = self.calculate_ssa(policy, mortality_table, r)
        csv_floor = policy.csv

        # Reserve = max of three components
        reserve = max(cte70, ssa, csv_floor)

        return VM21Result(
            cte70=cte70,
            ssa=ssa,
            csv_floor=csv_floor,
            reserve=reserve,
            scenario_count=len(scenario_pvs),
            mean_pv=float(np.mean(scenario_pvs)),
            std_pv=float(np.std(scenario_pvs)),
            worst_pv=float(np.max(scenario_pvs)),
        )

    def _run_scenarios(
        self,
        policy: PolicyData,
        scenarios: AG43Scenarios,
        mortality_table: Callable[[int], float],
        r: float,
    ) -> np.ndarray:
        """
        Run all scenarios and calculate PV of liability for each.

        Parameters
        ----------
        policy : PolicyData
            Policy data
        scenarios : AG43Scenarios
            Economic scenarios
        mortality_table : callable
            Function age -> qx
        r : float
            Discount rate

        Returns
        -------
        ndarray
            PV of liability for each scenario
        """
        pvs = []
        for scenario in scenarios.scenarios:
            pv = self._run_single_scenario(policy, scenario, mortality_table, r)
            pvs.append(pv)
        return np.array(pvs)

    def _run_single_scenario(
        self,
        policy: PolicyData,
        scenario: EconomicScenario,
        mortality_table: Callable[[int], float],
        r: float,
    ) -> float:
        """
        Run single scenario and calculate PV of liability.

        [T1] Liability = PV of (guaranteed withdrawals when AV = 0)

        Parameters
        ----------
        policy : PolicyData
            Policy data
        scenario : EconomicScenario
            Single economic scenario
        mortality_table : callable
            Function age -> qx
        r : float
            Discount rate

        Returns
        -------
        float
            PV of liability for this scenario
        """
        max_age = 100
        n_years = min(max_age - policy.age, len(scenario.equity_returns))

        av = policy.av
        gwb = policy.gwb
        pv_liability = 0.0
        alive = True

        rng = np.random.default_rng(abs(hash((self.seed or 0, scenario.scenario_id))))  # Deterministic per scenario

        for t in range(n_years):
            current_age = policy.age + t

            # Check mortality
            qx = mortality_table(current_age)
            if rng.random() < qx:
                alive = False
                break

            # Get equity return for this year
            equity_return = scenario.equity_returns[t]

            # Update AV (market return - fee)
            av = av * (1 + equity_return) * (1 - policy.fee_rate)

            # Guaranteed withdrawal
            guaranteed_wd = gwb * policy.withdrawal_rate

            # If AV is exhausted, insurer pays
            if av <= 0 and alive:
                # Use scenario discount rate or fixed rate
                discount_rate = scenario.rates[t] if len(scenario.rates) > t else r
                df = np.exp(-discount_rate * (t + 1))
                pv_liability += guaranteed_wd * df

            # Reduce AV by withdrawal
            av = max(0, av - guaranteed_wd)

        return pv_liability

    def _default_mortality(self, age: int) -> float:
        """
        Default mortality table (Gompertz approximation).

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
        # Gompertz: qx = 0.0001 * e^(0.08 * age)
        qx = 0.0001 * np.exp(0.08 * age)
        return min(qx, 1.0)


def calculate_cte_levels(
    scenario_results: np.ndarray,
    levels: Optional[List[float]] = None,
) -> dict:
    """
    Calculate CTE at multiple levels.

    Parameters
    ----------
    scenario_results : ndarray
        PV of liability for each scenario
    levels : list, optional
        CTE levels to calculate (default: 65, 70, 75, 80, 85, 90, 95)

    Returns
    -------
    dict
        CTE values at each level

    Examples
    --------
    >>> results = np.array([100, 200, 300, 400, 500, 600, 700, 800, 900, 1000])
    >>> ctes = calculate_cte_levels(results)
    >>> ctes['CTE70']
    900.0
    """
    if levels is None:
        levels = [0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]

    calc = VM21Calculator()
    ctes = {}
    for level in levels:
        key = f"CTE{int(level * 100)}"
        ctes[key] = calc.calculate_cte(scenario_results, alpha=level)

    return ctes


def sensitivity_analysis(
    policy: PolicyData,
    n_scenarios: int = 1000,
    seed: Optional[int] = None,
) -> dict:
    """
    Perform sensitivity analysis on VM-21 reserve.

    Parameters
    ----------
    policy : PolicyData
        Base policy data
    n_scenarios : int
        Number of scenarios
    seed : int, optional
        Random seed

    Returns
    -------
    dict
        Sensitivity results

    Examples
    --------
    >>> policy = PolicyData(av=100_000, gwb=110_000, age=70)
    >>> sens = sensitivity_analysis(policy, n_scenarios=100, seed=42)
    >>> 'base_reserve' in sens
    True
    """
    calc = VM21Calculator(n_scenarios=n_scenarios, seed=seed)

    # Base case
    base_result = calc.calculate_reserve(policy)

    # GWB +10%
    policy_gwb_up = PolicyData(
        av=policy.av,
        gwb=policy.gwb * 1.10,
        age=policy.age,
        csv=policy.csv,
        withdrawal_rate=policy.withdrawal_rate,
        fee_rate=policy.fee_rate,
    )
    result_gwb_up = calc.calculate_reserve(policy_gwb_up)

    # Age +5
    policy_older = PolicyData(
        av=policy.av,
        gwb=policy.gwb,
        age=policy.age + 5,
        csv=policy.csv,
        withdrawal_rate=policy.withdrawal_rate,
        fee_rate=policy.fee_rate,
    )
    result_older = calc.calculate_reserve(policy_older)

    # AV -20%
    policy_av_down = PolicyData(
        av=policy.av * 0.80,
        gwb=policy.gwb,
        age=policy.age,
        csv=policy.csv,
        withdrawal_rate=policy.withdrawal_rate,
        fee_rate=policy.fee_rate,
    )
    result_av_down = calc.calculate_reserve(policy_av_down)

    return {
        "base_reserve": base_result.reserve,
        "base_cte70": base_result.cte70,
        "gwb_up_10pct": result_gwb_up.reserve,
        "gwb_sensitivity": (result_gwb_up.reserve - base_result.reserve) / base_result.reserve
        if base_result.reserve > 0
        else 0,
        "age_plus_5": result_older.reserve,
        "age_sensitivity": (result_older.reserve - base_result.reserve) / base_result.reserve
        if base_result.reserve > 0
        else 0,
        "av_down_20pct": result_av_down.reserve,
        "av_sensitivity": (result_av_down.reserve - base_result.reserve) / base_result.reserve
        if base_result.reserve > 0
        else 0,
    }
