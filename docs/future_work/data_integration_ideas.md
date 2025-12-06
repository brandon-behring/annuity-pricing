# Data Integration Ideas for Annuity Pricing

**Created**: 2025-12-05
**Source**: ChatGPT landscape analysis (`chat_gpt_what_exists.md`)
**Status**: Future work proposals

---

## Overview

The ChatGPT analysis identified several data integration opportunities that would make the annuity-pricing library more "plug-and-play." This document captures those ideas for future implementation.

---

## 1. Treasury Yield Curve API

### Goal
Provide easy access to current U.S. Treasury yield curves for pricing scenarios.

### Data Sources

| Source | API | Content |
|--------|-----|---------|
| **FRED** (Federal Reserve) | `fredapi` | Daily Treasury rates (DGS1, DGS2, DGS5, DGS10, DGS30) |
| **Treasury.gov** | XML/CSV | Daily par yield curve |
| **Quandl** | `quandl` | Historical rates |

### Proposed Interface

```python
from annuity_pricing.data import treasury

# Get current yield curve
curve = treasury.get_current_curve()
# Returns: {1: 0.045, 2: 0.042, 5: 0.040, 10: 0.041, 30: 0.043}

# Get historical curve
curve = treasury.get_curve(date="2024-01-15")

# Bootstrap zero curve
zero_curve = treasury.bootstrap_zero_curve(curve)
```

### Implementation Notes

- Use `fredapi` with free API key
- Cache results to avoid rate limits
- Provide fallback to embedded sample data

---

## 2. Equity Volatility Surface

### Goal
Access current implied volatility data for RILA option pricing.

### Data Sources

| Source | API | Content |
|--------|-----|---------|
| **CBOE** | Delayed CSV | VIX, SPX implied vols |
| **Yahoo Finance** | `yfinance` | Option chains with IVs |
| **FRED** | `fredapi` | VIXCLS (VIX close) |

### Proposed Interface

```python
from annuity_pricing.data import volatility

# Get current VIX
vix = volatility.get_vix()  # Returns: 18.5

# Get SPX vol surface
surface = volatility.get_spx_surface()
# Returns DataFrame: strike x expiry → implied_vol

# Interpolate for specific parameters
vol = volatility.get_implied_vol(
    underlying="SPX",
    strike_pct=0.90,  # 90% moneyness
    expiry_days=365
)
```

### Implementation Notes

- VIX from FRED is simplest (no API key required for basic)
- Full surface requires `yfinance` or paid data
- Consider caching with daily refresh

---

## 3. Scenario File Standards

### Goal
Provide standardized scenario files consistent with regulatory requirements.

### VM-21 Risk-Neutral Scenarios

| Component | Format | Source |
|-----------|--------|--------|
| **Equity scenarios** | CSV/Parquet | AAA ESG or equivalent |
| **Interest rate scenarios** | CSV/Parquet | AAA or prescribed |
| **Number of scenarios** | 1,000-10,000 | Per VM-21 guidance |

### AG43 Standard Scenario

```python
from annuity_pricing.scenarios import ag43

# Get prescribed interest rate shocks
shocks = ag43.get_standard_scenario()
# Returns: {"up_100bp": {...}, "down_100bp": {...}, ...}

# Apply to base curve
stressed_curve = ag43.apply_shock(base_curve, "up_100bp")
```

### AAA ESG Format

```python
from annuity_pricing.scenarios import aaa_esg

# Load AAA-style equity scenarios
scenarios = aaa_esg.load_equity_scenarios(
    n_scenarios=1000,
    horizon_years=30,
    frequency="monthly"
)
# Returns: DataFrame (scenario_id x time → return)
```

### Implementation Notes

- AAA generator is proprietary; provide compatible format
- EconomicScenarioGenerators.jl has Julia implementation
- Consider embedded sample scenarios for testing

---

## 4. Sample Datasets

### Goal
Embed sample datasets for testing, tutorials, and validation.

### Proposed Datasets

| Dataset | Format | Content |
|---------|--------|---------|
| **Historical yield curves** | Parquet | 10+ years of Treasury rates |
| **Sample mortality experience** | CSV | Anonymized lapse/mortality data |
| **Economic indicators** | Parquet | VIX, rates, equity returns |
| **RILA product specs** | JSON | Sample product parameters |

### Interface

```python
from annuity_pricing.data import samples

# Load sample yield curve history
yields = samples.load_yield_history()  # 2010-2024 Treasury rates

# Load sample mortality table
table = samples.load_mortality("soa_2012_iam")

# Load sample RILA spec
rila = samples.load_product("sample_rila_10_buffer")
```

### Implementation Notes

- Keep file sizes small (<10MB total)
- Use Parquet for time series (efficient compression)
- Include data dictionary

---

## 5. SOA Mortality Tables

### Current State

- Julia: MortalityTables.jl has comprehensive SOA tables
- Python: lifelib has some; actuarialmath has basics
- Our repo: Limited

### Proposed Enhancement

```python
from annuity_pricing.mortality import tables

# List available tables
tables.list_tables()
# ['soa_2012_iam', 'soa_2017_cso', 'soa_2015_vbt', ...]

# Load specific table
iam = tables.load("soa_2012_iam")
qx_65 = iam.qx(65)  # Mortality rate at age 65

# Load with select period
select_table = tables.load("soa_2015_vbt", select_period=25)
```

### Sources

- SOA website (free download)
- MortalityTables.jl (can extract/convert)
- actuarialmath (Python reference)

---

## 6. Economic Data Integrations

### FRED Integration

```python
from annuity_pricing.data import fred

# Configure API key (one-time)
fred.set_api_key("your_key")

# Get series
dgs10 = fred.get_series("DGS10", start="2020-01-01")
vix = fred.get_series("VIXCLS", start="2020-01-01")

# Get multiple series aligned
data = fred.get_multi(["DGS10", "DGS30", "VIXCLS"], start="2020-01-01")
```

### Useful FRED Series

| Series | Description |
|--------|-------------|
| DGS1, DGS2, DGS5, DGS10, DGS30 | Treasury constant maturity |
| DFII10 | 10-year TIPS |
| VIXCLS | VIX close |
| SP500 | S&P 500 index |
| CPIAUCSL | CPI (inflation) |

---

## 7. Implementation Priority

### Phase 1: Embedded Samples (Low Effort)

- [ ] Add sample yield curve history (Parquet)
- [ ] Add SOA 2012 IAM mortality table
- [ ] Add sample RILA product specs (JSON)

### Phase 2: FRED Integration (Medium Effort)

- [ ] Create `fred.py` module
- [ ] Add Treasury curve functions
- [ ] Add VIX retrieval

### Phase 3: Scenario Standards (Higher Effort)

- [ ] Document AG43 standard scenario format
- [ ] Create scenario loader/writer
- [ ] Add sample VM-21 scenarios

### Phase 4: Full Volatility Surface (Highest Effort)

- [ ] yfinance option chain parsing
- [ ] Vol surface interpolation
- [ ] Integration with BS pricing

---

## 8. Related Resources

| Resource | URL | Content |
|----------|-----|---------|
| FRED API | https://fred.stlouisfed.org/docs/api/ | Economic data |
| SOA Mortality | https://mort.soa.org/ | Mortality tables |
| AAA ESG Docs | (proprietary) | Scenario generator |
| JuliaActuary ESG | https://github.com/JuliaActuary | Julia scenarios |

---

## Notes

This document captures ideas from the ChatGPT landscape analysis for future implementation. Priority should be given to items that:

1. Enable validation against known sources
2. Support regulatory compliance (VM-21, AG43)
3. Reduce friction for new users
4. Align with existing ecosystem (lifelib, JuliaActuary)

**Next Step**: Implement Phase 1 (embedded samples) as part of annuity-pricing v1.0 release.
