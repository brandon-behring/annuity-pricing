"""
Validation framework for pricing results.

Provides HALT/PASS gates for validating pricing outputs:
- PresentValueBoundsGate: Check PV within bounds
- DurationBoundsGate: Check duration reasonable
- FIAOptionBudgetGate: Check FIA option value vs budget
- FIAExpectedCreditGate: Check FIA credit bounds
- RILAMaxLossGate: Check RILA max loss consistency
- RILAProtectionValueGate: Check RILA protection value
- ArbitrageBoundsGate: No-arbitrage checks

See: METHODOLOGY.md Section 5
"""

from annuity_pricing.validation.gates import (
    ArbitrageBoundsGate,
    DurationBoundsGate,
    FIAExpectedCreditGate,
    FIAOptionBudgetGate,
    GateResult,
    # Enums and Results
    GateStatus,
    # Specific Gates
    PresentValueBoundsGate,
    RILAMaxLossGate,
    RILAProtectionValueGate,
    # Engine
    ValidationEngine,
    # Base Gate
    ValidationGate,
    ValidationReport,
    ensure_valid,
    # Convenience Functions
    validate_pricing_result,
)

__all__ = [
    # Enums and Results
    "GateStatus",
    "GateResult",
    "ValidationReport",
    # Base Gate
    "ValidationGate",
    # Specific Gates
    "PresentValueBoundsGate",
    "DurationBoundsGate",
    "FIAOptionBudgetGate",
    "FIAExpectedCreditGate",
    "RILAMaxLossGate",
    "RILAProtectionValueGate",
    "ArbitrageBoundsGate",
    # Engine
    "ValidationEngine",
    # Convenience Functions
    "validate_pricing_result",
    "ensure_valid",
]
