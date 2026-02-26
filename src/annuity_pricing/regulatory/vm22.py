"""
VM-22 Calculator - Phase 9.

[PROTOTYPE] EDUCATIONAL USE ONLY - NOT FOR PRODUCTION REGULATORY FILING
===========================================================================
This module provides a simplified implementation of NAIC VM-22 (PBR for
fixed annuities) for educational purposes. Key limitations vs production:

MISSING FOR COMPLIANCE:
- NAIC-prescribed scenario generator (transition to GOES effective 2026)
- Full asset-liability matching model
- Prescribed lapse formulas with dynamic adjustments
- Company experience studies and credibility weighting
- Non-guaranteed element modeling
- NAIC VM-G (corporate governance) requirements
- VM-31 Actuarial Report requirements
- Independent model validation

VM-22 TIMELINE:
- January 1, 2026: Voluntary adoption begins
- January 1, 2029: Mandatory for all fixed annuities

This implementation uses:
- Custom Vasicek + GBM scenarios (NOT NAIC-prescribed)
- Simplified deterministic/stochastic reserve methodology
- Educational approximations for SET/SST

For production regulatory filing, requires FSA/MAAA certification and
NAIC-compliant scenario generators. Estimated gap: 6-12 months.

See: docs/regulatory/AG43_COMPLIANCE_GAP.md
===========================================================================

Implements NAIC VM-22 for fixed annuity reserves (Principle-Based Reserving).

Theory
------
[T1] VM-22 reserve determination:
1. Stochastic Exclusion Test (SET) - if pass, use DR
2. Single Scenario Test (SST) - if pass, use DR
3. If both fail → Stochastic Reserve (SR)

[T1] Reserve = max(DR, SR if required, Net Premium Reserve)

Effective Dates:
- January 1, 2026: Voluntary adoption
- January 1, 2029: Mandatory compliance

See: docs/knowledge/domain/vm21_vm22.md
"""

from dataclasses import dataclass
from enum import Enum

import numpy as np

from ..loaders.yield_curve import YieldCurve, YieldCurveLoader
from .scenarios import ScenarioGenerator, generate_deterministic_scenarios


class ReserveType(Enum):
    """Type of reserve calculation used."""

    DETERMINISTIC = "deterministic"
    STOCHASTIC = "stochastic"


@dataclass(frozen=True)
class VM22Result:
    """
    VM-22 calculation result.

    Attributes
    ----------
    reserve : float
        Required reserve
    net_premium_reserve : float
        NPR component
    deterministic_reserve : float
        DR component
    stochastic_reserve : float
        SR component (if applicable)
    reserve_type : ReserveType
        Which reserve calculation was binding
    set_passed : bool
        Whether Stochastic Exclusion Test passed
    sst_passed : bool
        Whether Single Scenario Test passed
    """

    reserve: float
    net_premium_reserve: float
    deterministic_reserve: float
    stochastic_reserve: float | None = None
    reserve_type: ReserveType = ReserveType.DETERMINISTIC
    set_passed: bool = True
    sst_passed: bool = True


@dataclass(frozen=True)
class FixedAnnuityPolicy:
    """
    Fixed annuity policy data.

    Attributes
    ----------
    premium : float
        Initial premium
    guaranteed_rate : float
        Guaranteed crediting rate (e.g., 0.04 for 4%)
    term_years : int
        Term of guarantee
    current_year : int
        Current policy year (0 = issue)
    surrender_charge_pct : float
        Current surrender charge percentage
    account_value : float
        Current account value (if different from premium)
    """

    premium: float
    guaranteed_rate: float
    term_years: int
    current_year: int = 0
    surrender_charge_pct: float = 0.07
    account_value: float | None = None

    @property
    def av(self) -> float:
        """Get account value (defaults to premium if not specified)."""
        return self.account_value if self.account_value is not None else self.premium


@dataclass(frozen=True)
class StochasticExclusionResult:
    """
    Result of Stochastic Exclusion Test.

    Attributes
    ----------
    passed : bool
        Whether product passes exclusion (can use DR)
    ratio : float
        SET ratio (liability / asset value)
    threshold : float
        Threshold for passing
    """

    passed: bool
    ratio: float
    threshold: float


class VM22Calculator:
    """
    VM-22 reserve calculator for fixed annuities.

    [PROTOTYPE] EDUCATIONAL USE ONLY
    --------------------------------
    This calculator is for educational/research purposes only.
    NOT suitable for regulatory filings. See module docstring for details.
    VM-22 mandatory compliance begins January 1, 2029.

    [T1] VM-22 uses principle-based reserving:
    - Stochastic Exclusion Test determines reserve type
    - Deterministic Reserve for simple products
    - Stochastic Reserve for complex products

    Examples
    --------
    >>> calc = VM22Calculator(seed=42)
    >>> policy = FixedAnnuityPolicy(premium=100_000, guaranteed_rate=0.04, term_years=5)
    >>> result = calc.calculate_reserve(policy)
    >>> result.reserve > 0
    True

    See Also
    --------
    docs/regulatory/AG43_COMPLIANCE_GAP.md : Detailed compliance gap analysis
    docs/knowledge/domain/vm21_vm22.md : Theory reference
    """

    def __init__(
        self,
        n_scenarios: int = 1000,
        projection_years: int = 30,
        seed: int | None = None,
    ):
        """
        Initialize VM-22 calculator.

        Parameters
        ----------
        n_scenarios : int
            Number of scenarios for stochastic reserve
        projection_years : int
            Years to project
        seed : int, optional
            Random seed
        """
        self.n_scenarios = n_scenarios
        self.projection_years = projection_years
        self.seed = seed
        self._scenario_generator = ScenarioGenerator(
            n_scenarios=n_scenarios,
            projection_years=projection_years,
            seed=seed,
        )
        self._yield_curve_loader = YieldCurveLoader()

    def calculate_reserve(
        self,
        policy: FixedAnnuityPolicy,
        market_rate: float | None = None,
        yield_curve: YieldCurve | None = None,
        lapse_rate: float = 0.05,
    ) -> VM22Result:
        """
        Calculate VM-22 reserve.

        [T1] Reserve = max(NPR, DR or SR based on exclusion tests)

        Parameters
        ----------
        policy : FixedAnnuityPolicy
            Policy data
        market_rate : float, optional
            Current market rate for discounting. If None, derived from yield_curve.
        yield_curve : YieldCurve, optional
            Yield curve for rates. If None, uses flat 4% curve.
        lapse_rate : float
            Assumed annual lapse rate

        Returns
        -------
        VM22Result
            Complete VM-22 result

        Examples
        --------
        >>> calc = VM22Calculator(seed=42)
        >>> policy = FixedAnnuityPolicy(premium=100_000, guaranteed_rate=0.04, term_years=5)
        >>> result = calc.calculate_reserve(policy)
        >>> result.reserve >= 0
        True
        """
        if policy.premium <= 0:
            raise ValueError(f"Premium must be positive, got {policy.premium}")
        if policy.guaranteed_rate < 0:
            raise ValueError(f"Guaranteed rate cannot be negative, got {policy.guaranteed_rate}")

        # Default to flat 4% yield curve if neither provided
        if yield_curve is None and market_rate is None:
            yield_curve = self._yield_curve_loader.flat_curve(0.04)
            market_rate = 0.04
        elif yield_curve is not None and market_rate is None:
            # Derive market rate from yield curve
            market_rate = yield_curve.get_rate(float(policy.term_years))
        elif market_rate is not None and yield_curve is None:
            # Use provided market_rate directly
            pass  # market_rate already set

        # After the above logic, market_rate must be resolved to a float.
        # Guard against any code path that leaves it as None.
        if market_rate is None:
            market_rate = 0.04  # Defensive default (same as flat_curve fallback)

        # Calculate Net Premium Reserve (floor)
        npr = self.calculate_net_premium_reserve(policy, market_rate)

        # Run Stochastic Exclusion Test
        set_result = self.stochastic_exclusion_test(policy, market_rate)

        # Run Single Scenario Test if SET fails
        sst_passed = True
        if not set_result.passed:
            sst_passed = self.single_scenario_test(policy, market_rate, lapse_rate)

        # Determine reserve type
        if set_result.passed or sst_passed:
            # Use Deterministic Reserve
            dr = self.calculate_deterministic_reserve(policy, market_rate, lapse_rate)
            reserve = max(npr, dr)
            return VM22Result(
                reserve=reserve,
                net_premium_reserve=npr,
                deterministic_reserve=dr,
                stochastic_reserve=None,
                reserve_type=ReserveType.DETERMINISTIC,
                set_passed=set_result.passed,
                sst_passed=sst_passed,
            )
        else:
            # Use Stochastic Reserve
            dr = self.calculate_deterministic_reserve(policy, market_rate, lapse_rate)
            sr = self.calculate_stochastic_reserve(policy, market_rate, lapse_rate)
            reserve = max(npr, dr, sr)
            return VM22Result(
                reserve=reserve,
                net_premium_reserve=npr,
                deterministic_reserve=dr,
                stochastic_reserve=sr,
                reserve_type=ReserveType.STOCHASTIC,
                set_passed=set_result.passed,
                sst_passed=sst_passed,
            )

    def calculate_net_premium_reserve(
        self,
        policy: FixedAnnuityPolicy,
        market_rate: float,
    ) -> float:
        """
        Calculate Net Premium Reserve (NPR).

        [T1] NPR = PV of future guaranteed benefits at valuation rate

        Parameters
        ----------
        policy : FixedAnnuityPolicy
            Policy data
        market_rate : float
            Valuation rate

        Returns
        -------
        float
            Net Premium Reserve

        Examples
        --------
        >>> calc = VM22Calculator()
        >>> policy = FixedAnnuityPolicy(premium=100_000, guaranteed_rate=0.04, term_years=5)
        >>> calc.calculate_net_premium_reserve(policy, market_rate=0.04) > 0
        True
        """
        # NPR = PV of guaranteed maturity value
        remaining_years = policy.term_years - policy.current_year

        # Guaranteed maturity value
        gmv = policy.av * ((1 + policy.guaranteed_rate) ** remaining_years)

        # Discount to present
        npr = gmv * np.exp(-market_rate * remaining_years)

        return npr

    def calculate_deterministic_reserve(
        self,
        policy: FixedAnnuityPolicy,
        market_rate: float,
        lapse_rate: float,
    ) -> float:
        """
        Calculate Deterministic Reserve (DR).

        [T1] DR = PV of liabilities under deterministic scenarios.

        Parameters
        ----------
        policy : FixedAnnuityPolicy
            Policy data
        market_rate : float
            Market rate
        lapse_rate : float
            Annual lapse rate

        Returns
        -------
        float
            Deterministic Reserve

        Examples
        --------
        >>> calc = VM22Calculator()
        >>> policy = FixedAnnuityPolicy(premium=100_000, guaranteed_rate=0.04, term_years=5)
        >>> calc.calculate_deterministic_reserve(policy, 0.04, 0.05) > 0
        True
        """
        scenarios = generate_deterministic_scenarios(
            n_years=self.projection_years,
            base_rate=market_rate,
        )

        # Run each scenario
        pvs = []
        for scenario in scenarios:
            pv = self._run_fixed_scenario(policy, scenario.rates, lapse_rate)
            pvs.append(pv)

        # DR = max of deterministic scenarios
        return max(pvs)

    def calculate_stochastic_reserve(
        self,
        policy: FixedAnnuityPolicy,
        market_rate: float,
        lapse_rate: float,
    ) -> float:
        """
        Calculate Stochastic Reserve (SR).

        [T1] SR = CTE70 over stochastic scenarios.

        Parameters
        ----------
        policy : FixedAnnuityPolicy
            Policy data
        market_rate : float
            Initial market rate
        lapse_rate : float
            Annual lapse rate

        Returns
        -------
        float
            Stochastic Reserve

        Examples
        --------
        >>> calc = VM22Calculator(n_scenarios=100, seed=42)
        >>> policy = FixedAnnuityPolicy(premium=100_000, guaranteed_rate=0.04, term_years=5)
        >>> calc.calculate_stochastic_reserve(policy, 0.04, 0.05) > 0
        True
        """
        ag43 = self._scenario_generator.generate_ag43_scenarios(
            initial_rate=market_rate,
        )

        # Run each scenario
        pvs = []
        for scenario in ag43.scenarios:
            pv = self._run_fixed_scenario(policy, scenario.rates, lapse_rate)
            pvs.append(pv)

        # CTE70 = average of worst 30%
        sorted_pvs = np.sort(pvs)[::-1]
        n_tail = max(1, int(len(sorted_pvs) * 0.30))
        return float(np.mean(sorted_pvs[:n_tail]))

    def stochastic_exclusion_test(
        self,
        policy: FixedAnnuityPolicy,
        market_rate: float,
        threshold: float = 1.10,
    ) -> StochasticExclusionResult:
        """
        Perform Stochastic Exclusion Test (SET).

        [T1] SET determines if full stochastic modeling is required.
        If liability/asset ratio < threshold, product "passes" and can use DR.

        Parameters
        ----------
        policy : FixedAnnuityPolicy
            Policy data
        market_rate : float
            Current market rate
        threshold : float
            Ratio threshold for passing (default 1.10)

        Returns
        -------
        StochasticExclusionResult
            Test result

        Examples
        --------
        >>> calc = VM22Calculator()
        >>> policy = FixedAnnuityPolicy(premium=100_000, guaranteed_rate=0.04, term_years=5)
        >>> result = calc.stochastic_exclusion_test(policy, market_rate=0.04)
        >>> isinstance(result.passed, bool)
        True
        """
        remaining_years = policy.term_years - policy.current_year

        # Guaranteed maturity value
        gmv = policy.av * ((1 + policy.guaranteed_rate) ** remaining_years)

        # Market maturity value (what assets would earn)
        mmv = policy.av * ((1 + market_rate) ** remaining_years)

        # Ratio = guaranteed / market
        ratio = gmv / mmv if mmv > 0 else float("inf")

        # Pass if ratio is below threshold
        passed = ratio < threshold

        return StochasticExclusionResult(
            passed=passed,
            ratio=ratio,
            threshold=threshold,
        )

    def single_scenario_test(
        self,
        policy: FixedAnnuityPolicy,
        market_rate: float,
        lapse_rate: float,
    ) -> bool:
        """
        Perform Single Scenario Test (SST).

        [T1] SST uses a prescribed stress scenario.
        If DR under stress < threshold, product "passes".

        Parameters
        ----------
        policy : FixedAnnuityPolicy
            Policy data
        market_rate : float
            Current market rate
        lapse_rate : float
            Lapse rate

        Returns
        -------
        bool
            Whether test passed

        Examples
        --------
        >>> calc = VM22Calculator()
        >>> policy = FixedAnnuityPolicy(premium=100_000, guaranteed_rate=0.04, term_years=5)
        >>> isinstance(calc.single_scenario_test(policy, 0.04, 0.05), bool)
        True
        """
        # Stress scenario: rates drop 2%
        stressed_rate = max(0.0, market_rate - 0.02)

        # Calculate DR under stress
        dr_base = self.calculate_deterministic_reserve(policy, market_rate, lapse_rate)
        dr_stress = self.calculate_deterministic_reserve(policy, stressed_rate, lapse_rate)

        # Pass if stress doesn't increase reserve by more than 20%
        if dr_base == 0:
            return True

        increase = (dr_stress - dr_base) / dr_base
        return bool(increase < 0.20)

    def _run_fixed_scenario(
        self,
        policy: FixedAnnuityPolicy,
        rate_path: np.ndarray,
        lapse_rate: float,
    ) -> float:
        """
        Run a single scenario for fixed annuity.

        [T1] PV of liability = discounted guaranteed benefits × survival probability

        Parameters
        ----------
        policy : FixedAnnuityPolicy
            Policy data
        rate_path : ndarray
            Interest rate path
        lapse_rate : float
            Annual lapse rate

        Returns
        -------
        float
            PV of liability for this scenario
        """
        remaining_years = policy.term_years - policy.current_year
        n_years = min(remaining_years, len(rate_path))

        av = policy.av
        pv_liability = 0.0
        survival = 1.0  # Probability of persistency

        for t in range(n_years):
            discount_rate = rate_path[t] if t < len(rate_path) else rate_path[-1]

            # Account grows at guaranteed rate
            av = av * (1 + policy.guaranteed_rate)

            # Lapse (surrender)
            lapse_benefit = av * (1 - policy.surrender_charge_pct * max(0, 1 - t / policy.term_years))
            pv_lapse = lapse_rate * survival * lapse_benefit * np.exp(-discount_rate * (t + 1))

            # Update survival
            survival *= (1 - lapse_rate)

            # Add to PV
            pv_liability += pv_lapse

        # Terminal benefit for survivors
        if n_years > 0:
            final_rate = rate_path[-1] if len(rate_path) > 0 else 0.04
            pv_maturity = survival * av * np.exp(-final_rate * n_years)
            pv_liability += pv_maturity

        return pv_liability


def compare_reserve_methods(
    policy: FixedAnnuityPolicy,
    market_rate: float = 0.04,
    lapse_rate: float = 0.05,
    n_scenarios: int = 1000,
    seed: int | None = None,
) -> dict:
    """
    Compare different reserve calculation methods.

    Parameters
    ----------
    policy : FixedAnnuityPolicy
        Policy data
    market_rate : float
        Market rate
    lapse_rate : float
        Lapse rate
    n_scenarios : int
        Number of scenarios
    seed : int, optional
        Random seed

    Returns
    -------
    dict
        Comparison of reserve methods

    Examples
    --------
    >>> policy = FixedAnnuityPolicy(premium=100_000, guaranteed_rate=0.04, term_years=5)
    >>> comparison = compare_reserve_methods(policy, n_scenarios=100, seed=42)
    >>> 'npr' in comparison
    True
    """
    calc = VM22Calculator(n_scenarios=n_scenarios, seed=seed)

    npr = calc.calculate_net_premium_reserve(policy, market_rate)
    dr = calc.calculate_deterministic_reserve(policy, market_rate, lapse_rate)
    sr = calc.calculate_stochastic_reserve(policy, market_rate, lapse_rate)
    set_result = calc.stochastic_exclusion_test(policy, market_rate)

    return {
        "npr": npr,
        "deterministic_reserve": dr,
        "stochastic_reserve": sr,
        "final_reserve": max(npr, dr),
        "set_passed": set_result.passed,
        "set_ratio": set_result.ratio,
        "sr_vs_dr": (sr - dr) / dr if dr > 0 else 0,
    }


def vm22_sensitivity(
    policy: FixedAnnuityPolicy,
    market_rate: float = 0.04,
    lapse_rate: float = 0.05,
    seed: int | None = None,
) -> dict:
    """
    Perform VM-22 sensitivity analysis.

    Parameters
    ----------
    policy : FixedAnnuityPolicy
        Policy data
    market_rate : float
        Base market rate
    lapse_rate : float
        Base lapse rate
    seed : int, optional
        Random seed

    Returns
    -------
    dict
        Sensitivity results

    Examples
    --------
    >>> policy = FixedAnnuityPolicy(premium=100_000, guaranteed_rate=0.04, term_years=5)
    >>> sens = vm22_sensitivity(policy, seed=42)
    >>> 'base_reserve' in sens
    True
    """
    calc = VM22Calculator(n_scenarios=500, seed=seed)

    # Base case
    base = calc.calculate_reserve(policy, market_rate=market_rate, lapse_rate=lapse_rate)

    # Rate up +1%
    rate_up = calc.calculate_reserve(policy, market_rate=market_rate + 0.01, lapse_rate=lapse_rate)

    # Rate down -1%
    rate_down = calc.calculate_reserve(policy, market_rate=max(0.0, market_rate - 0.01), lapse_rate=lapse_rate)

    # Lapse up 2x
    lapse_up = calc.calculate_reserve(policy, market_rate=market_rate, lapse_rate=lapse_rate * 2)

    # Lapse down 0.5x
    lapse_down = calc.calculate_reserve(policy, market_rate=market_rate, lapse_rate=lapse_rate * 0.5)

    return {
        "base_reserve": base.reserve,
        "base_type": base.reserve_type.value,
        "rate_up_1pct": rate_up.reserve,
        "rate_sensitivity": (rate_up.reserve - base.reserve) / base.reserve
        if base.reserve > 0
        else 0,
        "rate_down_1pct": rate_down.reserve,
        "lapse_up_2x": lapse_up.reserve,
        "lapse_sensitivity": (lapse_up.reserve - base.reserve) / base.reserve
        if base.reserve > 0
        else 0,
        "lapse_down_05x": lapse_down.reserve,
    }
