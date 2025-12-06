"""
Data Loaders - Phase 10.

Enhanced data loading for:
- Yield curves (construction, interpolation, Nelson-Siegel)
- Mortality tables (SOA 2012 IAM, Gompertz, improvements)

See: docs/CROSS_VALIDATION_MATRIX.md
"""

from .yield_curve import (
    YieldCurve,
    YieldCurveLoader,
    NelsonSiegelParams,
    InterpolationMethod,
    fit_nelson_siegel,
    calculate_duration,
)

from .mortality import (
    MortalityTable,
    MortalityLoader,
    compare_life_expectancy,
    calculate_annuity_pv,
)

__all__ = [
    # Yield Curve
    "YieldCurve",
    "YieldCurveLoader",
    "NelsonSiegelParams",
    "InterpolationMethod",
    "fit_nelson_siegel",
    "calculate_duration",
    # Mortality
    "MortalityTable",
    "MortalityLoader",
    "compare_life_expectancy",
    "calculate_annuity_pv",
]
