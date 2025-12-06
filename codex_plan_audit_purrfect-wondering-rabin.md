# Codex Plan Audit — purrfect-wondering-rabin (2025-12-05)

Audit of `~/.claude/plans/purrfect-wondering-rabin.md` for latent risks, gaps, and missed opportunities. No code changes made.

## Critical Gaps vs. Known Issues
- Pricing math not fixed: Plan omits the core risk-neutral PV bug (principal undiscounted and expected credit/return from undiscounted MC payoffs) in FIA/RILA. It only tightens method selection and trigger pricing.
- RILA expected return/breakeven: Plan raises `NotImplementedError` for breakeven but still leaves expected return computation unchanged (still undiscounted). Pipeline callers will now fail hard without a migration path.
- Validation alignment: Removing PV clipping without adjusting validation gates could surface negative PVs without clear handling. Need gate updates or caller expectations set.
- Option budget enforcement: Plan does not revisit fair cap/participation calculations against corrected, discounted expected credit; budgets may still be bypassed.

## Plan-Level Logic Risks
- Term conflict check (RILA Fix 1): With default `term_years=1.0`, any product carrying `term_years` (e.g., 6-year RILA) will raise a conflict when `price()` is called with defaults. Should prefer product.term_years if present and only raise when an explicit conflicting argument is provided.
- Buffer requirement (RILA Fix 2): For floor products, the plan still demands `buffer_rate`; ensure floor semantics are handled (and sign conventions validated) so legitimate floors are not blocked.
- Trigger fix: Uses `_calculate_d1_d2` from BS module but plan omits import and still assumes ATM strike. If trigger thresholds differ from ATM, pricing remains approximate; also, fair-term calculations still rely on expected credit built from undiscounted MC.
- Breakeven `NotImplementedError`: Any existing caller of `breakeven_return` will now fail; consider deprecation path or guarded use.
- Validation notebook steps: Only one notebook called out; remaining promised notebooks (MC vs pyfeng, yield_curve vs PyCurve, mortality) are not scoped—risk of continued drift.

## Adapter/Dependency Risks
- New adapters (financepy, pyfeng, QuantLib) increase optional dependency surface; plan lacks install/skip guards and CI strategy. QuantLib especially can fail builds without pinned wheels.
- No smoke tests planned for adapters beyond Hull cases; without golden numbers for curves/mortality, validators could silently drift.

## Roadmap/Docs Synchronization
- Plan updates ROADMAP/CURRENT_WORK but does not address CROSS_VALIDATION_MATRIX “Ready” modules that don’t exist (curves, mortality, greeks). Risks overstating readiness if not corrected simultaneously.
- Stubs for Phases 7–10 are proposed, but no linkage to domain docs (dynamic lapse, GLWB, VM-21/22) in tests; risk of dead code and forgotten TODOs.

## Missed Opportunities
- Option-budget enforcement: Fair cap/participation still not tied to corrected, discounted expected credit; plan doesn’t revisit budget checks.
- RILA max-loss/protection consistency checks remain unaddressed; validation gates could be strengthened alongside pricing fixes.
- Golden-value regression set: Plan adds few tests; broader parameterized BS/MC/parity/no-arb sweeps would harden foundations.
- Data loaders: Term extraction for RILA is planned, but no checksum/field validation additions for WINK term data.
- External validator coverage: Plan calls for adapters but lacks explicit golden cases and tolerances for each validator: financepy/QuantLib (BS/digital/Greeks), pyfeng (MC/SABR), PyCurve (curves), actuarialmath (mortality factors), lifelib (dynamic lapse patterns), MortalityTables.jl or lifecontingencies (mortality cross-check), SEC RILA examples (buffer/floor payoff tables). Without specified cases, adapters risk being superficial.

## Recommended Adjustments to the Plan
1) Include the risk-neutral PV/expected-credit fixes for FIA/RILA and rerun fair-term logic using discounted values.  
2) Relax RILA term conflict logic: if `product.term_years` is set and caller passes default, use product term; only raise on explicit conflicting args.  
3) Validate floor vs buffer inputs separately (signs, presence) and adjust error messages accordingly.  
4) Add adapter install/skip guards and a minimal smoke test per adapter with golden values (Hull BS, a simple curve bootstrap, one mortality qx).  
5) Update CROSS_VALIDATION_MATRIX concurrently to mark missing modules as gaps until code exists.  
6) Provide a breakeven fallback (e.g., return `None` with a warning) or gate its use to avoid breaking current callers.  
7) Broaden regression tests (parameterized no-arb/parity/MC vs BS sweeps) to reduce future drift.  
8) Define which notebooks will be completed in this cycle beyond BS/financepy, with target validators and tolerances, and list golden cases per validator (e.g., Hull Ch.15 calls/puts/Greeks; SEC RILA buffer/floor table; PyCurve NS test parameters; actuarialmath SOA IAM65 qx).
