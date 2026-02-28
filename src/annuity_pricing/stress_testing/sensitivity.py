"""
Sensitivity Analysis for Stress Testing - Phase I.2.

[T2] Implements one-at-a-time (OAT) parameter sweeps and
tornado diagram data generation for stress test analysis.

Design Principles:
- **OAT Methodology**: Vary one parameter at a time while holding others constant
- **Tornado Diagrams**: Rank parameters by sensitivity width (impact magnitude)
- **Integration**: Reuses StressTestRunner for impact calculation

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


class SensitivityDirection(Enum):
    """Direction of parameter perturbation."""

    UP = "up"
    DOWN = "down"
    BOTH = "both"


@dataclass(frozen=True)
class SensitivityParameter:
    """
    Definition of a parameter for sensitivity analysis.

    Attributes
    ----------
    name : str
        Parameter identifier (e.g., "equity_shock", "rate_shock")
    display_name : str
        Human-readable name for reports
    base_value : float
        Current value in the base scenario
    range_down : float
        Lower bound for perturbation (absolute value)
    range_up : float
        Upper bound for perturbation (absolute value)
    unit : str
        Display unit (e.g., "%", "bps", "x")
    """

    name: str
    display_name: str
    base_value: float
    range_down: float
    range_up: float
    unit: str = ""

    def __post_init__(self) -> None:
        """Validate parameter ranges."""
        if self.range_down > self.base_value:
            # Allow range_down to be less than base (for negative parameters)
            pass
        if self.range_up < self.base_value:
            # Allow range_up to be greater than base
            pass


@dataclass(frozen=True)
class SensitivityResult:
    """
    Result of OAT sensitivity analysis for a single parameter.

    Attributes
    ----------
    parameter : str
        Parameter name
    display_name : str
        Human-readable parameter name
    base_value : float
        Base parameter value
    base_reserve : float
        Reserve at base value
    down_value : float
        Parameter value at down shock
    down_reserve : float
        Reserve at down shock
    up_value : float
        Parameter value at up shock
    up_reserve : float
        Reserve at up shock
    down_delta_pct : float
        Percentage change from base to down (can be negative)
    up_delta_pct : float
        Percentage change from base to up (can be negative)
    sensitivity_width : float
        Total width = abs(up_delta_pct - down_delta_pct)
    """

    parameter: str
    display_name: str
    base_value: float
    base_reserve: float
    down_value: float
    down_reserve: float
    up_value: float
    up_reserve: float
    down_delta_pct: float
    up_delta_pct: float
    sensitivity_width: float

    def __post_init__(self) -> None:
        """Validate sensitivity width is positive."""
        if self.sensitivity_width < 0:
            raise ValueError("sensitivity_width must be >= 0")


@dataclass
class TornadoData:
    """
    Data for tornado diagram visualization.

    Results are sorted by sensitivity_width in descending order
    (most impactful parameters first).

    Attributes
    ----------
    results : List[SensitivityResult]
        Sensitivity results sorted by impact (descending)
    base_reserve : float
        Base reserve value (center of tornado)
    scenario_name : str
        Name of base scenario
    n_parameters : int
        Number of parameters analyzed
    """

    results: list[SensitivityResult]
    base_reserve: float
    scenario_name: str
    n_parameters: int = field(init=False)

    def __post_init__(self) -> None:
        """Calculate derived fields."""
        self.n_parameters = len(self.results)
        # Ensure sorted by sensitivity_width descending
        self.results = sorted(self.results, key=lambda r: r.sensitivity_width, reverse=True)

    @property
    def most_sensitive_parameter(self) -> str | None:
        """Return name of most sensitive parameter."""
        if self.results:
            return self.results[0].parameter
        return None

    @property
    def least_sensitive_parameter(self) -> str | None:
        """Return name of least sensitive parameter."""
        if self.results:
            return self.results[-1].parameter
        return None


# =============================================================================
# Default Parameters
# =============================================================================


def get_default_sensitivity_parameters(
    base_equity_shock: float = -0.30,
    base_rate_shock: float = -0.0100,
    base_vol_shock: float = 2.0,
    base_lapse_mult: float = 1.0,
    base_withdrawal_mult: float = 1.0,
) -> list[SensitivityParameter]:
    """
    Get default parameters for sensitivity analysis.

    [T2] Default ranges based on reasonable stress bounds.

    Parameters
    ----------
    base_equity_shock : float
        Base equity shock (default -30%)
    base_rate_shock : float
        Base rate shock (default -100 bps)
    base_vol_shock : float
        Base volatility multiplier (default 2x)
    base_lapse_mult : float
        Base lapse multiplier (default 1.0)
    base_withdrawal_mult : float
        Base withdrawal multiplier (default 1.0)

    Returns
    -------
    List[SensitivityParameter]
        Default parameter definitions
    """
    return [
        SensitivityParameter(
            name="equity_shock",
            display_name="Equity Shock",
            base_value=base_equity_shock,
            range_down=-0.60,  # -60% (more severe)
            range_up=-0.10,  # -10% (less severe)
            unit="%",
        ),
        SensitivityParameter(
            name="rate_shock",
            display_name="Rate Shock",
            base_value=base_rate_shock,
            range_down=-0.0200,  # -200 bps
            range_up=0.0100,  # +100 bps
            unit="bps",
        ),
        SensitivityParameter(
            name="vol_shock",
            display_name="Volatility Multiplier",
            base_value=base_vol_shock,
            range_down=1.0,  # 1x (no vol shock)
            range_up=4.0,  # 4x
            unit="x",
        ),
        SensitivityParameter(
            name="lapse_multiplier",
            display_name="Lapse Multiplier",
            base_value=base_lapse_mult,
            range_down=0.5,  # 50% of base
            range_up=2.0,  # 200% of base
            unit="x",
        ),
        SensitivityParameter(
            name="withdrawal_multiplier",
            display_name="Withdrawal Multiplier",
            base_value=base_withdrawal_mult,
            range_down=0.5,  # 50% of base
            range_up=2.0,  # 200% of base
            unit="x",
        ),
    ]


# =============================================================================
# Sensitivity Analyzer
# =============================================================================


class SensitivityAnalyzer:
    """
    Performs one-at-a-time (OAT) sensitivity analysis.

    [T2] Varies each parameter independently while holding others
    at their base values to assess impact on stressed reserve.

    Examples
    --------
    >>> from annuity_pricing.stress_testing import (
    ...     SensitivityAnalyzer, ORSA_SEVERELY_ADVERSE
    ... )
    >>> analyzer = SensitivityAnalyzer()
    >>> tornado = analyzer.run_oat(
    ...     base_scenario=ORSA_SEVERELY_ADVERSE,
    ...     base_reserve=100_000,
    ... )
    >>> print(f"Most sensitive: {tornado.most_sensitive_parameter}")
    """

    def __init__(
        self,
        impact_function: Callable[..., float] | None = None,
    ):
        """
        Initialize analyzer.

        Parameters
        ----------
        impact_function : Optional[Callable]
            Custom function to calculate stressed reserve.
            If None, uses simplified impact model.
        """
        self._impact_function = impact_function or self._default_impact_model

    def _default_impact_model(
        self,
        base_reserve: float,
        equity_shock: float,
        rate_shock: float,
        vol_shock: float,
        lapse_multiplier: float,
        withdrawal_multiplier: float,
    ) -> float:
        """
        Calculate stressed reserve using simplified impact model.

        [T2] Matches StressTestRunner._apply_stress_to_reserve().
        """
        # Equity impact: Negative returns increase reserve
        equity_impact = -equity_shock * 0.8

        # Rate impact: Lower rates increase reserve
        rate_impact = -rate_shock * 10.0

        # Vol impact: Higher vol increases reserve
        vol_impact = (vol_shock - 1.0) * 0.15

        # Lapse impact: Higher lapses reduce reserve
        lapse_impact = -(lapse_multiplier - 1.0) * 0.10

        # Withdrawal impact: Higher withdrawals increase reserve
        withdrawal_impact = (withdrawal_multiplier - 1.0) * 0.16

        total_impact = equity_impact + rate_impact + vol_impact + lapse_impact + withdrawal_impact

        stressed_reserve = base_reserve * (1.0 + total_impact)
        return max(stressed_reserve, 0.01)

    def _calculate_reserve(
        self,
        base_reserve: float,
        params: dict[str, float],
    ) -> float:
        """Calculate reserve with given parameters."""
        return self._impact_function(
            base_reserve=base_reserve,
            equity_shock=params.get("equity_shock", 0.0),
            rate_shock=params.get("rate_shock", 0.0),
            vol_shock=params.get("vol_shock", 1.0),
            lapse_multiplier=params.get("lapse_multiplier", 1.0),
            withdrawal_multiplier=params.get("withdrawal_multiplier", 1.0),
        )

    def run_single_parameter(
        self,
        parameter: SensitivityParameter,
        base_params: dict[str, float],
        base_reserve: float,
    ) -> SensitivityResult:
        """
        Run sensitivity analysis for a single parameter.

        Parameters
        ----------
        parameter : SensitivityParameter
            Parameter to analyze
        base_params : Dict[str, float]
            Base scenario parameters
        base_reserve : float
            Reserve at base parameters

        Returns
        -------
        SensitivityResult
            Sensitivity result for this parameter
        """
        # Calculate base reserve with base params
        base_reserve_calc = self._calculate_reserve(base_reserve, base_params)

        # Down shock: perturb to range_down
        down_params = base_params.copy()
        down_params[parameter.name] = parameter.range_down
        down_reserve = self._calculate_reserve(base_reserve, down_params)

        # Up shock: perturb to range_up
        up_params = base_params.copy()
        up_params[parameter.name] = parameter.range_up
        up_reserve = self._calculate_reserve(base_reserve, up_params)

        # Calculate deltas
        if base_reserve_calc > 0:
            down_delta_pct = (down_reserve - base_reserve_calc) / base_reserve_calc
            up_delta_pct = (up_reserve - base_reserve_calc) / base_reserve_calc
        else:
            down_delta_pct = 0.0
            up_delta_pct = 0.0

        sensitivity_width = abs(up_delta_pct - down_delta_pct)

        return SensitivityResult(
            parameter=parameter.name,
            display_name=parameter.display_name,
            base_value=parameter.base_value,
            base_reserve=base_reserve_calc,
            down_value=parameter.range_down,
            down_reserve=down_reserve,
            up_value=parameter.range_up,
            up_reserve=up_reserve,
            down_delta_pct=down_delta_pct,
            up_delta_pct=up_delta_pct,
            sensitivity_width=sensitivity_width,
        )

    def run_oat(
        self,
        base_reserve: float,
        parameters: list[SensitivityParameter] | None = None,
        base_equity_shock: float = -0.30,
        base_rate_shock: float = -0.0100,
        base_vol_shock: float = 2.0,
        base_lapse_mult: float = 1.0,
        base_withdrawal_mult: float = 1.0,
        scenario_name: str = "Base Scenario",
    ) -> TornadoData:
        """
        Run one-at-a-time sensitivity analysis for all parameters.

        Parameters
        ----------
        base_reserve : float
            Base reserve value
        parameters : Optional[List[SensitivityParameter]]
            Parameters to analyze. If None, uses defaults.
        base_equity_shock : float
            Base equity shock for default parameters
        base_rate_shock : float
            Base rate shock for default parameters
        base_vol_shock : float
            Base volatility multiplier for default parameters
        base_lapse_mult : float
            Base lapse multiplier for default parameters
        base_withdrawal_mult : float
            Base withdrawal multiplier for default parameters
        scenario_name : str
            Name of base scenario for reporting

        Returns
        -------
        TornadoData
            Complete sensitivity analysis results
        """
        if parameters is None:
            parameters = get_default_sensitivity_parameters(
                base_equity_shock=base_equity_shock,
                base_rate_shock=base_rate_shock,
                base_vol_shock=base_vol_shock,
                base_lapse_mult=base_lapse_mult,
                base_withdrawal_mult=base_withdrawal_mult,
            )

        # Build base params dict from parameter list
        base_params: dict[str, float] = {}
        for p in parameters:
            base_params[p.name] = p.base_value

        results: list[SensitivityResult] = []
        for param in parameters:
            result = self.run_single_parameter(param, base_params, base_reserve)
            results.append(result)

        return TornadoData(
            results=results,
            base_reserve=base_reserve,
            scenario_name=scenario_name,
        )

    def run_oat_from_scenario(
        self,
        scenario: "StressScenario",  # Forward reference
        base_reserve: float,
        parameters: list[SensitivityParameter] | None = None,
    ) -> TornadoData:
        """
        Run OAT analysis from a StressScenario object.

        Parameters
        ----------
        scenario : StressScenario
            Base scenario to perturb
        base_reserve : float
            Base reserve value
        parameters : Optional[List[SensitivityParameter]]
            Parameters to analyze. If None, derives from scenario.

        Returns
        -------
        TornadoData
            Complete sensitivity analysis results
        """
        if parameters is None:
            parameters = get_default_sensitivity_parameters(
                base_equity_shock=scenario.equity_shock,
                base_rate_shock=scenario.rate_shock,
                base_vol_shock=scenario.vol_shock,
                base_lapse_mult=scenario.lapse_multiplier,
                base_withdrawal_mult=scenario.withdrawal_multiplier,
            )

        return self.run_oat(
            base_reserve=base_reserve,
            parameters=parameters,
            base_equity_shock=scenario.equity_shock,
            base_rate_shock=scenario.rate_shock,
            base_vol_shock=scenario.vol_shock,
            base_lapse_mult=scenario.lapse_multiplier,
            base_withdrawal_mult=scenario.withdrawal_multiplier,
            scenario_name=scenario.display_name,
        )


# =============================================================================
# Formatting Functions
# =============================================================================


def format_sensitivity_result(result: SensitivityResult) -> str:
    """
    Format a single sensitivity result as a table row.

    Parameters
    ----------
    result : SensitivityResult
        Result to format

    Returns
    -------
    str
        Formatted row string
    """
    return (
        f"| {result.display_name:<25} | "
        f"{result.down_delta_pct * 100:>+7.1f}% | "
        f"{result.up_delta_pct * 100:>+7.1f}% | "
        f"{result.sensitivity_width * 100:>6.1f}% |"
    )


def format_tornado_table(tornado: TornadoData) -> str:
    """
    Format tornado data as a Markdown table.

    Parameters
    ----------
    tornado : TornadoData
        Tornado data to format

    Returns
    -------
    str
        Formatted Markdown table
    """
    lines = [
        f"### Sensitivity Analysis: {tornado.scenario_name}",
        f"Base Reserve: ${tornado.base_reserve:,.0f}",
        "",
        "| Parameter                 | Down Δ   | Up Δ     | Width  |",
        "|---------------------------|----------|----------|--------|",
    ]

    for result in tornado.results:
        lines.append(format_sensitivity_result(result))

    if tornado.most_sensitive_parameter:
        lines.append("")
        lines.append(
            f"**Most sensitive**: {tornado.most_sensitive_parameter} "
            f"(width: {tornado.results[0].sensitivity_width * 100:.1f}%)"
        )

    return "\n".join(lines)


def format_tornado_summary(tornado: TornadoData) -> str:
    """
    Format a brief summary of tornado results.

    Parameters
    ----------
    tornado : TornadoData
        Tornado data to summarize

    Returns
    -------
    str
        One-paragraph summary
    """
    if not tornado.results:
        return "No sensitivity results available."

    most = tornado.results[0]
    least = tornado.results[-1]

    return (
        f"Sensitivity analysis of {tornado.n_parameters} parameters "
        f"shows {most.display_name} is most impactful "
        f"(width: {most.sensitivity_width * 100:.1f}%), "
        f"while {least.display_name} is least impactful "
        f"(width: {least.sensitivity_width * 100:.1f}%)."
    )


# =============================================================================
# Convenience Functions
# =============================================================================


def quick_sensitivity_analysis(
    base_reserve: float,
    equity_shock: float = -0.30,
    rate_shock: float = -0.0100,
    vol_shock: float = 2.0,
    verbose: bool = False,
) -> TornadoData:
    """
    Quick sensitivity analysis with default parameters.

    Parameters
    ----------
    base_reserve : float
        Base reserve value
    equity_shock : float
        Base equity shock
    rate_shock : float
        Base rate shock
    vol_shock : float
        Base volatility multiplier
    verbose : bool
        Print results

    Returns
    -------
    TornadoData
        Complete sensitivity analysis results

    Examples
    --------
    >>> tornado = quick_sensitivity_analysis(base_reserve=100_000)
    >>> print(f"Most sensitive: {tornado.most_sensitive_parameter}")
    """
    analyzer = SensitivityAnalyzer()
    tornado = analyzer.run_oat(
        base_reserve=base_reserve,
        base_equity_shock=equity_shock,
        base_rate_shock=rate_shock,
        base_vol_shock=vol_shock,
    )

    if verbose:
        logger.info(format_tornado_table(tornado))

    return tornado


# Import for type hints (avoiding circular import)
try:
    from .scenarios import StressScenario
except ImportError:
    # Allow module to load without scenarios
    pass
