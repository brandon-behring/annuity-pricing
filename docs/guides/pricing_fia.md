# Pricing FIA Products

```{note}
This guide is under active development. Core functionality is implemented and tested.
See the [API Reference](../api/products.md) for current capabilities.
```

## Overview

FIA (Fixed Indexed Annuity) products credit interest based on index performance, subject to a cap, floor, and participation rate.

## Crediting Formula

$$\text{Credit} = \max\left(0, \min\left(\text{Cap}, \text{Participation} \times \text{Index Return}\right)\right)$$

## Option Budgeting

The fair cap is determined by the option budget available to purchase index participation:

```python
from annuity_pricing.products.fia import FIAPricer, MarketParams
from annuity_pricing.data.schemas import FIAProduct

market = MarketParams(spot=100, risk_free_rate=0.05, dividend_yield=0.02, volatility=0.20)
pricer = FIAPricer(market_params=market)

# Find fair cap for 3% option budget
fair_cap = pricer.solve_fair_cap(option_budget=0.03, term_years=1.0)
print(f"Fair Cap: {fair_cap:.1%}")
```

## See Also

- {doc}`pricing_rila` — Buffer/floor protection
- {doc}`../api/products` — Full API reference
