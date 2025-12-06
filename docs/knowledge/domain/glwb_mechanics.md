# GLWB Mechanics (Guaranteed Lifetime Withdrawal Benefit)

**Tier**: T1 (Product Definition) + T2 (Industry Practice)
**Source**: Milliman research, SEC filings, industry whitepapers

---

## Overview

GLWB (Guaranteed Lifetime Withdrawal Benefit) is a rider that guarantees lifetime income withdrawals regardless of account performance. It's the most common living benefit rider on Variable Annuities, and increasingly offered on FIAs and RILAs.

**Key characteristic**: Path-dependent AND life-contingent payoff.

---

## Core Mechanics

### 1. Guaranteed Withdrawal Base (GWB)

The GWB is the notional amount used to calculate guaranteed withdrawals. It is NOT the account value.

```
GWB ≠ Account Value
Guaranteed_Annual_Withdrawal = GWB × Withdrawal_Rate
```

### 2. GWB Accumulation Methods

| Method | Description | Example |
|--------|-------------|---------|
| **Return of Premium** | GWB = Initial premium, no growth | GWB stays at $100K |
| **Ratchet** | GWB = max(GWB, AV) on anniversary | GWB locks in gains |
| **Roll-up** | GWB grows at fixed rate until first withdrawal | 5% simple or compound |
| **Combination** | Ratchet + Roll-up | Higher of roll-up or ratchet |

### 3. Withdrawal Phase

Once withdrawals begin:
- **Guaranteed withdrawal**: GWB × withdrawal_rate (e.g., 5%)
- **Excess withdrawal**: Reduces GWB proportionally
- **Account depletion**: Withdrawals continue from insurer

---

## Withdrawal Rate Schedules

Typical rates vary by age at first withdrawal:

| Age at First Withdrawal | Withdrawal Rate |
|-------------------------|-----------------|
| 55-59 | 4.0% |
| 60-64 | 4.5% |
| 65-69 | 5.0% |
| 70-74 | 5.5% |
| 75+ | 6.0% |

**T2 Note**: Rates vary by product and insurer. RILA GLWBs often offer more generous rates to attract customers.

---

## GLWB Payoff Structure

```
At time t:
  If Account_Value(t) > 0:
    Withdrawal = min(Guaranteed_Amount, Account_Value(t))
    Account_Value(t+1) = Account_Value(t) - Withdrawal + Credits - Fees
  Else (Account depleted):
    Withdrawal = Guaranteed_Amount  # Insurer pays
    Continue until death
```

---

## Comparison: VA GLWB vs RILA GLWB

| Aspect | VA GLWB | RILA GLWB |
|--------|---------|-----------|
| **Valuation framework** | VM-21 | VM-21 (same) |
| **Equity exposure** | 100% (minus fees) | Buffered/floored |
| **Withdrawal rates** | Standard | Often more generous |
| **Convexity risk** | Standard | Slightly higher |
| **Hedging approach** | Delta + vega | Similar, higher gamma |

**Key insight from Milliman**: "RILA GLWBs share similar risk profiles with VA GLWBs" but exhibit "slightly more convexity" due to higher equity allocation and generous withdrawal rates.

---

## Risk Factors

### For the Insurer

1. **Longevity risk**: Policyholder lives longer than expected
2. **Market risk**: Account depletes faster in down markets
3. **Behavior risk**: Policyholders optimize withdrawals
4. **Basis risk**: Hedge vs. actual account mismatch

### Hedging Implications

- Requires delta hedging for equity exposure
- Vega hedging for volatility risk
- Rho hedging for interest rate risk
- **Convexity**: RILA GLWB requires more attention to gamma

From Milliman: "Unfloored CTE 98 requirement is reduced significantly when the GLWB is hedged."

---

## Pricing Considerations

### Option-Like Components

1. **Put option**: Guarantees floor on withdrawals
2. **Longevity option**: Continues after account depletion
3. **Lookback/ratchet**: Locks in market highs

### Fee Structure

Typical GLWB fee: 0.75% - 1.50% of GWB or AV annually

### Valuation Approach

```
GLWB_Value = E[PV(Guaranteed_Payments)] - E[PV(Account_Funded_Payments)]
           = E[PV(Excess_Payments_When_Account_Depleted)]
```

Requires nested simulation:
1. Outer loop: Economic scenarios (equity, rates)
2. Inner consideration: Mortality, behavior

---

## Implementation Complexity

**Why GLWB is hard to model**:

1. **Path-dependent**: GWB depends on entire account history
2. **Life-contingent**: Payments continue until death
3. **Behavioral**: Policyholders may optimize
4. **Multi-factor**: Equity + rates + mortality + behavior

**No open-source solution exists** (as of 2025) for plug-and-play GLWB valuation.

---

## Future Work (Phase 7+)

### Potential Implementation Path

1. **Phase 7a**: Document GLWB mechanics (this file) ✅
2. **Phase 7b**: Add simple GLWB simulation (no optimization)
3. **Phase 7c**: Add dynamic policyholder behavior
4. **Phase 7d**: Add VM-21 integration

### Module Structure

```
actuarial/
├── riders/
│   ├── glwb.py          # GLWB mechanics
│   ├── gmdb.py          # Death benefit
│   └── gmab.py          # Accumulation benefit
└── behavior/
    ├── withdrawal.py    # Withdrawal optimization
    └── lapse.py         # Dynamic lapse
```

---

## References

- Milliman: "GLWB hedging and capital management under different annuity contracts"
- SOA: Variable Annuity Guaranteed Living Benefits Utilization Study
- SEC: RILA prospectuses with GLWB riders
- VM-21: Requirements for VA reserves (applies to RILA GLWB)
