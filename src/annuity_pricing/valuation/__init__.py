"""
Valuation module for annuity pricing.

[T2] Provides present value calculations, duration, convexity,
and risk metrics for MYGA (Multi-Year Guaranteed Annuity) products.

See: METHODOLOGY.md Section 4.1
"""

from .myga_pv import (
    CashFlow,
    MYGAValuation,
    calculate_convexity,
    calculate_dollar_duration,
    calculate_effective_duration,
    calculate_macaulay_duration,
    calculate_modified_duration,
    calculate_myga_maturity_value,
    calculate_present_value,
    sensitivity_analysis,
    value_myga,
)

__all__ = [
    # Dataclasses
    "CashFlow",
    "MYGAValuation",
    # Maturity value
    "calculate_myga_maturity_value",
    # Present value
    "calculate_present_value",
    # Duration metrics
    "calculate_macaulay_duration",
    "calculate_modified_duration",
    "calculate_effective_duration",
    # Risk metrics
    "calculate_convexity",
    "calculate_dollar_duration",
    # Complete valuation
    "value_myga",
    "sensitivity_analysis",
]
