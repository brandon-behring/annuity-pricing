"""
Reverse Stress Testing - Phase I.3.

[T2] Implements bisection search to find breaking points where
specific risk thresholds are breached.

Design Principles:
- **Bisection Algorithm**: O(log(range/tolerance)) convergence
- **Flexible Targets**: Reserve exhaustion, RBC breach, or custom
- **Integration**: Uses existing stress impact model

See: docs/stress_testing/STRESS_TESTING_GUIDE.md
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# Dataclasses
# =============================================================================


class BreachCondition(Enum):
    """Type of breach condition to check."""

    BELOW = "below"  # Target breached when value < threshold
    ABOVE = "above"  # Target breached when value > threshold


@dataclass(frozen=True)
class ReverseStressTarget:
    """
    Definition of a reverse stress testing target.

    Attributes
    ----------
    target_type : str
        Type identifier (e.g., "reserve_exhaustion", "rbc_breach")
    threshold : float
        Value at which target is considered breached
    description : str
        Human-readable description
    breach_condition : BreachCondition
        Whether breach occurs above or below threshold
    metric_name : str
        Name of the metric being tested
    """

    target_type: str
    threshold: float
    description: str
    breach_condition: BreachCondition
    metric_name: str = "reserve"

    def is_breached(self, value: float) -> bool:
        """Check if value breaches this target."""
        if self.breach_condition == BreachCondition.BELOW:
            return value < self.threshold
        else:
            return value > self.threshold


# =============================================================================
# Predefined Targets
# =============================================================================


RESERVE_EXHAUSTION = ReverseStressTarget(
    target_type="reserve_exhaustion",
    threshold=0.0,
    description="Reserve fully exhausted (<=0)",
    breach_condition=BreachCondition.BELOW,
    metric_name="reserve",
)

RESERVE_NEGATIVE = ReverseStressTarget(
    target_type="reserve_negative",
    threshold=0.01,
    description="Reserve falls below minimum (<=0.01)",
    breach_condition=BreachCondition.BELOW,
    metric_name="reserve",
)

RBC_BREACH_200 = ReverseStressTarget(
    target_type="rbc_breach_200",
    threshold=2.0,
    description="RBC ratio falls below 200%",
    breach_condition=BreachCondition.BELOW,
    metric_name="rbc_ratio",
)

RBC_BREACH_300 = ReverseStressTarget(
    target_type="rbc_breach_300",
    threshold=3.0,
    description="RBC ratio falls below 300%",
    breach_condition=BreachCondition.BELOW,
    metric_name="rbc_ratio",
)

SOLVENCY_BREACH = ReverseStressTarget(
    target_type="solvency_breach",
    threshold=1.0,
    description="Solvency ratio falls below 100%",
    breach_condition=BreachCondition.BELOW,
    metric_name="solvency_ratio",
)

RESERVE_INCREASE_50 = ReverseStressTarget(
    target_type="reserve_increase_50",
    threshold=0.50,
    description="Reserve increases by more than 50%",
    breach_condition=BreachCondition.ABOVE,
    metric_name="reserve_delta_pct",
)

RESERVE_INCREASE_100 = ReverseStressTarget(
    target_type="reserve_increase_100",
    threshold=1.00,
    description="Reserve doubles (increases by 100%+)",
    breach_condition=BreachCondition.ABOVE,
    metric_name="reserve_delta_pct",
)

# All predefined targets
ALL_PREDEFINED_TARGETS = (
    RESERVE_EXHAUSTION,
    RESERVE_NEGATIVE,
    RBC_BREACH_200,
    RBC_BREACH_300,
    SOLVENCY_BREACH,
    RESERVE_INCREASE_50,
    RESERVE_INCREASE_100,
)


def create_custom_target(
    target_type: str,
    threshold: float,
    description: str,
    breach_condition: str = "below",
    metric_name: str = "reserve",
) -> ReverseStressTarget:
    """
    Create a custom reverse stress target.

    Parameters
    ----------
    target_type : str
        Unique identifier for this target
    threshold : float
        Breach threshold value
    description : str
        Human-readable description
    breach_condition : str
        "below" or "above"
    metric_name : str
        Name of metric being tested

    Returns
    -------
    ReverseStressTarget
        Custom target definition
    """
    condition = (
        BreachCondition.BELOW if breach_condition.lower() == "below" else BreachCondition.ABOVE
    )
    return ReverseStressTarget(
        target_type=target_type,
        threshold=threshold,
        description=description,
        breach_condition=condition,
        metric_name=metric_name,
    )


# =============================================================================
# Result Dataclasses
# =============================================================================


@dataclass
class ReverseStressResult:
    """
    Result of reverse stress testing for a single target-parameter pair.

    Attributes
    ----------
    target : ReverseStressTarget
        Target that was tested
    parameter_name : str
        Parameter that was varied
    breaking_point : Optional[float]
        Value where target was breached (None if not breached)
    iterations : int
        Number of bisection iterations used
    converged : bool
        Whether bisection converged
    breached : bool
        Whether target was breached in search range
    base_value : float
        Parameter value at base scenario
    search_range : Tuple[float, float]
        Search range used
    final_metric_value : Optional[float]
        Metric value at breaking point
    """

    target: ReverseStressTarget
    parameter_name: str
    breaking_point: float | None
    iterations: int
    converged: bool
    breached: bool
    base_value: float
    search_range: tuple[float, float]
    final_metric_value: float | None = None

    @property
    def parameter_delta(self) -> float | None:
        """Return change from base to breaking point."""
        if self.breaking_point is not None:
            return self.breaking_point - self.base_value
        return None

    @property
    def parameter_delta_pct(self) -> float | None:
        """Return percentage change from base to breaking point."""
        if self.breaking_point is not None and abs(self.base_value) > 1e-10:
            return (self.breaking_point - self.base_value) / abs(self.base_value)
        return None


@dataclass
class ReverseStressReport:
    """
    Complete report of reverse stress testing.

    Attributes
    ----------
    results : Dict[Tuple[str, str], ReverseStressResult]
        Results keyed by (target_type, parameter_name)
    base_reserve : float
        Base reserve value
    targets_tested : int
        Number of targets tested
    parameters_tested : int
        Number of parameters tested
    """

    results: dict[tuple[str, str], ReverseStressResult]
    base_reserve: float
    targets_tested: int = field(init=False)
    parameters_tested: int = field(init=False)

    def __post_init__(self) -> None:
        """Calculate derived fields."""
        targets = {k[0] for k in self.results}
        params = {k[1] for k in self.results}
        self.targets_tested = len(targets)
        self.parameters_tested = len(params)

    def get_result(self, target_type: str, parameter_name: str) -> ReverseStressResult | None:
        """Get result for specific target-parameter pair."""
        return self.results.get((target_type, parameter_name))

    def get_breached_results(self) -> list[ReverseStressResult]:
        """Get all results where target was breached."""
        return [r for r in self.results.values() if r.breached]

    def get_results_for_target(self, target_type: str) -> list[ReverseStressResult]:
        """Get all results for a specific target."""
        return [r for (t, p), r in self.results.items() if t == target_type]


# =============================================================================
# Reverse Stress Tester
# =============================================================================


class ReverseStressTester:
    """
    Performs reverse stress testing using bisection search.

    [T2] Finds parameter values that cause specific risk thresholds
    to be breached using binary search algorithm.

    Examples
    --------
    >>> tester = ReverseStressTester()
    >>> result = tester.find_breaking_point(
    ...     target=RESERVE_EXHAUSTION,
    ...     parameter="equity_shock",
    ...     search_range=(-1.0, 0.0),
    ...     base_reserve=100_000,
    ... )
    >>> if result.breached:
    ...     print(f"Reserve exhausted at equity shock: {result.breaking_point:.1%}")
    """

    def __init__(
        self,
        impact_function: Callable[..., float] | None = None,
        rbc_function: Callable[..., float] | None = None,
    ):
        """
        Initialize tester.

        Parameters
        ----------
        impact_function : Optional[Callable]
            Function to calculate stressed reserve.
            Signature: (base_reserve, **params) -> float
        rbc_function : Optional[Callable]
            Function to calculate RBC ratio.
            Signature: (reserve, **params) -> float
        """
        self._impact_function = impact_function or self._default_impact_model
        self._rbc_function = rbc_function or self._default_rbc_model

    def _default_impact_model(
        self,
        base_reserve: float,
        equity_shock: float = 0.0,
        rate_shock: float = 0.0,
        vol_shock: float = 1.0,
        lapse_multiplier: float = 1.0,
        withdrawal_multiplier: float = 1.0,
    ) -> float:
        """
        Calculate stressed reserve using simplified impact model.

        [T2] Matches StressTestRunner._apply_stress_to_reserve().
        """
        equity_impact = -equity_shock * 0.8
        rate_impact = -rate_shock * 10.0
        vol_impact = (vol_shock - 1.0) * 0.15
        lapse_impact = -(lapse_multiplier - 1.0) * 0.10
        withdrawal_impact = (withdrawal_multiplier - 1.0) * 0.16

        total_impact = equity_impact + rate_impact + vol_impact + lapse_impact + withdrawal_impact

        stressed_reserve = base_reserve * (1.0 + total_impact)
        return max(stressed_reserve, 0.01)

    def _default_rbc_model(
        self,
        reserve: float,
        authorized_control_level: float = 50_000,
    ) -> float:
        """
        Calculate simplified RBC ratio.

        RBC Ratio = Total Adjusted Capital / Authorized Control Level

        [T2] Simplified model for demonstration.
        """
        if authorized_control_level <= 0:
            return float("inf")
        # Assume TAC = reserve (simplified)
        return reserve / authorized_control_level

    def _calculate_metric(
        self,
        target: ReverseStressTarget,
        base_reserve: float,
        params: dict[str, float],
    ) -> float:
        """Calculate the relevant metric for a target."""
        reserve = self._impact_function(base_reserve, **params)

        if target.metric_name == "reserve":
            return reserve
        elif target.metric_name == "reserve_delta_pct":
            return (reserve - base_reserve) / base_reserve if base_reserve > 0 else 0.0
        elif target.metric_name == "rbc_ratio":
            return self._rbc_function(reserve)
        elif target.metric_name == "solvency_ratio":
            # Simplified: assume assets = 1.5 * base_reserve
            assets = 1.5 * base_reserve
            return reserve / assets if assets > 0 else 0.0
        else:
            # For custom metrics, default to reserve
            return reserve

    def find_breaking_point(
        self,
        target: ReverseStressTarget,
        parameter: str,
        search_range: tuple[float, float],
        base_reserve: float,
        base_params: dict[str, float] | None = None,
        tolerance: float = 0.001,
        max_iterations: int = 25,
    ) -> ReverseStressResult:
        """
        Find parameter value where target is breached using bisection.

        Parameters
        ----------
        target : ReverseStressTarget
            Target to test for breach
        parameter : str
            Parameter to vary
        search_range : Tuple[float, float]
            Range to search (low, high)
        base_reserve : float
            Base reserve value
        base_params : Optional[Dict[str, float]]
            Base parameter values. If None, uses defaults.
        tolerance : float
            Convergence tolerance
        max_iterations : int
            Maximum bisection iterations

        Returns
        -------
        ReverseStressResult
            Result of the search
        """
        if base_params is None:
            base_params = {
                "equity_shock": 0.0,
                "rate_shock": 0.0,
                "vol_shock": 1.0,
                "lapse_multiplier": 1.0,
                "withdrawal_multiplier": 1.0,
            }

        base_value = base_params.get(parameter, 0.0)
        low, high = search_range

        # Check if already breached at base
        base_metric = self._calculate_metric(target, base_reserve, base_params)
        if target.is_breached(base_metric):
            return ReverseStressResult(
                target=target,
                parameter_name=parameter,
                breaking_point=base_value,
                iterations=0,
                converged=True,
                breached=True,
                base_value=base_value,
                search_range=search_range,
                final_metric_value=base_metric,
            )

        # Check endpoints
        low_params = base_params.copy()
        low_params[parameter] = low
        low_metric = self._calculate_metric(target, base_reserve, low_params)
        low_breached = target.is_breached(low_metric)

        high_params = base_params.copy()
        high_params[parameter] = high
        high_metric = self._calculate_metric(target, base_reserve, high_params)
        high_breached = target.is_breached(high_metric)

        # If neither endpoint breaches, target may not be reachable
        if not low_breached and not high_breached:
            return ReverseStressResult(
                target=target,
                parameter_name=parameter,
                breaking_point=None,
                iterations=0,
                converged=True,
                breached=False,
                base_value=base_value,
                search_range=search_range,
                final_metric_value=None,
            )

        # Ensure low is non-breached side, high is breached side
        if low_breached and not high_breached:
            low, high = high, low
            low_breached, high_breached = high_breached, low_breached

        # Bisection search
        iterations = 0
        while (high - low) > tolerance and iterations < max_iterations:
            mid = (low + high) / 2.0
            mid_params = base_params.copy()
            mid_params[parameter] = mid
            mid_metric = self._calculate_metric(target, base_reserve, mid_params)
            mid_breached = target.is_breached(mid_metric)

            if mid_breached:
                high = mid
            else:
                low = mid

            iterations += 1

        breaking_point = (low + high) / 2.0
        final_params = base_params.copy()
        final_params[parameter] = breaking_point
        final_metric = self._calculate_metric(target, base_reserve, final_params)

        return ReverseStressResult(
            target=target,
            parameter_name=parameter,
            breaking_point=breaking_point,
            iterations=iterations,
            converged=(high - low) <= tolerance,
            breached=True,
            base_value=base_value,
            search_range=search_range,
            final_metric_value=final_metric,
        )

    def find_multiple_breaking_points(
        self,
        targets: list[ReverseStressTarget],
        parameters: list[str],
        search_ranges: dict[str, tuple[float, float]],
        base_reserve: float,
        base_params: dict[str, float] | None = None,
        tolerance: float = 0.001,
        max_iterations: int = 25,
    ) -> ReverseStressReport:
        """
        Find breaking points for multiple target-parameter combinations.

        Parameters
        ----------
        targets : List[ReverseStressTarget]
            Targets to test
        parameters : List[str]
            Parameters to vary
        search_ranges : Dict[str, Tuple[float, float]]
            Search range for each parameter
        base_reserve : float
            Base reserve value
        base_params : Optional[Dict[str, float]]
            Base parameter values
        tolerance : float
            Convergence tolerance
        max_iterations : int
            Maximum iterations per search

        Returns
        -------
        ReverseStressReport
            Complete report of all searches
        """
        results: dict[tuple[str, str], ReverseStressResult] = {}

        for target in targets:
            for param in parameters:
                if param not in search_ranges:
                    continue

                result = self.find_breaking_point(
                    target=target,
                    parameter=param,
                    search_range=search_ranges[param],
                    base_reserve=base_reserve,
                    base_params=base_params,
                    tolerance=tolerance,
                    max_iterations=max_iterations,
                )
                results[(target.target_type, param)] = result

        return ReverseStressReport(
            results=results,
            base_reserve=base_reserve,
        )


# =============================================================================
# Default Search Ranges
# =============================================================================


DEFAULT_SEARCH_RANGES: dict[str, tuple[float, float]] = {
    "equity_shock": (-1.0, 0.50),  # -100% to +50%
    "rate_shock": (-0.05, 0.05),  # -500 bps to +500 bps
    "vol_shock": (0.1, 10.0),  # 0.1x to 10x
    "lapse_multiplier": (0.1, 10.0),  # 0.1x to 10x
    "withdrawal_multiplier": (0.1, 10.0),  # 0.1x to 10x
}


# =============================================================================
# Formatting Functions
# =============================================================================


def format_reverse_stress_result(result: ReverseStressResult) -> str:
    """
    Format a single reverse stress result.

    Parameters
    ----------
    result : ReverseStressResult
        Result to format

    Returns
    -------
    str
        Formatted string
    """
    if not result.breached:
        return (
            f"| {result.target.target_type:<25} | "
            f"{result.parameter_name:<20} | "
            f"{'N/A':>12} | "
            f"Not breached in range |"
        )

    if result.breaking_point is not None:
        bp_str = f"{result.breaking_point:>12.4f}"
    else:
        bp_str = f"{'N/A':>12}"

    return (
        f"| {result.target.target_type:<25} | "
        f"{result.parameter_name:<20} | "
        f"{bp_str} | "
        f"{result.iterations:>3} iterations |"
    )


def format_reverse_stress_table(report: ReverseStressReport) -> str:
    """
    Format reverse stress report as Markdown table.

    Parameters
    ----------
    report : ReverseStressReport
        Report to format

    Returns
    -------
    str
        Formatted Markdown table
    """
    lines = [
        "### Reverse Stress Testing Results",
        f"Base Reserve: ${report.base_reserve:,.0f}",
        "",
        "| Target                    | Parameter            | Breaking Point | Status |",
        "|---------------------------|----------------------|----------------|--------|",
    ]

    for (_target_type, _param), result in sorted(report.results.items()):
        lines.append(format_reverse_stress_result(result))

    breached = report.get_breached_results()
    lines.append("")
    lines.append(f"**Breached**: {len(breached)} / {len(report.results)} combinations")

    return "\n".join(lines)


def format_reverse_stress_summary(report: ReverseStressReport) -> str:
    """
    Format brief summary of reverse stress results.

    Parameters
    ----------
    report : ReverseStressReport
        Report to summarize

    Returns
    -------
    str
        One-paragraph summary
    """
    breached = report.get_breached_results()

    if not breached:
        return (
            f"Reverse stress testing of {len(report.results)} combinations "
            f"found no scenarios that breach the tested thresholds."
        )

    # Find most critical (smallest parameter delta to breach)
    critical = None
    min_delta = float("inf")
    for r in breached:
        if r.breaking_point is not None and abs(r.base_value) > 1e-10:
            delta = abs(r.breaking_point - r.base_value)
            if delta < min_delta:
                min_delta = delta
                critical = r

    if critical:
        return (
            f"Reverse stress testing found {len(breached)} breach scenarios. "
            f"Most critical: {critical.target.target_type} breached at "
            f"{critical.parameter_name}={critical.breaking_point:.4f} "
            f"(delta: {critical.parameter_delta:.4f} from base)."
        )

    return f"Reverse stress testing found {len(breached)} breach scenarios."


# =============================================================================
# Convenience Functions
# =============================================================================


def quick_reverse_stress(
    base_reserve: float,
    targets: list[ReverseStressTarget] | None = None,
    parameters: list[str] | None = None,
    verbose: bool = False,
) -> ReverseStressReport:
    """
    Quick reverse stress testing with defaults.

    Parameters
    ----------
    base_reserve : float
        Base reserve value
    targets : Optional[List[ReverseStressTarget]]
        Targets to test. If None, uses RESERVE_EXHAUSTION and RBC_BREACH_200.
    parameters : Optional[List[str]]
        Parameters to vary. If None, uses equity_shock and rate_shock.
    verbose : bool
        Print results

    Returns
    -------
    ReverseStressReport
        Complete report

    Examples
    --------
    >>> report = quick_reverse_stress(base_reserve=100_000, verbose=True)
    >>> breached = report.get_breached_results()
    """
    if targets is None:
        targets = [RESERVE_INCREASE_50, RESERVE_INCREASE_100]

    if parameters is None:
        parameters = ["equity_shock", "rate_shock", "vol_shock"]

    tester = ReverseStressTester()
    report = tester.find_multiple_breaking_points(
        targets=targets,
        parameters=parameters,
        search_ranges=DEFAULT_SEARCH_RANGES,
        base_reserve=base_reserve,
    )

    if verbose:
        logger.info(format_reverse_stress_table(report))

    return report


def find_reserve_exhaustion_point(
    base_reserve: float,
    parameter: str = "equity_shock",
    search_range: tuple[float, float] | None = None,
    verbose: bool = False,
) -> ReverseStressResult:
    """
    Find parameter value that exhausts reserve.

    Parameters
    ----------
    base_reserve : float
        Base reserve value
    parameter : str
        Parameter to vary
    search_range : Optional[Tuple[float, float]]
        Search range. If None, uses default for parameter.
    verbose : bool
        Print result

    Returns
    -------
    ReverseStressResult
        Result of the search
    """
    if search_range is None:
        search_range = DEFAULT_SEARCH_RANGES.get(parameter, (-1.0, 1.0))

    tester = ReverseStressTester()
    result = tester.find_breaking_point(
        target=RESERVE_EXHAUSTION,
        parameter=parameter,
        search_range=search_range,
        base_reserve=base_reserve,
    )

    if verbose:
        if result.breached:
            logger.info(
                f"Reserve exhaustion at {parameter}={result.breaking_point:.4f} "
                f"({result.iterations} iterations)"
            )
        else:
            logger.info(f"Reserve not exhausted in range {search_range}")

    return result
