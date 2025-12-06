# Codex Comprehensive To-Do (2025-12-05)

This is a consolidated, non-executed action plan covering code, validation, cross-validation, documentation, and roadmap readiness. No changes have been applied.

## Core Pricing Corrections (High)
- Discount full payoff for FIA/RILA (principal + credit) and derive expected credit/return from discounted MC price or closed form (`src/annuity_pricing/products/fia.py:145-210,384-392`, `products/rila.py:138-212,444-481`).
- Replace trigger shortcut with digital/call-spread pricing tied to term/rates/vol (`products/fia.py:384-392`).
- Remove silent buffer defaults and PV clipping in RILA; require explicit buffer/floor and implement real breakeven logic (`products/rila.py:138-212,451-481`).
- Ingest `term_years` when building RILA products from WINK rows (`data/schemas.py:330-358`).
- Align implementations with Constitution: risk-neutral discounting, explicit protection terms, no silent defaults that alter product economics, and breakeven calculations consistent with caps/protection.

## Validation & Tests (High)
- Swap placeholder constants in `tests/anti_patterns/test_arbitrage_bounds.py` for real BS calls so no-arbitrage regressions are enforced.
- Add regression tests for corrected discounting, trigger pricing, explicit buffer/floor enforcement, breakeven logic, and RILA term-year ingestion.
- Add tests enforcing Constitution §8 HALT protocols (option>underlying, parity errors, negative FIA credits, MC vs BS convergence).

## Cross-Validation & External Adapters (High)
- Build thin adapters to validators per domain: financepy/QuantLib (BS + digital), PyCurve/QuantLib (curves), pyfeng (MC cross-check), actuarialmath (mortality).
- Convert roadmap/matrix expected values into automated tests or notebook assertions with golden numbers.
- Wire promised notebooks (e.g., black_scholes_vs_financepy, yield_curve_vs_pycurve, mortality vs actuarialmath/JL/R, FIA/RILA validation) to real code and validators.
- Implement missing modules called “Ready” in CROSS_VALIDATION_MATRIX (greeks, curves, mortality) or mark them as gaps until code exists.

## Roadmap & Documentation Alignment (Medium)
- Refresh `ROADMAP.md`, `CURRENT_WORK.md`, and `ROADMAP_EXTENDED.md` with current phase status, test counts, and actual deliverables.
- Update `docs/CROSS_VALIDATION_MATRIX.md` to reflect actual modules and mark gaps until implemented; fix path errors (e.g., options/simulation/monte_carlo.py vs options/pricing/monte_carlo.py).
- Add closure plans for FIA/RILA validation gaps (which validator, which notebook, target cases).

## Feature/Architecture Stubs for Upcoming Phases (Medium)
- Phase 7: Add dynamic lapse module skeleton with tests.
- Phase 8: Add GLWB state/MC scaffolding and placeholder failing tests.
- Phase 9: Add VM-21/VM-22 scenario schema, curve/mortality inputs, and a simple CTE stub.
- Phase 10: Add yield-curve loader (PyCurve/QuantLib) and mortality loader (actuarialmath) stubs; plan R/Julia bridges if in scope.

## Ecosystem/Dependencies Hygiene (Medium)
- Add smoke tests that exercise installed validators (financepy, QuantLib, pyfeng, PyCurve, lifelib) or slim dependencies until adapters exist.
- Decide on Julia/R validator scope: either install and smoke-test or de-scope in docs.
- Include external references in validation scope: financepy/QuantLib (options/digitals), pyfeng (MC/SABR), PyCurve (curves), actuarialmath (mortality), lifelib (dynamic lapse), MortalityTables.jl/lifecontingencies (cross-check mortality), and SEC RILA examples (for buffer/floor payoffs). Ensure each has at least one golden-value test or notebook.

## Methodology Enforcement (Medium)
- Enforce Constitution HALTs: no undiscounted PVs, no implicit buffer defaults, no silent overrides; breakeven must reflect product terms.
- Add targeted tests for each protocol item in Constitution §8 (suspicious results).

## Sequencing Suggestion (Optional)
1) Fix pricing math (FIA/RILA), replace trigger shortcut, enforce explicit buffer/floor, add regressions.  
2) Repair anti-pattern arbitrage test placeholders.  
3) Stand up one validator adapter per domain with golden-value tests/notebooks; implement or de-scope missing “Ready” modules.  
4) Update roadmap docs and cross-validation matrix to match reality.  
5) Add Phase 7–10 stubs and dependency smoke tests.  
6) Expand validation notebooks and CI hooks once adapters are stable.
