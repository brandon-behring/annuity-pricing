# GLWB Pricer Model Card

## Overview

| Field | Value |
|-------|-------|
| **Version** | 1.0.0 |
| **Module** | `annuity_pricing.glwb.path_sim` |
| **Class** | `GLWBPathSimulator` |
| **Type** | Simulator (path-dependent Monte Carlo) |
| **License** | MIT |
| **Knowledge Tier** | T1 (risk-neutral MC) + T3 (behavioral models) |

`GLWBPathSimulator` prices Guaranteed Lifetime Withdrawal Benefit riders using
path-dependent Monte Carlo simulation. Each path models the full interaction
between account value evolution (GBM + fees), GWB tracking (rollup, ratchet),
withdrawal/lapse behavior, and mortality. The guarantee value equals the
expected PV of insurer payments when the account value is exhausted.

## Inputs

### Constructor Parameters

| Parameter | Type | Default | Description | Tier |
|-----------|------|---------|-------------|------|
| `gwb_config` | `GWBConfig` | required | GWB mechanics (rollup, ratchet, withdrawal rate, fee) | T2 |
| `n_paths` | `int` | `10000` | Number of MC paths | -- |
| `seed` | `int \| None` | `None` | Random seed | -- |
| `lapse_assumptions` | `LapseAssumptions \| None` | `None` | Dynamic lapse parameters (defaults if None) | T3 |
| `withdrawal_assumptions` | `WithdrawalAssumptions \| None` | `None` | Withdrawal utilization parameters (defaults if None) | T3 |
| `expense_assumptions` | `ExpenseAssumptions \| None` | `None` | Insurer expense parameters (defaults if None) | T3 |
| `steps_per_year` | `int` | `1` | Timestep granularity (1=annual, 12=monthly) | -- |

### `GWBConfig` Fields

| Field | Type | Description | Tier |
|-------|------|-------------|------|
| `rollup_type` | `RollupType` | Simple, compound, or none | T2 |
| `rollup_rate` | `float` | Annual rollup rate (e.g., 0.05 = 5%) | T2 |
| `rollup_cap_years` | `int \| None` | Maximum years rollup applies | T2 |
| `ratchet_enabled` | `bool` | Step-up to AV high water mark | T2 |
| `ratchet_frequency` | `int` | Years between ratchet evaluations | T2 |
| `withdrawal_rate` | `float` | Annual withdrawal as % of GWB | T2 |
| `fee_rate` | `float` | Annual fee deducted from AV | T2 |
| `fee_basis` | `str` | Basis for fee calculation | T2 |

### `price()` Parameters

| Parameter | Type | Default | Description | Tier |
|-----------|------|---------|-------------|------|
| `premium` | `float` | required | Initial premium (must be > 0) | -- |
| `age` | `int` | required | Current age of policyholder | T2 |
| `r` | `float` | required | Risk-free rate (annualized) | T1 |
| `sigma` | `float` | required | Equity volatility (annualized) | T1 |
| `max_age` | `int` | `100` | Maximum simulation age | T3 |
| `mortality_table` | `callable \| MortalityTable \| None` | `None` | age -> qx function; defaults to SOA 2012 IAM | T2 |
| `utilization_rate` | `float \| None` | `None` | Fixed utilization (overrides behavioral model) | T3 |
| `gender` | `str` | `"male"` | Gender for default mortality table | T2 |
| `surrender_period_years` | `int` | `7` | Years until surrender period ends | T2 |
| `use_behavioral_models` | `bool` | `True` | Enable lapse/withdrawal/expense models | T3 |
| `deferral_years` | `int` | `0` | Years before withdrawals begin (rollup during deferral) | T2 |

## Outputs

### `GLWBPricingResult`

| Field | Type | Description | Tier |
|-------|------|-------------|------|
| `price` | `float` | Risk-neutral price of GLWB guarantee | T1 |
| `guarantee_cost` | `float` | Cost of guarantee as fraction of premium | T1 |
| `mean_payoff` | `float` | Average discounted payoff across paths | T1 |
| `std_payoff` | `float` | Standard deviation of discounted payoff | T1 |
| `standard_error` | `float` | Standard error of mean (std / sqrt(n_paths)) | T1 |
| `prob_ruin` | `float` | Probability account value exhausted before death | T1 |
| `mean_ruin_year` | `float` | Average year of ruin (-1 if no ruin observed) | T1 |
| `prob_lapse` | `float` | Probability of lapse before death/ruin | T3 |
| `mean_lapse_year` | `float` | Average year of lapse (-1 if no lapse) | T3 |
| `n_paths` | `int` | Number of paths simulated | -- |

### `PathResult` (per-path diagnostics)

| Field | Type | Description |
|-------|------|-------------|
| `pv_insurer_payments` | `float` | PV of payments from insurer when AV exhausted |
| `pv_withdrawals` | `float` | PV of all withdrawals taken |
| `pv_expenses` | `float` | PV of insurer expenses |
| `ruin_year` | `int` | Year AV exhausted (-1 if never) |
| `lapse_year` | `int` | Year of lapse (-1 if never) |
| `final_av` | `float` | Account value at end of simulation |
| `final_gwb` | `float` | GWB at end of simulation |
| `death_year` | `int` | Year of death (-1 if survived) |

## Methodology

### Path Simulation

[T1] Each path simulates year-by-year (or month-by-month) evolution:

1. **Mortality check**: Draw against qx converted to step probability via `1 - (1-qx)^dt`
2. **Dynamic lapse check**: Evaluate lapse model based on GWB/AV ratio and surrender period
3. **Market return**: GBM step with `drift = (r - 0.5*sigma^2)*dt`, `diffusion = sigma*sqrt(dt)*Z`
4. **Expenses**: Period expense calculation if behavioral models enabled
5. **Withdrawal**: Apply utilization rate (fixed or behavioral) to max withdrawal = GWB * withdrawal_rate * dt
6. **GWB update**: Rollup, ratchet, and state evolution via `GWBTracker.step()`
7. **Ruin detection**: If AV <= 0, insurer pays guaranteed amount for remaining steps
8. **Discounting**: All cash flows discounted at e^(-r*t)

### Guarantee Pricing

[T1] GLWB guarantee value = E[PV(insurer payments when AV = 0)]

The insurer pays when:
- Account value is exhausted (AV = 0)
- Policyholder is still alive
- Guaranteed withdrawals continue until death

### Fair Fee Calculation

`calculate_fair_fee()` uses bisection search to find the fee rate where
guarantee_cost = target_cost (default 0 for actuarial fair value).

### Sensitivity Analysis

`sensitivity_analysis()` computes:
- **Sigma sensitivity**: (price at 1.1*sigma - price at 0.9*sigma) / (0.2*sigma)
- **Rate sensitivity**: (price at r+1% - price at r-1%) / 2%
- **Age sensitivity**: (price at age+5 - base price) / 5

### Key Assumptions

| Assumption | Justification | Tier |
|------------|---------------|------|
| Risk-neutral pricing | No-arbitrage framework | T1 |
| GBM dynamics | Standard equity model | T1 |
| SOA 2012 IAM mortality | Industry-standard table (default) | T2 |
| Dynamic lapse model | Calibrated to experience studies | T3 |
| Behavioral withdrawal model | Age-dependent utilization | T3 |
| Annual expense model | Insurer cost assumptions | T3 |
| No regime switching | Single volatility regime | T3 |
| No policyholder optionality | No strategic exercise | T3 |

### References

- [T1] Bauer, Kling & Russ (2008). *A Universal Pricing Framework for Guaranteed Minimum Benefits in Variable Annuities*
- [T1] Hardy (2003). *Investment Guarantees*
- [T1] Glasserman (2003). *Monte Carlo Methods in Financial Engineering* (Ch. 3, 4)
- [T2] SOA 2018 GLWB Experience Study
- [T2] SOA 2012 IAM Mortality Table

## Validation Status

| Test | Purpose | Status |
|------|---------|--------|
| GBM drift test | Mean return = r - q under risk-neutral measure | Verified |
| Martingale test | E[S_T * e^(-rT)] = S_0 | Verified |
| Convergence rate | 1/sqrt(n) convergence verified | Verified |
| Ruin probability bounds | prob_ruin in [0, 1] and monotonic in sigma | Verified |
| Fee bisection convergence | Fair fee solver converges within tolerance | Verified |

### Cross-Validation

- GBM path generation validated against analytical moments
- No external library cross-validation for full GLWB pricing (path-dependent; no closed form)

## Limitations

- **Computationally intensive**: 10K paths x 35 years at annual steps; monthly steps require 12x more computation.
- **No variance reduction beyond antithetic**: Control variates, importance sampling not implemented for GLWB paths.
- **Single equity fund**: No multi-fund or asset allocation modeling.
- **GBM only**: No stochastic volatility (Heston) or regime-switching (RSLN) for path generation.
- **Behavioral models are T3**: Lapse, withdrawal, and expense assumptions are calibrated approximations, not market-observed.
- **No policyholder optionality**: Does not model strategic lapse or withdrawal optimization.
- **No partial withdrawals beyond utilization rate**: Full withdrawal amount or nothing per period.
- **Mortality is age-only**: No health state, underwriting class, or improvement factors.
- **Not suitable for regulatory reserves**: Use VM-21 modules for statutory calculations.

## Example Usage

```python
from annuity_pricing.glwb.path_sim import GLWBPathSimulator
from annuity_pricing.glwb.gwb_tracker import GWBConfig

config = GWBConfig(
    rollup_rate=0.05,
    withdrawal_rate=0.05,
    fee_rate=0.01,
)
sim = GLWBPathSimulator(config, n_paths=10000, seed=42)

result = sim.price(
    premium=100_000,
    age=65,
    r=0.04,
    sigma=0.18,
    max_age=100,
)
print(f"Guarantee price: ${result.price:,.2f}")
print(f"Guarantee cost: {result.guarantee_cost:.4%} of premium")
print(f"P(ruin): {result.prob_ruin:.2%}")
print(f"Mean ruin year: {result.mean_ruin_year:.1f}")
print(f"Standard error: ${result.standard_error:,.2f}")

# Fair fee calculation
fair_fee = sim.calculate_fair_fee(
    premium=100_000, age=65, r=0.04, sigma=0.18
)
print(f"Fair fee: {fair_fee:.4%}")
```

## See Also

- {class}`annuity_pricing.glwb.gwb_tracker.GWBTracker` -- GWB state tracking engine
- {class}`annuity_pricing.glwb.rollup` -- Rollup and ratchet mechanics
- {class}`annuity_pricing.behavioral.dynamic_lapse.DynamicLapseModel` -- Lapse modeling
- {class}`annuity_pricing.loaders.mortality.MortalityLoader` -- SOA mortality tables
- {doc}`fia` -- FIA pricer (simpler, no path dependence)
