# Regulatory Document: SEC RILA Final Rule (2024)

**Tier**: L3 (Regulatory Summary)
**Citation**: SEC Release No. 33-11294; 34-100450; IC-35273 (July 2024). "Registration for Index-Linked Annuities and Registered Market Value Adjustment Annuities; Amendments to Form N-4"
**Source**: Federal Register / Securities and Exchange Commission
**Effective Date**: September 23, 2024
**Status**: [x] Acquired / [x] Summarized

---

## Key Contribution

First comprehensive SEC regulatory framework specifically for RILAs. Mandates tailored Form N-4 registration with enhanced disclosure requirements including Key Information Table (KIT), buffer/cap/floor explanations with numeric examples, and price return vs total return index disclosures.

---

## Context

**Problem addressed**: RILA market grew from $9.2B (2017) to $47.4B (2023)—quintupling in 6 years. Complex products sold to retail investors with insufficient standardized disclosure. Q4 2023: RILA sales surpassed variable annuity sales for first time.

**Prior regulation**:
- Consolidated Appropriations Act, 2023 (RILA Act) - mandated SEC action
- VASP Adopting Release (2020) - variable annuity summary prospectus framework
- OIAD Investor Testing Report - documented investor comprehension difficulties

---

## Core Regulatory Framework

### Form N-4 Registration

**Requirement**: All RILAs must register on Form N-4 (previously used only for variable annuities)

**Scope**: Applies to:
- Standalone RILAs with index-linked options
- Combination contracts (index-linked + variable + fixed options)
- Registered MVA annuities

---

## Key Definitions (Per SEC)

### Limits on Gains [T1 - Regulatory Definition]

| Term | Definition | Effect |
|------|------------|--------|
| **Cap Rate** | Upper limit on investor's ability to participate in index's upside performance directly | If index return = 12%, cap = 4% → credited = 4% |
| **Participation Rate** | Sets investor's return to specified percentage of index return | If index return = 10%, participation = 80% → credited = 8% |

### Limits on Losses [T1 - Regulatory Definition]

| Term | Definition | Effect |
|------|------------|--------|
| **Buffer** | Limits investor's exposure to losses up to a fixed percentage | If index = -25%, buffer = 10% → credited = -15% |
| **Floor** | Places lower limit on investor's exposure to loss | If index = -25%, floor = -10% → credited = -10% |

### Contract Adjustments [T1 - Regulatory Definition]

| Term | Definition |
|------|------------|
| **Interim Value Adjustment (IVA)** | Adjusts contract value if amounts withdrawn from index-linked option before crediting period ends |
| **Market Value Adjustment (MVA)** | Positive or negative adjustment from interest rate changes on withdrawal |
| **Surrender Charge** | Penalty for withdrawal within specified period after premium payment |

---

## Key Information Table (KIT) Requirements

### Mandatory Structure

Form N-4 prescribes standardized KIT format for all RILA offerings:

```
┌────────────────────────────────────────────────────────────┐
│                FEES, EXPENSES, AND ADJUSTMENTS             │
├────────────────────────────────────────────────────────────┤
│ Are There Charges or Adjustments for Early Withdrawals?    │
│ Are There Transaction Charges?                             │
│ Are There Ongoing Fees and Expenses?                       │
├────────────────────────────────────────────────────────────┤
│                          RISKS                             │
├────────────────────────────────────────────────────────────┤
│ Is There a Risk of Loss from Poor Performance?             │
│ Is this a Short-Term Investment?                           │
│ What Are the Risks Associated with the Investment Options? │
│ What are the Risks Related to the Insurance Company?       │
├────────────────────────────────────────────────────────────┤
│                      RESTRICTIONS                          │
├────────────────────────────────────────────────────────────┤
│ Are There Restrictions on the Investment Options?          │
│ Are There any Restrictions on Contract Benefits?           │
├────────────────────────────────────────────────────────────┤
│                         TAXES                              │
├────────────────────────────────────────────────────────────┤
│ What Are the Contract's Tax Implications?                  │
├────────────────────────────────────────────────────────────┤
│                  CONFLICTS OF INTEREST                     │
├────────────────────────────────────────────────────────────┤
│ How Are Investment Professionals Compensated?              │
│ Should I Exchange My Contract?                             │
└────────────────────────────────────────────────────────────┘
```

### Format Requirements

1. **Tabular presentation** - prescribed order, no modifications to headings
2. **Cross-references** - link to statutory prospectus for detail
3. **Electronic links** - required for electronic versions
4. **Succinct language** - consistent with tabular limitations

---

## Disclosure Requirements

### Upside Limits Disclosure (Item 3)

Insurance companies **must**:

1. State that cap/participation rate/other measure will limit positive index returns
2. Provide **numeric example** for each limit type:
   ```
   "If the Index return is 12% and the cap rate is 4%, we will credit
   4% in interest at the end of the Crediting Period"
   ```
3. Prominently state this may result in investor earning less than index return
4. Disclose **minimum limit on index gains** guaranteed for contract life

### Downside Protection Disclosure (Item 3)

Insurance companies **must**:

1. State that floor/buffer/other measure will limit negative index returns
2. Provide **numeric example** for each protection type:
   ```
   "If the Index return is -25% and the buffer rate is -10%, we will
   credit -15% (the amount that exceeds the buffer rate) at the end
   of the crediting period"
   ```

### Price Return vs Total Return Index

**New requirement**: If applicable, insurers must disclose:
- Index is a "price index," not "total return index"
- Does not reflect dividends paid on securities composing index
- Or: index deducts fees/costs when calculating performance
- This will cause index to underperform direct investment in securities

**Rationale**: Investor testing showed this is the "biggest drag" on RILA performance, and investors often don't understand the distinction.

---

## Investor Testing Findings

The OIAD Investor Testing Report documented significant comprehension difficulties:

| Finding | Implication |
|---------|-------------|
| Confusion with "buffer" concept | Investors often did not understand buffers absorbed first X% of loss |
| "Investment term" misunderstood | Crediting period vs contract term confusion |
| "Interim value adjustment" confusing | Complex formula, can change daily, positive or negative |
| Price vs total return index | Many investors unaware of dividend exclusion impact |
| Q&A format improved comprehension | 5.7 percentage point effect on "non-investor" comprehension |

---

## Economic Tradeoffs (SEC Characterization)

### Bounded Return Structure

> "RILAs limit or reduce downside risk, but also limit upside performance. In exchange for
> some protection against losses if the index goes down in value, investors must also agree
> to contractual provisions limiting the gains they will receive if the index goes up in value."

### Hidden Cost Structure

> "For many RILAs, the investor pays no direct or explicit ongoing fees and expenses under
> the RILA... However, the RILA's bounded return structure requires investors to agree to
> tradeoffs that come with their own economic costs."

### Not Low-Risk

> "Despite the bounded return structure, a RILA is not necessarily a low-risk investment
> product as the investor could lose a significant amount of money if the index performs poorly."

---

## Relevance to annuity-pricing

### Module Mapping

| SEC Requirement | Implementation Module |
|-----------------|----------------------|
| Buffer mechanics | `products/rila.py` |
| Floor mechanics | `products/rila.py` |
| Cap/participation rates | `products/fia.py`, `products/rila.py` |
| Price vs total return | `options/payoffs/index_options.py` |
| Crediting period returns | `valuation/rila_pv.py` |

### Validation Requirements

From SEC examples, implement test cases:

| Test Case | Parameters | Expected |
|-----------|------------|----------|
| Cap example | index=12%, cap=4% | credited=4% |
| Buffer example | index=-25%, buffer=10% | credited=-15% |
| Floor example | index=-25%, floor=-10% | credited=-10% |
| Participation | index=10%, part=80% | credited=8% |

### Compliance Considerations

For any pricing tool used to support RILA sales:

1. **Buffer vs Floor distinction** - must be clear and correct
2. **Numeric examples** - follow SEC format exactly
3. **Price return assumption** - document when using price-only indices
4. **IVA/MVA complexity** - model early withdrawal adjustments

---

## Implementation Notes

### Buffer Payoff Function

Per SEC definition (buffer absorbs first X%):

```python
def buffer_payoff(index_return: float, buffer: float, cap: float) -> float:
    """
    Calculate RILA buffer payoff per SEC definition.

    Parameters
    ----------
    index_return : float
        Index return (decimal, e.g., -0.25 for -25%)
    buffer : float
        Buffer level (decimal, e.g., 0.10 for 10%)
    cap : float
        Upside cap (decimal, e.g., 0.12 for 12%)

    Returns
    -------
    float
        Credited return per SEC examples

    Examples
    --------
    >>> buffer_payoff(-0.25, 0.10, 0.12)  # SEC example
    -0.15  # "credit -15% (the amount that exceeds the buffer rate)"
    >>> buffer_payoff(0.12, 0.10, 0.04)   # SEC example
    0.04   # "credit 4% in interest"
    """
    if index_return >= 0:
        # Upside: apply cap
        return min(index_return, cap)
    else:
        # Downside: buffer absorbs first X%
        if index_return >= -buffer:
            return 0.0  # Buffer absorbs entire loss
        else:
            return index_return + buffer  # Loss beyond buffer
```

### Floor Payoff Function

Per SEC definition (floor = lower limit on loss):

```python
def floor_payoff(index_return: float, floor: float, cap: float) -> float:
    """
    Calculate RILA floor payoff per SEC definition.

    Parameters
    ----------
    index_return : float
        Index return (decimal, e.g., -0.25 for -25%)
    floor : float
        Floor level (decimal, e.g., -0.10 for -10% floor)
    cap : float
        Upside cap (decimal, e.g., 0.12 for 12%)

    Returns
    -------
    float
        Credited return

    Examples
    --------
    >>> floor_payoff(-0.25, -0.10, 0.12)
    -0.10  # Loss capped at floor
    >>> floor_payoff(-0.05, -0.10, 0.12)
    -0.05  # Loss less severe than floor, passes through
    """
    if index_return >= 0:
        return min(index_return, cap)
    else:
        return max(index_return, floor)
```

---

## Critical Distinctions

### Buffer vs Floor [T1 - Per SEC]

| Feature | Buffer | Floor |
|---------|--------|-------|
| Protection type | Absorbs first X% of loss | Limits maximum loss |
| -5% with 10% protection | 0% credited | -5% credited |
| -15% with 10% protection | -5% credited | -10% credited |
| -25% with 10% protection | -15% credited | -10% credited |
| Cost to insurer | Higher for small losses | Higher for large losses |

### Price Return vs Total Return [T1 - Per SEC]

| Index Type | Includes Dividends | Typical Use |
|------------|-------------------|-------------|
| Price return (S&P 500 PR) | No | Most RILAs |
| Total return (S&P 500 TR) | Yes | Index funds |
| Impact | ~2% annual drag | Significant over crediting period |

---

## Related Documents

| Document | Relationship |
|----------|--------------|
| `sec_rila_investor_testing_2023.md` | OIAD testing informing this rule |
| `finra_22_08_complex_products.md` | Broker-dealer obligations |
| `../domain/buffer_floor.md` | L1 quick reference |
| `../domain/crediting_methods.md` | FIA/RILA crediting |

---

## Change Log

| Date | Change |
|------|--------|
| 2025-12-05 | Initial comprehensive summary |
