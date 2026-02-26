# FIA Pricer Model Card

## Overview

| Field | Value |
|-------|-------|
| **Version** | 1.0.0 |
| **Module** | `annuity_pricing.products.fia` |
| **Class** | `FIAPricer` |
| **Type** | Pricer (analytical + Monte Carlo) |
| **License** | MIT |
| **Knowledge Tier** | T1 (Black-Scholes / Heston / SABR) + T2 (WINK calibration) |

`FIAPricer` values Fixed Indexed Annuity products with embedded index-linked
options. It decomposes FIA into a bond component (principal protection via 0%
floor) and an option component (index-linked upside), pricing the option via
Black-Scholes, Heston, or SABR and estimating expected credits via Monte Carlo.

## Inputs

### Constructor Parameters

| Parameter | Type | Default | Description | Tier |
|-----------|------|---------|-------------|------|
| `market_params` | `MarketParams` | required | Spot, risk-free rate, dividend yield, volatility, optional vol_model | T1 |
| `option_budget_pct` | `float` | `0.03` | Option budget as % of premium (e.g., 0.03 = 3%) | T3 |
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
| `product` | `FIAProduct` | required | FIA product with crediting method fields | T2 |
| `as_of_date` | `date \| None` | `None` | Valuation date | -- |
| `term_years` | `float \| None` | `None` | Investment term; required if not on product | T1 |
| `premium` | `float` | `100.0` | Premium amount for scaling | -- |

### Crediting Method Fields (on `FIAProduct`)

| Field | Method | Description |
|-------|--------|-------------|
| `cap_rate` | Cap | Maximum return (capped call = ATM call - OTM call) |
| `participation_rate` | Participation | Fraction of index return (par * ATM call) |
| `spread_rate` | Spread | Index return minus spread (call with adjusted strike) |
| `performance_triggered_rate` | Trigger | Digital option (pays fixed rate if index positive) |
| `indexing_method` | Monthly average | Path-dependent monthly averaging (MC required) |

## Outputs

### `FIAPricingResult`

| Field | Type | Description | Tier |
|-------|------|-------------|------|
| `present_value` | `float` | Risk-neutral PV = e^(-rT) * premium * (1 + expected_credit) | T1 |
| `duration` | `float` | Simplified duration (equals term_years) | T3 |
| `embedded_option_value` | `float` | BS/Heston/SABR value of embedded option | T1 |
| `option_budget` | `float` | PV of annual hedge spend over term (annuity-immediate factor) | T1 |
| `fair_cap` | `float` | Cap rate that exhausts option budget (binary search) | T1 |
| `fair_participation` | `float` | Participation rate = budget / ATM call value | T1 |
| `expected_credit` | `float` | Expected credited return from MC simulation | T1 |

### `CompetitivePosition`

| Field | Type | Description |
|-------|------|-------------|
| `rate` | `float` | Product's cap or participation rate |
| `percentile` | `float` | Percentile rank (0--100) among comparables |
| `rank` | `int` | Absolute rank (1 = highest rate) |
| `total_products` | `int` | Number of comparable products |

## Methodology

### Pricing Architecture

[T1] FIA = Bond + Call Option:
- Bond component provides 0% floor (principal protection)
- Option component provides index-linked upside

### Volatility Model Dispatch

The pricer routes option pricing to the appropriate model:

| Model | Trigger | Method |
|-------|---------|--------|
| Black-Scholes | No `vol_model` set | `black_scholes_call()` |
| Heston | `vol_model = HestonVolatility(...)` | `heston_price()` via COS method |
| SABR | `vol_model = SABRVolatility(...)` | `sabr_price_call()` via implied vol |

### Option Budget Calculation

[T1] Uses annuity-immediate factor for time value of money:

```
a_n = (1 - (1 + r)^(-n)) / r
option_budget = premium * option_budget_pct * a_n
```

### Fair Cap / Fair Participation Solving

- **Fair cap**: Binary search (50 iterations max) for cap where capped_call_value = budget [T1]
- **Fair participation**: Closed-form: budget / ATM_call_value [T1]

### Expected Credit (Monte Carlo)

- GBM or Heston paths depending on vol_model
- Antithetic variates enabled by default
- 252 daily steps for point-to-point; 12 * term monthly steps for monthly averaging
- Expected credit = mean(payoffs) / spot

### Key Assumptions

| Assumption | Justification | Tier |
|------------|---------------|------|
| Risk-neutral pricing | No-arbitrage framework | T1 |
| Single-period crediting | No interim reset | T3 |
| No fees or hedging frictions | Academic simplification | T3 |
| No surrender charges | Out of scope | T3 |
| 0% floor enforced | FIA principal protection | T1 |
| Option budget = 3% of premium | Industry approximation | T3 |
| Log-normal returns (GBM) | Standard BS assumption | T1 |

### References

- [T1] Black, F., & Scholes, M. (1973). *The Pricing of Options and Corporate Liabilities*
- [T1] Hull, J. C. (2018). *Options, Futures, and Other Derivatives* (10th ed.)
- [T1] Heston, S. (1993). *A Closed-Form Solution for Options with Stochastic Volatility*
- [T2] WINK Market Data (quarterly rate surveys)

## Validation Status

| Test | Purpose | Status |
|------|---------|--------|
| `test_put_call_parity.py` | BS implementation correctness | Verified (tolerance < 1e-10) |
| `test_arbitrage_bounds.py` | Option value <= underlying | Verified |
| `test_floor_enforcement.py` | FIA payoff >= 0 | Verified |
| `test_bs_known_answers.py` | Hull Example 15.6 (S=42, K=40) | Verified |
| `test_mc_convergence.py` | MC converges to BS for vanilla | Verified (< 5% divergence) |

### Cross-Validation

- [T2] financepy BS implementation matches within 1e-10
- [T2] Heston COS method matches QuantLib Heston engine

## Limitations

- **Single-period crediting**: Does not compound multi-year terms with annual resets.
- **No transaction costs or hedging frictions**: Assumes frictionless markets.
- **European-style only**: No early exercise or reset modeling.
- **Monthly averaging is approximate for embedded option value**: Analytical value uses capped call as upper bound; MC-based expected credit is more accurate.
- **Trigger method uses BS d2 for all vol models**: Digital option pricing does not use Heston- or SABR-specific digital formulas.
- **No credit risk**: Assumes insurer solvency.
- **Duration is simplified**: Returns term_years, not option-adjusted duration.

## Example Usage

```python
from annuity_pricing.products.fia import FIAPricer, MarketParams
from annuity_pricing.data.schemas import FIAProduct

market = MarketParams(
    spot=100, risk_free_rate=0.05, dividend_yield=0.02, volatility=0.20
)
pricer = FIAPricer(market_params=market, option_budget_pct=0.03)

product = FIAProduct(
    company_name="Example Life",
    product_name="Cap FIA",
    product_group="FIA",
    status="current",
    cap_rate=0.10,
)
result = pricer.price(product, term_years=1.0, premium=100.0)

print(f"PV: {result.present_value:.4f}")
print(f"Embedded option: {result.embedded_option_value:.4f}")
print(f"Fair cap: {result.fair_cap:.4f}")
print(f"Expected credit: {result.expected_credit:.4f}")
```

## See Also

- {class}`annuity_pricing.products.rila.RILAPricer` -- RILA with partial protection
- {class}`annuity_pricing.options.pricing.black_scholes` -- Underlying BS pricer
- {class}`annuity_pricing.options.payoffs.fia` -- FIA payoff functions
- {doc}`myga` -- Simpler deterministic MYGA pricer
