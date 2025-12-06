"""
Validation adapters for cross-checking against external libraries.

This module provides thin adapters to external validators for:
- Black-Scholes pricing (financepy)
- Monte Carlo simulation (pyfeng)
- Yield curve construction (QuantLib)

Usage
-----
>>> from annuity_pricing.adapters import FINANCEPY_AVAILABLE
>>> if FINANCEPY_AVAILABLE:
...     from annuity_pricing.adapters.financepy_adapter import validate_bs_call
"""

from .base import ValidationResult, BaseAdapter
from .financepy_adapter import FINANCEPY_AVAILABLE, FinancepyAdapter
from .pyfeng_adapter import PYFENG_AVAILABLE, PyfengAdapter
from .quantlib_adapter import QUANTLIB_AVAILABLE, QuantLibAdapter

__all__ = [
    "ValidationResult",
    "BaseAdapter",
    "FINANCEPY_AVAILABLE",
    "FinancepyAdapter",
    "PYFENG_AVAILABLE",
    "PyfengAdapter",
    "QUANTLIB_AVAILABLE",
    "QuantLibAdapter",
]
