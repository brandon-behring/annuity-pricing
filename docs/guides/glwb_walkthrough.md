# GLWB Walkthrough

```{note}
This guide is under active development. Core functionality is implemented and tested.
See the [API Reference](../api/products.md) for current capabilities.
```

## Overview

GLWB (Guaranteed Lifetime Withdrawal Benefit) provides lifetime income guarantees on variable annuities.

## Key Components

1. **Benefit Base**: Account value with rollup during deferral
2. **Withdrawal Rate**: Annual percentage of benefit base
3. **Step-up**: Periodic increases if account value exceeds benefit base

## Monte Carlo Valuation

```python
from annuity_pricing.glwb.path_sim import GLWBPathSimulator

simulator = GLWBPathSimulator(
    initial_premium=100_000,
    rollup_rate=0.05,
    withdrawal_rate=0.05,
    n_paths=10_000,
    seed=42,
)

result = simulator.run()
print(f"Fair Fee: {result.fair_fee:.2%}")
print(f"CTE70 Reserve: ${result.cte70:,.0f}")
```

## Behavioral Assumptions

The simulator integrates behavioral models:

- **Dynamic Lapse**: Moneyness-driven lapse rates
- **Withdrawal Efficiency**: Actual vs optimal withdrawal behavior
- **Mortality**: SOA 2012 IAM tables

## See Also

- {doc}`regulatory_vm21_vm22` — VM-21 reserves
- {doc}`behavior_calibration` — Behavioral model setup
