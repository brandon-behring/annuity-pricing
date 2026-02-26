# RILA Pricer Model Card

## Overview

| Field | Value |
|-------|-------|
| **Version** | 1.0.0 |
| **Module** | `annuity_pricing.products.rila` |
| **Class** | `RILAPricer` |
| **Type** | Pricer (analytical + Monte Carlo) |
| **License** | MIT |
| **Knowledge Tier** | T1 (Put spread / put replication) |

`RILAPricer` values Registered Index-Linked Annuity products with partial
downside protection. Unlike FIA (0% floor), RILA offers buffer or floor
protection in exchange for higher upside caps. Protection is priced using
option replication: buffers as put spreads, floors as long OTM puts.

## Inputs

### Constructor Parameters

| Parameter | Type | Default | Description | Tier |
|-----------|------|---------|-------------|------|
| `market_params` | `MarketParams` | required | Spot, risk-free rate, dividend yield, volatility, optional vol_model | T1 |
| `n_mc_paths` | `int` | `100000` | Number of Monte Carlo paths | -- |
| `seed` | `int \| None` | `None` | Random seed for reproducibility | -- |

### `MarketParams` Fields

| Field | Type | Description | Tier |
|-------|------|-------------|------|
| `spot` | `float` | Current index level (must be > 0) | T1 |
| `risk_free_rate` | `float` | Risk-free rate (annualized, decimal) | T1 |
| `dividend_yield` | `float` | Index dividend yield (annualized, decimal) | T1 |
| `volatility` | `float` | Index volatility (annualized, decimal; must be >= 0) | T1 |
| `vol_model` | `VolatilityModel \| None` | Optional Heston or SABR override | T1 |

### `price()` Parameters

| Parameter | Type | Default | Description | Tier |
|-----------|------|---------|-------------|------|
| `product` | `RILAProduct` | required | RILA product with buffer/floor and cap fields | T2 |
| `as_of_date` | `date \| None` | `None` | Valuation date | -- |
| `term_years` | `float \| None` | `None` | Investment term; required if not on product | T1 |
| `premium` | `float` | `100.0` | Premium amount for scaling | -- |

### Protection Type Detection

Protection type is determined by `buffer_modifier` on `RILAProduct`:

| `buffer_modifier` value | Protection type |
|--------------------------|-----------------|
| `"Losses Covered Up To"` / `"Buffer"` | Buffer (absorbs FIRST X%) |
| `"Losses Covered After"` / other | Floor (covers losses BEYOND X%) |

## Outputs

### `RILAPricingResult`

| Field | Type | Description | Tier |
|-------|------|-------------|------|
| `present_value` | `float` | Risk-neutral PV = e^(-rT) * premium * (1 + expected_return) | T1 |
| `duration` | `float` | Simplified duration (equals term_years) | T3 |
| `protection_value` | `float` | Value of downside protection (put spread or OTM put) | T1 |
| `protection_type` | `str` | `"buffer"` or `"floor"` | T1 |
| `upside_value` | `float` | Value of capped upside (capped call) | T1 |
| `expected_return` | `float` | Expected return from MC simulation | T1 |
| `max_loss` | `float` | Maximum possible loss (1 - buffer for buffer; floor level for floor) | T1 |
| `breakeven_return` | `float \| None` | Index return needed to break even | T1 |

### `RILAGreeks` (from `calculate_greeks()`)

| Field | Type | Description | Tier |
|-------|------|-------------|------|
| `delta` | `float` | Position delta (dV/dS), net across option legs | T1 |
| `gamma` | `float` | Position gamma (d^2V/dS^2) | T1 |
| `vega` | `float` | Position vega (dV/d sigma) per 1% vol change | T1 |
| `theta` | `float` | Position theta (dV/dt) per day | T1 |
| `rho` | `float` | Position rho (dV/dr) per 1% rate change | T1 |
| `atm_put_delta` | `float` | Delta of ATM put component (buffer only) | T1 |
| `otm_put_delta` | `float` | Delta of OTM put component | T1 |
| `dollar_delta` | `float` | delta * spot * notional | T1 |

### `CompetitivePosition`

| Field | Type | Description |
|-------|------|-------------|
| `rate` | `float` | Product's cap rate |
| `percentile` | `float` | Percentile rank (0--100) among comparables |
| `rank` | `int` | Absolute rank (1 = highest rate) |
| `total_products` | `int` | Number of comparable products |

## Methodology

### Protection Mechanics

**Buffer** [T1]: Insurer absorbs the FIRST X% of losses.

```
Index return: -15%, Buffer: 10%
Client loss:   -5% (buffer absorbed first 10%)
```

Option replication: Long ATM put (K=S) - Short OTM put (K=S*(1-buffer))

**Floor** [T1]: Insurer covers losses BEYOND X%.

```
Index return: -15%, Floor: -10%
Client loss:  -10% (capped at floor level)
```

Option replication: Long OTM put (K=S*(1-floor))

**100% buffer edge case**: When buffer >= 100%, equivalent to full ATM put protection (no short leg). OTM strike at 0 is invalid for BS, so the pricer handles this as a special case.

### Upside Pricing

Capped call = ATM call - OTM call at S*(1+cap). If no cap, full ATM call value.

### Volatility Model Dispatch

Same dispatch architecture as FIAPricer:

| Model | Method |
|-------|--------|
| Black-Scholes | `black_scholes_call()` / `black_scholes_put()` |
| Heston | `heston_price()` via COS method |
| SABR | `sabr_price_call()` / `sabr_price_put()` via implied vol |

### Expected Return (Monte Carlo)

- Uses `BufferPayoff` or `FloorPayoff` objects applied to GBM or Heston paths
- Antithetic variates enabled; 252 daily steps
- Expected return = mean(payoffs) / spot

### Breakeven Calculation

Analytical (no numerical solver):
- **Buffer**: breakeven = -buffer_rate (buffer fully absorbs loss at this point)
- **Floor**: breakeven = 0.0 (any negative return = loss)

### Greeks Calculation

[T1] Greeks computed from the Black-Scholes option replication:
- Buffer: net Greeks = long ATM put Greeks - short OTM put Greeks
- Floor: Greeks = long OTM put Greeks
- Dollar delta = delta * spot * notional

### Key Assumptions

| Assumption | Justification | Tier |
|------------|---------------|------|
| Risk-neutral pricing | No-arbitrage framework | T1 |
| Buffer = put spread | Standard option replication | T1 |
| Floor = long OTM put | Standard option replication | T1 |
| Log-normal returns (GBM) | Standard BS assumption | T1 |
| Single-period crediting | No interim reset | T3 |
| No fees or hedging frictions | Academic simplification | T3 |
| European exercise | Standard RILA terms | T1 |

### References

- [T1] Hull, J. C. (2018). *Options, Futures, and Other Derivatives* (10th ed.)
- [T1] SEC Final Rule: RILAs as registered securities (2024)
- [T1] Black, F., & Scholes, M. (1973). *The Pricing of Options and Corporate Liabilities*
- [T2] WINK RILA rate surveys

## Validation Status

| Test | Purpose | Status |
|------|---------|--------|
| `test_buffer_mechanics.py` | Buffer payoff correctness | Verified |
| `test_buffer_vs_floor.py` | Buffer and floor are distinct | Verified |
| `test_put_call_parity.py` | BS implementation | Verified (tolerance < 1e-10) |
| `test_arbitrage_bounds.py` | Option value <= underlying | Verified |
| `test_bs_known_answers.py` | Hull Example 15.6 | Verified |

### Cross-Validation

- [T2] QuantLib validation for put spread pricing
- [T2] Heston COS method matches QuantLib Heston engine

## Limitations

- **Buffer and floor are mutually exclusive**: Cannot combine both protection types on one product.
- **Single buffer/floor level only**: No tiered or layered protection.
- **Single-period crediting**: Does not compound multi-year terms with annual resets.
- **No transaction costs or hedging frictions**: Assumes frictionless markets.
- **European-style only**: No early exercise.
- **Greeks use BS only**: `calculate_greeks()` uses Black-Scholes regardless of `vol_model` setting; no Heston or SABR Greeks.
- **No credit risk**: Assumes insurer solvency.
- **Duration is simplified**: Returns term_years, not option-adjusted duration.
- **SEC registration implications not modeled**: Regulatory costs and constraints are out of scope.

## Example Usage

```python
from annuity_pricing.products.rila import RILAPricer, MarketParams
from annuity_pricing.data.schemas import RILAProduct

market = MarketParams(
    spot=100, risk_free_rate=0.05, dividend_yield=0.02, volatility=0.20
)
pricer = RILAPricer(market_params=market)

product = RILAProduct(
    company_name="Example Life",
    product_name="10% Buffer RILA",
    product_group="RILA",
    status="current",
    buffer_rate=0.10,
    buffer_modifier="Losses Covered Up To",
    cap_rate=0.15,
)
result = pricer.price(product, term_years=1.0, premium=100.0)

print(f"PV: {result.present_value:.4f}")
print(f"Protection type: {result.protection_type}")
print(f"Protection value: {result.protection_value:.4f}")
print(f"Expected return: {result.expected_return:.4f}")
print(f"Max loss: {result.max_loss:.2%}")

# Calculate hedge Greeks
greeks = pricer.calculate_greeks(product, term_years=1.0)
print(f"Delta: {greeks.delta:.4f}")
print(f"Dollar delta: ${greeks.dollar_delta:,.2f}")
```

## See Also

- {class}`annuity_pricing.products.fia.FIAPricer` -- FIA with 0% floor
- {class}`annuity_pricing.options.payoffs.rila.BufferPayoff` -- Buffer payoff function
- {class}`annuity_pricing.options.payoffs.rila.FloorPayoff` -- Floor payoff function
- {doc}`fia` -- FIA pricer model card
