"""
Stress Scenarios for Annuity Pricing - Phase I.

[T2] Defines stress scenarios including:
- Conversion from historical crises to scenarios
- ORSA standard adverse scenarios
- Custom scenario creation

Design: StressScenario is a simplified representation of market shocks
that can be applied to VM-21/VM-22 calculators.

See: docs/stress_testing/STRESS_TESTING_GUIDE.md
"""

from dataclasses import dataclass
from enum import Enum

from .historical import ALL_HISTORICAL_CRISES, HistoricalCrisis


class ScenarioType(Enum):
    """Classification of stress scenario source."""

    HISTORICAL = "historical"  # Derived from historical crisis
    ORSA = "orsa"  # Own Risk and Solvency Assessment
    REGULATORY = "regulatory"  # e.g., VM-21 prescribed
    CUSTOM = "custom"  # User-defined


@dataclass(frozen=True)
class StressScenario:
    """
    Stress scenario definition for reserve testing.

    [T2] Encapsulates market shocks to apply to pricing calculators.

    Attributes
    ----------
    name : str
        Scenario identifier
    display_name : str
        Human-readable description
    equity_shock : float
        Equity return shock (decimal, e.g., -0.30 = -30%)
    rate_shock : float
        Interest rate shock (decimal, e.g., -0.0100 = -100 bps)
    vol_shock : float
        Volatility multiplier (e.g., 2.0 = double vol, 1.0 = unchanged)
    lapse_multiplier : float
        Lapse rate multiplier (e.g., 1.5 = 50% higher lapses)
    withdrawal_multiplier : float
        Withdrawal utilization multiplier
    scenario_type : ScenarioType
        Classification of scenario source
    source_crisis : Optional[str]
        If historical, the crisis name (e.g., "2008_gfc")
    notes : str
        Additional context
    """

    name: str
    display_name: str
    equity_shock: float
    rate_shock: float
    vol_shock: float = 1.0
    lapse_multiplier: float = 1.0
    withdrawal_multiplier: float = 1.0
    scenario_type: ScenarioType = ScenarioType.CUSTOM
    source_crisis: str | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        """Validate scenario parameters."""
        if self.vol_shock < 0:
            raise ValueError(f"vol_shock must be >= 0, got {self.vol_shock}")
        if self.lapse_multiplier < 0:
            raise ValueError(f"lapse_multiplier must be >= 0, got {self.lapse_multiplier}")
        if self.withdrawal_multiplier < 0:
            raise ValueError(
                f"withdrawal_multiplier must be >= 0, got {self.withdrawal_multiplier}"
            )


# =============================================================================
# ORSA Standard Scenarios
# =============================================================================
# Based on typical ORSA adverse scenario calibrations
# These represent increasingly severe market conditions

ORSA_MODERATE_ADVERSE = StressScenario(
    name="orsa_moderate",
    display_name="ORSA Moderate Adverse",
    equity_shock=-0.15,  # 15% equity decline
    rate_shock=-0.0050,  # -50 bps
    vol_shock=1.3,  # 30% higher vol
    lapse_multiplier=1.15,  # 15% higher lapses
    withdrawal_multiplier=1.10,  # 10% higher withdrawals
    scenario_type=ScenarioType.ORSA,
    notes="1-in-10 year event. Typical mild recession.",
)

ORSA_SEVERELY_ADVERSE = StressScenario(
    name="orsa_severe",
    display_name="ORSA Severely Adverse",
    equity_shock=-0.30,  # 30% equity decline
    rate_shock=-0.0100,  # -100 bps
    vol_shock=2.0,  # Double vol
    lapse_multiplier=1.30,  # 30% higher lapses
    withdrawal_multiplier=1.25,  # 25% higher withdrawals
    scenario_type=ScenarioType.ORSA,
    notes="1-in-25 year event. Comparable to 2011 or 2015-16.",
)

ORSA_EXTREMELY_ADVERSE = StressScenario(
    name="orsa_extreme",
    display_name="ORSA Extremely Adverse",
    equity_shock=-0.50,  # 50% equity decline
    rate_shock=-0.0200,  # -200 bps
    vol_shock=4.0,  # 4x vol (VIX ~60-80)
    lapse_multiplier=1.50,  # 50% higher lapses
    withdrawal_multiplier=1.50,  # 50% higher withdrawals
    scenario_type=ScenarioType.ORSA,
    notes="1-in-100 year event. Comparable to 2008 GFC.",
)

ALL_ORSA_SCENARIOS: tuple[StressScenario, ...] = (
    ORSA_MODERATE_ADVERSE,
    ORSA_SEVERELY_ADVERSE,
    ORSA_EXTREMELY_ADVERSE,
)


# =============================================================================
# Conversion Functions
# =============================================================================


def crisis_to_scenario(
    crisis: HistoricalCrisis,
    vol_shock: float | None = None,
    lapse_multiplier: float = 1.0,
    withdrawal_multiplier: float = 1.0,
) -> StressScenario:
    """
    Convert a historical crisis to a stress scenario.

    Parameters
    ----------
    crisis : HistoricalCrisis
        The historical crisis to convert
    vol_shock : Optional[float]
        Volatility multiplier. If None, calculated from VIX peak:
        vol_shock = vix_peak / 15 (assuming baseline VIX ~15)
    lapse_multiplier : float
        Lapse rate multiplier (default 1.0 = unchanged)
    withdrawal_multiplier : float
        Withdrawal utilization multiplier (default 1.0 = unchanged)

    Returns
    -------
    StressScenario
        Scenario derived from the historical crisis

    Examples
    --------
    >>> from annuity_pricing.stress_testing import CRISIS_2008_GFC, crisis_to_scenario
    >>> scenario = crisis_to_scenario(CRISIS_2008_GFC)
    >>> scenario.equity_shock
    -0.568
    >>> scenario.vol_shock  # 80.9 / 15
    5.39...
    """
    # Calculate vol shock from VIX if not provided
    # Baseline VIX assumed ~15
    if vol_shock is None:
        vol_shock = crisis.vix_peak / 15.0

    return StressScenario(
        name=f"hist_{crisis.name}",
        display_name=f"Historical: {crisis.display_name}",
        equity_shock=crisis.equity_shock,
        rate_shock=crisis.rate_shock,
        vol_shock=vol_shock,
        lapse_multiplier=lapse_multiplier,
        withdrawal_multiplier=withdrawal_multiplier,
        scenario_type=ScenarioType.HISTORICAL,
        source_crisis=crisis.name,
        notes=crisis.notes,
    )


def create_custom_scenario(
    name: str,
    display_name: str,
    equity_shock: float,
    rate_shock: float,
    vol_shock: float = 1.0,
    lapse_multiplier: float = 1.0,
    withdrawal_multiplier: float = 1.0,
    notes: str = "",
) -> StressScenario:
    """
    Create a custom stress scenario.

    Parameters
    ----------
    name : str
        Scenario identifier (should be unique)
    display_name : str
        Human-readable description
    equity_shock : float
        Equity return shock (decimal, e.g., -0.30 = -30%)
    rate_shock : float
        Interest rate shock (decimal, e.g., -0.0100 = -100 bps)
    vol_shock : float
        Volatility multiplier (default 1.0 = unchanged)
    lapse_multiplier : float
        Lapse rate multiplier (default 1.0 = unchanged)
    withdrawal_multiplier : float
        Withdrawal utilization multiplier (default 1.0 = unchanged)
    notes : str
        Additional context

    Returns
    -------
    StressScenario
        The custom scenario

    Examples
    --------
    >>> scenario = create_custom_scenario(
    ...     name="stagflation",
    ...     display_name="Stagflation Scenario",
    ...     equity_shock=-0.25,
    ...     rate_shock=0.02,  # Rising rates
    ...     vol_shock=1.5,
    ...     notes="1970s-style stagflation"
    ... )
    """
    return StressScenario(
        name=name,
        display_name=display_name,
        equity_shock=equity_shock,
        rate_shock=rate_shock,
        vol_shock=vol_shock,
        lapse_multiplier=lapse_multiplier,
        withdrawal_multiplier=withdrawal_multiplier,
        scenario_type=ScenarioType.CUSTOM,
        notes=notes,
    )


def get_all_historical_scenarios(
    lapse_multiplier: float = 1.0,
    withdrawal_multiplier: float = 1.0,
) -> tuple[StressScenario, ...]:
    """
    Convert all historical crises to scenarios.

    Parameters
    ----------
    lapse_multiplier : float
        Lapse rate multiplier to apply (default 1.0)
    withdrawal_multiplier : float
        Withdrawal utilization multiplier (default 1.0)

    Returns
    -------
    Tuple[StressScenario, ...]
        All historical crises as scenarios
    """
    return tuple(
        crisis_to_scenario(
            crisis,
            lapse_multiplier=lapse_multiplier,
            withdrawal_multiplier=withdrawal_multiplier,
        )
        for crisis in ALL_HISTORICAL_CRISES
    )


def get_scenario_by_severity(
    min_equity_shock: float = -1.0,
    max_equity_shock: float = 0.0,
) -> tuple[StressScenario, ...]:
    """
    Filter historical scenarios by equity shock severity.

    Parameters
    ----------
    min_equity_shock : float
        Minimum (most severe) equity shock to include
    max_equity_shock : float
        Maximum (least severe) equity shock to include

    Returns
    -------
    Tuple[StressScenario, ...]
        Filtered scenarios

    Examples
    --------
    >>> # Get scenarios with equity shock between -30% and -15%
    >>> scenarios = get_scenario_by_severity(-0.30, -0.15)
    >>> len(scenarios)
    3  # 2018 Q4, 2011 Euro, 2015 China
    """
    all_scenarios = get_all_historical_scenarios()
    return tuple(s for s in all_scenarios if min_equity_shock <= s.equity_shock <= max_equity_shock)


def scenario_summary(scenario: StressScenario) -> str:
    """
    Generate a one-line summary of a scenario.

    Parameters
    ----------
    scenario : StressScenario
        The scenario to summarize

    Returns
    -------
    str
        Summary string

    Examples
    --------
    >>> summary = scenario_summary(ORSA_SEVERELY_ADVERSE)
    >>> print(summary)
    'ORSA Severely Adverse: Equity -30.0%, Rate -100bps, Vol 2.0x'
    """
    rate_bps = int(scenario.rate_shock * 10000)
    rate_sign = "+" if rate_bps >= 0 else ""
    return (
        f"{scenario.display_name}: "
        f"Equity {scenario.equity_shock * 100:.1f}%, "
        f"Rate {rate_sign}{rate_bps}bps, "
        f"Vol {scenario.vol_shock:.1f}x"
    )
