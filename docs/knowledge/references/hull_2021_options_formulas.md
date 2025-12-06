# Textbook Summary: Hull (2021) - Key Formulas

**Tier**: L3 (Textbook Summary)
**Citation**: Hull, J. C. (2021). Options, Futures, and Other Derivatives (11th ed.). Pearson.
**Status**: [x] Acquired | [x] Summarized (Chapters 13, 14, 15, 19)

---

## Overview

The standard graduate-level textbook on derivatives pricing. This summary extracts key formulas from Chapters 13 (Binomial Trees), 14 (Wiener Processes), 15 (Black-Scholes-Merton), and 19 (Greek Letters).

---

## Chapter 13: Binomial Trees

### Single-Period Model

Up and down factors:
$$u = e^{\sigma\sqrt{\Delta t}}, \quad d = e^{-\sigma\sqrt{\Delta t}} = \frac{1}{u}$$

Risk-neutral probability:
$$p = \frac{e^{r\Delta t} - d}{u - d}$$

Option value:
$$f = e^{-r\Delta t}[pf_u + (1-p)f_d]$$

### Convergence to Black-Scholes

As $n \to \infty$ in binomial model:
$$c = S_0 N(d_1) - Ke^{-rT}N(d_2)$$

Where:
$$d_1 = \frac{\ln(S_0/K) + (r + \sigma^2/2)T}{\sigma\sqrt{T}}$$
$$d_2 = \frac{\ln(S_0/K) + (r - \sigma^2/2)T}{\sigma\sqrt{T}} = d_1 - \sigma\sqrt{T}$$

---

## Chapter 14: Wiener Processes and Itô's Lemma

### Wiener Process Properties

For $\Delta z = \epsilon\sqrt{\Delta t}$ where $\epsilon \sim N(0,1)$:

- Mean: $E[\Delta z] = 0$
- Variance: $Var[\Delta z] = \Delta t$
- Standard deviation: $\sqrt{\Delta t}$

### Geometric Brownian Motion

Stock price process:
$$\frac{dS}{S} = \mu \, dt + \sigma \, dW$$

Or equivalently:
$$dS = \mu S \, dt + \sigma S \, dW$$

Discrete approximation:
$$\frac{\Delta S}{S} = \mu \Delta t + \sigma \epsilon \sqrt{\Delta t}$$

### Itô's Lemma

For function $G(S, t)$ where $dS = a \, dt + b \, dW$:

$$dG = \left(\frac{\partial G}{\partial S}a + \frac{\partial G}{\partial t} + \frac{1}{2}\frac{\partial^2 G}{\partial S^2}b^2\right) dt + \frac{\partial G}{\partial S} b \, dW$$

**Application to $G = \ln S$**:
$$d(\ln S) = \left(\mu - \frac{\sigma^2}{2}\right)dt + \sigma \, dW$$

Therefore:
$$\ln S_T - \ln S_0 \sim N\left(\left(\mu - \frac{\sigma^2}{2}\right)T, \sigma^2 T\right)$$

---

## Chapter 15: Black-Scholes-Merton Model

### The Black-Scholes-Merton Formulas

**European Call**:
$$c = S_0 N(d_1) - Ke^{-rT}N(d_2)$$

**European Put**:
$$p = Ke^{-rT}N(-d_2) - S_0 N(-d_1)$$

Where:
$$d_1 = \frac{\ln(S_0/K) + (r + \sigma^2/2)T}{\sigma\sqrt{T}}$$
$$d_2 = d_1 - \sigma\sqrt{T}$$

### Interpretation of $N(d_1)$ and $N(d_2)$

- $N(d_2)$ = Risk-neutral probability that call will be exercised
- $S_0 N(d_1)$ = PV of expected asset price in risk-neutral world, conditional on exercise
- $Ke^{-rT}N(d_2)$ = PV of strike price times probability of payment

### Extensions

**With continuous dividend yield $q$**:
$$c = S_0 e^{-qT} N(d_1) - Ke^{-rT}N(d_2)$$
$$p = Ke^{-rT}N(-d_2) - S_0 e^{-qT} N(-d_1)$$

Where:
$$d_1 = \frac{\ln(S_0/K) + (r - q + \sigma^2/2)T}{\sigma\sqrt{T}}$$

**Currency options (Garman-Kohlhagen)**:
$$c = S_0 e^{-r_f T} N(d_1) - Ke^{-rT}N(d_2)$$

Where $r_f$ is the foreign risk-free rate.

### Put-Call Parity

**No dividends**:
$$c + Ke^{-rT} = p + S_0$$

**With dividends** (PV of dividends $D$):
$$c + D + Ke^{-rT} = p + S_0$$

**With continuous dividend yield $q$**:
$$c + Ke^{-rT} = p + S_0 e^{-qT}$$

### Bounds on Option Prices

**Call bounds** (no dividends):
$$\max(S_0 - Ke^{-rT}, 0) \leq c \leq S_0$$

**Put bounds** (no dividends):
$$\max(Ke^{-rT} - S_0, 0) \leq p \leq Ke^{-rT}$$

---

## Chapter 19: The Greek Letters

### Summary Table

| Greek | Symbol | Definition | Call Formula | Put Formula |
|-------|--------|------------|--------------|-------------|
| Delta | $\Delta$ | $\frac{\partial f}{\partial S}$ | $N(d_1)$ | $N(d_1) - 1$ |
| Gamma | $\Gamma$ | $\frac{\partial^2 f}{\partial S^2}$ | $\frac{N'(d_1)}{S_0\sigma\sqrt{T}}$ | Same |
| Theta | $\Theta$ | $\frac{\partial f}{\partial t}$ | See below | See below |
| Vega | $\mathcal{V}$ | $\frac{\partial f}{\partial \sigma}$ | $S_0\sqrt{T}N'(d_1)$ | Same |
| Rho | $\rho$ | $\frac{\partial f}{\partial r}$ | $KTe^{-rT}N(d_2)$ | $-KTe^{-rT}N(-d_2)$ |

Where:
$$N'(x) = \frac{1}{\sqrt{2\pi}}e^{-x^2/2}$$

### Delta ($\Delta$)

**Definition**: Rate of change of option price with respect to underlying asset price.

**European call (no dividends)**:
$$\Delta_{call} = N(d_1)$$

**European put (no dividends)**:
$$\Delta_{put} = N(d_1) - 1$$

**With dividend yield $q$**:
$$\Delta_{call} = e^{-qT}N(d_1)$$
$$\Delta_{put} = e^{-qT}(N(d_1) - 1)$$

**Delta-neutral portfolio**: Position with $\Delta = 0$.

**Dynamic hedging**: Maintain delta-neutral by rebalancing.

### Gamma ($\Gamma$)

**Definition**: Rate of change of delta with respect to asset price.

$$\Gamma = \frac{N'(d_1)}{S_0\sigma\sqrt{T}}$$

**For delta-neutral portfolio**:
$$\Delta\Pi \approx \Theta\Delta t + \frac{1}{2}\Gamma(\Delta S)^2$$

**Key insight**: High gamma means delta changes rapidly → frequent rebalancing needed.

**Gamma neutrality**: Requires trading options (not just underlying).

### Theta ($\Theta$)

**Definition**: Rate of change of option price with respect to time.

**European call (no dividends)**:
$$\Theta_{call} = -\frac{S_0 N'(d_1)\sigma}{2\sqrt{T}} - rKe^{-rT}N(d_2)$$

**European put (no dividends)**:
$$\Theta_{put} = -\frac{S_0 N'(d_1)\sigma}{2\sqrt{T}} + rKe^{-rT}N(-d_2)$$

**Note**: Theta is usually negative for long positions (time decay).

### Vega ($\mathcal{V}$)

**Definition**: Rate of change of option price with respect to volatility.

$$\mathcal{V} = S_0\sqrt{T}N'(d_1)$$

**Note**: Same formula for calls and puts.

**Key insight**: ATM options have highest vega; vega decreases as option moves ITM or OTM.

### Rho ($\rho$)

**Definition**: Rate of change of option price with respect to interest rate.

**European call**:
$$\rho_{call} = KTe^{-rT}N(d_2)$$

**European put**:
$$\rho_{put} = -KTe^{-rT}N(-d_2)$$

### Black-Scholes-Merton PDE

All derivatives on non-dividend-paying stock satisfy:
$$\frac{\partial f}{\partial t} + rS\frac{\partial f}{\partial S} + \frac{1}{2}\sigma^2 S^2 \frac{\partial^2 f}{\partial S^2} = rf$$

**In Greek notation**:
$$\Theta + rS\Delta + \frac{1}{2}\sigma^2 S^2 \Gamma = r\Pi$$

**For delta-neutral portfolio** ($\Delta = 0$):
$$\Theta + \frac{1}{2}\sigma^2 S^2 \Gamma = r\Pi$$

**Insight**: Large positive theta ↔ large negative gamma (and vice versa).

---

## Implementation

### Python: Black-Scholes with Greeks

```python
import numpy as np
from scipy.stats import norm

def black_scholes(
    S: float,
    K: float,
    r: float,
    sigma: float,
    T: float,
    q: float = 0.0,
    option_type: str = "call"
) -> dict:
    """
    Black-Scholes-Merton pricing with Greeks [T1: Hull 2021 Ch 15, 19].

    Parameters
    ----------
    S : Spot price
    K : Strike price
    r : Risk-free rate
    sigma : Volatility
    T : Time to maturity (years)
    q : Continuous dividend yield
    option_type : "call" or "put"

    Returns
    -------
    dict with keys: price, delta, gamma, theta, vega, rho
    """
    if T <= 0:
        if option_type == "call":
            return {"price": max(S - K, 0), "delta": 1.0 if S > K else 0.0,
                    "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0}
        else:
            return {"price": max(K - S, 0), "delta": -1.0 if S < K else 0.0,
                    "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0}

    sqrt_T = np.sqrt(T)

    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T

    # Standard normal PDF and CDF
    n_d1 = norm.pdf(d1)
    N_d1 = norm.cdf(d1)
    N_d2 = norm.cdf(d2)

    # Discount factors
    disc = np.exp(-r * T)
    div_disc = np.exp(-q * T)

    if option_type == "call":
        price = S * div_disc * N_d1 - K * disc * N_d2
        delta = div_disc * N_d1
        theta = (
            -S * div_disc * n_d1 * sigma / (2 * sqrt_T)
            - r * K * disc * N_d2
            + q * S * div_disc * N_d1
        )
        rho = K * T * disc * N_d2
    else:  # put
        N_neg_d1 = norm.cdf(-d1)
        N_neg_d2 = norm.cdf(-d2)
        price = K * disc * N_neg_d2 - S * div_disc * N_neg_d1
        delta = div_disc * (N_d1 - 1)
        theta = (
            -S * div_disc * n_d1 * sigma / (2 * sqrt_T)
            + r * K * disc * N_neg_d2
            - q * S * div_disc * N_neg_d1
        )
        rho = -K * T * disc * N_neg_d2

    # Same for calls and puts
    gamma = div_disc * n_d1 / (S * sigma * sqrt_T)
    vega = S * div_disc * sqrt_T * n_d1

    return {
        "price": price,
        "delta": delta,
        "gamma": gamma,
        "theta": theta / 365,  # Daily theta
        "vega": vega / 100,    # Per 1% vol change
        "rho": rho / 100       # Per 1% rate change
    }
```

### Python: Verify Put-Call Parity

```python
def verify_put_call_parity(
    S: float,
    K: float,
    r: float,
    sigma: float,
    T: float,
    q: float = 0.0,
    tol: float = 1e-10
) -> bool:
    """
    Verify put-call parity holds [T1: Hull 2021 Eq 11.6].

    c + Ke^(-rT) = p + S*e^(-qT)
    """
    call = black_scholes(S, K, r, sigma, T, q, "call")["price"]
    put = black_scholes(S, K, r, sigma, T, q, "put")["price"]

    lhs = call + K * np.exp(-r * T)
    rhs = put + S * np.exp(-q * T)

    return abs(lhs - rhs) < tol
```

---

## Test Cases (from Hull Examples)

### Example 19.1 (p. 401)

| Parameter | Value |
|-----------|-------|
| $S_0$ | $49 |
| $K$ | $50 |
| $r$ | 5% |
| $T$ | 20 weeks (0.3846 yr) |
| $\sigma$ | 20% |

**Expected results**:
- $d_1 = 0.0542$
- $\Delta = N(d_1) = 0.522$

### Example 19.4 (p. 410)

Same parameters as above.
**Expected**: $\Gamma = 0.066$

### Example 19.6 (p. 414)

Same parameters.
**Expected**: $\mathcal{V} = 12.1$ (per 100% vol change)

### Example 19.7 (p. 415)

Same parameters.
**Expected**: $\rho = 8.91$ (per 100% rate change)

---

## Relevance to annuity-pricing

**Direct applications**:
- `options/pricing/black_scholes.py` - Core BS implementation
- `options/greeks.py` - Greek letter calculations
- `products/rila.py` - Buffer options via put decomposition
- `products/fia.py` - Cap pricing via call spreads
- `valuation/hedging.py` - Dynamic hedging simulation

**Key implementation priorities**:
1. Core BS formula with all Greeks
2. Put-call parity verification
3. Extensions for dividend yield (FIA/RILA pricing)
4. Greeks-based hedging simulation

---

## Change Log

| Date | Change |
|------|--------|
| 2025-12-05 | Initial summary from PDF (Chapters 13, 14, 15, 19) |

