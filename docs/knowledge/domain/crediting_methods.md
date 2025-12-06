# FIA Crediting Methods Quick Reference

**Tier**: [T1] Academic + [T2] WINK Empirical

---

## Overview [T1]

FIA returns are linked to index performance but subject to limits. The insurer does NOT invest your money in the index; they track it and credit interest based on performance.

**Key Principle**: FIA always has 0% floor - you cannot lose principal to market declines.

---

## Method 1: Cap Rate [T1]

**Definition**: Maximum return you can earn, regardless of index performance.

### Formula

```python
def cap_crediting(index_return: float, cap: float) -> float:
    """
    Cap rate crediting. [T1]

    Returns min of index return and cap, floored at 0.
    """
    return min(max(index_return, 0), cap)
```

### Examples (8% Cap)

| Index Return | Credited |
|--------------|----------|
| +15% | +8% (capped) |
| +8% | +8% |
| +5% | +5% |
| -10% | 0% (floor) |

### WINK Stats [T2]

| Metric | Value |
|--------|-------|
| Median cap | 5-6% |
| High cap | 10%+ |
| Field | `capRate` |

### Replication [T1]

Cap = Call Spread
```
Capped_Call = Long Call(K=S) - Long Call(K=S×(1+cap))
```

---

## Method 2: Participation Rate [T1]

**Definition**: Percentage of index gain credited to your account.

### Formula

```python
def participation_crediting(index_return: float, participation: float) -> float:
    """
    Participation rate crediting. [T1]

    Returns participation × index return, floored at 0.
    """
    return max(index_return * participation, 0)
```

### Examples (80% Participation)

| Index Return | Credited |
|--------------|----------|
| +10% | +8% (10% × 80%) |
| +5% | +4% |
| -10% | 0% (floor) |

### WINK Stats [T2]

| Metric | Value |
|--------|-------|
| Median | ~50% |
| High | 100%+ |
| Field | `participationRate` |

**Note**: Participation rates can exceed 100% for some products.

---

## Method 3: Spread (Margin) [T1]

**Definition**: Fee subtracted from index return before crediting.

### Formula

```python
def spread_crediting(index_return: float, spread: float) -> float:
    """
    Spread/margin crediting. [T1]

    Returns index return minus spread, floored at 0.
    """
    return max(index_return - spread, 0)
```

### Examples (2% Spread)

| Index Return | Credited |
|--------------|----------|
| +10% | +8% (10% - 2%) |
| +5% | +3% |
| +2% | 0% |
| -5% | 0% (floor) |

### WINK Stats [T2]

| Metric | Value |
|--------|-------|
| Typical | 1-3% |
| Field | `spreadRate` |

---

## Method 4: Performance Triggered [T1]

**Definition**: Fixed rate credited if index has ANY positive return.

### Formula

```python
def trigger_crediting(index_return: float, trigger_rate: float) -> float:
    """
    Performance triggered crediting. [T1]

    Returns fixed rate if index > 0, else 0.
    """
    return trigger_rate if index_return > 0 else 0
```

### Examples (5% Trigger Rate)

| Index Return | Credited |
|--------------|----------|
| +20% | +5% |
| +0.1% | +5% |
| 0% | 0% |
| -5% | 0% |

### WINK Stats [T2]

| Metric | Value |
|--------|-------|
| Typical | 4-6% |
| Field | `performanceTriggeredRate` |
| Fill rate | 4.9% (sparse) |

---

## Crediting Frequency [T2]

| Method | Description | WINK Field |
|--------|-------------|------------|
| **Annual PTP** | Compare year-start to year-end | `indexCreditingFrequency` |
| **Monthly PTP** | Sum of monthly returns (often with monthly cap) | |
| **Monthly Average** | Average of 12 month-end values | |
| **Term End Point** | Compare start to end of multi-year term | |

---

## Index Used [T2]

Most common indices in WINK:

| Index | Notes |
|-------|-------|
| S&P 500 | Most common |
| Russell 2000 | Small cap |
| NASDAQ-100 | Tech-heavy |
| MSCI EAFE | International |
| Proprietary/Vol-Control | Vendor data required |

**Crediting Basis**: Usually price return (excludes dividends).

---

## Combined Methods [T1]

Some products combine methods:

### Cap + Participation

```python
def cap_participation(index_return: float, cap: float, participation: float) -> float:
    """Cap applied to participation-adjusted return."""
    adjusted = index_return * participation
    return min(max(adjusted, 0), cap)
```

### Spread + Cap

```python
def spread_cap(index_return: float, spread: float, cap: float) -> float:
    """Spread deducted, then capped."""
    after_spread = max(index_return - spread, 0)
    return min(after_spread, cap)
```

---

## WINK Data Fields Summary [T2]

| Field | Method | Fill Rate |
|-------|--------|-----------|
| `capRate` | Cap | 23.9% |
| `participationRate` | Participation | 41.8% |
| `spreadRate` | Spread | Varies |
| `performanceTriggeredRate` | Trigger | 4.9% |
| `indexUsed` | Index | Most rows |
| `indexingMethod` | Method type | Most rows |
| `indexCreditingFrequency` | Frequency | Most rows |

---

## Data Quality Notes [T2]

| Field | Issue | Fix |
|-------|-------|-----|
| `capRate` | max = 9999.99 | Clip to ≤ 10.0 |
| `performanceTriggeredRate` | max = 999 | Clip to ≤ 1.0 |
| `spreadRate` | max = 99.0 | Clip to ≤ 1.0 |

---

## Anti-Pattern Tests

```python
def test_floor_enforcement():
    """FIA crediting never goes negative."""
    assert cap_crediting(-0.10, 0.08) == 0.0
    assert participation_crediting(-0.10, 0.80) == 0.0
    assert spread_crediting(-0.10, 0.02) == 0.0
    assert trigger_crediting(-0.10, 0.05) == 0.0

def test_cap_limits_upside():
    """Cap method limits upside."""
    assert cap_crediting(0.20, 0.08) == 0.08
    assert cap_crediting(0.05, 0.08) == 0.05  # Not capped

def test_participation_scales():
    """Participation scales return."""
    assert participation_crediting(0.10, 0.80) == 0.08
    assert participation_crediting(0.10, 1.20) == 0.12  # > 100% par
```

---

## References

- Pacific Life: Understanding FIA Crediting Methods
- WINK, Inc. AnnuitySpecs documentation
- Hardy (2003) "Investment Guarantees"
