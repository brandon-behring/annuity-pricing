# Paper Summary: Glasserman (2003) - Monte Carlo Methods in Financial Engineering

**Tier**: L3 (Paper/Textbook Summary)
**Citation**: Glasserman, P. (2003). *Monte Carlo Methods in Financial Engineering*. Springer. Applications of Mathematics, Vol. 53.
**DOI**: 10.1007/978-0-387-21617-1
**Status**: [x] Acquired / [x] Summarized

---

## Key Contribution

Definitive reference for Monte Carlo simulation in finance, covering path generation, variance reduction, discretization of SDEs, and sensitivity estimation (Greeks). Essential foundation for pricing path-dependent derivatives including FIA and RILA products.

---

## Context

**Problem addressed**: Unified treatment of simulation methods for derivative pricing, from basic random number generation through advanced variance reduction and American option techniques.

**Prior work**: Builds on Boyle (1977) for option pricing by simulation, bridges theory (stochastic calculus) with implementation (computational methods).

---

## Core Methodology

### Chapters Extracted (Relevance to annuity-pricing)

| Chapter | Topic | Module Relevance |
|---------|-------|------------------|
| Ch 3 | Generating Sample Paths | `options/simulation/` |
| Ch 4 | Variance Reduction | `options/simulation/` |
| Ch 6 | Discretization Methods | `options/simulation/` |
| Ch 7 | Estimating Sensitivities | `options/analysis/` |

---

## Key Equations

### 1. Geometric Brownian Motion (GBM) Simulation [T1]

**Exact simulation formula** (Ch 3, p. 94):

$$S(t_{i+1}) = S(t_i) \exp\left[\left(\mu - \frac{1}{2}\sigma^2\right)(t_{i+1} - t_i) + \sigma\sqrt{t_{i+1} - t_i} \, Z_{i+1}\right]$$

Where:
- $S(t_i)$ = asset price at time $t_i$
- $\mu$ = drift (use risk-free rate $r$ under risk-neutral measure)
- $\sigma$ = volatility
- $Z_{i+1} \sim N(0,1)$ = standard normal

**Interpretation**: Log-returns are normally distributed; this is exact (no discretization error) for GBM.

**Implementation**:
```python
def gbm_path(S0: float, r: float, sigma: float, T: float, n_steps: int, Z: np.ndarray) -> np.ndarray:
    """Generate exact GBM path.

    Parameters
    ----------
    S0 : float - Initial price
    r : float - Risk-free rate (annualized)
    sigma : float - Volatility (annualized)
    T : float - Time horizon (years)
    n_steps : int - Number of time steps
    Z : np.ndarray - Standard normal samples, shape (n_steps,)

    Returns
    -------
    np.ndarray - Price path, shape (n_steps + 1,)
    """
    dt = T / n_steps
    drift = (r - 0.5 * sigma**2) * dt
    diffusion = sigma * np.sqrt(dt)

    log_returns = drift + diffusion * Z
    log_S = np.zeros(n_steps + 1)
    log_S[0] = np.log(S0)
    log_S[1:] = log_S[0] + np.cumsum(log_returns)

    return np.exp(log_S)
```

---

### 2. Euler Discretization Scheme [T1]

**General SDE** (Ch 6, p. 339):

$$dX(t) = a(X(t))dt + b(X(t))dW(t)$$

**Euler scheme**:

$$\hat{X}_{i+1} = \hat{X}_i + a(\hat{X}_i)h + b(\hat{X}_i)\sqrt{h} \, Z_{i+1}$$

Where:
- $h = \Delta t$ = time step
- $a(\cdot)$ = drift coefficient
- $b(\cdot)$ = diffusion coefficient
- $Z_{i+1} \sim N(0,1)$

**Weak convergence**: $O(h)$ - sufficient for pricing
**Strong convergence**: $O(\sqrt{h})$ - matters for path-dependent payoffs

**When to use**:
- Required for processes where exact simulation unavailable (Heston, SABR)
- GBM: prefer exact formula above (no discretization error)

---

### 3. Milstein Discretization Scheme [T1]

**Improved scheme** (Ch 6, p. 346):

$$\hat{X}_{i+1} = \hat{X}_i + a(\hat{X}_i)h + b(\hat{X}_i)\sqrt{h}Z_{i+1} + \frac{1}{2}b'(\hat{X}_i)b(\hat{X}_i)h(Z_{i+1}^2 - 1)$$

**Strong convergence**: $O(h)$ - one order better than Euler

**Implementation note**: For GBM with $b(x) = \sigma x$, we have $b'(x) = \sigma$, so correction term = $\frac{1}{2}\sigma^2 X h(Z^2 - 1)$.

**When to use**:
- Path-dependent payoffs requiring strong convergence
- Barrier options, lookbacks, Asian options

---

### 4. Control Variates [T1]

**Basic setup** (Ch 4, p. 185):

Given estimator $Y$ of $E[Y]$, use correlated variable $X$ with known mean $E[X]$:

$$Y_c = Y - c(X - E[X])$$

**Optimal coefficient**:

$$c^* = \frac{\text{Cov}(X, Y)}{\text{Var}(X)}$$

**Variance reduction**:

$$\frac{\text{Var}(Y_c)}{\text{Var}(Y)} = 1 - \rho_{XY}^2$$

Where $\rho_{XY}$ = correlation between $X$ and $Y$.

**Example for European call**:
- Price Asian call → use European call (BS closed-form) as control
- Price call on basket → use calls on individual assets as controls

**Implementation**:
```python
def control_variate_estimate(
    payoffs: np.ndarray,  # MC payoffs
    control_values: np.ndarray,  # Control variate sample values
    control_mean: float  # Known/analytical mean of control
) -> tuple[float, float]:
    """Estimate with control variate variance reduction.

    Returns
    -------
    tuple[float, float] - (adjusted_mean, adjusted_stderr)
    """
    # Estimate optimal coefficient
    cov_matrix = np.cov(payoffs, control_values)
    c_star = cov_matrix[0, 1] / cov_matrix[1, 1]

    # Adjusted payoffs
    adjusted = payoffs - c_star * (control_values - control_mean)

    return adjusted.mean(), adjusted.std() / np.sqrt(len(adjusted))
```

---

### 5. Antithetic Variates [T1]

**Method** (Ch 4, p. 205):

For each sample $Z$, also use $-Z$:

$$\hat{Y} = \frac{1}{2}[Y(Z) + Y(-Z)]$$

**Variance reduction** (for monotonic payoffs):

$$\text{Var}(\hat{Y}) = \frac{1}{2}\text{Var}(Y)[1 + \rho]$$

Where $\rho = \text{Corr}(Y(Z), Y(-Z))$ is typically negative for monotonic payoffs.

**Effectiveness**:
- Excellent for vanilla options ($\rho \approx -1$)
- Less effective for path-dependent options
- Zero benefit if payoff is even function of $Z$

**Implementation**:
```python
def antithetic_gbm_paths(
    S0: float, r: float, sigma: float, T: float,
    n_steps: int, n_paths: int, rng: np.random.Generator
) -> np.ndarray:
    """Generate antithetic GBM paths.

    Returns
    -------
    np.ndarray - Paths, shape (2*n_paths, n_steps+1)
    """
    Z = rng.standard_normal((n_paths, n_steps))

    # Original paths
    paths_pos = gbm_path_vectorized(S0, r, sigma, T, n_steps, Z)
    # Antithetic paths
    paths_neg = gbm_path_vectorized(S0, r, sigma, T, n_steps, -Z)

    return np.vstack([paths_pos, paths_neg])
```

---

### 6. Greeks via Finite Differences [T1]

**Forward difference** (Ch 7, p. 382):

$$\hat{\Delta}_{\text{fwd}} = \frac{V(S_0 + h) - V(S_0)}{h}$$

- Bias: $O(h)$
- Variance: $O(h^{-2})$ when using same random numbers

**Central difference**:

$$\hat{\Delta}_{\text{cent}} = \frac{V(S_0 + h) - V(S_0 - h)}{2h}$$

- Bias: $O(h^2)$
- Variance: Higher than forward difference

**Optimal $h$ selection**: Balance bias vs variance
- Too large: bias dominates
- Too small: variance explodes
- Rule of thumb: $h \approx \sigma S_0 \sqrt{\Delta t}$ or $h \approx 0.01 S_0$

**Implementation note**: Always use **common random numbers** (same $Z$ for base and bumped prices) to reduce variance dramatically.

---

### 7. Pathwise (IPA) Greeks [T1]

**For differentiable payoffs** (Ch 7, p. 393):

$$\frac{\partial}{\partial \theta} E[f(X(\theta))] = E\left[\frac{\partial f}{\partial x} \cdot \frac{\partial X}{\partial \theta}\right]$$

**For GBM delta**:

$$\Delta = e^{-rT} E\left[\mathbf{1}_{S_T > K} \cdot \frac{S_T}{S_0}\right]$$

**Advantage**: No bias, better variance than finite differences
**Limitation**: Requires differentiable payoff (fails for digital options)

---

## Variance Reduction Summary

| Method | Typical Reduction | Best For | Limitation |
|--------|-------------------|----------|------------|
| **Antithetic** | 2-10x | Vanilla options | Even payoffs |
| **Control variate** | 10-100x | High correlation available | Need analytical control |
| **Importance sampling** | Problem-dependent | Rare events, Greeks | Requires density knowledge |
| **Stratified sampling** | 2-5x | General | Curse of dimensionality |

**Recommendation for annuity-pricing**:
1. Always use antithetic variates (nearly free)
2. Use European option as control for path-dependent options
3. Combine multiple techniques for maximum reduction

---

## Validation

**Test cases from textbook**:

| Test | Parameters | Expected Result |
|------|------------|-----------------|
| GBM European call | S=100, K=100, r=0.05, σ=0.20, T=1 | BS price ± MC stderr |
| Antithetic variance | Same as above, 10k paths | Var < naive/2 |
| Control variate | Asian call with European control | Stderr reduced 5-20x |
| Euler vs exact (GBM) | 100 steps | Should match exactly |
| Milstein convergence | Varying steps | Error ~ O(h) |

---

## Relevance to annuity-pricing

**Applicable modules**:

| Module | Concepts Used |
|--------|---------------|
| `options/simulation/gbm.py` | GBM exact simulation, antithetic |
| `options/simulation/monte_carlo.py` | Variance reduction, path generation |
| `options/pricing/monte_carlo.py` | Control variates, convergence |
| `options/analysis/greeks.py` | Finite difference, pathwise |
| `valuation/fia_pv.py` | Path-dependent FIA crediting |
| `valuation/rila_pv.py` | Buffer/floor payoff simulation |

**Implementation status**: [ ] Not started / [x] Partial / [ ] Complete

**Priority implementation order**:
1. GBM exact simulation (foundation)
2. Antithetic variates (easy win)
3. Control variates with BS (high impact)
4. Finite difference Greeks (essential for hedging)

---

## Key Implementation Patterns

### Pattern 1: Seeded RNG for Reproducibility

```python
def create_rng(seed: int | None = None) -> np.random.Generator:
    """Create reproducible random generator."""
    return np.random.default_rng(seed)
```

### Pattern 2: Common Random Numbers

```python
def price_with_bump(
    S0: float, bump: float, base_rng_state, ...
) -> tuple[float, float]:
    """Price base and bumped with same randoms."""
    rng = np.random.default_rng(base_rng_state)
    Z = rng.standard_normal(...)

    price_base = simulate_and_price(S0, Z, ...)
    price_bump = simulate_and_price(S0 + bump, Z, ...)  # Same Z!

    return price_base, price_bump
```

### Pattern 3: Convergence Diagnostics

```python
def mc_with_diagnostics(
    payoff_func, n_paths: int, batch_size: int = 1000
) -> dict:
    """Run MC with running statistics for convergence check."""
    means = []
    stderrs = []

    for batch in range(0, n_paths, batch_size):
        # ... accumulate statistics
        pass

    return {
        "price": final_mean,
        "stderr": final_stderr,
        "convergence_plot": (means, stderrs)
    }
```

---

## Notes

1. **GBM is exact**: For pure GBM, use the exact log-normal formula. Euler/Milstein only needed for more complex processes (Heston, SABR, local vol).

2. **Variance reduction compounds**: Antithetic + control variate can give 50-100x reduction.

3. **Path storage tradeoff**: For memory efficiency, compute payoffs incrementally rather than storing full paths.

4. **Quasi-Monte Carlo** (Ch 5): Low-discrepancy sequences (Sobol, Halton) can outperform MC for moderate dimensions. Consider for d < 50.

5. **American options** (Ch 8): Requires regression-based methods (Longstaff-Schwartz). Not covered here but relevant for GLWB optimal exercise.

---

## Related Documents

| Document | Relationship |
|----------|--------------|
| `hull_2021_options_formulas.md` | BS closed-form for control variates |
| `hardy_2003_investment_guarantees.md` | VA simulation context |
| `../domain/option_pricing.md` | L1 quick reference |
| `../derivations/monte_carlo.md` | L2 MC derivation |

---

## Change Log

| Date | Change |
|------|--------|
| 2025-12-05 | Initial comprehensive summary from Ch 3, 4, 6, 7 |
