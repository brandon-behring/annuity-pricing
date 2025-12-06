# Dynamic Lapse Behavior

**Tier**: T1 (Academic) + T2 (Industry Practice)
**Source**: lifelib savings_example2, Milliman research

---

## Overview

Dynamic lapse models adjust policyholder surrender rates based on economic conditions, particularly the "moneyness" of guarantees. This reflects rational behavior: policyholders are more likely to surrender when their account value exceeds the guarantee (guarantee is "out of the money" to them).

---

## Core Formula

```
lapse_rate(t) = base_lapse_rate(t) × dynamic_factor(t)
```

Where:
```
dynamic_factor = account_value / guarantee_value
             = CSV_per_policy / sum_assured
```

### Interpretation

| Moneyness | Factor | Behavior |
|-----------|--------|----------|
| AV > Guarantee | > 1.0 | **Higher lapse** - rational to surrender |
| AV = Guarantee | = 1.0 | Base lapse rate |
| AV < Guarantee | < 1.0 | **Lower lapse** - rational to keep coverage |

---

## Implementation Pattern (from lifelib)

```python
def dynamic_lapse_factor(t: int, account_value: float, guarantee: float,
                         is_dynamic: bool = True) -> float:
    """
    Calculate dynamic lapse adjustment factor.

    Parameters
    ----------
    t : int
        Time period
    account_value : float
        Current account/cash surrender value
    guarantee : float
        Guaranteed amount (death benefit, withdrawal base, etc.)
    is_dynamic : bool
        Toggle dynamic behavior on/off

    Returns
    -------
    float
        Multiplier for base lapse rate
    """
    if not is_dynamic:
        return 1.0

    # Moneyness = AV / Guarantee
    moneyness = account_value / guarantee if guarantee > 0 else 1.0

    return moneyness
```

---

## Base Lapse Rate Pattern

Typical base lapse rates decline with duration (policy "aging"):

```python
def base_lapse_rate(duration: int) -> float:
    """
    Base deterministic lapse rate by policy duration.

    Typical pattern: higher early, declining with duration.
    """
    # Example: 10% year 1, declining by 1% per year, floor at 2%
    return max(0.10 - 0.01 * duration, 0.02)
```

---

## Product-Specific Applications

### Variable Annuities (VA)

- **Moneyness metric**: Account Value / GMDB or GMAB guarantee
- **High lapse trigger**: AV significantly exceeds guarantee
- **Low lapse trigger**: Deep in-the-money guarantee (AV << Guarantee)

### Fixed Indexed Annuities (FIA)

- **Moneyness metric**: Account Value / Surrender Value (net of MVA)
- Also influenced by: credited rate vs. market rates

### RILAs

- Similar to VA but with buffer/floor considerations
- Protection value affects rational surrender decision

### MYGAs

- **Interest rate sensitivity**: Lapse increases when market rates exceed guaranteed rate
- Formula variant:
  ```
  dynamic_factor = f(market_rate - guaranteed_rate)
  ```

---

## Calibration Considerations

### Data Sources

- **SOA/LIMRA experience studies** for industry benchmarks
- **Company-specific experience** for calibration
- **T2 assumption**: Calibration parameters are empirical

### Key Factors

1. **Duration**: Lapses typically highest in early years
2. **Surrender charges**: Suppress lapses during charge period
3. **Age**: Older policyholders less likely to lapse
4. **Product type**: Different products have different base patterns

---

## Implementation Checklist

- [ ] Define base lapse rate curve by duration
- [ ] Implement moneyness calculation for product type
- [ ] Add toggle for dynamic vs. static assumptions
- [ ] Calibrate factors to experience data
- [ ] Test sensitivity to moneyness levels

---

## References

- lifelib savings_example2: Dynamic lapse implementation
- SOA/LIMRA: Experience studies for calibration
- Milliman: GLWB hedging research (behavioral assumptions)

---

## Future Work (Phase 7+)

1. Add `actuarial/lapse.py` module to annuity-pricing
2. Implement moneyness-based adjustment
3. Support product-specific formulas (VA, FIA, RILA, MYGA)
4. Include calibration utilities
