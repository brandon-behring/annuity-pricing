# WINK Research Archive

Comprehensive documentation and research materials for the WINK, Inc. annuity dataset.

---

## Contents

```
wink-research-archive/
├── README.md                          # This file
├── data-dictionary/
│   └── WINK_DATA_DICTIONARY.md        # Complete 62-column reference
├── product-guides/
│   └── ANNUITY_PRODUCT_GUIDE.md       # Educational guide to annuity types
├── quick-reference/
│   └── WINK_QUICK_REFERENCE.md        # One-page cheat sheet
├── gap-reports/
│   ├── gap-report-round1.md           # Initial coverage analysis
│   └── gap-report-round2.md           # Data quality findings
└── research-notes/
    └── plan-notes.md                  # Original research notes
```

---

## Quick Start

### 1. Load the Data
```python
import pandas as pd
df = pd.read_parquet('wink.parquet')
```

### 2. Filter to Current Rates
```python
df_current = df[df['status'] == 'current']  # 251,594 rows
```

### 3. Select Product Type
```python
df_myga = df_current[df_current['productGroup'] == 'MYGA']
df_fia = df_current[df_current['productGroup'] == 'FIA']
df_rila = df_current[df_current['productGroup'] == 'RILA']
```

---

## Dataset Summary

| Attribute | Value |
|-----------|-------|
| **Source** | WINK, Inc. (winkintel.com) |
| **Rows** | 1,087,253 |
| **Columns** | 62 |
| **Date Range** | 2005-08-01 to 2025-11-08 |
| **File Size** | 38.2 MB |

### Product Mix

| Type | Description | Rows | % |
|------|-------------|------|---|
| **MYGA** | Multi-Year Guaranteed Annuity | 122,513 | 11.3% |
| **FIA** | Fixed Indexed Annuity | 334,074 | 30.7% |
| **RILA** | Registered Index-Linked Annuity | 160,294 | 14.7% |
| **FA** | Traditional Fixed Annuity | 10,106 | 0.9% |
| **IVA** | Variable Annuity | 460,264 | 42.3% |

---

## Document Guide

### For Understanding the Data Schema
→ **Read:** `data-dictionary/WINK_DATA_DICTIONARY.md`

Full reference for all 62 columns including:
- Data types and null percentages
- Value ranges and distributions
- Product applicability matrix
- Recommended cleaning steps

### For Learning About Annuity Products
→ **Read:** `product-guides/ANNUITY_PRODUCT_GUIDE.md`

Educational guide covering:
- What each product type is and how it works
- MYGA vs FIA vs RILA vs FA vs IVA
- Crediting methods (caps, participation, spreads)
- Buffer vs floor strategies
- MVA and MGSV concepts

### For Quick Code Snippets
→ **Read:** `quick-reference/WINK_QUICK_REFERENCE.md`

One-page cheat sheet with:
- Common filters
- Key columns by product type
- Data cleaning code
- Quick aggregations

### For Data Quality Issues
→ **Read:** `gap-reports/gap-report-round2.md`

Identified issues:
- Outliers in capRate, performanceTriggeredRate
- Sparse columns (effectiveannualrate: 1.2%)
- mgsvBaseRate interpretation (87.5% factor, not rate)
- guaranteeDuration -1 values

---

## Key Findings

### Data Quality Notes

1. **Filter to current**: Use `status == 'current'` for analysis
2. **Clip outliers**:
   - `capRate` max=9999.99 → clip to ≤10
   - `performanceTriggeredRate` max=999 → clip to ≤1
3. **Remove bad values**: `guaranteeDuration >= 0`
4. **Scale is decimal**: 0.03 = 3%, 1.0 = 100%

### Field Applicability

| Field | Applies To |
|-------|------------|
| fixedRate | MYGA, FA |
| capRate | FIA, RILA |
| participationRate | FIA, RILA |
| bufferRate | RILA only |
| guaranteeDuration | MYGA, FA |

---

## Market Context (2024)

| Metric | Value |
|--------|-------|
| Total Annuity Sales | $434.1B (record) |
| FIA Sales | $125.5B (+31% YoY) |
| RILA Sales | $65.6B (+38% YoY) |
| RILA Streak | 10 consecutive records |

Source: LIMRA

---

## References

### Data Source
- [WINK, Inc.](https://www.winkintel.com/)
- [AnnuitySpecs](https://www.winkintel.com/analysis-tools/annuityspecs/)

### Regulatory
- [FINRA Notice 22-08](https://www.finra.org/rules-guidance/notices/22-08)
- [NAIC Nonforfeiture Law](https://content.naic.org/sites/default/files/model-law-808.pdf)

### Market Data
- [LIMRA Reports](https://www.limra.com/en/newsroom/news-releases/)

---

*Archive created: 2025-12-04*
