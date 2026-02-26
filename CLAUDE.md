# CLAUDE.md - Actuarial Pricing

**Version**: 1.0.0 | **Status**: Phase 0 - Context Engineering Setup

---

## Project Overview

Actuarial pricing calculations for MYGA, FIA, and RILA annuity products using WINK competitive rate data.

**Purpose**: Research and pricing tooling, NOT production deployment.

**Scope**:
- Competitive positioning (rate percentiles, spreads over Treasury)
- Product valuation (PV of liabilities, embedded option value)
- Rate setting (recommendations given market conditions)
- Option modeling (Empirical → Black-Scholes → Monte Carlo)

---

## Hub Reference

**This project uses shared patterns from lever_of_archimedes**:

| Pattern | Purpose | Path |
|---------|---------|------|
| Testing | 6-layer validation architecture | `~/Claude/lever_of_archimedes/patterns/testing.md` |
| Sessions | CURRENT_WORK.md, ROADMAP.md | `~/Claude/lever_of_archimedes/patterns/sessions.md` |
| Git | Commit format and workflow | `~/Claude/lever_of_archimedes/patterns/git.md` |

---

## Core Principles (Priority Order)

1. **NEVER FAIL SILENTLY** - Every error must be explicitly reported
2. **Test-First Development** - Anti-patterns before implementation
3. **External-First Validation** - Known answers (Hull textbook) → Internal
4. **Knowledge Tiering** - T1/T2/T3 on all claims
5. **Skepticism of Success** - Option price > underlying = HALT

---

## Domain Knowledge Index

### Quick Reference (docs/knowledge/domain/)

| Document | Purpose | When to Use |
|----------|---------|-------------|
| `option_pricing.md` | BS formula, Greeks, put-call parity | Implementing pricers |
| `buffer_floor.md` | RILA protection mechanics | RILA payoffs |
| `crediting_methods.md` | FIA cap/participation/spread | FIA payoffs |
| `mgsv_mva.md` | NAIC requirements | Surrender value calcs |
| `competitive_analysis.md` | Rate positioning | Company rankings |

### Detailed Derivations (docs/knowledge/derivations/)

| Document | Purpose | When to Use |
|----------|---------|-------------|
| `bs_greeks.md` | Greeks formulas and sensitivities | Understanding hedging |
| `put_spread_buffer.md` | Buffer = long put ATM - short put OTM | RILA valuation |
| `monte_carlo.md` | GBM paths, variance reduction | MC engine implementation |
| `glwb_pde.md` | GLWB PDE formulation | GLWB pricing |

> **Note**: Full BS derivation is in `docs/knowledge/domain/option_pricing.md`

### Bug Prevention (docs/episodes/bugs/)

Bug postmortems follow this pattern:
```markdown
# BUG-NNN: Short Name
**Severity**: CRITICAL | **Status**: Fixed

## Summary
## What Happened (with code)
## Root Cause
## The Fix
## Prevention Test (link to test file)
## Key Lesson (one-liner)
```

---

## Quick Reference Commands

```bash
# Activate environment
source venv/bin/activate

# Run all tests (MUST pass before commit)
pytest tests/ --cov=src -v

# Run bug prevention tests specifically
pytest tests/anti_patterns/ -v

# Run validation tests
pytest tests/validation/ -v

# Helper scripts
./scripts/validate.sh --full        # Tests + type check + lint
./scripts/setup_check.py --verbose  # Verify environment/deps
./scripts/fetch_market_data.py      # Download Treasury/VIX/S&P (needs FRED_API_KEY)
./scripts/run_notebooks.sh --list   # List/run validation notebooks
```

---

## Knowledge Tier System

All claims in documentation are tiered:

| Tier | Meaning | Example |
|------|---------|---------|
| **[T1]** | Academically validated | "Black-Scholes (1973)" |
| **[T2]** | Empirical from WINK data | "Median cap rate = 5%" |
| **[T3]** | Assumption, needs justification | "Option budget = 3%" |

When working with domain knowledge:
- **T1**: Trust and apply
- **T2**: Apply, verify against current WINK data
- **T3**: Consider sensitivity analysis

---

## The Critical Anti-Patterns (MEMORIZE)

| Test | Prevents | Why Critical |
|------|----------|--------------|
| `test_arbitrage_bounds.py` | Option > underlying | Breaks no-arbitrage [T1] |
| `test_put_call_parity.py` | BS implementation errors | Fundamental identity [T1] |
| `test_floor_enforcement.py` | Negative FIA credits | FIA floor = 0% [T1] |
| `test_buffer_mechanics.py` | Buffer payoff errors | Buffer absorbs first X% [T1] |
| `test_buffer_vs_floor.py` | Confused protection types | Buffer ≠ Floor [T1] |

---

## Suspicious Results Protocol

### Automatic HALT Triggers

| Condition | Action |
|-----------|--------|
| Option value > underlying price | Verify no-arbitrage bounds |
| Put-call parity violated > 0.01 | Check BS implementation |
| FIA payoff < 0 | Verify floor enforcement |
| MC price diverges from BS by >5% | Check convergence/paths |

### Investigation Sequence

```bash
# 1. Anti-pattern tests (definitive bug detection)
pytest tests/anti_patterns/ -v

# 2. Known-answer validation (Hull textbook examples)
pytest tests/validation/test_bs_known_answers.py -v

# 3. Convergence tests (MC → BS for vanilla)
pytest tests/validation/test_mc_convergence.py -v
```

---

## Troubleshooting & FAQ

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: annuity_pricing` | Package not installed | `pip install -e .` |
| `FileNotFoundError: wink.parquet` | Data file missing | Check `wink.parquet` exists in project root |
| `FRED_API_KEY not set` | Market data fetch needs API key | Get free key at fred.stlouisfed.org |
| `put_call_parity test fails` | BS implementation error | Check d1/d2 formula, verify q (dividend) term |
| `Option value > underlying` | No-arbitrage violation | Check for rate/time scaling issues |

### Diagnostic Commands

```bash
# Check environment
python scripts/setup_check.py --verbose

# Verify dependencies match pyproject.toml
pip check

# Test a single pricer
python -c "from annuity_pricing.options.pricing.black_scholes import black_scholes_call; print(black_scholes_call(100, 100, 0.05, 0.02, 0.20, 1.0))"
```

### When to Check What

| Symptom | Check First | Then Check |
|---------|-------------|------------|
| Import errors | `pip install -e .` | `python scripts/setup_check.py` |
| Wrong option prices | Put-call parity test | Hull Example 15.6 (S=42, K=40) |
| FIA payoff negative | Floor enforcement | `floor = max(0, credited)` |
| MC doesn't converge | Path count (need 10k+) | Variance reduction settings |
| Data loading fails | File path | Parquet vs CSV format |

### Known Limitations

1. **financepy/QuantLib optional**: Cross-validation notebooks require these (install separately)
2. **FRED API key required**: For `fetch_market_data.py` (free registration)
3. **R actuarial packages**: For mortality cross-validation, requires R installation

---

## Source Code Structure

```
src/annuity_pricing/
├── adapters/                 # External library integrations
│   ├── base.py               # Adapter base class
│   ├── financepy_adapter.py  # financepy BS validation
│   ├── pyfeng_adapter.py     # pyfeng SABR/Heston
│   └── quantlib_adapter.py   # QuantLib curves/bonds
├── behavioral/               # Policyholder behavior models
│   ├── calibration.py        # Model calibration routines
│   ├── dynamic_lapse.py      # Dynamic lapse modeling
│   ├── expenses.py           # Expense assumptions
│   ├── soa_benchmarks.py     # SOA study benchmarks
│   └── withdrawal.py         # Withdrawal patterns
├── competitive/
│   ├── positioning.py        # Rate percentile analysis
│   ├── rankings.py           # Company/product rankings
│   └── spreads.py            # Spread over Treasury
├── config/
│   └── settings.py           # Frozen dataclass config
├── credit/                   # Credit risk modeling
│   ├── cva.py                # Credit valuation adjustment
│   ├── default_prob.py       # Default probability models
│   └── guaranty_funds.py     # State guaranty fund coverage
├── data/
│   ├── cleaner.py            # Outlier handling
│   ├── loader.py             # WINK loader with checksum
│   ├── market_data.py        # FRED + Yahoo + Stooq loaders
│   └── schemas.py            # Product dataclasses
├── glwb/                     # GLWB/GMxB modeling
│   ├── gwb_tracker.py        # GWB account tracking
│   ├── path_sim.py           # Path simulation
│   └── rollup.py             # Rollup benefit calculations
├── loaders/                  # External data loaders
│   ├── mortality.py          # SOA mortality tables
│   └── yield_curve.py        # Yield curve data
├── options/
│   ├── payoffs/
│   │   ├── base.py           # BasePayoff abstract class
│   │   ├── fia.py            # FIA crediting payoffs
│   │   └── rila.py           # RILA buffer/floor payoffs
│   ├── pricing/
│   │   ├── black_scholes.py  # BS pricing and Greeks
│   │   ├── heston.py         # Heston stochastic vol
│   │   ├── heston_cos.py     # Heston COS method
│   │   └── sabr.py           # SABR model
│   └── simulation/
│       ├── gbm.py            # GBM path generation
│       ├── heston_paths.py   # Heston path generation
│       └── monte_carlo.py    # Monte Carlo engine
├── products/
│   ├── base.py               # BasePricer abstract class
│   ├── fia.py                # FIA pricer (includes valuation)
│   ├── myga.py               # MYGA pricer
│   ├── registry.py           # Product type registry
│   └── rila.py               # RILA pricer (includes valuation)
├── rate_setting/
│   └── recommender.py        # Rate recommendations
├── regulatory/               # NAIC regulatory calculations
│   ├── scenarios.py          # Regulatory scenarios
│   ├── vm21.py               # VM-21 (variable annuities)
│   └── vm22.py               # VM-22 (fixed annuities)
├── stress_testing/           # Stress testing framework
│   ├── historical.py         # Historical crisis scenarios
│   ├── metrics.py            # Stress metrics
│   ├── reporting.py          # Report generation
│   ├── reverse.py            # Reverse stress testing
│   ├── runner.py             # Stress test runner
│   ├── scenarios.py          # Scenario definitions
│   └── sensitivity.py        # Sensitivity analysis
├── validation/
│   └── gates.py              # HALT/PASS validation gates
└── valuation/
    └── myga_pv.py            # MYGA present value
```

**Note**: FIA and RILA valuation logic is embedded in their respective pricers (`products/fia.py`, `products/rila.py`) rather than separate valuation modules.

---

## Code Patterns

### Error Handling (NEVER fail silently)

```python
# CORRECT:
if data.empty:
    raise ValueError(
        f"CRITICAL: Empty data in {function_name}. "
        f"Expected: DataFrame with data. Got: Empty."
    )

# WRONG (silent failure):
if data.empty:
    return pd.DataFrame()  # PROHIBITED
```

### Type Hints (Required)

```python
def price_call(
    spot: float,
    strike: float,
    rate: float,
    vol: float,
    time: float
) -> float:
    """Price European call using Black-Scholes [T1]."""
    ...
```

### Docstrings (NumPy style with tier tags)

```python
def price_buffer_payoff(
    index_return: float,
    buffer: float,
    cap: float
) -> float:
    """
    Calculate RILA buffer payoff.

    [T1] Buffer absorbs first X% of losses.
    See: docs/knowledge/domain/buffer_floor.md

    Parameters
    ----------
    index_return : float
        Index return over the term (decimal, e.g., -0.15 for -15%)
    buffer : float
        Buffer level (decimal, e.g., 0.10 for 10% buffer)
    cap : float
        Maximum return cap (decimal, e.g., 0.12 for 12% cap)

    Returns
    -------
    float
        Credited return (decimal)

    Examples
    --------
    >>> price_buffer_payoff(-0.05, 0.10, 0.12)  # -5% return, 10% buffer
    0.0  # Buffer absorbs the loss
    >>> price_buffer_payoff(-0.15, 0.10, 0.12)  # -15% return, 10% buffer
    -0.05  # Client absorbs 5% (15% - 10% buffer)
    """
```

---

## Test-First Development

### Before Writing Any Code

1. Write test that would catch the bug (from anti_patterns/)
2. Verify test fails (red)
3. Implement code
4. Verify test passes (green)
5. Run all anti-pattern tests
6. Refactor if needed

### Test Categories

```
tests/
├── anti_patterns/        # Bug prevention (MUST pass before commit)
│   ├── test_arbitrage_bounds.py
│   ├── test_put_call_parity.py
│   └── test_floor_enforcement.py
├── validation/           # External verification (Hull examples)
│   ├── test_bs_known_answers.py
│   ├── test_mc_convergence.py
│   └── test_wink_sanity.py
├── unit/                 # Standard unit tests
└── integration/          # End-to-end pricing tests
```

---

## Git Workflow

### Pre-Commit Checks

```bash
# MUST pass before commit:
pytest tests/anti_patterns/ -v  # Bug prevention
pytest tests/validation/ -v     # Known answers
```

### Commit Messages

```
feat: Add Black-Scholes pricer

- Implements call/put pricing with Greeks
- Verified against Hull Ch.15 examples [T1]
- Tests in tests/validation/test_bs_known_answers.py

🤖 Generated with [Claude Code](https://claude.com/claude-code)
Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Reference Documents

| Document | Purpose | Location |
|----------|---------|----------|
| METHODOLOGY.md | Frozen methodology | Project root |
| CURRENT_WORK.md | 30-second context switch | Project root |
| ROADMAP.md | Progress tracking | Project root |
| docs/knowledge/ | Domain knowledge (tiered) | L1 quick ref, L2 derivations |
| docs/episodes/ | Bug postmortems | One per bug |
| wink-research-archive/ | WINK data documentation | Data dictionary, product guides |

---

## Key Domain Resources

| File | Purpose |
|------|---------|
| `wink-research-archive/data-dictionary/WINK_DATA_DICTIONARY.md` | All 62 columns documented |
| `wink-research-archive/product-guides/ANNUITY_PRODUCT_GUIDE.md` | Product mechanics explained |

---

## Option Modeling Tiers

| Level | Approach | When to Use |
|-------|----------|-------------|
| **L1: Empirical** | WINK pattern analysis | Competitive positioning |
| **L2: Black-Scholes** | Closed-form pricing | Fair value, Greeks |
| **L3: Monte Carlo** | Path simulation | Path-dependent payoffs |

---

## Knowledge Reference Index

### Quick Lookup by Topic

| Topic | L1 (Quick Ref) | L2 (Derivation) | L3 (Paper) | Notebook |
|-------|----------------|-----------------|------------|----------|
| **GLWB/GMWB** | `glwb_mechanics.md` | `glwb_pde.md` | `bauer_kling_russ_2008.md` | - |
| **RILA** | `rila_mechanics.md` | - | `sec_rila_final_rule_2024.md` | - |
| **FIA/EIA** | `crediting_methods.md` | - | `boyle_tian_2008.md` | - |
| **Monte Carlo** | - | `monte_carlo.md` | `glasserman_2003_monte_carlo.md` | - |
| **Black-Scholes** | `option_pricing.md` | `bs_greeks.md` | `black_scholes_1973.md`, `hull_2021_options_formulas.md` | `options/black_scholes_vs_financepy.ipynb` |
| **Buffer/Floor** | `buffer_floor.md` | - | `sec_rila_investor_testing_2023.md` | - |
| **Dynamic Lapse** | `dynamic_lapse.md` | - | - | - |
| **VM-21/VM-22** | `vm21_vm22.md` | - | - | - |
| **NAIC Regs** | - | - | `naic_805_nonforfeiture.md`, `naic_806_regulation.md` | - |
| **Mortality** | - | - | - | `mortality/tables_vs_julia.ipynb` |
| **Yield Curves** | - | - | - | `curves/yield_curve_vs_pycurve.ipynb` |

### L3 Reference Documents (Complete List)

| Document | Topic | Key Content |
|----------|-------|-------------|
| `black_scholes_1973.md` | Options | Original BS formula, d1/d2 |
| `hull_2021_options_formulas.md` | Options | BS summary, Greeks |
| `glasserman_2003_monte_carlo.md` | Simulation | GBM, variance reduction, Greeks |
| `bauer_kling_russ_2008.md` | GMxB | Universal pricing framework |
| `hardy_2003_investment_guarantees.md` | VA | RSLN model, EIA crediting |
| `boyle_tian_2008.md` | EIA | Investor perspective |
| `sec_rila_final_rule_2024.md` | Regulatory | Form N-4, buffer/floor disclosure |
| `sec_rila_investor_testing_2023.md` | Regulatory | OIAD investor comprehension |
| `naic_805_nonforfeiture.md` | Regulatory | Nonforfeiture law |
| `naic_806_regulation.md` | Regulatory | Annuity regulation |
| `finra_22_08_complex_products.md` | Regulatory | Complex products guidance |

### Validation Packages by Language

| Language | Package | Validates |
|----------|---------|-----------|
| Python | financepy | BS pricing, Greeks |
| Python | QuantLib | Yield curves, bonds |
| Python | pyfeng | SABR, Heston |
| Python | PyCurve | Nelson-Siegel |
| Python | actuarialmath | Life contingencies |
| Julia | MortalityTables.jl | SOA tables |
| Julia | LifeContingencies.jl | Life-contingent values |
| Julia | FinanceModels.jl | Yield curves |
| R | lifecontingencies | Life actuarial math |
| R | StMoMo | Stochastic mortality |

### Key Papers to Acquire

| Paper | Why | Status |
|-------|-----|--------|
| Milevsky & Salisbury (2006) | GMWB foundation | `docs/references/acquisition_list_glwb_va.md` |
| Bauer, Kling & Russ (2008) | Universal GMxB | **FREE** - ✅ summarized |
| Hardy (2003) book | Investment guarantees | ✅ summarized |
| Glasserman (2003) book | Monte Carlo methods | ✅ summarized (Ch 3,4,6,7) |
| SEC RILA 2024 | Regulatory framework | ✅ summarized |

### Additional Resources

| Resource | Location |
|----------|----------|
| Cross-Validation Matrix | `docs/CROSS_VALIDATION_MATRIX.md` |
| Extended Roadmap (Phases 7-10) | `ROADMAP_EXTENDED.md` |
| WINK Data Dictionary | `docs/data/WINK_DATA_DICTIONARY.md` |

---

**Remember**: "Too good to be true" usually is. Option value > underlying means a bug, not a discovery.
