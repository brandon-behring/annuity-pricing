# Behavior Calibration

```{note}
This guide is under active development. Core functionality is implemented and tested.
See the [API Reference](../api/behavioral.md) for current capabilities.
```

## Overview

Behavioral models capture policyholder actions that deviate from rational economic behavior.

## Dynamic Lapse

Moneyness-driven lapse rates:

```python
from annuity_pricing.behavioral.dynamic_lapse import DynamicLapseModel

model = DynamicLapseModel(
    base_lapse_rate=0.03,
    itm_multiplier=0.5,   # Lower lapse when ITM
    otm_multiplier=2.0,   # Higher lapse when OTM
)

lapse_rate = model.calculate_lapse_rate(moneyness=1.2)
```

## Withdrawal Efficiency

Actual vs optimal withdrawal behavior:

```python
from annuity_pricing.behavioral.withdrawal import WithdrawalEfficiency

efficiency = WithdrawalEfficiency(
    base_efficiency=0.85,  # 85% of optimal
)

actual_withdrawal = efficiency.calculate(optimal=5000)
```

## Expense Loading

```python
from annuity_pricing.behavioral.expenses import ExpenseModel

model = ExpenseModel(
    acquisition_cost=0.05,    # 5% of premium
    maintenance_cost=50.0,    # $50/year
    per_withdrawal_cost=25.0, # $25/withdrawal
)
```

## Integration with GLWB

All behavioral models are integrated into the GLWB path simulator.

## See Also

- {doc}`glwb_walkthrough` — GLWB valuation
- {doc}`../api/behavioral` — Behavioral API reference
