# GLWB PDE Valuation Derivation

**Tier**: L2 (Full Derivation)
**Domain**: Variable Annuity Pricing
**Prerequisites**: BS formula, stochastic calculus, actuarial mathematics
**References**: Bauer, Kling & Russ (2008); Milevsky & Salisbury (2006); Dai et al. (2008)

---

## Problem Statement

Value a Guaranteed Lifetime Withdrawal Benefit (GLWB) rider that guarantees lifetime withdrawals at rate $w$ of a guarantee base $G_t$, regardless of account value $A_t$.

**Key complexity**: Policyholder may optimize withdrawal timing and amounts.

---

## State Variables

| Variable | Description | Dynamics |
|----------|-------------|----------|
| $A_t$ | Account value | GBM with withdrawals |
| $G_t$ | Guarantee base | Ratchet/roll-up rules |
| $W_t$ | Cumulative withdrawals | Controlled by policyholder |
| $t$ | Time | Deterministic |
| $x$ | Age at issue | Deterministic |

---

## Account Value Dynamics

Under the risk-neutral measure $\mathbb{Q}$:

$$dA_t = (r - m)A_t \, dt + \sigma A_t \, dW_t - dW_t$$

Where:
- $r$ = risk-free rate
- $m$ = M&E charges + rider fee (typically 1.5-2.5% annually)
- $\sigma$ = equity volatility
- $dW_t$ = standard Brownian motion
- $dW_t$ = withdrawal at time $t$ (control variable)

---

## GLWB Payoff Structure

### During Accumulation Phase

$$A_{t+1} = A_t \cdot \exp\left[(r - m - \frac{\sigma^2}{2})\Delta t + \sigma \sqrt{\Delta t} Z\right]$$

### During Withdrawal Phase

At each time step:

```
if A_t > 0:
    withdrawal = min(w × G_t, A_t)  # Funded from account
else:
    withdrawal = w × G_t             # Insurer pays (guarantee kicks in)
```

### Guarantee Base Evolution

**Ratchet mechanism** (annual reset):
$$G_{t+1} = \max(G_t, A_t) \quad \text{on anniversary dates}$$

**Roll-up mechanism** (before first withdrawal):
$$G_t = G_0 \cdot (1 + g)^t$$

where $g$ = roll-up rate (typically 5-7% simple or compound).

---

## Valuation Framework

### Value Function Definition

Let $V(A, G, t, x)$ be the value of the GLWB to the policyholder, where:
- $A$ = current account value
- $G$ = current guarantee base
- $t$ = time since issue
- $x$ = current age

### Terminal Condition

At contract maturity $T$:
$$V(A, G, T, x) = \max(G - A, 0) \quad \text{(if policyholder survives)}$$

Actually, for a **lifetime** withdrawal benefit, there's no fixed terminal condition. Instead:

$$V(0, G, t, x) = a_{x+t} \cdot w \cdot G$$

where $a_{x+t}$ = life annuity factor at age $x+t$.

---

## Hamilton-Jacobi-Bellman Equation

### Optimal Control Problem

The policyholder chooses withdrawal rate $\omega_t$ to maximize:

$$V(A, G, t, x) = \sup_{\omega} \mathbb{E}^Q\left[\int_t^{\tau_d} e^{-r(s-t)} \cdot \text{Benefit}(A_s, G_s, \omega_s) \, ds \,|\, \mathcal{F}_t\right]$$

where $\tau_d$ = random death time.

### HJB Equation

$$\frac{\partial V}{\partial t} + (r - m)A \frac{\partial V}{\partial A} + \frac{1}{2}\sigma^2 A^2 \frac{\partial^2 V}{\partial A^2} - rV + \mu_{x+t}(V^{death} - V) + \sup_{\omega}\{\omega + \text{impact of } \omega\} = 0$$

### Simplified Form (No Optimization)

For static withdrawal rate $w$ (no optimization):

$$\frac{\partial V}{\partial t} + (r - m)A \frac{\partial V}{\partial A} + \frac{1}{2}\sigma^2 A^2 \frac{\partial^2 V}{\partial A^2} - rV + \mu_{x+t}(\bar{V} - V) + w \cdot G = 0$$

Where:
- $\mu_{x+t}$ = force of mortality at age $x+t$
- $\bar{V}$ = death benefit value (if different from living benefit)

---

## Boundary Conditions

### 1. Account Depleted ($A = 0$)

When account is depleted, policyholder receives guaranteed income for life:

$$V(0, G, t, x) = w \cdot G \cdot \ddot{a}_{x+t}$$

where $\ddot{a}_{x+t}$ = present value of life annuity-due at age $x+t$.

**Life annuity factor**:
$$\ddot{a}_x = \sum_{k=0}^{\omega-x} {}_{k}p_x \cdot v^k = \sum_{k=0}^{\omega-x} \frac{l_{x+k}}{l_x} \cdot e^{-rk}$$

### 2. High Account Value ($A \to \infty$)

As account value grows large, guarantee becomes worthless:
$$\lim_{A \to \infty} V(A, G, t, x) = 0$$

### 3. At Ratchet Date

$$V(A, G, t^+, x) = V(A, \max(G, A), t^-, x)$$

---

## Numerical Solution: Finite Difference Method

### Grid Setup

| Dimension | Range | Grid Points |
|-----------|-------|-------------|
| $A$ | $[0, A_{max}]$ | $N_A$ (typically 100-200) |
| $G$ | $[G_{min}, G_{max}]$ | $N_G$ (typically 50-100) |
| $t$ | $[0, T]$ | $N_t$ (daily or weekly) |

### Discretization

**Explicit scheme** (Euler):

$$V_{i,j}^{n-1} = V_{i,j}^n + \Delta t \cdot \left[\text{PDE terms}\right]$$

**Implicit scheme** (Crank-Nicolson recommended for stability):

$$\frac{V_{i,j}^n - V_{i,j}^{n-1}}{\Delta t} = \frac{1}{2}\left[\mathcal{L}V^n + \mathcal{L}V^{n-1}\right]$$

where $\mathcal{L}$ is the differential operator.

### Stability Condition

For explicit scheme:
$$\Delta t \leq \frac{(\Delta A)^2}{\sigma^2 A_{max}^2}$$

---

## Monte Carlo Alternative

For GLWB, Monte Carlo is often preferred due to:
1. High dimensionality (multiple state variables)
2. Path-dependence (ratchet)
3. Mortality integration

### MC Algorithm

```python
def price_glwb_mc(
    A0: float,      # Initial account value
    G0: float,      # Initial guarantee base
    w: float,       # Withdrawal rate (e.g., 0.05)
    r: float,       # Risk-free rate
    sigma: float,   # Volatility
    m: float,       # M&E + rider fee
    x: int,         # Age at issue
    T: int,         # Maximum horizon (years)
    n_paths: int,   # Number of MC paths
    mortality_table: np.ndarray  # qx values
) -> float:
    """Price GLWB using Monte Carlo simulation."""

    dt = 1/252  # Daily steps
    n_steps = int(T * 252)

    values = np.zeros(n_paths)

    for path in range(n_paths):
        A = A0
        G = G0
        pv_benefits = 0.0
        survival_prob = 1.0

        for step in range(n_steps):
            t = step * dt
            age = x + t

            # Mortality: check if policyholder dies this period
            q = interpolate_qx(mortality_table, age) * dt
            survival_prob *= (1 - q)

            # Withdrawal
            guaranteed_withdrawal = w * G * dt
            actual_withdrawal = min(guaranteed_withdrawal, A)
            excess_cost = max(guaranteed_withdrawal - actual_withdrawal, 0)

            # PV of excess cost (insurer pays when account depleted)
            pv_benefits += survival_prob * excess_cost * np.exp(-r * t)

            # Account evolution
            if A > 0:
                dW = np.random.normal(0, np.sqrt(dt))
                A = A * np.exp((r - m - 0.5*sigma**2)*dt + sigma*dW)
                A = max(A - actual_withdrawal, 0)

            # Annual ratchet
            if step % 252 == 0:
                G = max(G, A)

    return np.mean(values)
```

---

## Key Insights

### 1. GLWB = Sequence of Put Options + Longevity Risk

The GLWB can be decomposed:
$$GLWB = \sum_{t} {}_{t}p_x \cdot e^{-rt} \cdot \mathbb{E}[\max(w \cdot G_t - \text{Withdrawal from Account}, 0)]$$

### 2. Ratchet Creates Path Dependence

The guarantee base $G_t$ depends on the maximum account value, creating path dependence that cannot be priced with closed-form BS.

### 3. Optimal Withdrawal Boundary

Rational policyholders withdraw more when:
- Account is near depletion (maximize guarantee)
- Near death (maximize utility)
- After poor market returns (lock in high GWB)

### 4. Insurer Risk Concentration

GLWB cost spikes when:
- Equity markets crash (accounts deplete faster)
- Interest rates fall (annuity factors increase)
- Policyholders live longer than expected

---

## Validation Test Cases

### Case 1: No Mortality (Pure Financial)

Set $\mu = 0$ (immortal policyholder). GLWB becomes perpetual withdrawal:

$$V(A, G, t) \approx \frac{w \cdot G}{r} \quad \text{when } A = 0$$

### Case 2: High Account Value

When $A >> G$:
$$V(A, G, t, x) \approx 0$$

Guarantee is worthless if account is large.

### Case 3: Deterministic Withdrawal (No Optimization)

Compare to:
$$V = \sum_{t=1}^{T} {}_{t}p_x \cdot e^{-rt} \cdot w \cdot G \cdot \mathbb{P}(A_t = 0 | A_0)$$

where $\mathbb{P}(A_t = 0)$ = probability of ruin by time $t$.

---

## Implementation Roadmap

### Phase 8a: Simple GLWB (No Optimization)
- Static withdrawal rate $w$
- Annual ratchet
- Monte Carlo simulation
- Deterministic mortality

### Phase 8b: Add Stochastic Mortality
- Random death time
- Multiple mortality tables
- Longevity risk quantification

### Phase 8c: Add Policyholder Optimization
- Optimal withdrawal boundary
- Dynamic programming / HJB solver
- Behavior calibration from SOA studies

### Phase 8d: VM-21 Integration
- CTE70 calculation
- Stochastic scenario generation
- Standard scenario reserve

---

## References

1. **Bauer, Kling & Russ (2008)** - Universal GMxB framework
   - See: `references/bauer_kling_russ_2008.md`

2. **Milevsky & Salisbury (2006)** - Original GMWB analysis
   - "Financial Valuation of Guaranteed Minimum Withdrawal Benefits"

3. **Dai, Kwok, Zong (2008)** - Optimal withdrawal analysis
   - "Guaranteed Minimum Withdrawal Benefit in Variable Annuities"

4. **Chen, Vetzal, Forsyth (2008)** - Numerical methods
   - "The effect of modelling parameters on the value of GMWB guarantees"

---

## Change Log

| Date | Change |
|------|--------|
| 2025-12-05 | Initial derivation document |
