# Extended Roadmap: Annuity Pricing Library

**Created**: 2025-12-05
**Purpose**: Cross-validation strategy + contribution opportunities + implementation roadmap
**Status**: Planning document

---

## Part I: Cross-Validation Matrix

### Purpose

Map each annuity-pricing module to external validation packages for rigorous benchmarking.

### Validation Packages Installed

| Language | Package | Version | Purpose |
|----------|---------|---------|---------|
| Python | QuantLib | 1.40 | Yield curves, bonds |
| Python | financepy | 1.0.1 | BS, Heston, Greeks |
| Python | pyfeng | 0.3.0 | SABR, Heston FFT |
| Python | PyCurve | 0.1.4 | Nelson-Siegel fitting |
| Python | stochvolmodels | 1.1.4 | Heston calibration |
| Python | actuarialmath | - | Life formulas |
| Python | lifelib | 0.11.0 | VA/GMAB models |
| Julia | MortalityTables.jl | 2.6.0 | SOA tables |
| Julia | LifeContingencies.jl | 2.5.0 | Life-contingent values |
| Julia | FinanceModels.jl | 4.15.0 | Yield curves |
| R | lifecontingencies | - | Life actuarial math |
| R | StMoMo | - | Stochastic mortality |
| R | AnnuityRIR | - | Annuity with random rates |

### Cross-Validation Matrix

| Module | Python Validator | Julia Validator | R Validator | Notebook |
|--------|------------------|-----------------|-------------|----------|
| `options/pricing/black_scholes.py` | financepy, QuantLib | - | - | `options/black_scholes_vs_financepy.ipynb` |
| `options/pricing/monte_carlo.py` | pyfeng | - | - | `options/monte_carlo_vs_pyfeng.ipynb` |
| `curves/yield_curve.py` | PyCurve, QuantLib | FinanceModels.jl | - | `curves/yield_curve_vs_pycurve.ipynb` |
| `mortality/` | actuarialmath, lifelib | MortalityTables.jl | lifecontingencies | `mortality/tables_vs_julia.ipynb` |
| `products/myga.py` | - | - | AnnuityRIR | `mortality/tables_vs_r.ipynb` |
| `products/rila.py` | **GAP** | **GAP** | **GAP** | - |
| `products/fia.py` | **GAP** | **GAP** | **GAP** | - |

### Test Cases with Expected Values

#### Black-Scholes Validation

| Test Case | Parameters | Expected | Validator |
|-----------|------------|----------|-----------|
| ATM Call | S=100, K=100, T=1, r=0.05, σ=0.20 | 10.4506 | financepy |
| OTM Put | S=100, K=90, T=0.5, r=0.03, σ=0.25 | 2.3851 | QuantLib |
| ITM Call | S=100, K=95, T=1, r=0.05, σ=0.20 | 13.6998 | financepy |
| Deep OTM | S=100, K=120, T=0.25, r=0.05, σ=0.15 | 0.0439 | QuantLib |

#### Greeks Validation

| Greek | Parameters | Expected | Validator |
|-------|------------|----------|-----------|
| Delta (Call) | ATM, T=1, σ=0.20 | 0.6368 | financepy |
| Gamma | ATM, T=1, σ=0.20 | 0.0188 | pyfeng |
| Vega | ATM, T=1, σ=0.20 | 37.52 | financepy |
| Theta (Call) | ATM, T=1, σ=0.20 | -6.41 | QuantLib |

#### Yield Curve Validation

| Test Case | Method | Expected (5Y zero) | Validator |
|-----------|--------|---------------------|-----------|
| US Treasury 2024-01 | Bootstrap | 4.12% | QuantLib |
| Sample curve | Nelson-Siegel | β0=0.04, β1=-0.02, β2=0.01, τ=2.0 | PyCurve |

#### Mortality Table Validation

| Table | Age | qx (expected) | Validator |
|-------|-----|---------------|-----------|
| SOA 2012 IAM Basic | 65 | 0.01096 | MortalityTables.jl |
| SOA 2012 IAM Basic | 75 | 0.02891 | lifecontingencies (R) |
| SOA 2012 IAM Basic | 85 | 0.08145 | actuarialmath |

#### Life Contingency Validation

| Calculation | Parameters | Expected | Validator |
|-------------|------------|----------|-----------|
| ä_65:10¬ (ann-due) | SOA08, i=5% | 7.8871 | lifecontingencies (R) |
| A_65 (whole life) | SOA08, i=5% | 0.4398 | LifeContingencies.jl |
| 10E_65 (pure end) | SOA08, i=5% | 0.5584 | actuarialmath |

---

## Part II: Contribution Opportunities

### Ecosystem Gaps Analysis

> "There is currently no open-source library that provides a RILA pricing module or template."
> — ChatGPT Landscape Analysis, 2025

| Gap | Impact | Complexity | Status | Notes |
|-----|--------|------------|--------|-------|
| **RILA pricing** | HIGH | Medium | **In Progress** | `products/rila.py` - first open-source |
| **FIA crediting** | HIGH | Medium | **In Progress** | `products/fia.py` - cap/floor/spread |
| **MYGA pricing** | MEDIUM | Low | **In Progress** | `products/myga.py` - basic |
| **GLWB engine** | VERY HIGH | Very High | Future (Phase 8) | "No plug-and-play solution" |
| **VM-21 calculator** | HIGH | High | Future (Phase 9) | Regulatory need |
| **Dynamic lapse** | MEDIUM | Medium | Documented | lifelib has partial |

### Strategic Positioning

1. **First-mover advantage**: RILA/FIA/MYGA pricing modules
2. **Bridge role**: "RILAs straddle insurance and investment domains"
3. **Validation credibility**: 3-way cross-validation (Python/Julia/R)
4. **Academic engagement**: Cite Milevsky, Hardy, Bauer in documentation

### Contribution Paths

| Path | Description | Effort |
|------|-------------|--------|
| **Standalone library** | Maintain annuity-pricing independently | Current |
| **lifelib contribution** | Contribute RILA module to lifelib | Medium |
| **JuliaActuary port** | Port products to Julia | High |
| **Publication** | Document methodology, publish examples | Low |

---

## Part III: Implementation Roadmap

### Effort Estimation Key

| Tier | Effort | Time Estimate | Example |
|------|--------|---------------|---------|
| **LOW** | < 1 week | 1-3 days | Add config parameter |
| **MEDIUM** | 1-2 weeks | 5-10 days | New pricing module |
| **HIGH** | 2-4 weeks | 10-20 days | Complex feature |
| **VERY HIGH** | 1-2 months | 20-40 days | New subsystem |

### Phase 7: Actuarial Extensions (Behavioral)

**Priority**: High
**Dependencies**: Phase 6 complete

| Component | Effort | Description | Reference |
|-----------|--------|-------------|-----------|
| Dynamic lapse | MEDIUM | Moneyness-based: `lapse = base × (AV/Guarantee)` | `docs/knowledge/domain/dynamic_lapse.md` |
| Lapse tables | LOW | SOA/LIMRA experience studies | SOA website |
| Commission | LOW | DAC, trail, bonus structures | - |
| Expenses | LOW | Per-policy, % of AV, maintenance | - |
| Withdrawal utilization | MEDIUM | GLWB withdrawal patterns | SOA studies |

### Phase 8: GLWB Pricing Engine

**Priority**: Very High (major gap)
**Dependencies**: Phase 7, mortality, yield curves

| Component | Effort | Dependencies | Description |
|-----------|--------|--------------|-------------|
| GWB tracking | MEDIUM | Monte Carlo engine | Guaranteed Withdrawal Base accounting |
| Roll-up/ratchet | MEDIUM | GWB tracking | GWB growth mechanics |
| Path-dependent sim | HIGH | GWB, Mortality | MC simulation with state tracking |
| Life-contingent | HIGH | Path-dependent sim | Mortality-weighted payoffs |
| Optimal withdrawal | VERY HIGH | All above + PDE solver | Policyholder optimization |

**Reference**: `docs/knowledge/domain/glwb_mechanics.md`, `docs/knowledge/derivations/glwb_pde.md`

**Key papers**:
- Milevsky & Salisbury (2006) - GMWB foundation
- Bauer, Kling & Russ (2008) - Universal GMxB framework
- Dai, Kwok, Zong (2008) - Optimal withdrawal analysis

### Phase 9: Regulatory Calculators

**Priority**: High
**Dependencies**: Phase 8, scenario generation

| Calculator | Effort | Dependencies | Timeline | Description |
|------------|--------|--------------|----------|-------------|
| VM-21 prototype | VERY HIGH | MC engine, Mortality, Scenarios | 2025 Q2 | CTE70, stochastic scenarios |
| VM-22 prototype | HIGH | MYGA pricer, Yield curves | 2026 Q1 | Fixed annuity PBR (effective 2026) |
| AG43 encoder | MEDIUM | Scenario generator | 2025 Q3 | Standard scenario format |

**Reference**: `docs/knowledge/domain/vm21_vm22.md`

### Phase 10: Data Integration

**Priority**: Medium
**Source**: `docs/future_work/data_integration_ideas.md`

| Component | Effort | Description |
|-----------|--------|-------------|
| Treasury API | Low | FRED integration for yield curves |
| Sample datasets | Low | Embedded Parquet files |
| SOA mortality | Low | Download and embed key tables |
| Vol surface | High | yfinance option chain parsing |
| Scenario files | Medium | VM-21/AG43 compatible format |

### Package Integrations

| Integration | Effort | Benefit |
|-------------|--------|---------|
| QuantLib yield curves | Low | Better curve fitting |
| financepy Greeks | Low | Fast validation |
| pyfeng SABR | Medium | Vol smile support |
| MortalityTables.jl | Medium | Julia cross-check |
| EconomicScenarioGenerators.jl | High | Scenario generation |

### Recommended Implementation Sequence

**Quick Wins (Complete in 1 Week)**:
1. Commission/Expense module (7.3) - LOW
2. FRED Treasury API enhancement (10.1) - LOW
3. SOA Mortality Tables (10.2) - LOW
4. Sample datasets (10.3) - LOW
5. financepy integration notebook - LOW
6. QuantLib integration notebook - LOW

**Risk-Adjusted Order**:

| Order | Phase | Item | Dependencies | Effort |
|-------|-------|------|--------------|--------|
| 1 | 7.3 | Commission/Expense | None | LOW |
| 2 | 10.1 | FRED Treasury API | None | LOW |
| 3 | 10.2 | SOA Mortality Tables | None | LOW |
| 4 | 7.1 | Dynamic Lapse | products/base.py | MEDIUM |
| 5 | 8.1 | GWB Tracking | Monte Carlo | MEDIUM |
| 6 | 8.2 | Roll-up/Ratchet | 8.1 | MEDIUM |
| 7 | 10.4 | Volatility Surface | Options module | MEDIUM |
| 8 | 7.2 | Withdrawal Utilization | 7.1 | MEDIUM |
| 9 | 8.3 | Path-Dependent Sim | 8.1, 8.2, Mortality | HIGH |
| 10 | 9.3 | AG43 Scenarios | Scenario generator | MEDIUM |
| 11 | 7.4 | Policyholder Optimization | 7.1, 7.2 | HIGH |
| 12 | 8.4 | Optimal Withdrawal | 8.1-8.3 | VERY HIGH |
| 13 | 9.1 | VM-21 Prototype | 8.3, Scenarios | VERY HIGH |
| 14 | 9.2 | VM-22 Prototype | MYGA, Curves | HIGH |

---

## Part IV: Validation Notebooks

### Directory Structure

```
notebooks/validation/
├── options/
│   ├── black_scholes_vs_financepy.ipynb
│   ├── black_scholes_vs_quantlib.ipynb
│   └── monte_carlo_vs_pyfeng.ipynb
├── curves/
│   └── yield_curve_vs_pycurve.ipynb
└── mortality/
    ├── tables_vs_julia.ipynb
    └── tables_vs_r.ipynb
```

### Notebook Template

Each validation notebook should include:

1. **Setup**: Import both our module and validator
2. **Test cases**: Table of parameters and expected values
3. **Comparison**: Side-by-side output
4. **Tolerance check**: Assert within acceptable epsilon
5. **Performance**: Timing comparison (optional)

---

## Part V: Context Engineering

### Knowledge Tier System

| Tier | Location | Purpose | Example |
|------|----------|---------|---------|
| L1 | `docs/knowledge/domain/` | Quick reference | GLWB formulas |
| L2 | `docs/knowledge/derivations/` | Full derivations | BS Greeks derivation |
| L3 | `docs/knowledge/references/` | Paper summaries | Milevsky 2006 summary |

### Reference Index (for CLAUDE.md)

| Topic | L1 Quick Ref | L2 Derivation | L3 Paper |
|-------|--------------|---------------|----------|
| GLWB pricing | `glwb_pricing.md` | `glwb_pde.md` | `milevsky_2006.md` |
| RILA mechanics | `rila_mechanics.md` | - | - |
| Dynamic lapse | `dynamic_lapse.md` | - | - |
| BS Greeks | - | `bs_greeks.md` | - |
| VM-21/22 | `vm21_vm22.md` | - | - |
| Mortality | - | - | `lee_carter_1992.md` |

---

## Appendix: Paper Acquisition List

### High Priority (Foundational)

| Paper | Authors | Year | Status |
|-------|---------|------|--------|
| Financial valuation of GMWB | Milevsky & Salisbury | 2006 | [ ] |
| Universal Pricing Framework GMxB | Bauer, Kling, Russ | 2008 | [ ] **FREE** |
| The Titanic Option (GMDB) | Milevsky & Posner | 2001 | [ ] |
| Lee-Carter mortality model | Lee & Carter | 1992 | [ ] |

### Books

| Book | Author | Year | Priority |
|------|--------|------|----------|
| Calculus of Retirement Income | Milevsky | 2006 | **HIGH** |
| Investment Guarantees | Hardy | 2003 | **HIGH** |

**Full list**: `docs/references/acquisition_list_extended.md`

---

## Change Log

| Date | Change |
|------|--------|
| 2025-12-05 | Initial creation from landscape analysis |
| 2025-12-05 | Added cross-validation matrix with test cases |
| 2025-12-05 | Added contribution opportunities |
| 2025-12-05 | Added context engineering section |
| 2025-12-05 | Added effort estimation key and implementation sequencing |
| 2025-12-05 | Added dependencies to Phase 8-9 tables |
| 2025-12-05 | Added reference to glwb_pde.md derivation |
