# Cross-Validation Matrix

**Purpose**: Map each annuity-pricing module to external validators with inline test cases.
**Philosophy**: Self-contained, no external lookups required.

---

## Quick Reference

| Module | Python Validator | Adapter | Status |
|--------|------------------|---------|--------|
| `options/pricing/black_scholes.py` | financepy, QuantLib | `adapters/financepy_adapter.py` | ✅ Ready |
| `options/simulation/monte_carlo.py` | pyfeng | `adapters/pyfeng_adapter.py` | ✅ Ready |
| Greeks (in black_scholes.py) | financepy | `adapters/financepy_adapter.py` | ✅ Ready |
| `loaders/yield_curve.py` | QuantLib, PyCurve | `adapters/quantlib_adapter.py` | ❌ **GAP - Phase 10** |
| `loaders/mortality.py` | actuarialmath | - | ❌ **GAP - Phase 10** |
| `products/myga.py` | manual | - | ✅ Ready |
| `products/fia.py` | SEC examples | - | ⚠️ Validation notebook TODO |
| `products/rila.py` | SEC examples | - | ⚠️ Validation notebook TODO |

**Notes**:
- `options/analysis/greeks.py` does not exist as separate file - Greeks are in `black_scholes.py`
- Curve/mortality modules are Phase 10 deliverables (stubs to be created)
- FIA/RILA validation uses SEC 2024 examples as golden test cases

---

## Options Pricing

### Black-Scholes Call/Put

**Module**: `src/annuity_pricing/options/pricing/black_scholes.py`

**Validators**:
- financepy: `FinEquityVanillaOption`
- QuantLib-Python: `BlackScholesProcess` + `AnalyticEuropeanEngine`
- pyfeng: `Bsm.price()`

**Test Cases** (Hull 9th Ed, Example 15.6):

| Test | S | K | r | σ | T | q | Expected Call | Expected Put |
|------|---|---|---|---|---|---|---------------|--------------|
| ATM | 42 | 40 | 0.10 | 0.20 | 0.5 | 0 | **4.76** | 0.81 |
| ITM | 50 | 40 | 0.10 | 0.20 | 0.5 | 0 | 11.49 | 0.06 |
| OTM | 35 | 40 | 0.10 | 0.20 | 0.5 | 0 | 0.73 | 3.79 |
| Deep ITM | 60 | 40 | 0.10 | 0.20 | 0.5 | 0 | 21.95 | 0.00 |
| Deep OTM | 25 | 40 | 0.10 | 0.20 | 0.5 | 0 | 0.01 | 13.08 |

**Tolerance**: |diff| < 0.01

**Put-Call Parity Check**:
$$C - P = S - K \cdot e^{-rT}$$
For Test 1: $4.76 - 0.81 = 3.95 \approx 42 - 40 \cdot e^{-0.05} = 3.95$ ✓

---

### Black-Scholes Greeks

**Module**: `src/annuity_pricing/options/analysis/greeks.py`

**Validators**: financepy, pyfeng

**Test Case** (S=100, K=100, r=0.05, σ=0.20, T=1, q=0):

| Greek | Formula | Expected Value | Tolerance |
|-------|---------|----------------|-----------|
| Delta (Call) | $N(d_1)$ | **0.6368** | ±0.001 |
| Delta (Put) | $N(d_1) - 1$ | -0.3632 | ±0.001 |
| Gamma | $\frac{n(d_1)}{S\sigma\sqrt{T}}$ | **0.0188** | ±0.0001 |
| Vega | $S \cdot n(d_1) \cdot \sqrt{T}$ | **37.52** | ±0.1 |
| Theta (Call) | See derivation | **-6.41** (annual) | ±0.1 |
| Rho (Call) | $K \cdot T \cdot e^{-rT} \cdot N(d_2)$ | **53.23** | ±0.1 |

**Where**:
- $d_1 = \frac{\ln(S/K) + (r + \sigma^2/2)T}{\sigma\sqrt{T}} = 0.35$
- $d_2 = d_1 - \sigma\sqrt{T} = 0.15$
- $N(0.35) = 0.6368$, $n(0.35) = 0.3752$

---

### Monte Carlo Convergence

**Module**: `src/annuity_pricing/options/simulation/monte_carlo.py`

**Validators**: pyfeng (for reference prices)

**Test Case**: European Call (S=100, K=100, r=0.05, σ=0.20, T=1)

| Paths | Expected Stderr | BS Price | MC Should Be |
|-------|-----------------|----------|--------------|
| 1,000 | ~0.30 | 10.45 | 10.45 ± 0.60 |
| 10,000 | ~0.09 | 10.45 | 10.45 ± 0.18 |
| 100,000 | ~0.03 | 10.45 | 10.45 ± 0.06 |
| 1,000,000 | ~0.01 | 10.45 | 10.45 ± 0.02 |

**Convergence Rate**: stderr ~ $\frac{1}{\sqrt{N}}$

**Variance Reduction Tests**:

| Method | Paths | Naive Var | Reduced Var | Reduction Factor |
|--------|-------|-----------|-------------|------------------|
| Antithetic | 10,000 | 8.5 | < 4.25 | > 2x |
| Control Variate | 10,000 | 8.5 | < 1.0 | > 8x |

---

## Yield Curves

### Nelson-Siegel Fitting

**Module**: `src/annuity_pricing/curves/yield_curve.py`

**Validators**:
- PyCurve: `NelsonSiegelCurve`
- QuantLib-Python: `FittedBondDiscountCurve`
- FinanceModels.jl: `NelsonSiegel`

**Test Case** (Standard parameters):

| Parameter | Value |
|-----------|-------|
| β₀ | 6.0 |
| β₁ | -3.0 |
| β₂ | 0.5 |
| τ | 2.0 |

**Nelson-Siegel Formula**:
$$y(m) = \beta_0 + \beta_1 \cdot \frac{1 - e^{-m/\tau}}{m/\tau} + \beta_2 \cdot \left(\frac{1 - e^{-m/\tau}}{m/\tau} - e^{-m/\tau}\right)$$

**Expected Yields**:

| Maturity | Expected Yield |
|----------|----------------|
| 1Y | 3.44% |
| 2Y | 3.66% |
| 3Y | 3.77% |
| 5Y | **3.87%** |
| 10Y | 4.14% |
| 30Y | 5.25% |

**Tolerance**: ±0.01%

---

## Mortality Tables

### SOA Tables

**Module**: `src/annuity_pricing/mortality/tables.py`

**Validators**:
- actuarialmath (Python)
- MortalityTables.jl (Julia)
- lifecontingencies (R)

**Test Case**: SOA 2012 IAM Basic Table (Male)

| Age x | q_x (Expected) | Source |
|-------|----------------|--------|
| 50 | 0.00330 | SOA |
| 55 | 0.00498 | SOA |
| 60 | 0.00753 | SOA |
| **65** | **0.01089** | SOA |
| 70 | 0.01619 | SOA |
| 75 | 0.02472 | SOA |
| 80 | 0.03941 | SOA |
| 85 | 0.06374 | SOA |
| 90 | 0.10368 | SOA |

**Life Expectancy at 65 (Male)**:
$$\mathring{e}_{65} \approx 18.9 \text{ years}$$

**Tolerance**: qx ±0.00001

---

### Life Annuity Factor

**Module**: `src/annuity_pricing/actuarial/annuity_factors.py`

**Test Case**: Life annuity-due at age 65, i=5%

$$\ddot{a}_{65} = \sum_{k=0}^{\omega-65} {}_{k}p_{65} \cdot v^k$$

| Interest Rate | Table | Expected $\ddot{a}_{65}$ |
|---------------|-------|--------------------------|
| 3% | 2012 IAM | ~15.8 |
| **5%** | 2012 IAM | **~13.2** |
| 7% | 2012 IAM | ~11.2 |

**Tolerance**: ±0.1

---

## MYGA Products

### Present Value Calculation

**Module**: `src/annuity_pricing/products/myga.py`

**Validator**: Manual calculation (no specialized package)

**Test Case**:

| Parameter | Value |
|-----------|-------|
| Premium | $100,000 |
| Term | 5 years |
| Guaranteed Rate | 4.00% |
| Discount Rate | 5.00% |

**Cash Flows**:

| Year | Interest | Balance | PV @ 5% |
|------|----------|---------|---------|
| 1 | $4,000 | $104,000 | $3,810 |
| 2 | $4,160 | $108,160 | $3,773 |
| 3 | $4,326 | $112,486 | $3,737 |
| 4 | $4,499 | $116,986 | $3,701 |
| 5 | $4,679 + $116,986 | $0 | $95,284 |

**Expected PV**: $110,305

**Spread Analysis**:
- Premium = $100,000
- PV of liabilities = $110,305 (at 5%)
- If insurer earns 5%: Loss = $10,305
- Breakeven discount rate: ~4% (matches guaranteed rate)

---

## FIA Products

### Point-to-Point Cap Crediting

**Module**: `src/annuity_pricing/products/fia.py`

**Validator**: (Gap - no dedicated package, use manual + Boyle-Tian 2008)

**Test Case** (Point-to-Point, Cap):

| Parameter | Value |
|-----------|-------|
| Participation Rate | 100% |
| Cap | 8% |
| Floor | 0% |
| Index Return | varies |

**Expected Credited Returns**:

| Index Return | Credited Return | Calculation |
|--------------|-----------------|-------------|
| +15% | **8%** | min(15%, 8%) = 8% |
| +5% | **5%** | min(5%, 8%) = 5% |
| +1% | **1%** | min(1%, 8%) = 1% |
| -5% | **0%** | max(-5%, 0%) = 0% |
| -20% | **0%** | max(-20%, 0%) = 0% |

---

### Participation Rate Crediting

**Test Case** (Participation Rate, No Cap):

| Parameter | Value |
|-----------|-------|
| Participation Rate | 80% |
| Cap | None |
| Floor | 0% |
| Index Return | varies |

**Expected Credited Returns**:

| Index Return | Credited Return | Calculation |
|--------------|-----------------|-------------|
| +15% | **12%** | 15% × 80% = 12% |
| +5% | **4%** | 5% × 80% = 4% |
| -10% | **0%** | max(-10% × 80%, 0%) = 0% |

---

## RILA Products

### Buffer Payoff (SEC Definition)

**Module**: `src/annuity_pricing/products/rila.py`

**Validator**: (Gap - use SEC 2024 examples as test cases)

**Test Case** (10% Buffer, 12% Cap):

| Parameter | Value |
|-----------|-------|
| Buffer | 10% |
| Cap | 12% |
| Index Return | varies |

**Expected Credited Returns** (per SEC 2024 Final Rule):

| Index Return | Credited Return | Calculation |
|--------------|-----------------|-------------|
| +15% | **12%** | min(15%, 12%) = 12% |
| +12% | **12%** | min(12%, 12%) = 12% |
| +5% | **5%** | min(5%, 12%) = 5% |
| 0% | **0%** | 0% |
| -5% | **0%** | Buffer absorbs (5% < 10%) |
| -10% | **0%** | Buffer absorbs (10% = 10%) |
| -15% | **-5%** | -15% + 10% = -5% |
| **-25%** | **-15%** | -25% + 10% = -15% (SEC example) |

---

### Floor Payoff (SEC Definition)

**Test Case** (10% Floor, 12% Cap):

| Parameter | Value |
|-----------|-------|
| Floor | -10% |
| Cap | 12% |
| Index Return | varies |

**Expected Credited Returns**:

| Index Return | Credited Return | Calculation |
|--------------|-----------------|-------------|
| +15% | **12%** | min(15%, 12%) = 12% |
| -5% | **-5%** | max(-5%, -10%) = -5% |
| -10% | **-10%** | max(-10%, -10%) = -10% |
| -25% | **-10%** | max(-25%, -10%) = -10% |

---

## Buffer vs Floor Comparison

**Critical Distinction** (from SEC RILA 2024):

| Index Return | 10% Buffer | 10% Floor | Winner |
|--------------|------------|-----------|--------|
| -5% | 0% | -5% | Buffer |
| -10% | 0% | -10% | Buffer |
| -15% | -5% | -10% | Floor |
| -25% | -15% | -10% | Floor |
| -50% | -40% | -10% | Floor |

**Insight**: Buffer better for small losses, Floor better for large losses.

---

## Validation Notebook Template

For each module, create a notebook at:
```
notebooks/validation/{module_path}/vs_{validator}.ipynb
```

Example structure:
```
notebooks/validation/
├── options/
│   ├── black_scholes_vs_financepy.ipynb
│   ├── black_scholes_vs_quantlib.ipynb
│   └── monte_carlo_vs_pyfeng.ipynb
├── curves/
│   └── yield_curve_vs_pycurve.ipynb
├── mortality/
│   ├── tables_vs_julia.ipynb
│   └── tables_vs_r.ipynb
└── products/
    ├── myga_manual_validation.ipynb
    ├── fia_boyle_tian_validation.ipynb
    └── rila_sec_examples.ipynb
```

---

## Validation Packages Installation

### Python (pip)

```bash
# Core validation
pip install financepy>=0.350
pip install QuantLib-Python>=1.31
pip install pyfeng>=0.2
pip install pycurve>=0.5
pip install actuarialmath>=1.0

# Already in pyproject.toml [validation]
```

### Julia

```julia
using Pkg
Pkg.add("MortalityTables")
Pkg.add("LifeContingencies")
Pkg.add("FinanceModels")
```

### R

```r
install.packages("lifecontingencies")
install.packages("StMoMo")
```

---

## Change Log

| Date | Change |
|------|--------|
| 2025-12-05 | Initial matrix with inline parameters |
| 2025-12-05 | Fixed module paths (greeks in black_scholes.py, curves/mortality as GAPs) |
| 2025-12-05 | Added adapter column linking to implementation |
