# Textbook Summary: Hardy (2003) Investment Guarantees

**Tier**: L3 (Textbook Summary)
**Citation**: Hardy, M. R. (2003). Investment Guarantees: Modeling and Risk Management for Equity-Linked Life Insurance. John Wiley & Sons.
**Status**: [x] Acquired | [x] Summarized

---

## Overview

Comprehensive treatment of pricing and risk management for equity-linked insurance products with embedded guarantees. Covers GMMB, GMDB, GAO/GMIB, and EIA contracts. Key contribution: bridges actuarial and financial engineering approaches.

---

## Part I: Stock Return Models (Chapters 2-5)

### Lognormal Model

Standard assumption: stock returns follow geometric Brownian motion.

$$\frac{S_{t+w}}{S_t} \sim LN(w\mu, \sqrt{w}\sigma)$$

**MLE Parameters** (Table 2.1):
| Index | Period | $\mu$ (monthly) | $\sigma$ (monthly) |
|-------|--------|-----------------|-------------------|
| TSE 300 | 1956-2000 | 0.0075 | 0.0434 |
| S&P 500 | 1956-2000 | 0.0093 | 0.0414 |

**Limitation**: Fails to capture volatility clustering and fat tails.

### Regime-Switching Lognormal (RSLN) Model

**Two-regime model** (recommended):

$$Y_t | \rho_t \sim N(\mu_{\rho_t}, \sigma^2_{\rho_t})$$

Where $\rho_t \in \{1, 2\}$ follows a Markov chain with transition probabilities $p_{12}$ and $p_{21}$.

**MLE Parameters** (Table 2.2 - S&P 500 1956-2000):
| Regime | $\mu$ | $\sigma$ | $p_{ij}$ |
|--------|-------|----------|----------|
| 1 (normal) | 0.0123 | 0.0345 | $p_{12} = 0.0398$ |
| 2 (volatile) | -0.0157 | 0.0775 | $p_{21} = 0.2083$ |

**Interpretation**: Regime 1 is persistent (low vol), Regime 2 is transient (high vol, negative mean).

### GARCH(1,1) Model

$$Y_t = \mu + \sigma_t \epsilon_t$$
$$\sigma_t^2 = \alpha_0 + \alpha_1(Y_{t-1} - \mu)^2 + \beta \sigma_{t-1}^2$$

Captures volatility clustering but assumes single regime.

---

## Part II: Guarantee Liability Modeling (Chapter 6)

### Key Variables

| Variable | Definition |
|----------|------------|
| $F_t$ | Fund value at time $t$ |
| $G$ | Guarantee level |
| $m$ | Management expense ratio (monthly) |
| $m_c$ | Margin offset (risk charge portion) |
| $S_t$ | Stock index accumulation factor |

### Fund Evolution

$$F_t = F_0^- \frac{S_t (1-m)^t}{S_0}$$

### GMMB Cash Flows

Margin offset income (monthly):
$$M_t = m_c F_0^- \frac{S_t (1-m)^t}{S_0}$$

Net liability cash flow at maturity:
$$C_n = -{}_{n}p_x^\tau (G - F_n)^+$$

### GMDB Cash Flows

$$C_t = -{}_{t}p_x^\tau M_t + {}_{t-1|1}q_x^d (G - F_t)^+$$

### Present Value of Liability

$$L_0 = \sum_{t=0}^{n} C_t e^{-rt}$$

---

## Part III: Risk Measures (Chapter 9)

### Quantile Risk Measure (VaR)

$$V_\alpha = \inf\{x : F_{L_0}(x) \geq \alpha\}$$

**Limitation**: Not coherent; ignores tail shape beyond quantile.

### Conditional Tail Expectation (CTE)

$$CTE_\alpha(L_0) = E[L_0 | L_0 > V_\alpha]$$

**Estimation from simulation** (Eq. 9.10):
$$\widetilde{CTE}_\alpha(L_0) = \frac{1}{N(1-\alpha)} \sum_{j=N\alpha+1}^{N} L_0^{(j)}$$

Where $L_0^{(j)}$ is the $j$-th smallest simulated loss.

### Standard Error of CTE

Approximate (biased low):
$$SE \approx \frac{SD(L^{(j)} : j > N\alpha)}{\sqrt{N(1-\alpha)}}$$

### CTE for GMMB (Exact Formula)

For $\alpha \geq \xi$ where $\xi = Pr[F_n > G]$:

$$CTE_\alpha(L) = e^{-rn}\left(G - \frac{e^{n(\mu + \log(1-m) + \sigma^2/2)}}{1-\alpha} \Phi(-z_\alpha - \sqrt{n}\sigma)\right)$$

### Coherence Properties

CTE satisfies all coherence criteria:
1. Bounded above by max loss
2. Bounded below by mean loss
3. Scalar additive/multiplicative
4. **Subadditive**: $CTE[X+Y] \leq CTE[X] + CTE[Y]$

**Regulatory adoption**: Canadian OSFI uses CTE80% for reserves, CTE95% for solvency capital.

---

## Part IV: Dynamic Hedging (Chapter 8)

### Black-Scholes Hedge

For GMMB with guarantee $G$:
$$H(t) = -G e^{-r(n-t)} \Phi(-d_2) + F_t \Phi(-d_1)$$

Where:
$$d_1 = \frac{\log(F_t/G) + (r + \sigma^2/2)(n-t)}{\sigma\sqrt{n-t}}$$
$$d_2 = d_1 - \sigma\sqrt{n-t}$$

### Hedge Components

| Component | Formula | Interpretation |
|-----------|---------|----------------|
| Stock position | $\Psi_t = -\Phi(-d_1)$ | Delta hedge |
| Bond position | $\Omega_t = G e^{-r(n-t)} \Phi(-d_2)$ | Discount factor |

### Hedging Error Sources

1. **Discrete rebalancing**: Monthly vs continuous
2. **Model error**: RSLN reality vs BS assumption
3. **Transaction costs**: ~0.2% of equity trades

### Hedging Error Formula

At time $t$:
$$HE_t = H(t) - H(t^-)$$

Where $H(t^-)$ is hedge brought forward without rebalancing.

### Life-Contingent Adjustment

Unconditional hedging error:
$$HE_t = H(t) - H(t^-) \times {}_{t-1}p_x^\tau$$

---

## Part V: Equity-Indexed Annuities (Chapter 13)

### Contract Structure

- **Guarantee**: $G = 0.95 P (1.03)^n$ (95% of premium at 3% guaranteed)
- **Equity participation**: Additional payout based on index performance
- **Typical term**: 5-10 years (commonly 7)

### Point-to-Point (PTP) Design

**Payoff**:
$$H = P\left(1 + \alpha\left(\frac{S_n}{S_0} - 1\right)\right)^+ - G$$

**Valuation** (Eq. 13.7):
$$H_0 = \alpha P e^{-dn} \Phi(d_1) - (G - P(1-\alpha)) e^{-rn} \Phi(d_2)$$

Where:
$$d_1 = \frac{\log(\alpha P / (G - P(1-\alpha))) + (r - d + \sigma^2/2)n}{\sigma\sqrt{n}}$$

**Break-even participation rates** (Table 13.1, 2% spread):
| $\sigma$ | Participation $\alpha$ |
|----------|----------------------|
| 20% | 81.3% |
| 25% | 70.5% |
| 30% | 62.1% |

### Compound Annual Ratchet (CAR) Design

**Payoff**:
$$RP = P \prod_{t=1}^{n} \left(1 + \max\left(\alpha\left(\frac{S_t}{S_{t-1}} - 1\right), 0\right)\right)$$

**Valuation** (without cap, Eq. 13.16):
$$H = P\left(e^{-r} + \alpha(e^{-d}\Phi(d_1) - e^{-r}\Phi(d_2))\right)^n$$

**With cap $c$ and floor $g$** (Eq. 13.25):
$$P\left(\alpha e^{-d}(\Phi(d_1) - \Phi(d_3)) + (1-\alpha)e^{-r}(\Phi(d_2) - \Phi(d_4)) + e^{g-r}\Phi(-d_2) + e^{c-r}\Phi(d_4)\right)^n$$

### Simple Annual Ratchet (SAR) Design

**Payoff**:
$$P\left(1 + \sum_{t=1}^{n} \max\left(\alpha\left(\frac{S_t}{S_{t-1}} - 1\right), 0\right)\right)$$

**Key difference**: Cheaper than CAR because simple vs compound accumulation.

### High Water Mark (HWM) Design

**Payoff**:
$$P\left(1 + \alpha\left(\frac{S_{max}}{S_0} - 1\right)\right)$$

Where $S_{max} = \max(S_0, S_1, \ldots, S_n)$.

**Most expensive** design due to lookback feature.

### Comparison of Break-Even Participation Rates (Table 13.7)

| Method | $\sigma=0.20$ | $\sigma=0.25$ |
|--------|---------------|---------------|
| PTP | 81.3% | 70.8% |
| CAR (no cap) | 50.0% | 41.8% |
| CAR (15% cap) | 68.9% | 63.2% |
| SAR (no cap) | 58.7% | 49.0% |
| HWM | 42.6% | 33.3% |

---

## Part VI: Guaranteed Annuity Options (Chapter 12)

### GAO Payoff

UK-style (guaranteed annuity rate $g$):
$$\max(g F_n a_{65}(n) - F_n, 0) = F_n(g a_{65}(n) - 1)^+$$

US-style (guaranteed income $X$):
$$\max(X a_{65}(n) - F_n, 0)$$

### Interest Rate Model (RSAR)

For long-term yields:
$$\log(1 + i_t) | \rho_t^y = \mu_{\rho_t^y}^y + \phi_{\rho_t^y}^y(\log(1 + i_{t-1}) - \mu_{\rho_t^y}^y) + \sigma_{\rho_t^y}^y \epsilon_t$$

**UK Parameters** (2.5% consols 1956-2001):
| Regime | $\mu^y$ | $\sigma^y$ | $\phi^y$ | $p_{ij}$ |
|--------|---------|-----------|---------|----------|
| 1 | 0.066 | 0.0014 | 0.9895 | $p_{12}=0.0279$ |
| 2 | 0.109 | 0.0038 | 0.9895 | $p_{21}=0.0440$ |

### GAO Hedge

Assuming lognormal discounted annuity:
$$H_t = F_t \{g a_{65}(t) \Phi(d_1(t)) - \Phi(d_2(t))\}$$

Where:
$$d_1(t) = \frac{\log(g a_{65}(t)) + \sigma_y^2(n-t)/2}{\sigma_y\sqrt{n-t}}$$

### GAO Risk Measures (Table 12.1)

| Approach | Yield Start | CTE90% | CTE95% |
|----------|-------------|--------|--------|
| Actuarial (stocks) | 8% | 14.73% | 19.67% |
| Actuarial (stocks) | 5% | 18.67% | 23.90% |
| Dynamic hedge | 8% | 13.51% | 15.39% |

---

## Implementation Notes

### Python: RSLN Simulation

```python
import numpy as np

def simulate_rsln(
    n_months: int,
    mu: tuple[float, float],
    sigma: tuple[float, float],
    p12: float,
    p21: float,
    n_sims: int = 10000
) -> np.ndarray:
    """
    Simulate RSLN-2 model paths [T1: Hardy 2003 Ch 2].

    Returns
    -------
    np.ndarray
        Shape (n_sims, n_months) of log-returns
    """
    # Stationary distribution
    pi1 = p21 / (p12 + p21)

    paths = np.zeros((n_sims, n_months))
    regimes = np.zeros((n_sims, n_months), dtype=int)

    # Initial regime
    regimes[:, 0] = (np.random.rand(n_sims) > pi1).astype(int)

    for t in range(n_months):
        if t > 0:
            # Transition
            r = regimes[:, t-1]
            u = np.random.rand(n_sims)
            # From regime 0: transition prob p12
            # From regime 1: transition prob p21
            trans_prob = np.where(r == 0, p12, p21)
            regimes[:, t] = np.where(u < trans_prob, 1 - r, r)

        # Generate returns
        r = regimes[:, t]
        paths[:, t] = np.where(
            r == 0,
            np.random.normal(mu[0], sigma[0], n_sims),
            np.random.normal(mu[1], sigma[1], n_sims)
        )

    return paths
```

### Python: CTE Calculation

```python
def cte_from_simulation(
    losses: np.ndarray,
    alpha: float
) -> tuple[float, float]:
    """
    Calculate CTE from simulation output [T1: Hardy 2003 Eq 9.10].

    Returns
    -------
    tuple
        (CTE estimate, standard error)
    """
    n = len(losses)
    sorted_losses = np.sort(losses)

    # Number of tail observations
    n_tail = int(n * (1 - alpha))
    tail_losses = sorted_losses[-n_tail:]

    cte = tail_losses.mean()
    se = tail_losses.std() / np.sqrt(n_tail)  # Biased low

    return cte, se
```

### Python: EIA PTP Valuation

```python
from scipy.stats import norm

def eia_ptp_value(
    P: float,
    alpha: float,
    G: float,
    r: float,
    d: float,
    sigma: float,
    n: float
) -> float:
    """
    Point-to-point EIA option value [T1: Hardy 2003 Eq 13.7].

    Parameters
    ----------
    P : Premium
    alpha : Participation rate
    G : Guarantee (e.g., 0.95 * P * 1.03^n)
    r : Risk-free rate
    d : Dividend yield
    sigma : Volatility
    n : Term in years
    """
    K = (G - P * (1 - alpha)) / (alpha * P)

    d1 = (np.log(1/K) + (r - d + 0.5 * sigma**2) * n) / (sigma * np.sqrt(n))
    d2 = d1 - sigma * np.sqrt(n)

    option_value = (
        alpha * P * np.exp(-d * n) * norm.cdf(d1) -
        (G - P * (1 - alpha)) * np.exp(-r * n) * norm.cdf(d2)
    )

    return option_value
```

---

## Relevance to annuity-pricing

**Direct applications**:
- `products/fia.py` - EIA crediting strategies, break-even analysis
- `products/rila.py` - Buffer/cap mechanics (similar to CAR with cap)
- `valuation/monte_carlo.py` - RSLN simulation
- `risk/cte.py` - CTE risk measure implementation

**Key implementation priorities**:
1. RSLN simulation engine (Chapter 2)
2. CTE calculator with standard errors (Chapter 9)
3. EIA valuation formulas: PTP, CAR, SAR (Chapter 13)
4. Dynamic hedge calculation and error projection (Chapter 8)

---

## Key Insights

### 1. RSLN Outperforms Lognormal
The two-regime model better captures:
- Fat tails (extreme events)
- Volatility clustering
- Negative mean in high-volatility regime

### 2. CTE Superior to VaR
- Coherent risk measure (subadditive)
- Captures tail shape, not just quantile
- Adopted by Canadian regulators

### 3. EIA Participation Trade-offs
Higher participation rate ↔ Lower guarantee OR caps/floors
- HWM most expensive → lowest participation
- CAR with cap allows higher participation
- Simple ratchet cheaper than compound

### 4. Dynamic Hedging Reduces Capital
Actuarial approach (no hedging): CTE95% ≈ 20% of premium
Dynamic hedging: CTE95% ≈ 15% of premium
Savings: ~25% reduction in capital requirements

### 5. GAO Interest Rate Sensitivity
- GAO liability highly sensitive to interest rates
- 2% rate change → liability changes by factor of 2-3x
- Requires interest rate modeling (not just equity)

---

## Limitations

| Topic | Hardy's Treatment |
|-------|-------------------|
| Stochastic volatility | RSLN captures; continuous stochastic vol not covered |
| Interest rate models | Simplified for GAO; recommends CIR for practice |
| Policyholder behavior | Deterministic lapses; acknowledges limitation |
| American options | Not covered; European maturity only |
| RILA products | Did not exist in 2003; principles apply |

---

## Related Papers

| Paper | Contribution |
|-------|--------------|
| Hardy (2001) | RSLN model calibration |
| Boyle & Tan (2002) | Trinomial lattice for CAR |
| Yang (2001) | GAO valuation methods |
| Tiong (2001) | EIA formulas (alternative approach) |
| Pelsser (2002) | GAO swaption hedging |

---

## Change Log

| Date | Change |
|------|--------|
| 2025-12-05 | Initial comprehensive summary from PDF |

