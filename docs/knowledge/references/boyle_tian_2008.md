# Paper Summary: Boyle & Tian (2008)

**Tier**: L3 (Paper Summary)
**Citation**: Boyle, P., & Tian, W. (2008). The Design of Equity-Indexed Annuities. Insurance: Mathematics and Economics, 43(3), 303-315.
**DOI**: 10.1016/j.insmatheco.2008.05.006
**Status**: [x] Acquired | [x] Summarized

---

## Key Contribution

Analyzes equity-indexed annuities (EIAs) from the **investor's perspective** rather than the issuer's. Shows that conventional EIA designs are generally **not optimal** for investors. Proposes a "generalized EIA" that combines a guaranteed return with a probabilistic constraint on beating a benchmark index.

---

## Context

**Problem addressed**: Most actuarial literature focuses on EIA pricing/hedging from the issuer's perspective. This paper asks: "Is the conventional EIA design optimal for the consumer?"

**Prior work**:
- Black & Scholes (1973), Merton (1973) - Fair premium approach
- Brennan & Schwartz (1976) - Equity-linked life insurance pricing
- Hardy (2003) - Investment guarantees
- Cox & Huang (1989), Merton (1971) - Optimal portfolio selection

**Answer**: No—conventional EIAs are generally inefficient for investors with standard utility functions.

---

## Core Methodology

### Market Setup

Stock follows GBM under real-world measure $P$:
$$\frac{dS}{S} = \mu \, dt + \sigma \, dW(t)$$

Where:
- $\mu$ = drift (expected return)
- $\sigma$ = volatility
- $r$ = risk-free rate
- $\mu > r$ assumed

### State-Price Density

Under log-normal assumption:
$$\xi_T = a \left(\frac{S_T}{S_0}\right)^{-b}$$

Where:
$$a = \exp\left[\frac{\theta}{\sigma}\left(\mu - \frac{1}{2}\sigma^2\right)T - \left(r + \frac{1}{2}\theta^2\right)T\right]$$
$$b = \frac{\theta}{\sigma}, \quad \theta = \frac{\mu - r}{\sigma}$$

---

## EIA Product Structures Analyzed

### Point-to-Point EIA (Main Example)

**Payoff**:
$$\Gamma = \max\left(x_0 e^{gT}, x_0 \left(\frac{S_T}{S_0}\right)^k\right)$$

Where:
- $x_0$ = initial premium
- $g$ = guaranteed rate
- $k$ = participation rate
- $T$ = contract term

**No-arbitrage value**:
$$y_0 = E[\xi_T \Gamma]$$

**Investor loss** (if premium exceeds fair value):
$$\text{Loss \%} = 1 - \frac{y_0}{x_0}$$

---

### Other EIA Types

| Type | Payoff Formula |
|------|----------------|
| **Cap & Floor** | $\Gamma = x_0 \max\left(e^{gT}, \min\left(\left(\frac{S_T}{S_0}\right)^k, e^{cT}\right)\right)$ |
| **Monthly Cap** | Return = $\max\left(g, k\sum_{i=1}^N \min\left(\frac{1}{T_i-T_{i-1}}\log\frac{S(T_i)}{S(T_{i-1})}, c\right)\right)$ |
| **High Water Mark** | $\Gamma = x_0 \left(\frac{\max S_t}{S_0}\right)^k$ |
| **Ratchet (Cliquet)** | $\Gamma = x_0 \prod_{i=1}^n \max\left(e^g, \left(\frac{S_{t_i}}{S_{t_{i-1}}}\right)^k\right)$ |

---

## Key Equations

### Equation 1: Trade-off Between k and g (Eq. 2.8)

For a "break-even" point-to-point EIA where $x_0 = y_0$:

$$e^{\hat{g}T}\Phi(\alpha) + e^{\hat{k}T(r + \frac{\hat{k}-1}{2}\sigma^2)}\Phi(-\alpha + \hat{k}\sigma\sqrt{T}) = e^{rT}$$

Where:
$$\alpha = \frac{g - k(r - \frac{1}{2}\sigma^2)}{k\sigma\sqrt{T}}$$

**Interpretation**: Higher guarantee $g$ → lower participation $k$.

**Example** (T=5, r=4%, σ=20%):
- $\hat{g} = 2\%$ → $\hat{k} = 60.22\%$
- $\hat{g} = 3\%$ → $\hat{k} = 48.6\%$

---

### Equation 2: Merton Optimal Wealth (Eq. 3.10)

Without constraints:
$$X_T^* = I(\lambda^m \xi_T)$$

Where:
- $I(\cdot) = (u')^{-1}$ = inverse marginal utility
- $\lambda^m$ solves $E[\xi_T I(\lambda^m \xi_T)] = x_0$

For log utility $u(x) = \log(x)$:
$$X_T^* = \frac{x_0}{a}\left(\frac{S_T}{S_0}\right)^b$$

---

### Equation 3: Optimal Wealth with Guarantee (Eq. 3.12)

With constraint $X_T \geq x_0 e^{gT}$:
$$X_T^* = \max\{I(\lambda^g \xi_T), x_0 e^{gT}\}$$

Where $\lambda^g > \lambda^m$ (guarantee reduces expected utility).

---

### Equation 4: Optimal Design Given EIA Benchmark (Eq. 3.19)

If investor wants payoff $\geq$ EIA payoff $\Gamma$:
$$X_T^* = \max\left(I(\lambda^g \xi_T), x_0 e^{gT}, x_0\left(\frac{S_T}{S_0}\right)^k\right)$$

**Key Result**: Current EIA payoff $\Gamma$ is NOT optimal for most investors.

---

### Theorem 3.1: General Optimal Design

For any benchmark $\Gamma$ with $E[\xi_T \Gamma] < x_0$:

$$X_T^{eia} = \max\{I(\lambda^g \xi_T), \Gamma\}$$

Where $\lambda^g$ satisfies:
$$E[\xi_T \max\{I(\lambda^g \xi_T), \Gamma\}] = x_0$$

**Present value of investor's loss**:
$$E[\xi_T(X_T^* - \Gamma)] = x_0 - y_0$$

---

## The Generalized EIA

### Innovation

A new contract type with **two constraints**:

1. **Minimum guarantee**: $X_T \geq x_0 e^{gT}$
2. **Probabilistic benchmark**: $P(X_T \geq \Gamma) \geq \alpha$

This allows higher participation rates at the cost of probabilistic (not certain) benchmark beating.

### Motivation

- Investors want safety BUT also high returns
- Can't have both with certainty (no-arbitrage)
- Probabilistic constraint allows trade-off: higher participation with probability $\alpha$

### Example Comparison

| Contract Type | Participation Rate | Benchmark Beat Probability |
|---------------|-------------------|---------------------------|
| Conventional EIA | $k = 60.22\%$ | 100% |
| Generalized EIA | $k = 75\%$ | 85% |

---

### Theorem 4.1: Optimal Generalized EIA

Under technical assumptions, the optimal payoff has form:

$$X^{geqp}(T) = X_{\lambda^*, \alpha}(T)$$

Where $X_{\lambda, \alpha}(T)$ depends on comparing:
- $I(\lambda\xi_T)$ vs $\Gamma$ vs $fx_0$
- Auxiliary function $h(\lambda, \xi_T)$ vs threshold $d(\lambda, \alpha)$

**Key feature**: Payoff may be **discontinuous** and **non-monotonic** in index level.

---

## Numerical Examples

### Parameters Used

| Parameter | Value |
|-----------|-------|
| $x_0$ | 1 |
| $S_0$ | 1 |
| $T$ | 5 years |
| $\mu$ | 6% |
| $\sigma$ | 20% |
| $r$ | 4% |
| $g$ | 2% |

### Risk Aversion Impact

For CRRA utility $u(x) = \frac{x^{1-\gamma}}{1-\gamma}$:

| $\gamma$ | Loss when index doubles |
|----------|------------------------|
| 1 (log) | Small |
| 2 | ~20% |
| 3 | ~45% |

**Insight**: More risk-averse investors suffer larger losses from inefficient EIA design.

---

## Implementation Implications

### For Product Design

1. **EIAs are not optimal** for most investor utility functions
2. **Only one specific risk aversion** makes a given EIA optimal
3. **Issuers should offer multiple EIAs** with different $(k, g)$ pairs
4. **Higher guarantee = lower participation** (fundamental trade-off)

### For Valuation

**Point-to-point EIA no-arbitrage value** (Eq. 2.6):
$$y_0 = e^{(g-r)T}x_0\Phi(\alpha) + x_0 e^{(k-1)rT + \frac{1}{2}k(k-1)\sigma^2 T}\Phi(-\alpha + k\sigma\sqrt{T})$$

### For Risk Management

- Generalized EIA payoffs have **discontinuities** → hedging challenges
- Similar to barrier options in complexity
- Transaction costs and trading restrictions matter

---

## Validation

**Test case from paper** (Figure 1):

| g | Maximum k (break-even) |
|---|----------------------|
| 0% | ~65% |
| 2% | 60.22% |
| 3% | 48.6% |
| 3.75% | ~30% |

**Reproduce with**: Solve Eq. 2.8 numerically.

---

## Relevance to annuity-pricing

**Applicable to**:
- `products/fia.py` - FIA crediting strategy analysis
- `products/rila.py` - RILA participation/cap trade-offs
- `valuation/fia_pv.py` - Embedded option valuation
- `competitive/positioning.py` - Fair value vs market rates

**Implementation priorities**:
1. Point-to-point EIA valuation formula (Eq. 2.6)
2. Trade-off curve computation (Eq. 2.8)
3. Loss percentage calculator
4. Optimal design comparison tools

**Implementation status**: [ ] Not started

---

## Implementation Notes

### Python: Point-to-Point EIA Valuation

```python
import numpy as np
from scipy.stats import norm

def eia_point_to_point_value(
    x0: float,      # Initial premium
    g: float,       # Guaranteed rate (annual)
    k: float,       # Participation rate
    r: float,       # Risk-free rate
    sigma: float,   # Volatility
    T: float        # Term (years)
) -> float:
    """
    No-arbitrage value of point-to-point EIA [T1].

    Based on Boyle & Tian (2008) Equation 2.6.
    """
    alpha = (g - k * (r - 0.5 * sigma**2)) / (k * sigma * np.sqrt(T))

    term1 = np.exp((g - r) * T) * x0 * norm.cdf(alpha)
    term2 = x0 * np.exp((k - 1) * r * T + 0.5 * k * (k - 1) * sigma**2 * T) * norm.cdf(-alpha + k * sigma * np.sqrt(T))

    return term1 + term2

def eia_loss_percentage(x0: float, y0: float) -> float:
    """Loss to investor when premium exceeds fair value."""
    return 1 - y0 / x0
```

### Python: Break-Even Trade-off Solver

```python
from scipy.optimize import brentq

def find_break_even_participation(
    g: float,       # Guaranteed rate
    r: float,       # Risk-free rate
    sigma: float,   # Volatility
    T: float        # Term
) -> float:
    """
    Find participation rate k such that fair value = premium.

    Solves Equation 2.8 from Boyle & Tian (2008).
    """
    def objective(k):
        alpha = (g - k * (r - 0.5 * sigma**2)) / (k * sigma * np.sqrt(T))
        lhs = np.exp(g * T) * norm.cdf(alpha) + np.exp(k * T * (r + (k - 1) / 2 * sigma**2)) * norm.cdf(-alpha + k * sigma * np.sqrt(T))
        rhs = np.exp(r * T)
        return lhs - rhs

    # Search in reasonable range
    k_hat = brentq(objective, 0.01, 2.0)
    return k_hat
```

---

## Key Insights

### 1. Investor Perspective Matters
Most EIA literature focuses on issuer pricing/hedging. This paper shows that consumer welfare analysis reveals design inefficiencies.

### 2. Guarantees Reduce Expected Utility
Adding a guarantee constraint always reduces the investor's expected utility relative to unconstrained Merton solution.

### 3. Risk Aversion Determines Optimal Contract
Different investors (different $\gamma$) prefer different $(k, g)$ combinations. One-size-fits-all EIAs are suboptimal.

### 4. Probabilistic Constraints Enable Higher Participation
The generalized EIA trades certainty for higher participation rates—may appeal to some investors.

### 5. Commission Impact
Paper notes average EIA first-year commissions ~8% of premium (Palmer 2006), directly reducing investor value.

---

## Limitations

| Limitation | Paper's Treatment |
|------------|-------------------|
| Constant volatility | Acknowledged; extensions possible |
| No mortality/surrender | Noted as future work |
| Complete markets | Required for closed-form solutions |
| Hedging challenges | Discontinuous payoffs acknowledged |

---

## Related Papers

| Paper | Contribution |
|-------|--------------|
| Tiong (2000) | EIA valuation formulas |
| Hardy (2003) | Investment guarantees textbook |
| Moore & Young (2005) | Perpetual EIA optimal design |
| Brennan & Schwartz (1976) | Equity-linked life insurance |

---

## Change Log

| Date | Change |
|------|--------|
| 2025-12-05 | Initial comprehensive summary from PDF |

