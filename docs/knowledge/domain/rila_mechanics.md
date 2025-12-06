# RILA (Registered Index-Linked Annuity) Mechanics

**Tier**: L1 (Quick Reference)
**Domain**: Product Mechanics
**Related**: `products/rila.py`

---

## Product Overview

RILA = "Buffered annuity" or "Buffer annuity"

**Key features**:
- Partial downside protection (buffer or floor)
- Limited upside participation (cap, spread, or participation rate)
- Index-linked returns (S&P 500, Russell 2000, etc.)
- No explicit guarantee of principal

---

## Protection Mechanisms

### Buffer

**Definition**: Insurer absorbs first X% of losses.

```
Buffer = 10%

Index return = -15%
→ Insurer absorbs first 10%
→ Client loss = -5%

Index return = -8%
→ Insurer absorbs all 8%
→ Client loss = 0%
```

**Common buffer levels**: 10%, 15%, 20%, 25%

### Floor

**Definition**: Maximum loss client can experience.

```
Floor = -10%

Index return = -15%
→ Client loss capped at -10%

Index return = -8%
→ Client loss = -8%
```

**Comparison**: Floor protects against catastrophic loss; buffer protects against moderate loss.

---

## Upside Mechanisms

### Cap

**Definition**: Maximum return client can earn.

```
Cap = 12%

Index return = +20%
→ Client return = +12%

Index return = +8%
→ Client return = +8%
```

### Participation Rate

**Definition**: Percentage of index return credited.

```
Participation rate = 80%

Index return = +20%
→ Client return = +16%

Index return = +10%
→ Client return = +8%
```

### Spread (Fee)

**Definition**: Fixed percentage subtracted from return.

```
Spread = 3%

Index return = +15%
→ Client return = +12%

Index return = +5%
→ Client return = +2%
```

---

## Payoff Formulas

### Buffer + Cap Strategy

$$\text{Return} = \min(\text{Cap}, \max(0, R + \text{Buffer})) \quad \text{if } R \geq -\text{Buffer}$$
$$\text{Return} = R + \text{Buffer} \quad \text{if } R < -\text{Buffer}$$

Where $R$ = index return.

**Simplified**:
```python
def buffer_cap_payoff(index_return, buffer, cap):
    if index_return >= -buffer:
        return min(cap, max(0, index_return))
    else:
        return index_return + buffer
```

### Floor + Cap Strategy

$$\text{Return} = \max(\text{Floor}, \min(\text{Cap}, R))$$

```python
def floor_cap_payoff(index_return, floor, cap):
    return max(floor, min(cap, index_return))
```

---

## Option Decomposition

A RILA can be replicated with vanilla options:

### Buffer + Cap

| Component | Option | Strike |
|-----------|--------|--------|
| Base | Long ZCB | - |
| Downside | Short put | 100% - buffer |
| Upside | Long call spread | 100% to cap |

### Floor + Cap

| Component | Option | Strike |
|-----------|--------|--------|
| Base | Long ZCB | - |
| Downside | Long put | 100% + floor |
| Upside | Short call | cap |

---

## Pricing Considerations

### Inputs Needed

| Parameter | Source |
|-----------|--------|
| Index volatility | Market (VIX, option chains) |
| Risk-free rate | Treasury curve |
| Term | Product spec (1Y, 3Y, 6Y) |
| Buffer/floor | Product spec |
| Cap/participation | Solve for fair value |

### Key Relationships

1. **Higher buffer → Lower cap**: More protection = less upside
2. **Longer term → Higher cap**: Time value favors insurer
3. **Higher volatility → Lower cap**: Options more expensive

---

## Market Data Requirements

| Data | Source | Frequency |
|------|--------|-----------|
| S&P 500 options | CBOE, Bloomberg | Daily |
| VIX index | CBOE | Real-time |
| Treasury rates | FRED | Daily |
| Dividend yield | Estimated | Quarterly |

---

## Validation Notes

**Gap**: No open-source RILA pricing library exists.

Our `products/rila.py` is first-mover.

**Cross-validation strategy**:
- Decompose to options, validate components against financepy
- Compare to published RILA rates from insurers
- Sensitivity analysis vs. market conditions

---

## References

- ChatGPT landscape analysis (2025): "No open-source RILA pricing module"
- LIMRA RILA sales data
- Product prospectuses (public filings)
