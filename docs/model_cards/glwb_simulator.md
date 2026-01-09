# GLWBPricer Model Card

## Overview

| Field | Value |
|-------|-------|
| **Version** | 0.2.0 |
| **Module** | `annuity_pricing.products.glwb` |
| **Type** | Simulator (Monte Carlo) |
| **License** | MIT |
| **Knowledge Tier** | T1 (Risk-neutral pricing) + T3 (Behavioral) |

## Component Details

`GLWBPricer` values Guaranteed Lifetime Withdrawal Benefit riders
using Monte Carlo simulation. It models the interaction between
account value, guaranteed withdrawal base (GWB), and lifetime income.

## Intended Use

**Primary use cases**:
- GLWB guarantee cost estimation
- Ruin probability analysis
- Sensitivity analysis (vol, rates, withdrawal)
- Product comparison

**Out-of-scope**:
- Real-time pricing for trading
- Exact regulatory reserves (use VM-21)
- Closed-form solutions (path-dependent)

## Parameters

| Parameter | Type | Default | Description | Tier |
|-----------|------|---------|-------------|------|
| `risk_free_rate` | float | 0.04 | Discount rate | T1 |
| `volatility` | float | 0.15 | Equity volatility | T1 |
| `n_paths` | int | 10000 | Monte Carlo paths | T1 |
| `seed` | int | None | Random seed | - |
| `withdrawal_rate` | float | 0.05 | Annual withdrawal % | T3 |
| `rollup_rate` | float | 0.05 | GWB growth rate | T2 |

## Monte Carlo Methodology

### Path Generation
[T1] Geometric Brownian Motion:
```
dS/S = (r - q)dt + σdW
```

### Guarantee Cost
[T1] Risk-neutral expectation of guarantee payments:
```
Guarantee Cost = E[max(GWB_withdrawal - AV_withdrawal, 0)]
```
discounted at risk-free rate.

### Convergence
Standard error ∝ 1/√n where n = number of paths.
10,000 paths gives ~1% standard error on guarantee cost.

## Assumptions

| Assumption | Validation | Tier |
|------------|------------|------|
| GBM dynamics | Standard | T1 |
| Risk-neutral pricing | No-arbitrage | T1 |
| Constant withdrawal rate | Simplification | T3 |
| No lapse | Conservative | T3 |
| Mortality via SOA tables | Industry standard | T2 |
| 100% utilization | Upper bound | T3 |

## Validation

### GBM Drift
[T1] Verified mean return = r - q (risk-neutral)

### Martingale Test
[T1] Discounted asset price is martingale:
```
E[S_T * exp(-rT)] = S_0
```

### Convergence Rate
[T1] Verified 1/√n convergence with antithetic variates

## Outputs

| Output | Description | Tier |
|--------|-------------|------|
| `guarantee_cost` | PV of guarantee as % of premium | T1 |
| `prob_ruin` | Probability account exhausted | T1 |
| `mean_ruin_year` | Expected year of ruin (if ruins) | T1 |
| `prob_lapse` | Probability of early surrender | T3 |

## Limitations

1. **Computationally intensive**: 10K paths × 35 years
2. **Behavioral assumptions**: Withdrawal rate assumed constant
3. **No dynamic policyholder behavior**: Uses static lapse
4. **Single fund**: No multi-fund tracking
5. **Annual steps**: Monthly available but slower

## References

- [T1] Bauer, Kling & Russ (2008). *A Universal Pricing Framework for GMxB*
- [T1] Hardy (2003). *Investment Guarantees*
- [T2] SOA 2018 GLWB Experience Study
- [T3] Internal calibration assumptions

## See Also

- {class}`annuity_pricing.glwb.path_sim.GLWBPathSimulator` - Simulation engine
- {class}`annuity_pricing.glwb.gwb_tracker.GWBTracker` - Account tracking
- {doc}`/guides/glwb_walkthrough` - Usage guide
