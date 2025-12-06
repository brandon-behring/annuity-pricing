# Research Notes

Original research and planning notes from the WINK dataset exploration.

---

## Research Process

1. **Initial Exploration**: Read parquet schema (62 columns, 1,087,253 rows)
2. **Gap Analysis Round 1**: Identified 27 undocumented columns
3. **Domain Research**: Researched MYGA, FIA, RILA, FA, IVA product types
4. **Gap Analysis Round 2**: Identified data quality issues
5. **Documentation**: Created comprehensive data dictionary

---

## Key Domain Knowledge Gathered

### Product Types

| Type | Full Name | Key Characteristic |
|------|-----------|-------------------|
| **MYGA** | Multi-Year Guaranteed Annuity | Fixed rate locked entire term (3-10 years) |
| **FIA** | Fixed Indexed Annuity | Index-linked returns with 0% floor |
| **RILA** | Registered Index-Linked Annuity | Higher upside, accepts limited downside via buffer/floor |
| **FA** | Traditional Fixed Annuity | Rate guaranteed one year, resets annually |
| **IVA** | Variable Annuity | Invested in subaccounts, full market exposure |

### FIA Crediting Methods

1. **Cap Rate**: Maximum return you can earn
2. **Participation Rate**: Percentage of index gain credited
3. **Spread (Margin)**: Fee subtracted from index return
4. **Performance Triggered**: Fixed rate if index has any positive return

### RILA Protection Strategies

1. **Buffer**: Insurer absorbs first X% of losses (e.g., 10% buffer = you absorb losses beyond 10%)
2. **Floor**: You absorb losses up to X%, insurer covers the rest (e.g., -10% floor = max loss is 10%)

### Key Concepts

1. **MVA (Market Value Adjustment)**: Adjusts surrender value based on interest rate changes
   - Rates rise → Negative MVA (reduces value)
   - Rates fall → Positive MVA (increases value)

2. **MGSV (Minimum Guaranteed Surrender Value)**: Statutory minimum per NAIC
   - Formula: 87.5% × Premiums × (1 + rate)^years
   - `mgsvBaseRate` = 0.875 (87.5% factor, not an interest rate)

3. **Surrender Charges**: Percentage deducted for early withdrawal
   - Typically 7% year 1, declining to 0% by year 7-8
   - Most contracts allow 10% annual penalty-free withdrawals

---

## Data Quality Findings

### Outliers Requiring Clipping

| Field | Issue | Recommendation |
|-------|-------|----------------|
| `capRate` | max=9999.99 | Clip to ≤10 (1000%) |
| `performanceTriggeredRate` | max=999 | Clip to ≤1 (100%) |
| `spreadRate` | max=99.0 | Clip to ≤1 |

### Bad Values

| Field | Issue | Recommendation |
|-------|-------|----------------|
| `guaranteeDuration` | Contains -1 | Filter to ≥0 |
| `mva` | Two "None" string values | Coerce to null |

### Sparse Columns

| Field | Non-Null % | Notes |
|-------|-----------|-------|
| `effectiveannualrate` | 1.2% | Very sparse |
| `averageannualrate` | 1.2% | Very sparse |
| `performanceTriggeredRate` | 4.9% | Indexed/Structured only |

### Field Applicability by Product

| Field | MYGA | FA | FIA | RILA | IVA |
|-------|:----:|:--:|:---:|:----:|:---:|
| fixedRate | ✓ | ✓ | - | - | - |
| capRate | - | - | ✓ | ✓ | - |
| participationRate | - | - | ✓ | ✓ | - |
| spreadRate | - | - | ✓ | - | - |
| bufferRate | - | - | - | ✓ | - |
| guaranteeDuration | ✓ | ✓ | - | - | - |

---

## Market Context (LIMRA 2024)

| Metric | Value |
|--------|-------|
| Total annuity sales | $434.1B (record) |
| FIA sales | $125.5B (+31% YoY) |
| RILA sales | $65.6B (+38% YoY) |
| RILA streak | 10 consecutive record years |

---

## References Consulted

### Data Source
- [WINK, Inc.](https://www.winkintel.com/)
- [AnnuitySpecs](https://www.winkintel.com/analysis-tools/annuityspecs/)

### Regulatory
- [FINRA Notice 22-08](https://www.finra.org/rules-guidance/notices/22-08) - Complex products guidance
- [NAIC Nonforfeiture Law](https://content.naic.org/sites/default/files/model-law-808.pdf) - MGSV requirements

### Market Data
- [LIMRA Reports](https://www.limra.com/en/newsroom/news-releases/)

---

*Notes compiled: 2025-12-04*
