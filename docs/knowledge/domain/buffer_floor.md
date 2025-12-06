# Buffer vs Floor Quick Reference

**Tier**: [T1] Academic | **Source**: Boyle & Tian (2008), RILA prospectuses

---

## Critical Distinction [T1]

| Protection | Who Absorbs First Losses | Who Absorbs Large Losses |
|------------|-------------------------|--------------------------|
| **Buffer** | INSURER absorbs first X% | CLIENT absorbs excess |
| **Floor** | CLIENT absorbs up to X% | INSURER covers excess |

**Memory Aid**:
- **Buffer** = Bumper → Protects against SMALL hits
- **Floor** = Foundation → Sets a MINIMUM (limits max loss)

---

## Buffer Payoff [T1]

**Definition**: Insurer absorbs the FIRST X% of losses.

### Formula

```python
def buffer_payoff(index_return: float, buffer: float, cap: float) -> float:
    """
    RILA buffer payoff. [T1]

    Buffer absorbs first `buffer` percent of losses.
    """
    if index_return >= 0:
        return min(index_return, cap)  # Upside capped
    elif index_return >= -buffer:
        return 0.0  # Buffer absorbs loss
    else:
        return index_return + buffer  # Client absorbs excess
```

### Examples (10% Buffer, 12% Cap)

| Index Return | Calculation | Client Gets |
|--------------|-------------|-------------|
| +15% | min(0.15, 0.12) | +12% (capped) |
| +8% | min(0.08, 0.12) | +8% |
| +2% | min(0.02, 0.12) | +2% |
| 0% | 0 | 0% |
| -5% | Buffer absorbs | 0% |
| -10% | Buffer absorbs | 0% |
| -15% | -0.15 + 0.10 | -5% |
| -25% | -0.25 + 0.10 | -15% |

### Replication [T1]

Buffer = Put Spread (bearish)
```
Buffer_Payoff = Long Put(K=100) - Long Put(K=100-buffer)
```

---

## Floor Payoff [T1]

**Definition**: Client absorbs losses UP TO X%, insurer covers excess.

### Formula

```python
def floor_payoff(index_return: float, floor: float, cap: float) -> float:
    """
    RILA floor payoff. [T1]

    Floor limits maximum loss to `floor` percent.
    """
    if index_return >= 0:
        return min(index_return, cap)  # Upside capped
    else:
        return max(index_return, -floor)  # Floor limits loss
```

### Examples (-10% Floor, 15% Cap)

| Index Return | Calculation | Client Gets |
|--------------|-------------|-------------|
| +20% | min(0.20, 0.15) | +15% (capped) |
| +8% | min(0.08, 0.15) | +8% |
| 0% | 0 | 0% |
| -5% | max(-0.05, -0.10) | -5% |
| -10% | max(-0.10, -0.10) | -10% |
| -15% | max(-0.15, -0.10) | -10% (floor) |
| -30% | max(-0.30, -0.10) | -10% (floor) |

### Replication [T1]

Floor = Long Put at floor level
```
Floor_Payoff ≈ Long Put(K=100-floor)
```

---

## Visual Comparison

```
Index Return: -25%  -20%  -15%  -10%  -5%   0%   +5%  +10%  +15%

BUFFER (10%, 12% cap):
Client Gets:  -15%  -10%   -5%    0%   0%   0%   +5%  +10%  +12%
              ↑ absorbs excess        ↑ buffer absorbs    ↑ capped

FLOOR (-10%, 15% cap):
Client Gets:  -10%  -10%  -10%  -10%  -5%   0%   +5%  +10%  +15%
              ↑ floor limits loss                         ↑ capped
```

---

## When to Use Each [T1/T2]

| Scenario | Better Choice | Rationale |
|----------|---------------|-----------|
| Expect small corrections | **Buffer** | Absorbs minor losses entirely |
| Fear market crash | **Floor** | Limits catastrophic downside |
| Want higher caps | **Buffer** | Cheaper to hedge, higher caps |
| Conservative investor | **Floor** | Predictable max loss |

---

## Common Values in WINK [T2]

### Buffer Rates
| Percentile | Buffer |
|------------|--------|
| 25th | 10% |
| Median | 10% |
| 75th | 15% |
| Common values | 10%, 15%, 20% |

### Floor Rates
| Common Floor | Notes |
|--------------|-------|
| -10% | Most common |
| -15% | Higher risk tolerance |
| -20% | Aggressive |

---

## WINK Data Fields [T2]

| Field | Meaning |
|-------|---------|
| `bufferRate` | Buffer/floor level (decimal, e.g., 0.10 = 10%) |
| `bufferModifier` | Type identifier |
| → "Losses Covered Up To" | This is a **BUFFER** |
| → "Losses Covered After" | This is a **FLOOR** |

**WARNING**: Check `bufferModifier` to determine if it's actually a buffer or floor!

---

## Anti-Pattern Tests

```python
def test_buffer_absorbs_first():
    """Buffer absorbs first X%, not last X%."""
    assert buffer_payoff(-0.05, 0.10, 0.12) == 0.0  # 10% buffer absorbs 5% loss
    assert buffer_payoff(-0.15, 0.10, 0.12) == -0.05  # Client absorbs 5%

def test_floor_limits_max_loss():
    """Floor limits max loss, doesn't absorb first."""
    assert floor_payoff(-0.05, 0.10, 0.15) == -0.05  # Client absorbs 5%
    assert floor_payoff(-0.15, 0.10, 0.15) == -0.10  # Floor limits to 10%

def test_buffer_not_floor():
    """Buffer and floor give different results for same inputs."""
    # -15% return, 10% protection, 12% cap
    buffer_result = buffer_payoff(-0.15, 0.10, 0.12)
    floor_result = floor_payoff(-0.15, 0.10, 0.12)
    assert buffer_result == -0.05  # Client absorbs excess
    assert floor_result == -0.10   # Floor limits loss
    assert buffer_result != floor_result
```

---

## References

- Boyle, P. P., & Tian, W. (2008). The design of equity-indexed annuities. *Insurance: Mathematics and Economics*.
- FINRA Notice 22-08: Complex Products Guidance
- SEC Investor Bulletin on RILAs
