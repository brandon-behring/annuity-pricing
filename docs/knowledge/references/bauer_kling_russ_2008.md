# Paper Summary: Bauer, Kling & Russ (2008)

**Tier**: L3 (Paper Summary)
**Citation**: Bauer, D., Kling, A., & Russ, J. (2008). A Universal Pricing Framework for Guaranteed Minimum Benefits in Variable Annuities. ASTIN Bulletin, 38(2), 621-651.
**DOI**: 10.1017/S0515036100015269
**Status**: [ ] Not acquired (FREE PDF available at ressources-actuarielles.net)

---

## Key Contribution

Provides a unified, model-independent framework for pricing all types of Guaranteed Minimum Benefits (GMxB) in variable annuities, including GMDB, GMAB, GMIB, and GMWB.

---

## Context

**Problem addressed**: Prior to this paper, each GMxB type required separate valuation methodology. This paper shows they can all be valued using a common framework.

**Prior work**:
- Milevsky & Posner (2001) - GMDB ("Titanic Option")
- Milevsky & Salisbury (2006) - GMWB
- Hardy (2003) - Investment Guarantees book

---

## Core Methodology

### Model Setup

1. **Account value process**: $A_t$ follows geometric Brownian motion
   $$dA_t = (r - m)A_t \, dt + \sigma A_t \, dW_t$$
   where $m$ = M&E charges

2. **Guarantee base**: $G_t$ tracks the guarantee level (product-specific rules)

3. **Death/survival probabilities**: Uses standard actuarial notation
   - $_tp_x$ = probability of survival from age $x$ to $x+t$
   - $\mu_{x+t}$ = force of mortality at age $x+t$

### Main Results

**Universal pricing formula**:
$$V_0 = \mathbb{E}^Q\left[\int_0^T e^{-rt} \cdot {}_{t}p_x \cdot \mu_{x+t} \cdot \text{Benefit}_t \, dt + e^{-rT} \cdot {}_Tp_x \cdot \text{Maturity}_T\right]$$

Where:
- First term = death benefits (GMDB component)
- Second term = maturity/survival benefits (GMAB, GMIB, GMWB)

---

## Key Equations

### Equation 1: GMDB Value

$$GMDB_0 = \mathbb{E}^Q\left[\int_0^T e^{-rt} \cdot {}_{t}p_x \cdot \mu_{x+t} \cdot \max(G_t - A_t, 0) \, dt\right]$$

**Interpretation**: Present value of mortality-weighted put options on the account value.

### Equation 2: GMAB Value

$$GMAB_0 = e^{-rT} \cdot {}_Tp_x \cdot \mathbb{E}^Q[\max(G_T - A_T, 0)]$$

**Interpretation**: Survival-weighted European put option.

### Equation 3: GMWB Value (simplified)

$$GMWB_0 = \sum_{t=1}^{T} e^{-rt} \cdot {}_{t}p_x \cdot \mathbb{E}^Q[\text{withdrawal benefit}_t]$$

**Interpretation**: Sum of survival-weighted withdrawal payments.

---

## Guarantee Base Evolution

| Product | G_t Rule |
|---------|----------|
| GMDB (Return of Premium) | $G_t = P$ (constant) |
| GMDB (Ratchet) | $G_t = \max(G_{t-1}, A_t)$ at anniversaries |
| GMAB | $G_T = P \cdot (1+g)^T$ |
| GMWB | $G_t = G_{t-1} - W_t$ (reduced by withdrawals) |

---

## Validation

**Test cases from paper**:

| Test | Parameters | Expected |
|------|------------|----------|
| GMDB (RoP) | x=55, T=20, σ=20%, m=1.5%, P=100 | Table 3 |
| GMAB | x=55, T=10, g=0%, σ=20% | Table 4 |

---

## Relevance to annuity-pricing

**Applicable to**:
- `products/variable_annuity.py` (future)
- Phase 8: GLWB Pricing Engine
- Understanding GMxB guarantee mechanics

**Implementation status**: [ ] Not started

---

## Notes

1. This is the foundational paper for unified GMxB pricing
2. FREE PDF available - should acquire first
3. Extends naturally to multiple decrements (lapse, mortality)
4. Monte Carlo implementation straightforward from equations

---

## Change Log

| Date | Change |
|------|--------|
| 2025-12-05 | Initial summary from landscape analysis |
