# Paper Summary: Black & Scholes (1973)

**Tier**: L3 (Paper Summary)
**Citation**: Black, F., & Scholes, M. (1973). The Pricing of Options and Corporate Liabilities. Journal of Political Economy, 81(3), 637-654.
**DOI**: 10.1086/260062
**Status**: [x] Acquired | [x] Summarized

---

## Key Contribution

Derives a closed-form valuation formula for European options using a no-arbitrage hedging argument. The key insight: a continuously rebalanced portfolio of stock and options creates a riskless position, so the expected return must equal the risk-free rate. This eliminates the need for subjective risk preferences or expected returns—**the option value depends only on observable parameters**.

---

## Context

**Problem addressed**: Prior formulas (Sprenkle 1961, Samuelson 1965) contained unknown parameters related to risk preferences and expected returns. No complete, preference-free valuation existed.

**Prior work**:
- Sprenkle (1961) - Formula with unknown risk parameters k, k*
- Samuelson (1965) - Expected return parameters α, β required
- Thorp & Kassouf (1967) - Empirical hedging but missed the equilibrium insight

**Key insight**: The hedged position is riskless → must earn risk-free rate → eliminates all preference parameters.

---

## Core Methodology

### Model Assumptions ("Ideal Conditions")

| Assumption | Description |
|------------|-------------|
| (a) | Short-term interest rate r is known and constant |
| (b) | Stock follows GBM: $dS = \mu S \, dt + \sigma S \, dW$, variance rate v² constant |
| (c) | No dividends |
| (d) | European option (exercise only at maturity) |
| (e) | No transaction costs |
| (f) | Can borrow/lend at rate r |
| (g) | No short-selling restrictions |

### Hedging Argument

1. **Hedged position**: Long 1 share of stock, short $1/w_1(x,t)$ options
   - $w_1 = \partial w / \partial x$ (delta)

2. **Value of equity in hedged position**:
   $$x - w/w_1$$

3. **Change in equity** (using Itô's lemma):
   $$\Delta w = w_1 \Delta x + \frac{1}{2} w_{11} v^2 x^2 \Delta t + w_2 \Delta t$$

4. **Riskless position** → return = $r \Delta t$

5. **Result**: The Black-Scholes PDE

---

## Key Equations

### Equation 1: Black-Scholes PDE (Eq. 7)

$$w_2 = rw - rxw_1 - \frac{1}{2}v^2 x^2 w_{11}$$

Or in modern notation:
$$\frac{\partial V}{\partial t} + rS\frac{\partial V}{\partial S} + \frac{1}{2}\sigma^2 S^2 \frac{\partial^2 V}{\partial S^2} = rV$$

**Interpretation**: The option value satisfies a partial differential equation that is independent of the stock's expected return μ.

**Boundary condition** (call at maturity):
$$w(x, t^*) = \max(x - c, 0)$$

---

### Equation 2: Black-Scholes Call Formula (Eq. 13)

$$w(x,t) = xN(d_1) - ce^{r(t-t^*)}N(d_2)$$

Where:
$$d_1 = \frac{\ln(x/c) + (r + \frac{1}{2}v^2)(t^* - t)}{v\sqrt{t^* - t}}$$

$$d_2 = \frac{\ln(x/c) + (r - \frac{1}{2}v^2)(t^* - t)}{v\sqrt{t^* - t}}$$

**Modern notation** (using $S$, $K$, $T$, $\sigma$):
$$C = SN(d_1) - Ke^{-rT}N(d_2)$$

$$d_1 = \frac{\ln(S/K) + (r + \frac{1}{2}\sigma^2)T}{\sigma\sqrt{T}}$$

$$d_2 = d_1 - \sigma\sqrt{T}$$

**Variable mapping**:
| Paper | Modern | Meaning |
|-------|--------|---------|
| $x$ | $S$ | Stock price |
| $c$ | $K$ | Strike price |
| $t^* - t$ | $T$ | Time to maturity |
| $v$ | $\sigma$ | Volatility (std dev of return) |
| $v^2$ | $\sigma^2$ | Variance rate |
| $r$ | $r$ | Risk-free rate |

---

### Equation 3: Delta (Eq. 14)

$$w_1(x,t) = N(d_1)$$

**Interpretation**: The number of shares needed to hedge one option. Also, the sensitivity of option price to stock price.

---

### Equation 4: Put-Call Parity (Eq. 25)

$$w(x,t) - u(x,t) = x - ce^{r(t-t^*)}$$

**Modern notation**:
$$C - P = S - Ke^{-rT}$$

**Interpretation**: Long call + short put = long stock + borrowing K at maturity.

---

### Equation 5: European Put Formula (Eq. 27)

$$u(x,t) = -xN(-d_1) + ce^{r(t-t^*)}N(-d_2)$$

**Modern notation**:
$$P = Ke^{-rT}N(-d_2) - SN(-d_1)$$

---

## Key Insights

### 1. Risk-Neutral Pricing (implicit)

The formula prices the option as if the stock earned the risk-free rate:
- Replace μ with r in the stock process
- Expected payoff under this "risk-neutral measure"
- Discount at r

This insight was later formalized by Cox & Ross (1976) and Harrison & Kreps (1979).

### 2. Option Properties

| Property | Effect on Call Value |
|----------|---------------------|
| Higher S | Increases |
| Higher K | Decreases |
| Higher T | Increases |
| Higher σ | Increases |
| Higher r | Increases |

### 3. Options More Volatile Than Stock

$$\frac{xw_1}{w} > 1 \quad \text{always}$$

The "elasticity" or leverage of the option exceeds 1.

### 4. American vs European Calls

Merton (1973) showed: American call = European call value (for non-dividend stocks).

Early exercise is never optimal because $w(x,t) > x - c$ always.

### 5. American vs European Puts

American put > European put. Early exercise CAN be optimal for puts (when stock near zero).

---

## Corporate Liabilities Application

The paper's profound extension: **almost all corporate liabilities are combinations of options**.

### Common Stock as a Call Option

Stockholders own a call option on the firm's assets:
- $x$ = total firm value
- $c$ = face value of debt
- Payoff at maturity: $\max(V - D, 0)$

### Corporate Bonds

Bond value = Firm value - Equity value = $x - w(x,t)$

**Default risk** = risk that firm value falls below debt face value.

### Key Corporate Finance Implications

1. **More debt → lower bond prices**: Increased default probability
2. **Higher dividends → lower bond prices**: Transfers value from bondholders
3. **Higher volatility → lower bond prices**: More default risk
4. **Callable bonds**: Additional option for stockholders

---

## Limitations Acknowledged

| Limitation | Paper's Discussion |
|------------|-------------------|
| Constant volatility | Acknowledged; v² may change over time |
| No dividends | Complicates analysis; early exercise possible |
| European only | American put formula not derived |
| Constant interest rate | Addressed by Merton (1973) extension |
| Compound options | Cannot handle (options on options) |

---

## Validation

**Test cases from paper** (Section: Empirical Tests):

The authors tested on call option data (Black & Scholes 1972):
- Option buyers pay prices **higher** than formula predicts
- Option writers receive prices **at** formula level
- Discrepancy larger for low-volatility stocks
- Transaction costs explain most deviation

**Modern validation approach**:

| Test | Parameters | Expected |
|------|------------|----------|
| ATM call | S=100, K=100, r=5%, σ=20%, T=1 | C ≈ 10.45 |
| Deep ITM | S=120, K=100, r=5%, σ=20%, T=1 | C ≈ 25.10 |
| Deep OTM | S=80, K=100, r=5%, σ=20%, T=1 | C ≈ 2.85 |
| Put-call parity | Verify C - P = S - Ke^(-rT) | Exact |

---

## Relevance to annuity-pricing

**Applicable to**:
- `options/pricing/black_scholes.py` - Core implementation
- `products/rila.py` - RILA buffer/floor decomposition into puts
- `products/fia.py` - Cap pricing as call spread
- `validation/arbitrage.py` - Put-call parity checks

**Implementation priorities**:
1. Core BS formula with Greeks
2. Put-call parity enforcement
3. Bounds checking (option < underlying)
4. Extension to dividends (via Merton 1973)

**Implementation status**: [ ] Not started

---

## Implementation Notes

### Python Implementation Pattern

```python
from scipy.stats import norm
import numpy as np

def black_scholes_call(S: float, K: float, r: float, sigma: float, T: float) -> float:
    """
    Black-Scholes call option price [T1].

    Parameters match paper notation:
    - S (paper: x) = spot price
    - K (paper: c) = strike price
    - r = risk-free rate (annual)
    - sigma (paper: v) = volatility (annual)
    - T (paper: t* - t) = time to maturity (years)
    """
    if T <= 0:
        return max(S - K, 0)

    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    call = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    return call

def black_scholes_put(S: float, K: float, r: float, sigma: float, T: float) -> float:
    """Black-Scholes put via put-call parity [T1]."""
    call = black_scholes_call(S, K, r, sigma, T)
    return call - S + K * np.exp(-r * T)
```

### Validation Test Cases

```python
# Hull textbook examples (Chapter 15)
def test_bs_known_answers():
    # ATM call
    C = black_scholes_call(S=42, K=40, r=0.10, sigma=0.20, T=0.5)
    assert abs(C - 4.76) < 0.01  # Hull example

    # Put-call parity
    call = black_scholes_call(S=100, K=100, r=0.05, sigma=0.20, T=1.0)
    put = black_scholes_put(S=100, K=100, r=0.05, sigma=0.20, T=1.0)
    assert abs((call - put) - (100 - 100*np.exp(-0.05))) < 1e-10
```

---

## Notes

1. **This is THE foundational paper** for all derivative pricing
2. The PDE approach was revolutionary—connects to heat equation via substitution
3. Risk-neutral pricing was implicit; made explicit by later work
4. Greeks (delta, gamma, theta, vega, rho) derived by differentiation
5. Extensions: dividends (Merton 1973), stochastic vol (Heston 1993), jumps (Merton 1976)

---

## Related Papers

| Paper | Contribution |
|-------|--------------|
| Merton (1973) | Continuous dividends, American options |
| Cox & Ross (1976) | Risk-neutral valuation explicit |
| Cox, Ross & Rubinstein (1979) | Binomial tree method |
| Hull & White (1987) | Stochastic volatility |
| Heston (1993) | Closed-form stochastic vol |

---

## Change Log

| Date | Change |
|------|--------|
| 2025-12-05 | Initial comprehensive summary from PDF |

