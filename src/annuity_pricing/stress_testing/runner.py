"""
Stress Test Runner - Phase I.

[T2] Orchestrates stress testing using wrapper pattern around
VM-21/VM-22 calculators without modifying them.

Design Principles:
- **Wrapper Pattern**: StressTestRunner wraps calculators, doesn't modify them
- **Single Responsibility**: Runner handles orchestration only
- **Open/Closed**: Add scenarios without changing runner
- **Dependency Inversion**: Depends on calculator interface, not implementation

See: docs/stress_testing/STRESS_TESTING_GUIDE.md
"""

import logging
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

logger = logging.getLogger(__name__)

from .metrics import (
    StressMetrics,
    StressTestSummary,
    check_reserve_increase_limit,
    check_reserve_positive,
    create_stress_metrics,
    create_summary,
)
from .scenarios import (
    ALL_ORSA_SCENARIOS,
    StressScenario,
    get_all_historical_scenarios,
)


class CalculatorType(Enum):
    """Type of reserve calculator."""

    VM21 = "vm21"
    VM22 = "vm22"
    CUSTOM = "custom"


# Protocol for calculator interface (duck typing)
class ReserveCalculator(Protocol):
    """Protocol defining calculator interface for stress testing."""

    def calculate_reserve(self, **kwargs: Any) -> Any:
        """Calculate reserve given inputs."""
        ...


@dataclass(frozen=True)
class StressTestConfig:
    """
    Configuration for stress test execution.

    Attributes
    ----------
    include_historical : bool
        Include all 7 historical crisis scenarios
    include_orsa : bool
        Include ORSA standard scenarios
    custom_scenarios : Tuple[StressScenario, ...]
        Additional custom scenarios to include
    max_reserve_increase : float
        Validation gate: max acceptable reserve increase (default 0.50 = 50%)
    parallel : bool
        Use multiprocessing for parallel execution
    n_workers : Optional[int]
        Number of worker processes (None = auto)
    verbose : bool
        Print progress during execution
    """

    include_historical: bool = True
    include_orsa: bool = True
    custom_scenarios: tuple[StressScenario, ...] = ()
    max_reserve_increase: float = 0.50
    parallel: bool = False
    n_workers: int | None = None
    verbose: bool = False


@dataclass
class StressTestResult:
    """
    Complete stress test result.

    Attributes
    ----------
    summary : StressTestSummary
        Aggregated summary statistics
    metrics : List[StressMetrics]
        Individual scenario results
    execution_time_sec : float
        Total execution time in seconds
    calculator_type : str
        Type of calculator used
    config : StressTestConfig
        Configuration used for the test
    """

    summary: StressTestSummary
    metrics: list[StressMetrics]
    execution_time_sec: float
    calculator_type: str
    config: StressTestConfig


@dataclass
class StressedParameters:
    """
    Market parameters with stress applied.

    Used to communicate stressed values to calculators.
    """

    equity_shock: float
    rate_shock: float
    vol_multiplier: float
    lapse_multiplier: float
    withdrawal_multiplier: float

    @classmethod
    def from_scenario(cls, scenario: StressScenario) -> "StressedParameters":
        """Create from a StressScenario."""
        return cls(
            equity_shock=scenario.equity_shock,
            rate_shock=scenario.rate_shock,
            vol_multiplier=scenario.vol_shock,
            lapse_multiplier=scenario.lapse_multiplier,
            withdrawal_multiplier=scenario.withdrawal_multiplier,
        )


class StressTestRunner:
    """
    Orchestrates stress testing across scenarios.

    [T2] Uses wrapper pattern - wraps existing calculators without modification.

    Examples
    --------
    >>> from annuity_pricing.regulatory import VM21Calculator, PolicyData
    >>> from annuity_pricing.stress_testing import StressTestRunner, StressTestConfig
    >>>
    >>> # Create calculator and runner
    >>> calc = VM21Calculator(n_scenarios=1000, seed=42)
    >>> runner = StressTestRunner(calculator_type=CalculatorType.VM21)
    >>>
    >>> # Run stress tests
    >>> policy = PolicyData(av=100_000, gwb=110_000, age=70)
    >>> result = runner.run(calc, policy, config=StressTestConfig())
    >>> print(f"Worst case: {result.summary.worst_scenario}")

    See Also
    --------
    StressTestConfig : Configuration options
    StressTestResult : Result container
    """

    def __init__(
        self,
        calculator_type: CalculatorType = CalculatorType.VM21,
    ):
        """
        Initialize stress test runner.

        Parameters
        ----------
        calculator_type : CalculatorType
            Type of calculator being wrapped
        """
        self.calculator_type = calculator_type
        self._scenarios: list[StressScenario] = []

    def _build_scenario_list(self, config: StressTestConfig) -> list[StressScenario]:
        """Build list of scenarios based on config."""
        scenarios: list[StressScenario] = []

        if config.include_historical:
            scenarios.extend(get_all_historical_scenarios())

        if config.include_orsa:
            scenarios.extend(ALL_ORSA_SCENARIOS)

        scenarios.extend(config.custom_scenarios)

        return scenarios

    def _apply_stress_to_reserve(
        self,
        base_reserve: float,
        scenario: StressScenario,
    ) -> float:
        """
        Apply stress scenario to calculate stressed reserve.

        This is a simplified model that estimates reserve impact from shocks.
        In production, would re-run full calculator with stressed parameters.

        Parameters
        ----------
        base_reserve : float
            Reserve under base case
        scenario : StressScenario
            Stress scenario to apply

        Returns
        -------
        float
            Estimated stressed reserve
        """
        # Simplified impact model:
        # Reserve increases with equity declines and vol increases
        # Reserve decreases with rate increases (higher discount rates)

        # Equity impact: Negative returns increase reserve
        # Scale: -50% equity → ~40% reserve increase (0.8 sensitivity)
        equity_impact = -scenario.equity_shock * 0.8

        # Rate impact: Lower rates increase reserve (higher PV of liabilities)
        # Scale: -100bps → ~10% reserve increase
        rate_impact = -scenario.rate_shock * 10.0

        # Vol impact: Higher vol increases reserve (option value)
        # Scale: 2x vol → ~15% reserve increase
        vol_impact = (scenario.vol_shock - 1.0) * 0.15

        # Lapse impact: Higher lapses reduce reserve (fewer policies)
        # Scale: +50% lapse → ~5% reserve decrease
        lapse_impact = -(scenario.lapse_multiplier - 1.0) * 0.10

        # Withdrawal impact: Higher withdrawals increase reserve
        # Scale: +50% withdrawal → ~8% reserve increase
        withdrawal_impact = (scenario.withdrawal_multiplier - 1.0) * 0.16

        # Total impact (multiplicative for severe scenarios)
        total_impact = (
            equity_impact
            + rate_impact
            + vol_impact
            + lapse_impact
            + withdrawal_impact
        )

        # Ensure reserve doesn't go negative
        stressed_reserve = base_reserve * (1.0 + total_impact)
        return max(stressed_reserve, 0.01)  # Minimum 1 cent

    def _run_single_scenario(
        self,
        scenario: StressScenario,
        base_reserve: float,
        max_reserve_increase: float,
    ) -> StressMetrics:
        """Run single scenario and return metrics."""
        # Calculate stressed reserve
        stressed_reserve = self._apply_stress_to_reserve(base_reserve, scenario)

        # Validation gates
        gates = {
            "reserve_positive": check_reserve_positive(stressed_reserve),
            "reserve_within_limit": check_reserve_increase_limit(
                (stressed_reserve - base_reserve) / base_reserve,
                max_reserve_increase,
            ),
        }

        return create_stress_metrics(
            scenario_name=scenario.name,
            base_reserve=base_reserve,
            stressed_reserve=stressed_reserve,
            validation_gates=gates,
        )

    def run(
        self,
        calculator: ReserveCalculator,
        policy_data: Any,
        config: StressTestConfig | None = None,
        base_reserve: float | None = None,
    ) -> StressTestResult:
        """
        Execute stress tests across all configured scenarios.

        Parameters
        ----------
        calculator : ReserveCalculator
            The calculator to use (VM21Calculator, VM22Calculator, etc.)
        policy_data : Any
            Policy data to pass to calculator
        config : Optional[StressTestConfig]
            Test configuration. If None, uses defaults.
        base_reserve : Optional[float]
            Pre-computed base reserve. If None, calculates from calculator.

        Returns
        -------
        StressTestResult
            Complete test results with summary and individual metrics

        Examples
        --------
        >>> result = runner.run(calc, policy)
        >>> print(f"Tested {result.summary.n_scenarios} scenarios")
        >>> print(f"Worst: {result.summary.worst_scenario}")
        """
        start_time = time.time()

        if config is None:
            config = StressTestConfig()

        # Build scenario list
        scenarios = self._build_scenario_list(config)
        if not scenarios:
            raise ValueError(
                "No scenarios to test. Enable include_historical or include_orsa, "
                "or provide custom_scenarios."
            )

        # Calculate base reserve if not provided
        if base_reserve is None:
            try:
                result = calculator.calculate_reserve(policy_data=policy_data)
                # Handle different result types
                if hasattr(result, "reserve"):
                    base_reserve = result.reserve
                elif isinstance(result, (int, float)):
                    base_reserve = float(result)
                else:
                    raise ValueError(
                        f"Cannot extract reserve from calculator result: {type(result)}"
                    )
            except Exception as e:
                raise RuntimeError(
                    f"Failed to calculate base reserve: {e}. "
                    "Provide base_reserve parameter directly."
                ) from e

        if config.verbose:
            logger.info(f"Base reserve: ${base_reserve:,.0f}")
            logger.info(f"Running {len(scenarios)} scenarios...")

        # Run scenarios
        metrics_list: list[StressMetrics] = []

        if config.parallel and len(scenarios) > 1:
            # Parallel execution
            metrics_list = self._run_parallel(
                scenarios, base_reserve, config
            )
        else:
            # Sequential execution
            for i, scenario in enumerate(scenarios):
                if config.verbose:
                    logger.info(f"  [{i+1}/{len(scenarios)}] {scenario.display_name}")

                metrics = self._run_single_scenario(
                    scenario, base_reserve, config.max_reserve_increase
                )
                metrics_list.append(metrics)

        # Create summary
        summary = create_summary(metrics_list)

        execution_time = time.time() - start_time

        if config.verbose:
            logger.info(f"Completed in {execution_time:.2f}s")
            logger.info(f"Worst case: {summary.worst_scenario} ({summary.worst_reserve_delta_pct*100:+.1f}%)")

        return StressTestResult(
            summary=summary,
            metrics=metrics_list,
            execution_time_sec=execution_time,
            calculator_type=self.calculator_type.value,
            config=config,
        )

    def _run_parallel(
        self,
        scenarios: list[StressScenario],
        base_reserve: float,
        config: StressTestConfig,
    ) -> list[StressMetrics]:
        """Run scenarios in parallel using ProcessPoolExecutor."""
        metrics_list: list[StressMetrics] = []

        with ProcessPoolExecutor(max_workers=config.n_workers) as executor:
            # Submit all tasks
            future_to_scenario = {
                executor.submit(
                    self._run_single_scenario,
                    scenario,
                    base_reserve,
                    config.max_reserve_increase,
                ): scenario
                for scenario in scenarios
            }

            # Collect results as they complete
            for future in as_completed(future_to_scenario):
                scenario = future_to_scenario[future]
                try:
                    metrics = future.result()
                    metrics_list.append(metrics)
                    if config.verbose:
                        logger.info(f"  Completed: {scenario.display_name}")
                except Exception as e:
                    if config.verbose:
                        logger.warning(f"  FAILED: {scenario.display_name}: {e}")
                    # Create failed metrics
                    metrics_list.append(
                        create_stress_metrics(
                            scenario_name=scenario.name,
                            base_reserve=base_reserve,
                            stressed_reserve=base_reserve,  # No change
                            validation_gates={"execution": False},
                        )
                    )

        return metrics_list

    def run_historical_only(
        self,
        calculator: ReserveCalculator,
        policy_data: Any,
        base_reserve: float | None = None,
        verbose: bool = False,
    ) -> StressTestResult:
        """
        Convenience method to run only historical scenarios.

        Parameters
        ----------
        calculator : ReserveCalculator
            The calculator to use
        policy_data : Any
            Policy data
        base_reserve : Optional[float]
            Pre-computed base reserve
        verbose : bool
            Print progress

        Returns
        -------
        StressTestResult
            Results for historical scenarios only
        """
        config = StressTestConfig(
            include_historical=True,
            include_orsa=False,
            verbose=verbose,
        )
        return self.run(calculator, policy_data, config, base_reserve)

    def run_orsa_only(
        self,
        calculator: ReserveCalculator,
        policy_data: Any,
        base_reserve: float | None = None,
        verbose: bool = False,
    ) -> StressTestResult:
        """
        Convenience method to run only ORSA scenarios.

        Parameters
        ----------
        calculator : ReserveCalculator
            The calculator to use
        policy_data : Any
            Policy data
        base_reserve : Optional[float]
            Pre-computed base reserve
        verbose : bool
            Print progress

        Returns
        -------
        StressTestResult
            Results for ORSA scenarios only
        """
        config = StressTestConfig(
            include_historical=False,
            include_orsa=True,
            verbose=verbose,
        )
        return self.run(calculator, policy_data, config, base_reserve)


# =============================================================================
# Utility Functions
# =============================================================================


def quick_stress_test(
    base_reserve: float,
    scenarios: list[StressScenario] | None = None,
    verbose: bool = False,
) -> StressTestResult:
    """
    Run quick stress test without a calculator.

    Useful for quick analysis when base reserve is already known.

    Parameters
    ----------
    base_reserve : float
        Known base reserve value
    scenarios : Optional[List[StressScenario]]
        Scenarios to test. If None, uses historical + ORSA.
    verbose : bool
        Print progress

    Returns
    -------
    StressTestResult
        Complete test results

    Examples
    --------
    >>> result = quick_stress_test(base_reserve=100_000)
    >>> print(f"95th percentile: {result.summary.percentiles[95]*100:.1f}%")
    """
    runner = StressTestRunner(calculator_type=CalculatorType.CUSTOM)

    if scenarios is None:
        config = StressTestConfig(
            include_historical=True,
            include_orsa=True,
            verbose=verbose,
        )
    else:
        config = StressTestConfig(
            include_historical=False,
            include_orsa=False,
            custom_scenarios=tuple(scenarios),
            verbose=verbose,
        )

    # Dummy calculator that just returns base reserve
    class DummyCalculator:
        def calculate_reserve(self, **kwargs: Any) -> float:
            return base_reserve

    return runner.run(DummyCalculator(), None, config, base_reserve)


def stress_single_scenario(
    base_reserve: float,
    scenario: StressScenario,
) -> StressMetrics:
    """
    Stress test with a single scenario.

    Parameters
    ----------
    base_reserve : float
        Base reserve value
    scenario : StressScenario
        Scenario to apply

    Returns
    -------
    StressMetrics
        Metrics for the single scenario
    """
    runner = StressTestRunner()
    return runner._run_single_scenario(
        scenario, base_reserve, max_reserve_increase=1.0
    )
