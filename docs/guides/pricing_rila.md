# Pricing RILA Products

```{note}
This guide is under active development. Core functionality is implemented and tested.
See the [API Reference](../api/products.md) for current capabilities.
```

## Overview

RILA (Registered Index-Linked Annuity) products offer market participation with downside protection via buffers or floors.

## Buffer vs Floor

| Protection | Small Loss (-5%) | Large Loss (-25%) |
|------------|------------------|-------------------|
| 10% Buffer | 0% (absorbed) | -15% (25-10) |
| 10% Floor | -5% (pass-through) | -10% (capped) |

**Buffer**: Better for small losses
**Floor**: Better for catastrophic losses

## Payoff Formulas

### Buffer Payoff
$$\text{Return} = \min\left(\text{Cap}, \max\left(\text{Index Return} + \text{Buffer}, \text{Index Return}\right)\right)$$

### Floor Payoff
$$\text{Return} = \min\left(\text{Cap}, \max\left(\text{Floor}, \text{Index Return}\right)\right)$$

## Greeks

```python
from annuity_pricing.products.rila import RILAPricer

pricer = RILAPricer()
greeks = pricer.calculate_greeks(rila_product, premium=100_000, term_years=1.0)

print(f"Delta: {greeks.delta:.4f}")
print(f"Vega: {greeks.vega:.4f}")
```

## See Also

- {doc}`pricing_fia` — FIA option budgeting
- {doc}`../api/products` — Full API reference
