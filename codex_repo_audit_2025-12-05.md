# Codex Repo Audit (2025-12-05)

## Scope
- Reviewed core pricing stack (`src/annuity_pricing/products/*`, `options/*`, validation gates), data schemas, and roadmap docs.
- Tests were not re-run in this pass; findings are code/document read-through.

## High Findings
- `src/annuity_pricing/products/fia.py:145-210,384-392` – Present value discounts only the credit leg and leaves the principal undiscounted, inflating PV by `(1 - df) * premium`. Expected credit is derived from undiscounted MC payoffs (vs the discounted MC price) and ignores option-budget binding; the trigger payoff is hard-coded to `0.5 * trigger_rate * premium`, independent of term, vol, or rates. These break risk-neutral valuation and fair-term calculations.
- `src/annuity_pricing/products/rila.py:138-212,444-448,451-481` – PV mirrors the FIA pattern (principal not discounted) and silently defaults `buffer_rate` to 10% even when the product lacks buffer/floor detail. Negative PVs are clipped to zero, masking loss scenarios. Expected returns are based on undiscounted MC payoffs and breakeven is stubbed to `0.0` for all structures.

## Medium Findings
- `src/annuity_pricing/data/schemas.py:330-358` – `create_rila_from_row` drops `term_years`, so any WINK rows with explicit terms are priced at the default one-year horizon, skewing PVs and validation gating.
- `tests/anti_patterns/test_arbitrage_bounds.py:18-159` – Anti-pattern suite uses placeholder constants instead of the Black-Scholes implementation, so arbitrage violations would not be caught. The rest of the anti-pattern tests rely on real code; this one should too.

## Documentation & Roadmap Gaps
- `ROADMAP.md` / `CURRENT_WORK.md` are stale (Phase 0/6 dates and 455-test claim) relative to the implemented FIA/RILA stack and current test counts. Needs a refresh with recent deliverables.
- `ROADMAP_EXTENDED.md` cross-validation matrix calls out modules/notebooks that do not exist yet (e.g., curves, mortality, `options/pricing/monte_carlo.py` instead of `options/simulation/monte_carlo.py`) and leaves FIA/RILA validation as “GAP” without a closure plan or golden-value links.
- Validation notebooks under `notebooks/validation/` remain TODO and are not wired to external validators listed in the extended roadmap (QuantLib/financepy/pyfeng, etc.), leaving the cross-validation story unimplemented.

## Recommendations
- Rework FIA/RILA valuation to discount the full payoff (`df * premium * (1 + expected_credit/return)`) and derive expected credit from discounted MC price or closed-form values; enforce option-budget parity and replace the trigger shortcut with a priced digital/call-spread.
- Require explicit buffer/floor inputs (or fail fast) in `RILAPricer`, remove PV clipping to expose loss scenarios, and compute breakeven consistent with cap/protection parameters.
- Ingest `term_years` in `create_rila_from_row` and add a regression covering row→product→price for multi-year terms.
- Replace placeholder values in `tests/anti_patterns/test_arbitrage_bounds.py` with calls into `black_scholes_call/put` so arbitrage regressions are caught.
- Refresh roadmap docs with current phase status, test counts, and a concrete plan for the cross-validation matrix (which validators, which notebooks, and expected values per module).

## Methodology Alignment (CONSTITUTION.md vs implementation)
- Risk-neutral discounting is violated in FIA/RILA PV (principal not discounted) and in expected-credit/return estimation (uses undiscounted MC means). This contradicts Constitution §4 (valuation) and §5 (MC specs), and the Suspicious Results protocol that HALTs when option value exceeds underlying.
- Buffer defaults (10% when unspecified) in RILA conflict with Constitution §1.3 (buffer vs floor must be explicit) and hide product misclassification. Breakeven stub conflicts with §4.2 fair-term guidance.
- Anti-pattern arbitrage test uses placeholders, undermining Constitution §2.2 (no-arbitrage bounds) and §8 HALT triggers.

## Cross-Validation and External References
- `docs/CROSS_VALIDATION_MATRIX.md` and `docs/analysis/ecosystem_opportunities.md` cite validators (financepy, QuantLib, pyfeng, PyCurve, actuarialmath, lifelib, MortalityTables.jl) but the codebase does not wire to any of them. Labeled “Ready” modules (`options/analysis/greeks.py`, `curves/yield_curve.py`, `mortality/tables.py`) are absent from `src/`, so the matrix is aspirational, not implemented.
- Validation notebooks listed in the matrix and extended roadmap (e.g., `black_scholes_vs_financepy.ipynb`, `yield_curve_vs_pycurve.ipynb`, mortality/RILA/FIA notebooks) are missing or contain TODOs; no golden values or CI hooks exist.
- External ecosystem comparison (lifelib, JuliaActuary, QuantLib) is documented in `docs/analysis/ecosystem_opportunities.md` but there is no adapter layer or regression tests using those libraries despite claiming “Ready” status.

## Readiness vs Roadmap (Extended)
- Extended roadmap promises Phase 7–10 items (dynamic lapse, GLWB, VM-21/VM-22, yield curves, mortality) but there are no corresponding modules, stubs, or tests in `src/`. Cross-validation targets for curves/mortality/greeks point to non-existent code paths.
- Installed-but-unused validation packages (QuantLib, financepy, pyfeng, stochvolmodels, PyCurve, lifelib) increase maintenance surface without coverage; add smoke tests or slim dependencies until adapters exist.

## Additional Actions to Close Gaps
- Add thin adapters to at least one validator per domain (e.g., financepy for BS/digital, QuantLib for curve bootstraps, actuarialmath for mortality factors) and wire notebook/test harnesses with golden values.
- Update CROSS_VALIDATION_MATRIX to reflect actual modules and planned notebooks; mark gaps explicitly until code exists.
- Document and enforce failure modes per Constitution (HALT on missing buffer/floor, HALT on undiscounted PV) and add targeted tests for each protocol item.

## ROADMAP_EXTENDED Readiness Check
- **Part I (Cross-Validation Matrix)**: Matrix claims “Ready” for `options/pricing/monte_carlo.py`, `curves/yield_curve.py`, `mortality/tables.py`, and `options/analysis/greeks.py`, but these modules are absent in `src/`. Validators (financepy, QuantLib, pyfeng, PyCurve, actuarialmath, MortalityTables.jl) are installed but unused. Notebooks listed (`black_scholes_vs_financepy.ipynb`, `yield_curve_vs_pycurve.ipynb`, mortality/RILA/FIA notebooks) are missing or TODO. **Gap**: Need code, adapters, and golden-value notebooks before claiming readiness.
- **Part II (Contribution Opportunities)**: Positioning vs lifelib/JuliaActuary/QuantLib is documented, but there is no adapter or example showing interoperability. **Gap**: Add one concrete integration example (e.g., price BS via financepy/QuantLib and compare) to substantiate the positioning.
- **Part III (Implementation Roadmap)**:
  - **Phase 7 (Behavioral/Dynamic Lapse)**: No lapse modules, tables, or stubs in `src/`; only docs. **Gap**: Add minimal lapse engine skeleton and tests before proceeding.
  - **Phase 8 (GLWB Engine)**: No GLWB state/MC/PDE scaffolding. **Gap**: Add placeholder module, data structures, and a failing test plan.
  - **Phase 9 (Regulatory VM-21/VM-22)**: No scenario generators, curve/mortality inputs, or CTE machinery. **Gap**: Add scenario schema and a VM-21/VM-22 “hello world” stub.
  - **Phase 10 (Data Integration)**: Scripts reference market data fetch, but no yield-curve or mortality ingestion modules exist; no R/Julia bridge despite references. **Gap**: Build a minimal curve loader with PyCurve/QuantLib and a mortality loader with actuarialmath as first validators.
- **Ecosystem/Packages**: Extended roadmap lists many packages (financepy, QuantLib, pyfeng, PyCurve, lifelib, MortalityTables.jl, R packages). Only Python packages are present in the venv; Julia/R packages are not installed nor exercised. **Gap**: Either install and smoke-test or narrow the scope to Python-first validation.
- **Metrics & Tests**: ROADMAP_EXTENDED cites “test cases with expected values” (BS, Greeks, yield curves, mortality) but none are expressed as automated tests. **Gap**: Convert tabled cases into pytest modules and notebook assertions.
