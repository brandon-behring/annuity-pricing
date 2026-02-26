# MYGA Pricer Model Card

## Overview

| Field | Value |
|-------|-------|
| **Version** | 0.3.0 |
| **Module** | `annuity_pricing.products.myga` |
| **Class** | `MYGAPricer` |
| **Type** | Pricer (deterministic) |
| **License** | MIT |
| **Knowledge Tier** | T1 (PV of guaranteed cash flows) |

`MYGAPricer` values Multi-Year Guaranteed Annuity products. MYGA is the
simplest annuity product: a fixed rate locked for the entire guarantee term
with 100% principal protection. Pricing is fully deterministic -- no
stochastic modeling is required.

## Inputs

### Constructor

`MYGAPricer` has no constructor parameters. It is stateless.

### `price()` Parameters

| Parameter | Type | Default | Description | Tier |
|-----------|------|---------|-------------|------|
| `product` | `MYGAProduct` | required | Product with `fixed_rate` and `guarantee_duration` | T1 |
| `as_of_date` | `date \| None` | `None` | Valuation date (defaults to today) | -- |
| `principal` | `float` | `100_000.0` | Initial premium amount | -- |
| `discount_rate` | `float \| None` | `None` | Discount rate for PV; defaults to product rate if omitted | T1 |
| `include_mgsv` | `bool` | `True` | Include MGSV floor in result details | T2 |

### `competitive_position()` Parameters

| Parameter | Type | Default | Description | Tier |
|-----------|------|---------|-------------|------|
| `product` | `MYGAProduct` | required | Product to rank | -- |
| `market_data` | `pd.DataFrame` | required | WINK comparable products | T2 |
| `duration_match` | `bool` | `True` | Filter to similar-duration products | -- |
| `duration_tolerance` | `int` | `1` | Years tolerance for duration matching | -- |

## Outputs

### `PricingResult`

| Field | Type | Description | Tier |
|-------|------|-------------|------|
| `present_value` | `float` | PV of maturity cash flow at discount rate | T1 |
| `duration` | `float` | Macaulay duration (equals guarantee term for zero-coupon) | T1 |
| `convexity` | `float` | Convexity = T(T+1) / (1+disc)^2 | T1 |
| `details["principal"]` | `float` | Input principal | -- |
| `details["maturity_value"]` | `float` | FV = principal * (1 + rate)^years | T1 |
| `details["modified_duration"]` | `float` | Macaulay / (1 + disc) | T1 |
| `details["mgsv"]` | `float \| None` | MGSV floor value | T2 |
| `details["effective_yield"]` | `float` | Equals stated fixed rate for MYGA | T1 |

### `CompetitivePosition`

| Field | Type | Description |
|-------|------|-------------|
| `rate` | `float` | Product's fixed rate |
| `percentile` | `float` | Percentile rank (0--100) among comparables |
| `rank` | `int` | Absolute rank (1 = highest rate) |
| `total_products` | `int` | Number of comparable products |

## Methodology

**Pricing approach**: Present value of a single guaranteed cash flow at maturity.

1. **Maturity value**: FV = principal * (1 + rate)^years [T1]
2. **Present value**: PV = FV / (1 + disc)^years [T1]
3. **Duration**: For a zero-coupon instrument, Macaulay duration equals time to maturity [T1]
4. **MGSV floor**: base_factor * principal * (1 + mgsv_rate)^years [T2]

### Key Assumptions

| Assumption | Justification | Tier |
|------------|---------------|------|
| Single cash flow at maturity | MYGA pays all at term end | T1 |
| Annual compounding | Industry convention | T1 |
| No early withdrawal / surrender | Simplification | T3 |
| MGSV base factor = 87.5%, rate = 1% | NAIC standard nonforfeiture | T2 |
| No credit risk | Assumes insurer solvency | T3 |

### References

- [T1] Standard time-value-of-money discounting
- [T2] NAIC Standard Nonforfeiture Law (MGSV calculation)
- [T2] WINK MYGA rate surveys

## Validation Status

| Test | Purpose | Status |
|------|---------|--------|
| PV at product rate = principal | Self-consistency | Verified |
| PV > principal when disc < rate | Arbitrage consistency | Verified |
| Duration = guarantee years | Zero-coupon property | Verified |
| Convexity = T(T+1)/(1+d)^2 | Closed-form identity | Verified |
| MGSV < maturity value | Floor below guaranteed | Verified |

### Cross-Validation

- No external library cross-validation needed (closed-form arithmetic).

## Limitations

- **No surrender charges**: Does not model early withdrawal penalties or market value adjustments (MVA).
- **No credit risk**: Assumes full insurer solvency; no default probability or guaranty fund modeling.
- **Annual compounding only**: Does not support daily or continuous compounding conventions.
- **No interim cash flows**: Models single maturity payment; no coupon or periodic interest variants.
- **No tax treatment**: Does not model tax-deferred accumulation or withdrawal taxation.
- **Spread over Treasury requires external input**: `calculate_spread_over_treasury()` needs a Treasury rate passed in; it does not fetch market data.

## Example Usage

```python
from annuity_pricing.products.myga import MYGAPricer
from annuity_pricing.data.schemas import MYGAProduct

pricer = MYGAPricer()
product = MYGAProduct(
    company_name="Example Life",
    product_name="5-Year MYGA",
    product_group="MYGA",
    status="current",
    fixed_rate=0.045,
    guarantee_duration=5,
)

# Price at a lower discount rate (PV > principal)
result = pricer.price(product, principal=100_000, discount_rate=0.04)
print(f"PV: ${result.present_value:,.2f}")
print(f"Duration: {result.duration} years")
print(f"Maturity value: ${result.details['maturity_value']:,.2f}")
print(f"MGSV floor: ${result.details['mgsv']:,.2f}")
```

## See Also

- {class}`annuity_pricing.products.base.BasePricer` -- Abstract base class
- {class}`annuity_pricing.data.schemas.MYGAProduct` -- Product schema
- {class}`annuity_pricing.valuation.myga_pv` -- Standalone PV calculation
