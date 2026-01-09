# FIAPricer Model Card

## Overview

| Field | Value |
|-------|-------|
| **Version** | 0.2.0 |
| **Module** | `annuity_pricing.products.fia` |
| **Type** | Pricer |
| **License** | MIT |
| **Knowledge Tier** | T1 (Black-Scholes) + T2 (WINK calibration) |

## Component Details

`FIAPricer` values Fixed Indexed Annuity products with embedded options.
It calculates expected credits, option budgets, and present values using
Black-Scholes pricing for the underlying crediting strategies.

## Intended Use

**Primary use cases**:
- Fair value calculation for FIA products
- Competitive rate analysis vs WINK market data
- Option budget estimation for product design
- Cap/participation rate solving

**Out-of-scope**:
- Real-time trading systems (use dedicated platforms)
- Regulatory capital calculations (see VM-21/VM-22 modules)
- Policy administration systems

## Parameters

| Parameter | Type | Default | Description | Tier |
|-----------|------|---------|-------------|------|
| `market_params` | MarketParams | required | Spot, rate, vol, dividend | T1 |
| `cap_rate` | float | 0.05 | Maximum credited return | T2 |
| `participation_rate` | float | 1.0 | Index participation (0-1+) | T2 |
| `spread` | float | 0.0 | Deduction from index return | T2 |
| `floor_rate` | float | 0.0 | Minimum return (0% standard) | T1 |

## Assumptions

| Assumption | Validation | Tier |
|------------|------------|------|
| Log-normal returns | Standard BS assumption | T1 |
| Constant volatility | Can use Heston for term structure | T1 |
| No early exercise | European-style crediting | T1 |
| 0% floor enforced | `max(credit, 0)` in payoff | T1 |
| Continuous compounding | Standard financial convention | T1 |
| No transaction costs | Academic assumption | T3 |

## Validation

### Put-Call Parity
[T1] Verified within 1e-10 tolerance:
```
C - P = S - K*exp(-rT)
```

### Hull Textbook Example 15.6
[T1] S=42, K=40, r=10%, σ=20%, T=0.5:
- Expected: Call=4.76, Put=0.81
- Actual: Call=4.759422, Put=0.808600 ✓

### Cross-Library Validation
[T2] financepy BS implementation matches within 1e-10

## Limitations

1. **Single period only**: Does not compound multi-year terms
2. **No transaction costs**: Assumes frictionless markets
3. **European-style**: No early exercise modeling
4. **Constant volatility**: Use Heston for vol term structure
5. **No credit risk**: Assumes insurer solvency

## References

- [T1] Black, F., & Scholes, M. (1973). *The Pricing of Options and Corporate Liabilities*
- [T1] Hull, J. C. (2018). *Options, Futures, and Other Derivatives* (10th ed.)
- [T2] WINK Market Data (quarterly rate surveys)

## See Also

- {class}`annuity_pricing.products.rila.RILAPricer` - For partial protection
- {func}`annuity_pricing.options.pricing.black_scholes_call` - Underlying pricer
- {doc}`/guides/pricing_fia` - Usage guide
