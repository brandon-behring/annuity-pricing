# Open-Source Annuity Pricing Ecosystem: Opportunities Analysis

**Date**: 2025-12-05
**Sources**: ChatGPT landscape analysis, package documentation, academic literature
**Purpose**: Strategic positioning and future work planning

---

## Executive Summary

### Market Position

Our `annuity-pricing` repository fills **explicitly documented gaps** in the open-source ecosystem:

| Gap (Explicitly Stated) | Our Solution |
|-------------------------|--------------|
| "No open-source library provides a RILA pricing module" | `products/rila.py` |
| "No dedicated open module for MYGAs" | `products/myga.py` |
| "Gaps remain for FIA crediting" | `products/fia.py` |
| "No integrated BS/MC for crediting" | `options/pricing/` |

### Competitive Landscape

| Library | Strengths | Gaps We Fill |
|---------|-----------|--------------|
| **lifelib** | VA/GMAB, dynamic lapse | No RILA, FIA, MYGA |
| **JuliaActuary** | Mortality, life contingencies | No product templates |
| **R lifecontingencies** | Traditional formulas | No modern products |
| **QuantLib** | Yield curves, bonds | No insurance products |

---

## Section 1: Installed Validation Packages

### Python (annuity-pricing venv)

| Package | Version | Purpose | Validates |
|---------|---------|---------|-----------|
| **QuantLib** | 1.40 | Comprehensive quant | Yield curves, bonds |
| **financepy** | 1.0.1 | Fast derivatives | BS, Heston, Greeks |
| **pyfeng** | 0.3.0 | Academic models | SABR, Heston FFT |
| **PyCurve** | 0.1.4 | Yield fitting | Nelson-Siegel |
| **stochvolmodels** | 1.1.4 | Stoch vol | Heston calibration |
| **chainladder** | 0.8.26 | P&C reserving | Triangle methods |
| **gemact** | 1.2.1 | Reinsurance | Aggregate loss |
| **lifelib** | 0.11.0 | Life actuarial | VA/GMAB |
| **actuarialmath** | - | Life formulas | Reserves, premiums |
| **pyliferisk** | - | Life contingencies | Basic formulas |

### Julia (Global Environment)

| Package | Version | Purpose |
|---------|---------|---------|
| **MortalityTables.jl** | 2.6.0 | SOA tables, survival |
| **LifeContingencies.jl** | 2.5.0 | Life-contingent values |
| **FinanceModels.jl** | 4.15.0 | Yield curves, contracts |
| **ActuaryUtilities.jl** | 5.1.0 | Actuarial utilities |
| **EconomicScenarioGenerators.jl** | 0.6.0 | ESG for scenarios |

### R (Not Yet Installed - Requires R)

| Package | Purpose |
|---------|---------|
| lifecontingencies | Life actuarial math |
| StMoMo | Stochastic mortality |
| MortalityTables | Life table management |
| AnnuityRIR | Annuity with random rates |
| LifeInsuranceContracts | Traditional contracts |
| actuar | Heavy-tailed distributions |
| demography | Lee-Carter modeling |

---

## Section 2: Validation Strategy

### 3-Way Cross-Validation

```
Implementation        →    Validator 1      →    Validator 2
─────────────────────────────────────────────────────────────
Black-Scholes         →    py_vollib        →    financepy/QuantLib
Yield curves          →    PyCurve          →    QuantLib
Life contingencies    →    actuarialmath    →    lifecontingencies (R)
Option Greeks         →    financepy        →    pyfeng
Stochastic vol        →    pyfeng           →    stochvolmodels
Mortality tables      →    lifelib          →    MortalityTables.jl
```

### Validation Notebooks to Create

| Notebook | Compares | Test Cases |
|----------|----------|------------|
| `validate_black_scholes.ipynb` | Our BS vs financepy vs QuantLib | ATM, OTM, ITM options |
| `validate_yield_curves.ipynb` | Our curves vs PyCurve vs QuantLib | Bootstrap, NS, NSS |
| `validate_mortality.ipynb` | Our tables vs MortalityTables.jl | SOA tables, parametric |
| `validate_greeks.ipynb` | Our Greeks vs pyfeng | Delta, gamma, vega |

---

## Section 3: Future Work Opportunities

### Phase 7: Behavioral Modeling

| Component | Description | Reference |
|-----------|-------------|-----------|
| **Dynamic Lapse** | Moneyness-based surrender | lifelib example |
| **Withdrawal Utilization** | GLWB withdrawal patterns | SOA studies |
| **Policyholder Optimization** | Rational behavior models | Milevsky papers |

### Phase 8: GLWB Pricing Engine

| Component | Complexity | Impact |
|-----------|------------|--------|
| GWB tracking | Medium | High |
| Roll-up/ratchet | Medium | High |
| Path-dependent simulation | High | Very High |
| Life-contingent payoffs | High | Very High |
| Optimal withdrawal | Very High | Very High |

### Phase 9: Regulatory Calculators

| Calculator | Timeline | Dependencies |
|------------|----------|--------------|
| VM-21 prototype | 2025 Q2 | ESG, GLWB |
| VM-22 prototype | 2026 Q1 | Interest rate scenarios |

---

## Section 4: Strategic Recommendations

### 1. Position as Gap-Filler

**Message**: "First open-source RILA/FIA/MYGA pricing library"

- Document this in README prominently
- Reference ChatGPT analysis quotes
- Publish comparison table

### 2. Complement, Don't Compete

**With lifelib**:
- They have VA/GMAB → We have RILA/FIA/MYGA
- Consider contributing RILA module to lifelib
- Or maintain as independent, lighter-weight alternative

**With JuliaActuary**:
- They have foundations → We have products
- Could port our products to Julia
- EconomicScenarioGenerators.jl integration

### 3. Build Validation Suite

**Rationale**: Credibility through validation

- Create comprehensive test suite
- Compare against 3+ independent implementations
- Publish results in documentation

### 4. Academic Engagement

**Opportunities**:
- Cite Milevsky, Hardy, Bauer in documentation
- Reproduce published examples
- Contribute to actuarial education

---

## Section 5: Package Integration Opportunities

### Immediate Integrations

| Integration | Benefit | Effort |
|-------------|---------|--------|
| QuantLib yield curves | Better curve fitting | Low |
| financepy Greeks | Faster validation | Low |
| pyfeng SABR | Vol smile support | Medium |
| MortalityTables.jl | Julia cross-check | Medium |

### Future Integrations

| Integration | Benefit | Effort |
|-------------|---------|--------|
| EconomicScenarioGenerators.jl | Scenario generation | High |
| lifelib dynamic lapse | Behavioral module | Medium |
| StMoMo (R) | Stochastic mortality | High |

---

## Section 6: Knowledge Base Status

### Completed Documentation

| Document | Location | Content |
|----------|----------|---------|
| `dynamic_lapse.md` | `docs/knowledge/domain/` | Moneyness-based lapse |
| `glwb_mechanics.md` | `docs/knowledge/domain/` | GLWB product mechanics |
| `vm21_vm22.md` | `docs/knowledge/domain/` | PBR framework |

### Pending Documentation

| Document | Priority | Notes |
|----------|----------|-------|
| Stochastic mortality | High | Lee-Carter, CBD |
| Policyholder behavior | High | Withdrawal patterns |
| ESG integration | Medium | Scenario generation |
| Greeks calculation | Medium | For hedging |

---

## Section 7: Reference Acquisition Status

### Acquired

- All 25 original references (per reference list)
- Created `acquisition_list_extended.md` with 26 additional items

### Priority Acquisitions

| Paper/Book | Why | Cost |
|------------|-----|------|
| Bauer et al. (2008) | Universal GMxB | **FREE** |
| Milevsky (2006) book | Best single reference | ~$70 |
| Hardy (2003) book | Investment guarantees | ~$100 |
| Lee-Carter (1992) | Mortality foundation | ~$35 |

### Free Resources to Download

- [ ] Bauer et al. PDF from ressources-actuarielles.net
- [ ] SABR paper from wilmott.com
- [ ] AAA VM-21 Practice Note
- [ ] NAIC Valuation Manual sections
- [ ] SOA experience studies

---

## Section 8: R Environment Setup (Manual)

Since R is not installed on this system, here's the setup guide:

```bash
# Install R (Ubuntu/Debian)
sudo apt install r-base r-base-dev

# Or via conda
conda install -c conda-forge r-base

# Then in R:
install.packages(c(
  "lifecontingencies",
  "StMoMo",
  "MortalityTables",
  "AnnuityRIR",
  "LifeInsuranceContracts",
  "actuar",
  "demography",
  "MortalityLaws"
))
```

---

## Appendix: Key Quotes from Landscape Analysis

> "There is currently no open-source library that provides a RILA pricing module or template."

→ **Our `products/rila.py` fills this gap**

> "GLWBs... have no ready open-source solution"

→ **Future opportunity for Phase 8**

> "No Python or Julia library today has a plug-and-play GLWB valuation engine"

→ **High-impact future contribution**

> "RILAs straddle insurance and investment domains, this contribution would be a bridge between actuarial modeling and quantitative finance"

→ **Exactly what our repo does**

---

## Change Log

| Date | Change |
|------|--------|
| 2025-12-05 | Initial analysis from combined landscape documents |
| 2025-12-05 | Added validation package status |
| 2025-12-05 | Added strategic recommendations |
