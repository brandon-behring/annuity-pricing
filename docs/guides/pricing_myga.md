# Pricing MYGA Products

```{note}
This guide is under active development. Core functionality is implemented and tested.
See the [API Reference](../api/products.md) for current capabilities.
```

## Overview

MYGA (Multi-Year Guaranteed Annuity) products offer a guaranteed fixed rate for a specified term.

## Present Value Calculation

The present value of a MYGA is the discounted value of all guaranteed cash flows:

$$PV = \sum_{t=1}^{T} \frac{CF_t}{(1+r)^t}$$

Where:
- $CF_t$ = Cash flow at time $t$ (interest + principal at maturity)
- $r$ = Discount rate
- $T$ = Term in years

## Example

```python
from annuity_pricing.products.myga import MYGAPricer
from annuity_pricing.data.schemas import MYGAProduct

myga = MYGAProduct(
    company_name="Example Life",
    product_name="5-Year MYGA",
    product_group="MYGA",
    fixed_rate=0.045,  # 4.5% guaranteed
    guarantee_duration=5,
)

pricer = MYGAPricer(discount_rate=0.05)
result = pricer.price(myga, premium=100_000)

print(f"Present Value: ${result.present_value:,.0f}")
```

## Spread Analysis

The spread to the insurer is the difference between the earned rate and guaranteed rate:

$$\text{Spread} = r_{earned} - r_{guaranteed}$$

## See Also

- {doc}`../api/products` — Full API reference
- {doc}`getting_started` — Quick start guide
