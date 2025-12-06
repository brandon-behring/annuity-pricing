# Regulatory Summary: NAIC Model 805

**Tier**: L3 (Regulatory Reference)
**Citation**: NAIC Model Laws, Regulations, Guidelines and Other Resources—Fall 2020
**Document**: Standard Nonforfeiture Law for Individual Deferred Annuities
**Status**: [x] Acquired | [x] Summarized

---

## Key Purpose

Establishes **minimum values** that must be available to policyholders upon cessation of premium payments or surrender of individual deferred annuity contracts. Ensures annuity contracts provide fair nonforfeiture benefits.

---

## Scope & Applicability (Section 2)

**Does NOT apply to**:
- Reinsurance
- Group annuities under employer retirement plans
- Premium deposit funds
- **Variable annuities**
- Investment annuities
- Immediate annuities
- Deferred annuity after annuity payments commence
- Reversionary annuities
- Contracts delivered outside the state
- **Contingent deferred annuities** (Sections 3-8 exempt)

**Key exclusion**: Variable annuities and CDAs have separate regulatory frameworks.

---

## Core Requirements (Section 3)

Every covered annuity contract must provide upon cessation of payments:

| Provision | Requirement |
|-----------|-------------|
| **Paid-up annuity benefit** | Must be granted on plan stipulated in contract |
| **Cash surrender benefit** | If contract provides lump sum at maturity |
| **Mortality/interest disclosure** | State tables and rates used in calculations |
| **Minimum benefit statement** | Benefits ≥ state statutory minimums |

**Deferral**: Company may defer cash surrender up to **6 months** with commissioner approval.

---

## Minimum Nonforfeiture Amount (Section 4)

### Formula

$$\text{Min NF Amount} = \text{Accumulated Net Considerations} - \text{Deductions}$$

Where:
- **Net considerations** = 87.5% of gross considerations
- **Accumulation rate** = per Section 4B

### Deductions

| Deduction | Description |
|-----------|-------------|
| Prior withdrawals | Accumulated at NF interest rate |
| Annual contract charge | **$50/year** accumulated |
| Premium taxes | If actually paid by company |
| Indebtedness | Including accrued interest |

---

## Nonforfeiture Interest Rate (Section 4B)

### Standard Rate

$$r_{NF} = \min(3\%, \text{5-Year CMT} - 125\text{bps})$$

**Floor**: 0.15% (15 basis points minimum)

### Equity-Indexed Adjustment (Section 4C)

For contracts with **substantive equity-indexed participation**:

$$r_{NF} = \min(3\%, \text{5-Year CMT} - 225\text{bps})$$

**Additional reduction**: Up to 100 bps to reflect equity index benefit value.

**Key constraint**: PV of additional reduction ≤ market value of equity index benefit.

---

## Cash Surrender Value (Section 6)

$$\text{CSV} = \text{PV(paid-up annuity at maturity)} - \text{withdrawals} - \text{indebtedness} + \text{additional credits}$$

**Discount rate**: Contract accumulation rate + up to 1%

**Death benefit floor**: Death benefit ≥ cash surrender value.

---

## Maturity Date Rules (Section 8)

For contracts with optional maturity dates, deemed maturity is the **later of**:
- Contract anniversary after annuitant's 70th birthday
- 10th anniversary of contract

---

## Key Formulas for Implementation

### Net Considerations

```python
def net_considerations(gross_premium: float) -> float:
    """
    Net considerations for nonforfeiture calculation [T1: NAIC 805 §4.A.2].

    87.5% of gross premium credited to contract.
    """
    return 0.875 * gross_premium
```

### Nonforfeiture Interest Rate

```python
def nonforfeiture_rate(cmt_5yr: float, equity_indexed: bool = False) -> float:
    """
    Calculate nonforfeiture interest rate [T1: NAIC 805 §4.B].

    Parameters
    ----------
    cmt_5yr : float
        5-Year Constant Maturity Treasury rate
    equity_indexed : bool
        True if contract has substantive equity-indexed participation

    Returns
    -------
    float
        Annual nonforfeiture interest rate
    """
    # Base reduction
    reduction_bps = 125

    # Additional reduction for equity-indexed (up to 100 bps more)
    if equity_indexed:
        reduction_bps = 225  # 125 + 100

    # Calculate rate
    rate = cmt_5yr - (reduction_bps / 10000)

    # Apply floor and ceiling
    rate = max(0.0015, rate)  # 15 bps floor
    rate = min(0.03, rate)    # 3% ceiling

    return rate
```

### Minimum Nonforfeiture Amount

```python
def minimum_nonforfeiture_amount(
    premiums: list[tuple[float, float]],  # (amount, years_ago)
    withdrawals: list[tuple[float, float]],
    nf_rate: float,
    years: int,
    annual_charge: float = 50.0,
    premium_tax_rate: float = 0.0
) -> float:
    """
    Calculate minimum nonforfeiture amount [T1: NAIC 805 §4.A.1].
    """
    # Accumulate net considerations
    accumulated = 0.0
    for amount, years_ago in premiums:
        net = 0.875 * amount
        accumulated += net * (1 + nf_rate) ** years_ago

    # Subtract accumulated withdrawals
    for amount, years_ago in withdrawals:
        accumulated -= amount * (1 + nf_rate) ** years_ago

    # Subtract accumulated annual charges
    for y in range(years):
        accumulated -= annual_charge * (1 + nf_rate) ** y

    # Subtract accumulated premium taxes
    for amount, years_ago in premiums:
        tax = amount * premium_tax_rate
        accumulated -= tax * (1 + nf_rate) ** years_ago

    return max(0, accumulated)
```

---

## Relevance to annuity-pricing

**Applicable to**:
- `products/myga.py` - MYGA surrender value calculations
- `products/fia.py` - FIA nonforfeiture values
- `valuation/surrender.py` - Cash surrender value floor

**Implementation priorities**:
1. Nonforfeiture rate calculation (CMT-based)
2. Minimum nonforfeiture amount accumulation
3. Cash surrender value floor enforcement

**Key insight for FIA/RILA**: The additional 100 bps reduction for equity-indexed contracts compensates for the cost of providing the index-linked benefit. This directly affects minimum guarantee levels.

---

## Regulatory History

| Date | Action |
|------|--------|
| 1977 | Adopted |
| 2003 | Amended (Fall 2020 version shows) |
| 2017 Q3 | Amended |
| Fall 2020 | Amended (current) |

---

## Change Log

| Date | Change |
|------|--------|
| 2025-12-05 | Initial summary from PDF |
