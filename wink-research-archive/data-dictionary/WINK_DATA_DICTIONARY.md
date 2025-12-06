# WINK Data Dictionary

**Source**: WINK, Inc. (winkintel.com) - Insurance industry data provider
**File**: `wink.parquet`
**Total Rows**: 1,087,253
**Total Columns**: 62
**Date Range**: 2005-08-01 to 2025-11-08
**Last Updated**: 2025-12-04

---

## Table of Contents

1. [Product Mix Overview](#product-mix-overview)
2. [Status Filtering Guide](#status-filtering-guide)
3. [Column Reference](#column-reference)
   - [Product Classification](#1-product-classification)
   - [Company Information](#2-company-information)
   - [Rate Fields](#3-rate-fields)
   - [Bonus Rate Fields](#4-bonus-rate-fields)
   - [Buffer/Downside Protection (RILA)](#5-bufferdownside-protection-rila)
   - [MGSV Fields (Nonforfeiture)](#6-mgsv-fields-nonforfeiture)
   - [Index/Crediting Fields](#7-indexcrediting-fields)
   - [Variable Annuity Fields](#8-variable-annuity-fields)
   - [Guarantee/Duration Fields](#9-guaranteeduration-fields)
   - [Premium/Tier Fields](#10-premiumtier-fields)
   - [Fee/Expense Fields](#11-feeexpense-fields)
   - [Temporal Fields](#12-temporal-fields)
   - [Metadata/Audit Fields](#13-metadataaudit-fields)
4. [Product Applicability Matrix](#product-applicability-matrix)
5. [Data Quality Notes](#data-quality-notes)
6. [Recommended Cleaning Steps](#recommended-cleaning-steps)

---

## Product Mix Overview

### By productGroup (Row Counts)

| productGroup | productTypeID | productTypeName | Rows | % |
|--------------|---------------|-----------------|------|---|
| IVA | 5.0 | Variable | 460,264 | 42.3% |
| FIA | 1.0 | Fixed Indexed | 334,074 | 30.7% |
| RILA | 4.0 | Structured | 160,294 | 14.7% |
| **MYGA** | 3.0 | MYG Fixed | **122,513** | **11.3%** |
| FA | 2.0 | Traditional Fixed | 10,106 | 0.9% |

### By rateType

| rateType | Rows | % |
|----------|------|---|
| Variable | 442,144 | 40.7% |
| Indexed | 304,662 | 28.0% |
| Fixed | 171,187 | 15.7% |
| Structured | 169,258 | 15.6% |

### Product Type Definitions

| Type | Description |
|------|-------------|
| **MYGA** | Multi-Year Guaranteed Annuity - fixed rate locked for entire term (3-10 years), like a CD with tax deferral |
| **FIA** | Fixed Indexed Annuity - returns linked to index (S&P 500) with 0% floor (can't lose principal) |
| **RILA** | Registered Index-Linked Annuity (Structured) - higher upside than FIA but accepts limited downside via buffer/floor |
| **FA** | Traditional Fixed Annuity - rate guaranteed one year at a time, resets annually |
| **IVA** | Variable Annuity - invested in subaccounts (mutual funds), full market exposure |

---

## Status Filtering Guide

| status | Rows | Description | Use For Analysis? |
|--------|------|-------------|-------------------|
| `historic` | 756,210 | Past/superseded rate records | Historical trends only |
| `current` | 251,594 | Currently active rates | **Yes - primary analysis** |
| `nlam` | 78,385 | No Longer Actively Marketed | Closed products |
| `new` | 1,062 | Recently added | Yes |
| `market_status` | 2 | System records | No |

**Recommendation**: Filter to `status == 'current'` for competitive rate analysis.

---

## Column Reference

### 1. Product Classification

| Column | Type | Non-Null | Description |
|--------|------|----------|-------------|
| `productGroup` | string | 100.0% | High-level category: MYGA, FIA, FA, RILA, IVA |
| `productTypeID` | float64 | 100.0% | Numeric ID: 1.0=FIA, 2.0=FA, 3.0=MYGA, 4.0=RILA, 5.0=IVA |
| `productTypeName` | string | 100.0% | "MYG Fixed", "Fixed Indexed", "Structured", "Traditional Fixed", "Variable" |
| `productID` | int64 | 100.0% | Unique product identifier (1-4,679) |
| `productName` | string | 100.0% | Full product name (3,437 unique) |
| `productNameSuffix` | string | 13.1% | Channel/state variant: "(NY)", "(Wells Fargo)", "(Edward Jones)", etc. |
| `productMarketStatus` | string | 100.0% | "Actively Marketed" (80%) or "No Longer Actively Marketed" (20%) |
| `rateType` | string | 100.0% | Fixed, Indexed, Structured, Variable |

### 2. Company Information

| Column | Type | Non-Null | Description |
|--------|------|----------|-------------|
| `companyID` | float64 | 100.0% | Unique company identifier (1-549) |
| `companyName` | string | 100.0% | Insurance carrier name (174 unique) |
| `amBestRating` | string | 100.0% | AM Best financial strength rating |

**amBestRating Values**: A++, A+, A, A-, B++, B+, B, B-, C++, E, NR (Not Rated)

### 3. Rate Fields

| Column | Type | Non-Null | Min | Max | Mean | Median | Description |
|--------|------|----------|-----|-----|------|--------|-------------|
| `fixedRate` | float64 | 15.7% | 0.0005 | 0.51 | 0.0295 | 0.027 | Guaranteed interest rate. **Scale**: Decimal (0.03 = 3%) |
| `capRate` | float64 | 23.9% | 0 | 9999.99 | 0.55 | 0.0935 | Maximum return cap. **Caution**: Outliers exist (p99=7.0) |
| `participationRate` | float64 | 41.8% | 0 | 9.0 | 1.027 | 1.0 | % of index gain credited. **Scale**: 1.0 = 100% |
| `spreadRate` | float64 | 2.6% | -0.0725 | 99.0 | 0.034 | 0.023 | Fee deducted from index return. **Scale**: Decimal |
| `performanceTriggeredRate` | float64 | 4.9% | 0 | 999.0 | 0.241 | 0.0775 | Fixed rate if index positive. **Caution**: Outliers, use median |
| `effectiveYield` | float64 | 13.1% | -0.031 | 4.85 | 0.0306 | 0.0285 | Calculated effective annual yield |
| `effectiveannualrate` | float32 | **1.2%** | 0.0085 | 0.10 | 0.043 | 0.0435 | Effective annual rate (very sparse) |
| `averageannualrate` | float32 | **1.2%** | 0.0085 | 0.10 | 0.043 | 0.0435 | Average annual rate (very sparse) |

### 4. Bonus Rate Fields

All bonus fields are 100% populated but mostly zeros (bonuses are optional product features).

| Column | Type | Max | Mean | Description |
|--------|------|-----|------|-------------|
| `bonusRate` | float64 | 0.50 | 0.0054 | Primary bonus rate (alias for bonusRate1) |
| `bonusRate1` | float64 | 0.50 | 0.0054 | First-year/tier bonus |
| `bonusRate2` | float64 | 0.215 | 0.0008 | Second-year/tier bonus |
| `bonusRate3` | float64 | 0.20 | 0.0002 | Third-year/tier bonus |
| `bonusRate4` | float64 | 0.18 | 0.00001 | Fourth-year/tier bonus |
| `bonusRate5` | float64 | 0.12 | 0.000002 | Fifth-year/tier bonus |
| `bonusRate1Footnote` | string | - | - | Free-text conditions (9.4% populated) |
| `bonusRate2Footnote` | string | - | - | Free-text conditions (1.4% populated) |

**Scale**: Decimal (0.05 = 5% bonus)

### 5. Buffer/Downside Protection (RILA)

| Column | Type | Non-Null | Min | Max | Mean | Description |
|--------|------|----------|-----|-----|------|-------------|
| `bufferRate` | float64 | 15.5% | -0.10 | 1.0 | 0.149 | % of losses absorbed by insurer |
| `bufferModifier` | string | 15.6% | - | - | - | Type of downside protection |

**bufferModifier Values**:
| Value | Count | Description |
|-------|-------|-------------|
| Losses Covered Up To | 144,259 | Buffer: insurer absorbs first X% of losses |
| Losses Covered After | 15,141 | Floor: you absorb first X%, insurer covers rest |
| No Downside Risk | 5,259 | Full principal protection (like FIA) |
| Percentage of Losses Covered | 1,613 | Partial loss absorption |
| Percentage of Losses Covered Up To | 1,589 | Variant of buffer |
| Loss Limiter | 421 | Caps maximum loss |
| Negative Participation Rate | 231 | Inverse participation on downside |

**Note**: 135 rows have negative `bufferRate` (-10%) representing floors.

### 6. MGSV Fields (Nonforfeiture)

Per NAIC Standard Nonforfeiture Law (Model #805): Minimum Guaranteed Surrender Value protects consumers from combined surrender charges + negative MVA.

| Column | Type | Non-Null | Min | Max | Mean | Description |
|--------|------|----------|-----|-----|------|-------------|
| `mgsvBaseRate` | float64 | 34.6% | 0 | 1.0 | **0.8749** | **Statutory 87.5% of premium factor** (NOT an interest rate) |
| `mgsvRate` | float64 | 34.6% | 0 | 0.035 | 0.010 | Annual MGSV interest rate (1-3% per NAIC) |
| `mgsvRateUpperBound` | float64 | 33.2% | 0 | 0.05 | 0.030 | Maximum MGSV rate allowed |
| `minGuaranteedSurrValue` | string | 43.4% | - | - | - | Free-text description of MGSV terms |

**Formula**: MGSV = `mgsvBaseRate` × Premiums × (1 + `mgsvRate`)^years

### 7. Index/Crediting Fields

| Column | Type | Non-Null | Description |
|--------|------|----------|-------------|
| `indexUsed` | string | 59.3% | Underlying market index (425 unique) |
| `indexingMethod` | string | 59.3% | How index returns calculated (90 unique) |
| `indexCreditingFrequency` | string | 59.3% | How often interest credited (18 unique) |
| `defaultActuarialView` | string | 59.3% | Actuarial calculation view (138 unique) |
| `othercreditingstrategyinformation` | string | 2.7% | Free-text additional details |

**Top indexUsed Values**:
- S&P 500: 187,000
- N/A: 171,199 (fixed products)
- Russell 2000: 47,598
- MSCI EAFE: 39,853
- NASDAQ-100: 25,896

**Top indexingMethod Values**:
| Method | Count | Description |
|--------|-------|-------------|
| Annual PTP | 242,004 | Point-to-Point: compare start vs end of year |
| Fixed w/ MYG | 123,334 | Fixed rate with multi-year guarantee |
| Term End Point | 62,223 | Compare start vs end of multi-year term |
| 2 Yr. PTP | 41,755 | Two-year point-to-point |
| Performance triggered | 38,789 | Fixed rate paid if index is positive |
| Mo. Avg. | 17,488 | Monthly averaging |
| Mo. PTP | 17,285 | Monthly point-to-point with caps |

**indexCreditingFrequency Distribution**:
- Annual: 338,741
- Daily: 144,922
- Biennial (2 yr): 49,964
- 6 years: 47,497
- 3 years: 25,503

### 8. Variable Annuity Fields

| Column | Type | Non-Null | Description |
|--------|------|----------|-------------|
| `subaccountUsed` | string | 40.7% | Investment subaccount name (6,997 unique) |
| `fundManager` | string | 40.7% | Asset manager (684 unique) |
| `fundGroup` | string | 100.0% | Fund family/category (19 unique) |
| `shareClass` | string | 57.1% | Variable annuity share class |

**shareClass Distribution**:
| Class | Count | Surrender | M&E Fees | Best For |
|-------|-------|-----------|----------|----------|
| B Share | 296,585 | 5-8 years | Lower | Long-term |
| I Share | 177,407 | - | Institutional | Advisors |
| C Share | 74,851 | None | Higher | Liquidity |
| L Share | 39,904 | 3-4 years | Higher | Flexibility |
| X Share | 17,302 | Various | - | - |
| O Share | 11,775 | Various | - | - |
| A Share | 2,734 | None | Lowest | Large investments |

### 9. Guarantee/Duration Fields

| Column | Type | Non-Null | Min | Max | Mean | Description |
|--------|------|----------|-----|-----|------|-------------|
| `guaranteeDuration` | float64 | 18.2% | **-1** | 20 | 3.75 | Years rate/terms guaranteed |
| `surrChargeDuration` | string | 100.0% | - | - | - | Years surrender charges apply |
| `mva` | object | 100.0% | - | - | - | Market Value Adjustment flag |

**guaranteeDuration by productGroup**:
| productGroup | Count | Min | Max | Mean | Notes |
|--------------|-------|-----|-----|------|-------|
| MYGA | 122,492 | 1 | 20 | 5.28 | Core field for MYGAs |
| FA | 10,072 | 0 | 6 | 1.01 | Typically 1-year guarantees |
| FIA | 49,950 | **-1** | 20 | 1.28 | Contains -1 outliers |
| RILA | 10,602 | 1 | 6 | 1.04 | |
| IVA | 5,241 | 1 | 10 | 2.25 | Sparse |

**Cleaning Required**: Filter `guaranteeDuration >= 0` to remove -1 outliers.

**surrChargeDuration Top Values**:
- 0 years: 269,010 (no charge)
- 7 years: 256,210 (most common)
- 5 years: 152,197
- 6 years: 133,436
- 10 years: 128,714

**mva Values**: Boolean stored as object
- False: 667,382 (61.4%)
- True: 419,869 (38.6%)

### 10. Premium/Tier Fields

| Column | Type | Non-Null | Description |
|--------|------|----------|-------------|
| `premiumBand` | string | 31.4% | Premium tier in $000s (e.g., "0", "100", "250") |
| `ratesBand` | string | 31.4% | Rate tier with labels (e.g., "$100k", "< $100k") |

Higher premiums typically receive better rates.

### 11. Fee/Expense Fields

| Column | Type | Non-Null | Min | Max | Mean | Description |
|--------|------|----------|-----|-----|------|-------------|
| `annualFeeForIndexingMethod` | float64 | 2.0% | 0.0005 | 0.075 | 0.0135 | Annual fee for indexed crediting |
| `netExpenseRatio` | float64 | 40.7% | -0.0078 | 1.01 | 0.0075 | Net expense ratio for variable subaccounts |
| `streetLevelComp` | float64 | 22.1% | 0 | 0.15 | 0.0545 | Agent commission rate |

### 12. Temporal Fields

| Column | Type | Non-Null | Min | Max | Description |
|--------|------|----------|-----|-----|-------------|
| `date` | datetime64 | 100.0% | 2005-08-01 | 2025-11-08 | Record/observation date |
| `effectiveDate` | datetime64 | 100.0% | 2005-08-01 | 2025-11-08 | When rate became active |
| `greatest_date` | datetime64 | **99.7%** | 2021-02-05 | 2025-11-08 | Most recent update timestamp |
| `createdDate` | datetime64 | 100.0% | 2021-02-05 | 2025-11-05 | Record creation timestamp |
| `modifiedDate` | datetime64 | 100.0% | 2021-02-05 | 2025-11-08 | Record modification timestamp |

### 13. Metadata/Audit Fields

| Column | Type | Non-Null | Description |
|--------|------|----------|-------------|
| `rateID` | int64 | 100.0% | Unique rate record identifier (0-548,492) |
| `fundproductgrp_dim_key` | string | 100.0% | Dimensional key for data warehouse joins (41 unique) |
| `rowNumber` | float64 | 100.0% | Row sequence number |
| `rowVersion` | int64 | 100.0% | Version for optimistic locking |
| `status` | string | 100.0% | historic, current, nlam, new, market_status |
| `createdBy` | string | 100.0% | Creator email (9 unique) |
| `modifiedBy` | string | 100.0% | Modifier email (13 unique) |

---

## Product Applicability Matrix

Which rate fields are populated for each productGroup (% of rows within that group):

| Field | MYGA | FA | FIA | RILA | IVA |
|-------|------|-----|-----|------|-----|
| `fixedRate` | **99.9%** | **99.7%** | 10.5% | 0.3% | 0.7% |
| `capRate` | - | - | 41.7% | **68.8%** | 2.3% |
| `participationRate` | 17.0%* | 30.5%* | **86.0%** | **81.4%** | 2.9% |
| `spreadRate` | - | 0.3% | 7.4% | 1.8% | 0.1% |
| `bufferRate` | - | - | 0.6% | **96.8%** | 2.6% |
| `performanceTriggeredRate` | 0.1%* | - | 6.1% | 17.0% | 1.1% |
| `effectiveYield` | **97.9%** | **70.9%** | 4.1% | 0.1% | 0.5% |
| `guaranteeDuration` | **100%** | **99.7%** | 15.0% | 6.6% | 1.1% |
| `mgsvRate` | 31.4% | 20.4% | **99.1%** | 2.9% | - |

*Low percentages in unexpected columns = data noise, not true applicability

**Legend**:
- **Bold** = Primary/expected field for this product type
- `-` = <0.1% or 0 rows
- `*` = Noise/anomaly

---

## Data Quality Notes

### 1. Percent Fields Stored as Decimals
All rate fields use decimal representation:
- 0.03 = 3%
- 1.0 = 100% (for participationRate)
- 0.875 = 87.5% (for mgsvBaseRate)

### 2. Outliers Requiring Attention

| Field | Issue | Recommendation |
|-------|-------|----------------|
| `capRate` | max=9999.99, 5 values >10 | Clip to ≤10.0 or filter |
| `performanceTriggeredRate` | max=999.0, 9 values >1.0 | Clip to ≤1.0 or filter |
| `bufferRate` | 135 values < 0 (min=-0.10) | May be valid (floor products) |
| `guaranteeDuration` | Contains -1 values | Filter ≥0 |
| `effectiveYield` | max=4.85 (485%) | Verify or filter |

### 3. Sparse Columns (<5% populated)

| Column | Non-Null % | Notes |
|--------|-----------|-------|
| `effectiveannualrate` | 1.2% | Very limited use |
| `averageannualrate` | 1.2% | Very limited use |
| `annualFeeForIndexingMethod` | 2.0% | Indexed products only |
| `spreadRate` | 2.6% | FIA only |
| `othercreditingstrategyinformation` | 2.7% | Free text |
| `performanceTriggeredRate` | 4.9% | Indexed/Structured only |

### 4. String Values Requiring Coercion

- `mva`: Boolean stored as object (False/True strings)
- `surrChargeDuration`: Numeric years as strings
- `premiumBand`: Numeric values as strings

---

## Recommended Cleaning Steps

```python
import pandas as pd
import numpy as np

df = pd.read_parquet('wink.parquet')

# 1. Filter to current rates for analysis
df_current = df[df['status'] == 'current'].copy()

# 2. Remove guaranteeDuration outliers
df_current = df_current[
    (df_current['guaranteeDuration'].isna()) |
    (df_current['guaranteeDuration'] >= 0)
]

# 3. Clip extreme rate values
df_current['capRate'] = df_current['capRate'].clip(upper=10.0)
df_current['performanceTriggeredRate'] = df_current['performanceTriggeredRate'].clip(upper=1.0)

# 4. Convert mva to boolean
df_current['mva'] = df_current['mva'].map({True: True, False: False, 'True': True, 'False': False})

# 5. Convert surrChargeDuration to numeric where possible
df_current['surrChargeDuration_num'] = pd.to_numeric(
    df_current['surrChargeDuration'], errors='coerce'
)

# 6. Filter by product type for focused analysis
df_myga = df_current[df_current['productGroup'] == 'MYGA']
df_fia = df_current[df_current['productGroup'] == 'FIA']
df_rila = df_current[df_current['productGroup'] == 'RILA']
```

---

## References

### Data Source
- [WINK, Inc.](https://www.winkintel.com/)
- [AnnuitySpecs](https://www.winkintel.com/analysis-tools/annuityspecs/)

### Regulatory
- [FINRA Regulatory Notice 22-08 (Complex Products)](https://www.finra.org/rules-guidance/notices/22-08)
- [NAIC Standard Nonforfeiture Law (Model #805/806)](https://content.naic.org/sites/default/files/model-law-808.pdf)

### Market Data
- [LIMRA: 2024 Retail Annuity Sales Record $434.1B](https://www.limra.com/en/newsroom/news-releases/2025/limra-2024-retail-annuity-sales-grow-12-to-a-record-$434.1-billion/)

### Product Education
- [MYGA Explained (Annuity.org)](https://www.annuity.org/annuities/types/fixed/myga/)
- [FIA Crediting Methods (Pacific Life)](https://www.annuities.pacificlife.com/content/dam/paclife/rsd/annuities/public/pdfs/guide/understanding-fixed-indexed-annuity-interest-crediting-methods.pdf)
- [RILA Explained (Annuity.org)](https://www.annuity.org/annuities/types/registered-index-linked-annuities/)
- [Market Value Adjustment (Annuity.org)](https://www.annuity.org/annuities/rates/market-value-adjustment/)
