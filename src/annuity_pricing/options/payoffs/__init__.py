"""
Option payoffs for FIA and RILA products.

Provides payoff implementations for:
- FIA: Cap, Participation, Spread, Trigger, Monthly Average
- RILA: Buffer, Floor, Combined Buffer+Floor

See: METHODOLOGY.md Section 3.2
"""

from annuity_pricing.options.payoffs.base import (
    BasePayoff,
    CreditingMethod,
    IndexPath,
    OptionType,
    PayoffResult,
    VanillaOption,
    calculate_moneyness,
    is_in_the_money,
)
from annuity_pricing.options.payoffs.fia import (
    CappedCallPayoff,
    MonthlyAveragePayoff,
    ParticipationPayoff,
    SpreadPayoff,
    TriggerPayoff,
    create_fia_payoff,
)
from annuity_pricing.options.payoffs.rila import (
    BufferPayoff,
    BufferWithFloorPayoff,
    FloorPayoff,
    StepRateBufferPayoff,
    compare_buffer_vs_floor,
    create_rila_payoff,
)

__all__ = [
    # Base classes
    "BasePayoff",
    "CreditingMethod",
    "IndexPath",
    "OptionType",
    "PayoffResult",
    "VanillaOption",
    "calculate_moneyness",
    "is_in_the_money",
    # FIA payoffs
    "CappedCallPayoff",
    "MonthlyAveragePayoff",
    "ParticipationPayoff",
    "SpreadPayoff",
    "TriggerPayoff",
    "create_fia_payoff",
    # RILA payoffs
    "BufferPayoff",
    "BufferWithFloorPayoff",
    "FloorPayoff",
    "StepRateBufferPayoff",
    "compare_buffer_vs_floor",
    "create_rila_payoff",
]
