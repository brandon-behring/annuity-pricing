# Option Pricing Quick Reference

**Tier**: [T1] Academic | **Source**: Black & Scholes (1973), Hull (2021)

---

## Black-Scholes Formula

### European Call [T1]

```
C = S × e^(-qT) × N(d₁) - K × e^(-rT) × N(d₂)
```

### European Put [T1]

```
P = K × e^(-rT) × N(-d₂) - S × e^(-qT) × N(-d₁)
```

### d₁ and d₂ [T1]

```
d₁ = [ln(S/K) + (r - q + σ²/2)T] / (σ√T)

d₂ = d₁ - σ√T
```

### Variables

| Symbol | Meaning | Units |
|--------|---------|-------|
| S | Spot price | $ |
| K | Strike price | $ |
| r | Risk-free rate | Decimal (e.g., 0.05 = 5%) |
| q | Dividend yield | Decimal |
| σ | Volatility | Decimal (annualized) |
| T | Time to maturity | Years |
| N(x) | Standard normal CDF | - |

---

## Put-Call Parity [T1]

```
C - P = S × e^(-qT) - K × e^(-rT)
```

**Verification**: Any BS implementation MUST satisfy this identity to within numerical precision (< 0.01).

---

## No-Arbitrage Bounds [T1]

| Option | Lower Bound | Upper Bound |
|--------|-------------|-------------|
| Call | max(S×e^(-qT) - K×e^(-rT), 0) | S |
| Put | max(K×e^(-rT) - S×e^(-qT), 0) | K×e^(-rT) |

**HALT Trigger**: Any violation indicates implementation error.

---

## Greeks [T1]

| Greek | Formula | Interpretation |
|-------|---------|----------------|
| **Delta (Δ)** | ∂V/∂S | Price change per $1 move in underlying |
| **Gamma (Γ)** | ∂²V/∂S² | Rate of delta change |
| **Vega (ν)** | ∂V/∂σ | Price change per 1% vol change |
| **Theta (Θ)** | ∂V/∂t | Time decay per day |
| **Rho (ρ)** | ∂V/∂r | Price change per 1% rate change |

### Call Greeks [T1]

```
Δ_call = e^(-qT) × N(d₁)
Γ = e^(-qT) × n(d₁) / (S × σ × √T)
ν = S × e^(-qT) × n(d₁) × √T
Θ_call = -(S × e^(-qT) × n(d₁) × σ)/(2√T) + q×S×e^(-qT)×N(d₁) - r×K×e^(-rT)×N(d₂)
ρ_call = K × T × e^(-rT) × N(d₂)
```

Where n(x) = standard normal PDF = (1/√2π) × e^(-x²/2)

---

## Forward Price [T1]

```
F = S × e^((r-q)T)
```

Used for building index forwards in FIA/RILA pricing.

---

## Hull Textbook Examples (Ch.15)

### Example 1: Call Pricing

| Input | Value |
|-------|-------|
| S | 42 |
| K | 40 |
| r | 0.10 |
| σ | 0.20 |
| T | 0.5 |
| q | 0 |

**Expected Call Price**: 4.76

### Example 2: Put Pricing

Same inputs as above.

**Expected Put Price**: 0.81

**Verification**: C - P = 42 - 40×e^(-0.10×0.5) = 4.76 - 0.81 = 3.95 ✓

---

## Python Implementation Pattern

```python
from scipy.stats import norm
import numpy as np

def bs_call(S: float, K: float, r: float, q: float, sigma: float, T: float) -> float:
    """
    Black-Scholes European call price. [T1]

    Reference: Hull Ch.15
    """
    if T <= 0:
        return max(S - K, 0)

    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    return S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
```

---

## References

- Black, F., & Scholes, M. (1973). The pricing of options and corporate liabilities. *Journal of Political Economy*.
- Hull, J. C. (2021). *Options, Futures, and Other Derivatives* (11th ed.). Chapter 15.
