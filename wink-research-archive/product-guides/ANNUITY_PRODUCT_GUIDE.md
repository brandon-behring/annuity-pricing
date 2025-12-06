# Annuity Product Guide

A comprehensive guide to understanding annuity product types in the WINK dataset.

---

## Table of Contents

1. [What is an Annuity?](#what-is-an-annuity)
2. [Product Types Overview](#product-types-overview)
3. [MYGA - Multi-Year Guaranteed Annuity](#myga---multi-year-guaranteed-annuity)
4. [FIA - Fixed Indexed Annuity](#fia---fixed-indexed-annuity)
5. [RILA - Registered Index-Linked Annuity](#rila---registered-index-linked-annuity)
6. [FA - Traditional Fixed Annuity](#fa---traditional-fixed-annuity)
7. [IVA - Variable Annuity](#iva---variable-annuity)
8. [Key Concepts](#key-concepts)
9. [Market Context](#market-context)
10. [References](#references)

---

## What is an Annuity?

An **annuity** is a contract between you and an insurance company where you make a lump-sum payment (or series of payments), and in return, the insurer provides regular disbursements beginning either immediately or at some point in the future.

**Key Benefits:**
- **Tax-deferred growth** - No taxes on gains until withdrawal
- **Principal protection** (for fixed products) - Cannot lose money to market declines
- **Lifetime income options** - Can convert to guaranteed income stream
- **Death benefits** - Pass remaining value to beneficiaries

---

## Product Types Overview

| Type | Risk Level | Growth Potential | Principal Protected? | Best For |
|------|------------|------------------|---------------------|----------|
| **MYGA** | Very Low | Moderate (fixed) | Yes | CD alternative, predictable growth |
| **FA** | Very Low | Low-Moderate | Yes | Flexible contributions, annual rate resets |
| **FIA** | Low | Moderate | Yes (0% floor) | Index participation without downside |
| **RILA** | Moderate | Higher | Partial (buffer/floor) | Higher returns with limited risk |
| **IVA** | High | Highest | No | Full market participation |

### Risk/Return Spectrum

```
Lower Risk                                              Higher Risk
    ├─────────┼─────────┼─────────┼─────────┼─────────┤
   MYGA      FA       FIA      RILA      IVA

   Fixed    Fixed   Index-    Buffer/   Full
   Rate     Rate    Linked    Floor     Market
            Resets  (0% floor) Protection Exposure
```

---

## MYGA - Multi-Year Guaranteed Annuity

### What It Is
A **Multi-Year Guaranteed Annuity (MYGA)** is essentially a CD-like product issued by an insurance company. You deposit a lump sum, and the insurer guarantees a fixed interest rate for the **entire** contract term.

### Key Characteristics

| Feature | Details |
|---------|---------|
| **Rate Guarantee** | Fixed for entire term (3-10 years typically) |
| **Premium** | Single lump-sum payment |
| **Principal Protection** | 100% - cannot lose money |
| **Tax Treatment** | Tax-deferred growth |
| **Liquidity** | Limited - surrender charges apply for early withdrawal |

### How It Works

1. You deposit $100,000 into a 5-year MYGA at 4.5%
2. Rate is **locked** for all 5 years regardless of market conditions
3. At end of term:
   - Value = $100,000 × (1.045)^5 = $124,618
   - Can renew, roll to new annuity, or withdraw

### MYGA vs CD

| Feature | MYGA | Bank CD |
|---------|------|---------|
| Tax Treatment | Tax-deferred | Taxed annually |
| Insurance | State guaranty association | FDIC ($250k) |
| Rates | Often higher | Lower |
| Early Withdrawal | Surrender charge + possible MVA | Early withdrawal penalty |

### WINK Data Fields for MYGA
- `fixedRate` - The guaranteed interest rate (99.9% populated)
- `guaranteeDuration` - Years the rate is guaranteed (1-20)
- `mva` - Whether Market Value Adjustment applies
- `effectiveYield` - Calculated effective annual yield (97.9% populated)

---

## FIA - Fixed Indexed Annuity

### What It Is
A **Fixed Indexed Annuity (FIA)** provides returns linked to a market index (like the S&P 500) but with a **guaranteed floor of 0%** - you can never lose principal due to market declines.

### Key Characteristics

| Feature | Details |
|---------|---------|
| **Growth Potential** | Tied to index performance |
| **Downside Protection** | 0% floor - never negative |
| **Upside Limits** | Caps, participation rates, or spreads |
| **Principal Protection** | 100% - cannot lose to market |
| **Crediting Period** | Annual, biennial, or multi-year |

### How FIA Returns Work

Your money is **not** invested in the index. Instead, the insurer tracks index performance and credits interest based on that performance, subject to limits:

```
Index Return → Apply Limits → Credited Interest
    ↓              ↓               ↓
  +15%      (8% cap)           +8%
  +5%       (8% cap)           +5%
  -10%      (0% floor)          0%
```

### Crediting Methods

#### 1. Cap Rate
Maximum return you can earn, regardless of index performance.

| Scenario | Index Return | Cap | Credited |
|----------|--------------|-----|----------|
| Bull market | +15% | 8% | 8% |
| Moderate | +6% | 8% | 6% |
| Bear market | -10% | 8% | 0% |

#### 2. Participation Rate
Percentage of index gain you receive.

| Scenario | Index Return | Participation | Credited |
|----------|--------------|---------------|----------|
| Bull market | +10% | 80% | 8% |
| Moderate | +5% | 80% | 4% |
| Bear market | -10% | 80% | 0% |

#### 3. Spread (Margin)
A fee subtracted from index return before crediting.

| Scenario | Index Return | Spread | Credited |
|----------|--------------|--------|----------|
| Bull market | +10% | 2% | 8% |
| Moderate | +3% | 2% | 1% |
| Bear market | -10% | 2% | 0% |

#### 4. Performance Triggered
A fixed rate paid if the index has **any** positive return.

| Scenario | Index Return | Trigger Rate | Credited |
|----------|--------------|--------------|----------|
| Any positive | +0.1% | 5% | 5% |
| Any positive | +20% | 5% | 5% |
| Negative | -5% | 5% | 0% |

### Indexing Methods

| Method | Description | Best When |
|--------|-------------|-----------|
| **Annual PTP** | Compare start vs end of year | Steady growth |
| **Monthly PTP** | Sum of monthly returns (capped) | Volatile markets |
| **Monthly Averaging** | Average of 12 month-end values | Declining end-of-year |
| **Term End Point** | Compare start vs end of multi-year term | Long-term growth |

### WINK Data Fields for FIA
- `capRate` - Maximum return cap
- `participationRate` - % of index gain credited
- `spreadRate` - Fee deducted from return
- `performanceTriggeredRate` - Fixed rate if index positive
- `indexUsed` - S&P 500, Russell 2000, etc.
- `indexingMethod` - Annual PTP, Monthly Avg, etc.
- `indexCreditingFrequency` - Annual, Biennial, etc.

---

## RILA - Registered Index-Linked Annuity

### What It Is
A **Registered Index-Linked Annuity (RILA)**, also called a **Structured Annuity** or **Buffer Annuity**, is a hybrid between FIA and variable annuities. It offers **higher upside potential** than FIA but requires you to accept **some downside risk**.

### Key Characteristics

| Feature | Details |
|---------|---------|
| **Growth Potential** | Higher than FIA (higher caps/participation) |
| **Downside Protection** | Partial - via buffer or floor |
| **SEC Registered** | Yes (unlike FIA) |
| **Principal Risk** | Yes - can lose money beyond buffer/floor |
| **Fastest Growing** | 10 consecutive record years |

### Buffer vs Floor

#### Buffer Strategy
The insurer absorbs the **first X%** of losses.

```
10% Buffer Example:
├── Index: -5%  → You: 0% loss (buffer absorbs)
├── Index: -10% → You: 0% loss (buffer absorbs)
├── Index: -15% → You: -5% loss (15% - 10% buffer)
└── Index: -25% → You: -15% loss (25% - 10% buffer)
```

#### Floor Strategy
You absorb losses **up to X%**, insurer covers the rest.

```
-10% Floor Example:
├── Index: -5%  → You: -5% loss
├── Index: -10% → You: -10% loss (max)
├── Index: -15% → You: -10% loss (floor limits)
└── Index: -25% → You: -10% loss (floor limits)
```

### Buffer vs Floor Comparison

| Feature | Buffer | Floor |
|---------|--------|-------|
| Small losses | Insurer absorbs | You absorb |
| Large losses | You absorb excess | Insurer absorbs excess |
| Best for | Protecting against minor corrections | Protecting against crashes |
| Upside | Often higher caps | Often lower caps |

### WINK Data Fields for RILA
- `bufferRate` - % of losses insurer absorbs (e.g., 0.10 = 10%)
- `bufferModifier` - Type: "Losses Covered Up To" (buffer) vs "Losses Covered After" (floor)
- `capRate` - Maximum return (typically higher than FIA)
- `participationRate` - Often 100%+

---

## FA - Traditional Fixed Annuity

### What It Is
A **Traditional Fixed Annuity** provides a guaranteed interest rate, but unlike MYGA, the rate is only guaranteed for **one year at a time** and resets annually.

### Key Characteristics

| Feature | Details |
|---------|---------|
| **Rate Guarantee** | One year at a time |
| **Rate Resets** | Annually, based on market conditions |
| **Minimum Rate** | Guaranteed floor (e.g., 1%) |
| **Premium** | Can be single or flexible |
| **Best For** | Rising rate environments |

### FA vs MYGA

| Feature | FA | MYGA |
|---------|-----|------|
| Rate lock | 1 year | Entire term |
| Rate changes | Yes, annually | No |
| Rising rates | Benefits | Misses out |
| Falling rates | Hurts | Protected |
| Predictability | Lower | Higher |

### WINK Data Fields for FA
- `fixedRate` - Current guaranteed rate
- `guaranteeDuration` - Typically 1 year
- `effectiveYield` - Calculated yield

---

## IVA - Variable Annuity

### What It Is
A **Variable Annuity (VA)** allows you to invest in **subaccounts** - investment portfolios similar to mutual funds. Your returns depend entirely on investment performance.

### Key Characteristics

| Feature | Details |
|---------|---------|
| **Growth Potential** | Highest - full market participation |
| **Risk** | Highest - can lose principal |
| **Investment Options** | Subaccounts (stocks, bonds, money market) |
| **Fee Structure** | Complex - M&E, admin, fund fees |
| **Guarantees** | Optional riders (death benefit, income) |

### Fee Structure

| Fee Type | Typical Range | Description |
|----------|---------------|-------------|
| **M&E (Mortality & Expense)** | 1.00-1.50% | Insurance costs |
| **Administrative** | 0.15-0.30% | Recordkeeping |
| **Subaccount Fees** | 0.50-1.50% | Fund management |
| **Total** | **1.65-3.30%** | Annual drag on returns |

### Share Classes

| Class | Up-Front Fee | Surrender Period | M&E | Best For |
|-------|--------------|------------------|-----|----------|
| **B Share** | None | 5-8 years | Lower | Long-term |
| **L Share** | None | 3-4 years | Higher | Flexibility |
| **C Share** | None | None | Highest | Full liquidity |
| **A Share** | Yes | None | Lowest | Large investments |

### WINK Data Fields for IVA
- `subaccountUsed` - Investment option name
- `fundManager` - Asset manager (BlackRock, Fidelity, etc.)
- `fundGroup` - Fund family
- `shareClass` - B, C, L, A, I, etc.
- `netExpenseRatio` - Fund expense ratio

---

## Key Concepts

### Market Value Adjustment (MVA)

An **MVA** adjusts your surrender value based on interest rate changes since purchase.

| Scenario | Interest Rates | MVA Effect |
|----------|----------------|------------|
| Rates rise | Higher than purchase | **Negative** - reduces value |
| Rates fall | Lower than purchase | **Positive** - increases value |

**Why it exists:** Protects insurer from early withdrawals when rates have risen (their bond portfolio has lost value).

### MGSV (Minimum Guaranteed Surrender Value)

Per **NAIC Standard Nonforfeiture Law**, insurers must guarantee a minimum surrender value:

```
MGSV = 87.5% × Premiums × (1 + rate)^years

Where:
- 87.5% = Statutory minimum (mgsvBaseRate in WINK)
- rate = 1-3% (mgsvRate in WINK)
```

**Purpose:** Protects consumers from combined surrender charges + negative MVA eliminating all value.

### Surrender Charges

A percentage deducted if you withdraw before the surrender period ends.

**Typical Schedule:**
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

Most contracts allow **10% annual penalty-free withdrawals**.

---

## Market Context

### 2024 Sales (LIMRA Data)

| Product Type | 2024 Sales | YoY Change |
|--------------|------------|------------|
| **Total Annuities** | $434.1B | +13% (record) |
| FIA | $125.5B | +31% |
| RILA | $65.6B | +38% |
| MYGA/FRD | ~$120B+ | Strong |
| Variable | Declining | Negative |

### Key Trends

1. **RILA is fastest-growing** - 10 consecutive record years
2. **FIA at all-time highs** - 3rd consecutive record
3. **Rate environment matters** - Higher rates benefit fixed products
4. **Variable declining** - Losing share to RILA

---

## References

### Regulatory
- [FINRA Notice 22-08 - Complex Products](https://www.finra.org/rules-guidance/notices/22-08)
- [NAIC Nonforfeiture Model Law](https://content.naic.org/sites/default/files/model-law-808.pdf)

### Educational
- [Annuity.org - MYGA](https://www.annuity.org/annuities/types/fixed/myga/)
- [Annuity.org - RILA](https://www.annuity.org/annuities/types/registered-index-linked-annuities/)
- [Pacific Life - FIA Crediting Methods](https://www.annuities.pacificlife.com/content/dam/paclife/rsd/annuities/public/pdfs/guide/understanding-fixed-indexed-annuity-interest-crediting-methods.pdf)

### Market Data
- [LIMRA Annuity Sales Reports](https://www.limra.com/en/newsroom/news-releases/)
- [WINK, Inc.](https://www.winkintel.com/)
