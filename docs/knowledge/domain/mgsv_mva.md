# MGSV and MVA Quick Reference

**Tier**: [T1] Regulatory | **Source**: NAIC Standard Nonforfeiture Law

---

## MGSV - Minimum Guaranteed Surrender Value [T1]

### Definition

The **Minimum Guaranteed Surrender Value** is the statutory minimum value an insurer must pay upon surrender, regardless of market conditions or surrender charges.

### Formula [T1]

```
MGSV = Base_Factor × Premium × (1 + MGSV_Rate)^Years
```

Where:
- **Base_Factor** = 87.5% (0.875) per NAIC law
- **Premium** = Initial premium paid
- **MGSV_Rate** = Statutory minimum rate (1-3%)
- **Years** = Duration in years

### Example

```
Premium: $100,000
Years: 5
MGSV_Rate: 1%
Base_Factor: 87.5%

MGSV = 0.875 × $100,000 × (1.01)^5
     = $87,500 × 1.0510
     = $91,962.50
```

### WINK Fields [T2]

| Field | Meaning | Typical Value |
|-------|---------|---------------|
| `mgsvBaseRate` | The 87.5% factor | 0.875 |
| `mgsvRate` | Statutory minimum rate | 0.01-0.03 |

**Important**: `mgsvBaseRate` is NOT an interest rate - it's the 87.5% statutory factor!

---

## MVA - Market Value Adjustment [T1]

### Definition

The **Market Value Adjustment** adjusts surrender value based on interest rate changes since purchase. It protects the insurer from early surrenders when rates have risen (and their bond portfolio has lost value).

### Concept [T1]

| Rate Environment | MVA Effect | Why |
|------------------|------------|-----|
| Rates **RISE** | **NEGATIVE** MVA | Insurer's bonds worth less |
| Rates **FALL** | **POSITIVE** MVA | Insurer's bonds worth more |

### Simplified Formula [T1]

```
MVA = Duration × (Purchase_Rate - Current_Rate) × Account_Value
```

Or using a more common approach:

```
MVA_Factor = (1 + Purchase_Rate / 1 + Current_Rate)^Remaining_Years - 1
MVA = Account_Value × MVA_Factor
```

### Example: Rising Rates (Negative MVA)

```
Purchase Rate: 4%
Current Rate: 6%
Remaining Years: 3
Account Value: $100,000

MVA_Factor = (1.04 / 1.06)^3 - 1
           = 0.9811^3 - 1
           = 0.9440 - 1
           = -0.056 (-5.6%)

MVA = $100,000 × (-0.056) = -$5,600
```

### Example: Falling Rates (Positive MVA)

```
Purchase Rate: 5%
Current Rate: 3%
Remaining Years: 3
Account Value: $100,000

MVA_Factor = (1.05 / 1.03)^3 - 1
           = 1.0194^3 - 1
           = 1.0591 - 1
           = +0.059 (+5.9%)

MVA = $100,000 × 0.059 = +$5,900
```

---

## Surrender Value Calculation [T1]

### Components

```
Surrender_Value = Account_Value - Surrender_Charge + MVA
```

With floor:

```
Surrender_Value = max(Surrender_Value, MGSV)
```

### Full Example

```
Initial Premium: $100,000
Years Held: 3
Account Value: $112,000 (earned interest)
Surrender Charge: 5% ($5,600)
MVA: -$3,000 (rates rose)
MGSV: $91,000

Raw Surrender = $112,000 - $5,600 - $3,000 = $103,400
Final Surrender = max($103,400, $91,000) = $103,400
```

If MVA was worse:

```
Account Value: $112,000
Surrender Charge: 5% ($5,600)
MVA: -$25,000 (rates rose sharply)

Raw Surrender = $112,000 - $5,600 - $25,000 = $81,400
Final Surrender = max($81,400, $91,000) = $91,000  ← MGSV floor protects
```

---

## WINK Fields [T2]

| Field | Meaning |
|-------|---------|
| `mva` | Whether MVA applies ("Y", "N", null) |
| `mgsvBaseRate` | 87.5% factor (NOT an interest rate) |
| `mgsvRate` | Statutory minimum rate |

### Data Quality Note [T2]

`mva` field contains "None" strings that should be coerced to null.

---

## Surrender Charge Schedule [T2]

Typical declining schedule:

| Year | Charge |
|------|--------|
| 1 | 7% |
| 2 | 6% |
| 3 | 5% |
| 4 | 4% |
| 5 | 3% |
| 6 | 2% |
| 7 | 1% |
| 8+ | 0% |

### WINK Fields [T2]

| Field | Meaning |
|-------|---------|
| `surrCharge1` through `surrCharge10` | Charge by year |
| `surrChargeDuration` | Years until 0% charge |

---

## Free Withdrawal Provisions [T2]

Most contracts allow **10% annual penalty-free withdrawal**.

| Field | Meaning |
|-------|---------|
| `freeWithdrawalPercent` | Annual penalty-free % |
| `freeWithdrawalAmount` | Dollar amount allowed |

---

## Implementation Pattern

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class SurrenderCalculator:
    """Calculate surrender values with MGSV floor. [T1]"""

    mgsv_base_rate: float = 0.875  # 87.5% statutory
    mgsv_rate: float = 0.01       # 1% minimum rate

    def mgsv(self, premium: float, years: int) -> float:
        """Minimum Guaranteed Surrender Value. [T1]"""
        return self.mgsv_base_rate * premium * (1 + self.mgsv_rate) ** years

    def mva_factor(
        self,
        purchase_rate: float,
        current_rate: float,
        remaining_years: float
    ) -> float:
        """Market Value Adjustment factor. [T1]"""
        return ((1 + purchase_rate) / (1 + current_rate)) ** remaining_years - 1

    def surrender_value(
        self,
        account_value: float,
        surrender_charge_pct: float,
        mva_factor: float,
        mgsv_value: float
    ) -> float:
        """Net surrender value with MGSV floor. [T1]"""
        raw = account_value * (1 - surrender_charge_pct) * (1 + mva_factor)
        return max(raw, mgsv_value)
```

---

## Anti-Pattern Tests

```python
def test_mgsv_base_is_not_rate():
    """mgsvBaseRate is 87.5% factor, not an interest rate."""
    assert 0.87 <= MGSV_BASE_RATE <= 0.88  # Should be ~0.875

def test_rising_rates_negative_mva():
    """Rising rates → negative MVA."""
    mva = mva_factor(purchase_rate=0.04, current_rate=0.06, years=3)
    assert mva < 0

def test_falling_rates_positive_mva():
    """Falling rates → positive MVA."""
    mva = mva_factor(purchase_rate=0.05, current_rate=0.03, years=3)
    assert mva > 0

def test_surrender_never_below_mgsv():
    """Surrender value floored at MGSV."""
    sv = surrender_value(
        account_value=100000,
        surrender_charge_pct=0.07,
        mva_factor=-0.20,  # Severe negative MVA
        mgsv_value=90000
    )
    assert sv >= 90000  # MGSV floor
```

---

## References

- NAIC Standard Nonforfeiture Law for Individual Deferred Annuities (Model 805)
- NAIC Model Regulation 806
- State insurance regulations (vary by state)
