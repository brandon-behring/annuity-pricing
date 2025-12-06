"""
Monte Carlo simulation for option pricing.

Provides:
- GBM path generation with variance reduction
- Monte Carlo pricing engine
- Convergence analysis tools

See: CONSTITUTION.md Section 4
"""

from annuity_pricing.options.simulation.gbm import (
    GBMParams,
    PathResult,
    generate_gbm_paths,
    generate_paths_with_monthly_observations,
    generate_terminal_values,
    validate_gbm_simulation,
)
from annuity_pricing.options.simulation.monte_carlo import (
    MCResult,
    MonteCarloEngine,
    convergence_analysis,
    price_vanilla_mc,
)

__all__ = [
    # GBM
    "GBMParams",
    "PathResult",
    "generate_gbm_paths",
    "generate_paths_with_monthly_observations",
    "generate_terminal_values",
    "validate_gbm_simulation",
    # Monte Carlo
    "MCResult",
    "MonteCarloEngine",
    "convergence_analysis",
    "price_vanilla_mc",
]
