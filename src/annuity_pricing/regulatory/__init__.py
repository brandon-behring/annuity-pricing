"""
Regulatory Calculations - Phase 9.

Implements NAIC VM-21 and VM-22 for annuity reserves:
- AG43/VM-21: Variable annuity reserve requirements
- VM-22: Fixed annuity principle-based reserves
- Scenario generation: Economic scenarios for stochastic modeling

See: docs/knowledge/domain/vm21_vm22.md
"""

from .scenarios import (
    ScenarioGenerator,
    EconomicScenario,
    AG43Scenarios,
    VasicekParams,
    EquityParams,
    generate_deterministic_scenarios,
    calculate_scenario_statistics,
)
from .vm21 import (
    VM21Calculator,
    VM21Result,
    PolicyData,
    calculate_cte_levels,
    sensitivity_analysis,
)
from .vm22 import (
    VM22Calculator,
    VM22Result,
    FixedAnnuityPolicy,
    StochasticExclusionResult,
    ReserveType,
    compare_reserve_methods,
    vm22_sensitivity,
)

__all__ = [
    # Scenario Generation
    "ScenarioGenerator",
    "EconomicScenario",
    "AG43Scenarios",
    "VasicekParams",
    "EquityParams",
    "generate_deterministic_scenarios",
    "calculate_scenario_statistics",
    # VM-21
    "VM21Calculator",
    "VM21Result",
    "PolicyData",
    "calculate_cte_levels",
    "sensitivity_analysis",
    # VM-22
    "VM22Calculator",
    "VM22Result",
    "FixedAnnuityPolicy",
    "StochasticExclusionResult",
    "ReserveType",
    "compare_reserve_methods",
    "vm22_sensitivity",
]
