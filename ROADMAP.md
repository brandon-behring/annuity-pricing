# ROADMAP.md - Actuarial Pricing Progress

**Last Updated**: 2025-12-06

---

## Current Status: Phase 10 Complete ✅

All phases complete including extended roadmap (Phases 7-10).

---

## Execution Order

```
Phase 0 → Phase 1 → Phase 3 → Phase 2 → Phase 4 → Phase 5 → Phase 6 → Phase 7 → Phase 8 → Phase 9 → Phase 10
   ✅        ✅        ✅        ✅        ✅        ✅        ✅        ✅        ✅        ✅        ✅
```

**Status**: All phases complete. Stream F (Code Quality Hardening) complete. 998 tests (4 skipped).

---

## Phase 7: Behavioral Modules ✅

| Module | Description | Tests |
|--------|-------------|-------|
| `behavioral/dynamic_lapse.py` | Moneyness-based lapse rates | 20 |
| `behavioral/withdrawal.py` | GLWB withdrawal utilization | 22 |
| `behavioral/expenses.py` | Per-policy + % of AV expenses | 28 |

**Key features**: Dynamic lapse `f(moneyness)`, age-based withdrawal, inflation-adjusted expenses, path-based calculations, PV with survival probabilities.

---

## Phase 8: GLWB Modules ✅

| Module | Description | Tests |
|--------|-------------|-------|
| `glwb/rollup.py` | Simple/compound rollup, ratchet | 27 |
| `glwb/gwb_tracker.py` | GWB state tracking | 19 |
| `glwb/path_sim.py` | Path-dependent Monte Carlo | 18 |

**Key features**: SimpleRollup, CompoundRollup, RatchetMechanic, GWBTracker state machine, GLWBPathSimulator with mortality, fair fee calculation via bisection.

---

## Phase 9: Regulatory Modules ✅

| Module | Description | Tests |
|--------|-------------|-------|
| `regulatory/scenarios.py` | Vasicek + GBM scenario generation | 32 |
| `regulatory/vm21.py` | VM-21/AG43 CTE calculations | 28 |
| `regulatory/vm22.py` | VM-22 fixed annuity PBR | 31 |

**Key features**: Correlated scenarios (Cholesky), CTE calculation, VM-21 Reserve = max(CTE70, SSA, CSV floor), SET/SST tests for VM-22, NPR/DR/SR reserves.

---

## Phase 10: Data Integration ✅

| Module | Description | Tests |
|--------|-------------|-------|
| `loaders/yield_curve.py` | Curve construction + interpolation | 35 |
| `loaders/mortality.py` | SOA tables + life expectancy | 48 |

**Key features**: YieldCurve (linear/log-linear/cubic interpolation), Nelson-Siegel fitting, discount/forward/par rates, Macaulay duration, MortalityTable (qx/px/npx/lx/dx), SOA 2012 IAM, Gompertz model, mortality improvement, annuity PV.

---

## Foundation Fixes (Pre-Phase 7) ✅

| Task | Status |
|------|--------|
| Fix PV discounting bug (FIA/RILA) | ✅ |
| Fix silent defaults | ✅ |
| Wire anti-pattern tests to real BS | ✅ |
| Create validator adapters | ✅ |
| Complete validation notebooks | ✅ |
| Add broader regression sweeps | ✅ |

**Key fixes**: PV formula correction, FIA trigger uses N(d2), RILA validation, financepy/pyfeng/QuantLib adapters.

---

## Completed

| Phase | Completion Date | Key Deliverable |
|-------|-----------------|-----------------|
| Phase 0 | 2025-12-04 | Context engineering setup (CLAUDE.md, CONSTITUTION.md, domain docs) |
| Phase 1 | 2025-12-04 | Foundation + TDD infrastructure (config, loader, cleaner, schemas, anti-pattern tests) |
| Phase 3 | 2025-12-05 | **MYGA Pricing Complete** - MYGAPricer, valuation, recommender |
| Phase 2 | 2025-12-05 | **Competitive Analysis Complete** - positioning, spreads, rankings |
| Phase 4 | 2025-12-05 | **Option Framework Complete** - BS pricing, MC simulation, FIA/RILA payoffs |
| Phase 5 | 2025-12-05 | **FIA/RILA Pricers Complete** - Product pricers with embedded options |
| Phase 6 | 2025-12-05 | **Integration Complete** - Registry, validation gates, demo notebooks |

### Phase 6 Deliverables
- `products/registry.py` - ProductRegistry with:
  - Unified dispatch for MYGA, FIA, RILA
  - MarketEnvironment configuration
  - price_from_row() for WINK data
  - price_multiple() for batch operations
  - create_default_registry() convenience function
- `validation/gates.py` - HALT/PASS framework with:
  - PresentValueBoundsGate
  - DurationBoundsGate
  - FIAOptionBudgetGate
  - FIAExpectedCreditGate
  - RILAMaxLossGate
  - RILAProtectionValueGate
  - ArbitrageBoundsGate
  - ValidationEngine
- `notebooks/03_fia_rila_pricing_demo.ipynb` - Interactive demo
- **66 integration tests** for registry and validation

### Phase 5 Deliverables
- `products/fia.py` - FIAPricer with:
  - Cap, participation, spread, trigger crediting methods
  - Embedded option value via Black-Scholes
  - Expected credit via Monte Carlo
  - Fair cap/participation calculation (solve for terms given option budget)
  - Competitive positioning against market
  - Batch pricing (price_multiple)
- `products/rila.py` - RILAPricer with:
  - Buffer protection (put spread replication)
  - Floor protection (OTM put replication)
  - Protection value + upside value breakdown
  - Expected return via Monte Carlo
  - Buffer vs floor comparison analysis
  - Competitive positioning against market
  - Batch pricing (price_multiple)
- **42 FIA/RILA pricer tests**

### Phase 4 Deliverables
- `options/payoffs/base.py` - BasePayoff, IndexPath, PayoffResult, VanillaOption
- `options/payoffs/fia.py` - CappedCallPayoff, ParticipationPayoff, SpreadPayoff, TriggerPayoff, MonthlyAveragePayoff
- `options/payoffs/rila.py` - BufferPayoff, FloorPayoff, BufferWithFloorPayoff, StepRateBufferPayoff
- `options/pricing/black_scholes.py` - Full BS implementation with Greeks (delta, gamma, vega, theta, rho)
- `options/simulation/gbm.py` - GBM path generation with antithetic variates
- `options/simulation/monte_carlo.py` - MonteCarloEngine with variance reduction
- **17 BS known-answer tests** - Hull textbook validation
- **11 MC convergence tests** - MC → BS verification

### Phase 3 Deliverables
- `products/base.py` - BasePricer abstract class, PricingResult, CompetitivePosition dataclasses
- `products/myga.py` - MYGAPricer with price(), competitive_position(), recommend_rate()
- `valuation/myga_pv.py` - Full valuation with PV, duration, convexity, DV01, effective duration
- `rate_setting/recommender.py` - RateRecommender with margin analysis, sensitivity analysis

### Phase 2 Deliverables
- `competitive/positioning.py` - PositioningAnalyzer with percentile/quartile analysis
- `competitive/spreads.py` - SpreadAnalyzer with Treasury spread calculations
- `competitive/rankings.py` - RankingAnalyzer with company/product rankings
- `notebooks/02_competitive_analysis.ipynb` - Demo notebook
- **63 additional tests** for competitive analysis modules

---

## Success Criteria

| Criterion | Target | Status |
|-----------|--------|--------|
| MYGA pricing works | PV with duration/convexity | ✅ Verified |
| Anti-pattern tests pass | All critical tests green | ✅ 17/17 passing |
| Competitive positioning | Rate percentile for any product | ✅ Working |
| BS known-answer tests pass | Hull textbook examples | ✅ 17 tests passing |
| MC converges to BS | < 1% relative error | ✅ Verified |
| FIA pricing | Given option budget, compute fair cap/participation | ✅ Working |
| RILA pricing | Buffer/floor protection pricing | ✅ Working |
| Product registry | Unified dispatch for all product types | ✅ Working |
| Validation gates | HALT/PASS framework | ✅ Working |

---

## Test Summary

```
tests/unit/                 773 tests - All modules (including adapters, behavioral, glwb, regulatory, loaders)
tests/integration/          101 tests - End-to-end pricing pipeline + registry + gates
tests/anti_patterns/         79 tests - Put-call parity, buffer/floor, no-arbitrage sweeps
tests/validation/            45 tests - BS known-answer, MC convergence, PV discounting
─────────────────────────────────────
Total:                      998 tests (4 skipped for pyfeng scipy 1.12+)
```

**Stream F Additions (2025-12-06):**
- F.1-F.3: 24 new tests for term scaling, buffer validation, monthly averaging
- F.4: 13 new tests for tightened validation gates
- F.5: 8 new tests for FRED fixture loading

---

## Module Summary

| Module | Purpose | Status |
|--------|---------|--------|
| `config/settings.py` | Frozen configuration | ✅ |
| `data/loader.py` | WINK loader + checksum | ✅ |
| `data/cleaner.py` | Outlier handling | ✅ |
| `data/schemas.py` | Product dataclasses | ✅ |
| `data/market_data.py` | Treasury/volatility loaders | ✅ |
| `products/base.py` | BasePricer abstract | ✅ |
| `products/myga.py` | MYGAPricer | ✅ |
| `products/fia.py` | FIAPricer | ✅ |
| `products/rila.py` | RILAPricer | ✅ |
| `products/registry.py` | Unified product dispatch | ✅ |
| `valuation/myga_pv.py` | MYGA valuation | ✅ |
| `rate_setting/recommender.py` | Rate recommendations | ✅ |
| `competitive/positioning.py` | Rate percentiles | ✅ |
| `competitive/spreads.py` | Treasury spreads | ✅ |
| `competitive/rankings.py` | Company rankings | ✅ |
| `options/payoffs/base.py` | Payoff base classes | ✅ |
| `options/payoffs/fia.py` | FIA crediting payoffs | ✅ |
| `options/payoffs/rila.py` | RILA buffer/floor payoffs | ✅ |
| `options/pricing/black_scholes.py` | BS pricing + Greeks | ✅ |
| `options/simulation/gbm.py` | GBM path generation | ✅ |
| `options/simulation/monte_carlo.py` | MC engine | ✅ |
| `validation/gates.py` | HALT/PASS validation | ✅ |
| `adapters/financepy_adapter.py` | BS validation against financepy | ✅ |
| `adapters/pyfeng_adapter.py` | MC validation against pyfeng | ✅ |
| `adapters/quantlib_adapter.py` | Curve validation against QuantLib | ✅ |
| `behavioral/dynamic_lapse.py` | Moneyness-based lapse rates | ✅ |
| `behavioral/withdrawal.py` | GLWB withdrawal utilization | ✅ |
| `behavioral/expenses.py` | Per-policy + % of AV expenses | ✅ |
| `glwb/rollup.py` | Simple/compound rollup, ratchet | ✅ |
| `glwb/gwb_tracker.py` | GWB state tracking | ✅ |
| `glwb/path_sim.py` | Path-dependent MC for GLWB | ✅ |
| `regulatory/scenarios.py` | Vasicek + GBM scenario generation | ✅ |
| `regulatory/vm21.py` | VM-21/AG43 CTE calculations | ✅ |
| `regulatory/vm22.py` | VM-22 fixed annuity PBR | ✅ |
| `loaders/yield_curve.py` | Yield curve construction | ✅ |
| `loaders/mortality.py` | SOA mortality tables | ✅ |

---

## Key Capabilities

### 1. Product Pricing
```python
from annuity_pricing.products import create_default_registry, price_product

# Quick price any product
result = price_product(myga_product)
result = price_product(fia_product, term_years=1.0)
result = price_product(rila_product, term_years=6.0)

# Or use registry for consistency
registry = create_default_registry(seed=42)
result = registry.price(product)
```

### 2. Competitive Analysis
```python
from annuity_pricing.competitive import PositioningAnalyzer

analyzer = PositioningAnalyzer(wink_data)
position = analyzer.get_position(product)
print(f"Percentile: {position.percentile}%")
```

### 3. Validation
```python
from annuity_pricing.validation import ensure_valid, validate_pricing_result

# Validate and raise on failure
result = ensure_valid(pricing_result, premium=100.0)

# Or get detailed report
report = validate_pricing_result(pricing_result, premium=100.0)
if not report.passed:
    for gate in report.halted_gates:
        print(f"HALT: {gate.message}")
```

---

## References

- [Full Plan](.claude/plans/snazzy-enchanting-whistle.md)
- [CONSTITUTION.md](CONSTITUTION.md) - Frozen methodology
- [codex-pricing-resources-rila-fia-myga.md](../myga-forecasting-v3/codex-pricing-resources-rila-fia-myga.md)
