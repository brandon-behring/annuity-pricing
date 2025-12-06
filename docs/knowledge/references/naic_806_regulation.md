# Regulatory Summary: NAIC Model 806

**Tier**: L3 (Regulatory Reference)
**Citation**: NAIC Model Laws, Regulations, Guidelines and Other Resources—October 2007
**Document**: Annuity Nonforfeiture Model Regulation
**Status**: [x] Acquired | [x] Summarized

---

## Key Purpose

Implements the Standard Nonforfeiture Law (Model 805) with detailed rules for:
1. **Initial method** for setting nonforfeiture rates
2. **Redetermination method** for updating rates
3. **Equity-indexed benefit** valuation for additional rate reductions

---

## Key Definitions (Section 3)

| Term | Definition |
|------|------------|
| **Basis** | Period over which CMT average is computed |
| **Equity-indexed benefits** | Benefits where crediting rate depends on equity index performance |
| **Index term** | Period until next indexed interest crediting date |
| **Initial method** | How initial NF rate is established |
| **Redetermination method** | How NF rate is updated over time |
| **Nonforfeiture rate** | Interest rate for minimum NF amount calculation |

**Exclusions from "equity-indexed"**: Variable annuity separate accounts, indexed guaranteed separate accounts for institutional buyers.

---

## Initial Method (Section 4)

### Requirements

1. Must be **filed with commissioner**
2. Changes allowed **once per calendar year**
3. **Not required** to be disclosed in contract form
4. Initial NF rate disclosure required **only if redetermination is used**

### Basis Options

The "basis" can use:
- A specified period (single day to multiple months)
- CMT change-triggered methodology (±50 bps max range)

---

## Redetermination Method (Section 5)

If used:
- **Must be disclosed** in contract form
- Changes for future issues allowed anytime with approval

### Triggering Methods

**Value-triggered redetermination**:
1. Calculate potential NF rate each modal period
2. If |potential - actual| > range threshold → update actual rate
3. Maximum allowable range: **±50 basis points**

**Example from Appendix A**:
```
Date        5Y CMT   Potential NF   Actual NF   Action
Jan 2004    3.1%     1.75%          1.75%       Initial rate
Apr 2004    3.3%     2.05%          2.05%       Updated (>25bps diff)
Aug 2004    2.6%     1.35%          1.35%       Updated (market drop)
```

---

## Nonforfeiture Rate Rules (Section 6)

### Contracts WITHOUT Equity-Indexed Benefits

**Single rate** applies to entire contract per Model 805 §4B.

### Contracts WITH Equity-Indexed Benefits

**Multiple rates possible**:

| Benefit Type | Rate Determination |
|--------------|-------------------|
| Non equity-indexed | Standard Model 805 §4B rate |
| Equity-indexed | May use additional 100 bps reduction per Model 805 §4C |

### Total Contract NF Amount

$$\text{Contract NF} = \sum_i \text{NF}_i(\text{benefit}_i) - \text{Indebtedness}$$

---

## Transfer Rules (Section 6.B.4)

When contract value transfers between benefits:

### From a Benefit

$$\text{New NF}_{\text{from}} = \text{Old NF}_{\text{from}} \times \left(1 - \frac{\text{Amount Transferred}}{\text{Old CV}_{\text{from}}}\right)$$

### To a Benefit

$$\text{New NF}_{\text{to}} = \text{Old NF}_{\text{to}} + \sum \text{Reductions} \times \frac{\text{Transfer to this}}{\text{Total Transferred}}$$

### Withdrawal Exceeds Benefit NF

If withdrawal > benefit's NF amount:
- Deduct excess from **other benefits' NF amounts**
- Order: **lowest to highest NF rate** (most favorable to customer)

---

## Equity-Indexed Benefit Valuation (Section 7)

### Substantive Participation Test

**Step 1**: Calculate annualized option cost (basis points) for index term

**Step 2**: If option cost ≥ **25 basis points** → substantive participation

**Step 3**: Additional reduction = **min(100 bps, annualized option cost)**

### Calculation Requirements

| Requirement | Details |
|-------------|---------|
| Use guaranteed parameters | Guaranteed participation rate, caps, etc. |
| Basis at term start | Parameters fixed at index term beginning |
| No adjustments | No persistency, death, utilization adjustments |
| Calibration | Must match capital markets-based option pricing |

### Actuarial Certification Required

**At filing**: Initial certification that methodology meets requirements (Appendix C)

**Annually**: Ongoing compliance certification with annual statement (Appendix D)

---

## Worked Example (Appendix B)

**Setup**:
- 5Y CMT = 3.75%
- Fixed NF rate = 2.5% (3.75% - 125 bps)
- EIA NF rate = 1.5% (2.5% - 100 bps additional)
- Premium = $100,000

**Year 1** (50/50 allocation):
```
EIA benefit NF = 50% × (87,500 - 50) × 1.015 = $44,380.88
Fixed benefit NF = 50% × (87,500 - 50) × 1.025 = $44,818.13
Total NF = $89,199.00
```

**Year 2** (rebalance from 60/40 to 50/50):
```
Transfer: 1/6 of EIA NF to Fixed
EIA NF after = 44,380.88 - 7,396.81 = $36,984.06
Fixed NF after = 44,818.13 + 7,396.81 = $52,214.94
(Total still = $89,199.00)

Roll forward:
EIA NF = (36,984.06 - 25) × 1.015 = $37,513.45
Fixed NF = (52,214.94 - 25) × 1.025 = $53,494.68
Total = $91,008.13
```

---

## Implementation Code

### Option Cost for EIA Substantive Participation Test

```python
import numpy as np
from scipy.stats import norm

def eia_option_cost_annualized(
    participation: float,
    cap: float | None,
    floor: float,
    index_vol: float,
    risk_free: float,
    dividend_yield: float,
    index_term_years: float
) -> float:
    """
    Calculate annualized option cost for EIA substantive participation test.

    Based on NAIC Model 806 Section 7.B.1.
    Uses Black-Scholes for point-to-point EIA valuation.

    Returns
    -------
    float
        Annualized option cost in basis points
    """
    T = index_term_years
    sigma = index_vol
    r = risk_free
    q = dividend_yield
    k = participation

    # Value of participation in index (call with strike 1)
    d1 = (r - q + 0.5 * sigma**2) * T / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    call_value = (np.exp(-q * T) * norm.cdf(d1) -
                  np.exp(-r * T) * norm.cdf(d2))

    # Participation-adjusted value
    option_value = k * call_value

    # If capped, subtract value above cap
    if cap is not None:
        # Cap strike = exp(cap * T)
        cap_strike = np.exp(cap * T)
        d1_cap = (np.log(1/cap_strike) + (r - q + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
        d2_cap = d1_cap - sigma * np.sqrt(T)
        call_cap = (np.exp(-q*T) * norm.cdf(d1_cap) -
                    cap_strike * np.exp(-r*T) * norm.cdf(d2_cap))
        option_value -= k * call_cap

    # Annualize to basis points
    annual_cost = option_value / T
    bps = annual_cost * 10000

    return bps


def qualifies_for_additional_reduction(option_cost_bps: float) -> bool:
    """Check if equity-indexed benefit qualifies for additional NF rate reduction."""
    return option_cost_bps >= 25  # 25 bps threshold


def additional_nf_reduction_bps(option_cost_bps: float) -> float:
    """Calculate additional NF rate reduction for equity-indexed benefit."""
    if option_cost_bps < 25:
        return 0.0
    return min(100, option_cost_bps)  # Capped at 100 bps
```

### Transfer Tracking

```python
from dataclasses import dataclass

@dataclass
class BenefitNF:
    """Track nonforfeiture amounts by benefit."""
    name: str
    contract_value: float
    nf_amount: float
    nf_rate: float

def transfer_between_benefits(
    source: BenefitNF,
    dest: BenefitNF,
    transfer_amount: float
) -> tuple[BenefitNF, BenefitNF]:
    """
    Apply transfer rules per NAIC 806 Section 6.B.4.
    """
    # Proportion transferred from source
    prop_from = transfer_amount / source.contract_value
    nf_transferred = source.nf_amount * prop_from

    # Update source
    new_source = BenefitNF(
        name=source.name,
        contract_value=source.contract_value - transfer_amount,
        nf_amount=source.nf_amount - nf_transferred,
        nf_rate=source.nf_rate
    )

    # Update destination
    new_dest = BenefitNF(
        name=dest.name,
        contract_value=dest.contract_value + transfer_amount,
        nf_amount=dest.nf_amount + nf_transferred,
        nf_rate=dest.nf_rate
    )

    return new_source, new_dest
```

---

## Relevance to annuity-pricing

**Applicable to**:
- `products/fia.py` - EIA/FIA nonforfeiture mechanics
- `products/rila.py` - RILA may qualify for additional reduction
- `valuation/nonforfeiture.py` - Multi-benefit NF tracking

**Key implementation needs**:
1. Option cost calculation for substantive participation test
2. Transfer rules between indexed and fixed buckets
3. Redetermination trigger logic

---

## Regulatory History

| Date | Action |
|------|--------|
| 2005 Q3 | Adopted by parent committee |
| 2005 Q4 | Adopted by Plenary |

---

## Change Log

| Date | Change |
|------|--------|
| 2025-12-05 | Initial summary from PDF |
