# Golden Test Cases

Reference values from Hull (2018) and other authoritative sources for validation.

> **Note**: These test cases do not require optional dependencies (financepy, QuantLib).

## Black-Scholes (Hull Example 15.6)

**Parameters**:

| Parameter | Value | Description |
|-----------|-------|-------------|
| S | 42.00 | Spot price |
| K | 40.00 | Strike price |
| r | 10.0% | Risk-free rate |
| q | 0.0% | Dividend yield |
| σ | 20.0% | Volatility |
| T | 0.5 | Time to expiry (years) |

**Expected Values** [T1]:

| Output | Expected | Tolerance |
|--------|----------|-----------|
| Call Price | $4.76 | ±$0.01 |
| Put Price | $0.81 | ±$0.01 |

```python
from annuity_pricing.options.pricing.black_scholes import black_scholes_call, black_scholes_put

call = black_scholes_call(spot=42, strike=40, rate=0.10, dividend=0, volatility=0.20, time_to_expiry=0.5)
put = black_scholes_put(spot=42, strike=40, rate=0.10, dividend=0, volatility=0.20, time_to_expiry=0.5)

assert abs(call - 4.76) < 0.01, f"Call: {call}"
assert abs(put - 0.81) < 0.01, f"Put: {put}"
```

## Greeks (ATM Call)

**Parameters**: S=K=100, r=5%, σ=20%, T=1, q=0

| Greek | Expected | Tolerance |
|-------|----------|-----------|
| Delta | 0.6368 | ±0.01 |
| Gamma | 0.0188 | ±0.001 |
| Vega | 37.52 (per 100% vol) | ±0.5 |
| Theta | -6.41 (per year) | ±0.5 |

## Monte Carlo Convergence

**Test**: ATM European Call (S=K=100, r=5%, σ=20%, T=1)
**BS Price**: 10.45

| Paths | Expected Stderr | MC Range |
|-------|-----------------|----------|
| 10,000 | ~0.09 | 10.45 ± 0.18 |
| 100,000 | ~0.03 | 10.45 ± 0.06 |

## Put-Call Parity

$$C - P = S \cdot e^{-qT} - K \cdot e^{-rT}$$

For Hull 15.6 (q=0):
- C = 4.76
- P = 0.81
- C - P = 3.95
- S - K·e^(-rT) = 42 - 40·e^(-0.10·0.5) = 42 - 38.05 = 3.95 ✓

```python
import math
from annuity_pricing.options.pricing.black_scholes import black_scholes_call, black_scholes_put

S, K, r, T = 42, 40, 0.10, 0.5
C = black_scholes_call(S, K, r, 0, 0.20, T)
P = black_scholes_put(S, K, r, 0, 0.20, T)

parity_diff = abs((C - P) - (S - K * math.exp(-r * T)))
assert parity_diff < 1e-10, f"Put-call parity violation: {parity_diff}"
```

## Tolerance Guidelines

| Comparison Type | Tolerance | Reason |
|-----------------|-----------|--------|
| Same formula (BS vs financepy) | 1e-10 | Floating point only |
| Different conventions (QuantLib) | 1e-8 | Day count differences |
| Different methods (SABR vs pyfeng) | 1e-6 | Numerical approximations |
| MC vs analytical | 0.01 | Statistical variance |
| Textbook values | 0.01 | Rounding in source |

## Validation Notebooks

- [Black-Scholes vs financepy](https://github.com/brandonmbehring-dev/annuity-pricing/blob/main/notebooks/validation/options/black_scholes_vs_financepy.ipynb)
- [Monte Carlo vs BS](https://github.com/brandonmbehring-dev/annuity-pricing/blob/main/notebooks/validation/options/monte_carlo_vs_pyfeng.ipynb)
- [PV Correction Derivation](https://github.com/brandonmbehring-dev/annuity-pricing/blob/main/notebooks/validation/pv_correction_derivation.ipynb)
