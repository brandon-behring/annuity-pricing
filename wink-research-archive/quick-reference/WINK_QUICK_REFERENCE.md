# WINK Data Quick Reference

One-page cheat sheet for working with `wink.parquet`.

---

## Dataset Overview

| Metric | Value |
|--------|-------|
| **Rows** | 1,087,253 |
| **Columns** | 62 |
| **Date Range** | 2005-08-01 to 2025-11-08 |
| **File Size** | 38.2 MB |

---

## Product Group Counts

| productGroup | productTypeName | Rows | % |
|--------------|-----------------|------|---|
| IVA | Variable | 460,264 | 42.3% |
| FIA | Fixed Indexed | 334,074 | 30.7% |
| RILA | Structured | 160,294 | 14.7% |
| MYGA | MYG Fixed | 122,513 | 11.3% |
| FA | Traditional Fixed | 10,106 | 0.9% |

---

## Common Filters

### Filter to Current Rates Only
```python
df_current = df[df['status'] == 'current']  # 251,594 rows
```

### Filter by Product Type
```python
df_myga = df[df['productGroup'] == 'MYGA']  # 122,513 rows
df_fia = df[df['productGroup'] == 'FIA']    # 334,074 rows
df_rila = df[df['productGroup'] == 'RILA']  # 160,294 rows
```

### Combine Filters
```python
df_current_myga = df[
    (df['status'] == 'current') &
    (df['productGroup'] == 'MYGA')
]
```

---

## Key Columns by Product Type

### MYGA
```python
myga_cols = ['companyName', 'productName', 'fixedRate', 'guaranteeDuration',
             'effectiveYield', 'mva', 'surrChargeDuration', 'premiumBand']
```

### FIA
```python
fia_cols = ['companyName', 'productName', 'capRate', 'participationRate',
            'spreadRate', 'indexUsed', 'indexingMethod', 'indexCreditingFrequency']
```

### RILA
```python
rila_cols = ['companyName', 'productName', 'bufferRate', 'bufferModifier',
             'capRate', 'participationRate', 'indexUsed', 'indexingMethod']
```

### IVA (Variable)
```python
iva_cols = ['companyName', 'productName', 'subaccountUsed', 'fundManager',
            'shareClass', 'netExpenseRatio']
```

---

## Data Cleaning Snippets

### Remove Outliers
```python
# Cap rate outliers (max 9999.99)
df['capRate'] = df['capRate'].clip(upper=10.0)

# Performance triggered outliers (max 999)
df['performanceTriggeredRate'] = df['performanceTriggeredRate'].clip(upper=1.0)

# Guarantee duration -1 values
df = df[df['guaranteeDuration'] >= 0]
```

### Convert Data Types
```python
# Surrender duration to numeric
df['surrChargeDuration_num'] = pd.to_numeric(df['surrChargeDuration'], errors='coerce')

# Premium band to numeric
df['premiumBand_num'] = pd.to_numeric(df['premiumBand'], errors='coerce')
```

### Scale Interpretation
```python
# All rates are decimals
# 0.05 = 5%
# 1.0 = 100% (for participationRate)
# 0.875 = 87.5% (for mgsvBaseRate)
```

---

## Status Values

| status | Rows | Description |
|--------|------|-------------|
| historic | 756,210 | Past rates |
| **current** | **251,594** | **Active rates (use this)** |
| nlam | 78,385 | No Longer Actively Marketed |
| new | 1,062 | Recently added |
| market_status | 2 | System |

---

## Rate Field Applicability

| Field | MYGA | FA | FIA | RILA | IVA |
|-------|:----:|:--:|:---:|:----:|:---:|
| fixedRate | ✓ | ✓ | - | - | - |
| capRate | - | - | ✓ | ✓ | - |
| participationRate | - | - | ✓ | ✓ | - |
| spreadRate | - | - | ✓ | - | - |
| bufferRate | - | - | - | ✓ | - |
| guaranteeDuration | ✓ | ✓ | - | - | - |
| effectiveYield | ✓ | ✓ | - | - | - |

---

## Null Percentages (Key Fields)

| Column | Non-Null % | Notes |
|--------|-----------|-------|
| fixedRate | 15.7% | MYGA/FA only |
| capRate | 23.9% | FIA/RILA only |
| participationRate | 41.8% | FIA/RILA |
| bufferRate | 15.5% | RILA only |
| guaranteeDuration | 18.2% | MYGA/FA |
| effectiveannualrate | 1.2% | Very sparse |
| performanceTriggeredRate | 4.9% | Sparse |

---

## Quick Stats

### MYGA Fixed Rates
```python
df_myga['fixedRate'].describe()
# mean: 2.95%
# min: 0.05%
# max: 51% (outlier)
# median: 2.70%
```

### FIA Cap Rates
```python
df_fia['capRate'].describe()
# mean: 55% (includes outliers)
# median: 9.35%
# p99: 7.0%
# Filter: capRate <= 10
```

### RILA Buffer Rates
```python
df_rila['bufferRate'].describe()
# mean: 14.9%
# median: 10%
# common: 10%, 15%, 20%
```

---

## Load Data

```python
import pandas as pd

# Load full dataset
df = pd.read_parquet('wink.parquet')

# Load with specific columns
df = pd.read_parquet('wink.parquet',
    columns=['companyName', 'productGroup', 'fixedRate', 'status'])

# Load current MYGA rates only
df = pd.read_parquet('wink.parquet')
df = df[(df['status'] == 'current') & (df['productGroup'] == 'MYGA')]
```

---

## Useful Aggregations

### Average Rate by Company (MYGA)
```python
df_myga.groupby('companyName')['fixedRate'].mean().sort_values(ascending=False)
```

### Rate Distribution by Guarantee Duration
```python
df_myga.groupby('guaranteeDuration')['fixedRate'].agg(['mean', 'count'])
```

### Product Count by Company
```python
df.groupby(['companyName', 'productGroup']).size().unstack(fill_value=0)
```
