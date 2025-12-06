# Codex Repo Audit

## Scope
- Reviewed core pricing engines (`src/annuity_pricing/products/*.py`), option/MC stack, data schemas, validation gates, and roadmap docs.
- Tests run: `./venv/bin/pytest -q --disable-warnings --maxfail=1` (all 542 passing on Python 3.13.7).
- Methodology cross-check against standard references: Hull “Options, Futures, and Other Derivatives” (10e) for BS/MC/discounting, Glasserman “Monte Carlo Methods in Financial Engineering” for MC convergence/discounting, and standard digital option pricing (e.g., QuantLib/financepy formulations).

## High/Medium Findings (code-level)
- `src/annuity_pricing/products/fia.py:145-200` – Present value treats principal as undiscounted cash today (`present_value = premium + df * premium * expected_credit`). Risk-neutral PV should discount the entire payoff (`df * premium * (1 + expected_credit)`); current approach overstates PV by roughly `(1 - df) * premium` (Hull ch.13, risk-neutral valuation).
- `src/annuity_pricing/products/fia.py:424-442` – Expected credit uses raw MC payoff means (undiscounted) and divides by spot. This ignores the MC discount factor and biases fair-cap/participation estimates upward when rates > 0. Use `expected_credit = mc_result.price / (df * spot)` or simulate returns directly and discount (Glasserman ch.3).
- `src/annuity_pricing/products/fia.py:384-393` – Trigger option value is hard-coded to `trigger_rate * premium * 0.5`, ignoring term, rates, vol, and dividend yield. Should price as a digital/call-spread under Black-Scholes: `price = df * trigger_rate * N(d2)` (or a narrow call spread around strike).
- `src/annuity_pricing/products/rila.py:170-212` – Same PV pattern as FIA (principal not discounted) and defaults to a 10% buffer when none supplied, even for floor/unknown products. This silently injects protection and can misclassify pricing; require explicit buffer/floor inputs or fail fast.
- `src/annuity_pricing/products/rila.py:444-449` – Expected return uses undiscounted MC means; align with discounting as above to keep risk-neutral consistency.
- `src/annuity_pricing/products/rila.py:451-482` – Breakeven calculation is a stub (always `0.0`); should reflect buffer/floor/cap structure (e.g., breakeven shifts downward for buffers, limited by caps).
- `src/annuity_pricing/data/schemas.py:330-358` – `create_rila_from_row` drops `term_years` although the schema includes it. Rows with term data are priced at the default 1-year horizon, skewing PVs and validation gates.

## Documentation & Roadmap Gaps
- `ROADMAP.md`/`CURRENT_WORK.md` dates and phase status lag code reality (docs mention Phase 0/6; tests show mature FIA/RILA stack; doc test count 455 vs actual 542). Refresh status, counts, and recent deliverables.
- `ROADMAP_EXTENDED.md` lists cross-validation targets (curves, mortality) and notebooks, but modules/notebooks are missing or TODO. It still labels FIA/RILA validation as “GAP” without a closure plan.
- Validation notebooks under `notebooks/validation/` contain TODO cells and no external validator wiring (QuantLib/financepy/pyfeng). No golden-value tests are hooked up despite the matrix in the extended roadmap.

## Readiness for Extended Roadmap
- Missing building blocks for planned phases: no `curves/` or `mortality/` modules, no VM-21/VM-22 scaffolding, and no data-integration hooks (FRED, SOA mortality). Add minimal stubs and schemas before attempting cross-validation.
- External validator packages listed in the extended roadmap are not referenced in code or tests. Need an adapter layer and golden-value tests against at least one validator per product (e.g., financepy/QuantLib for BS/digital, PyCurve for curves, MortalityTables.jl or lifecontingencies for mortality).

## Suggested Next Steps
- Correct FIA/RILA PV and expected-credit calculations (discount full payoff, derive expected credit from discounted MC price) and add regression tests comparing MC to BS for vanilla cases.
- Replace trigger pricing shortcut with a proper digital/call-spread valuation; update option-budget validation to use the calibrated value.
- Require explicit protection parameters for RILA (or raise) and ingest `term_years` from WINK rows.
- Refresh `ROADMAP.md`, `CURRENT_WORK.md`, and `ROADMAP_EXTENDED.md` with current status, test counts, and a concrete cross-validation build plan.
- Stand up initial stubs for yield-curve and mortality engines plus a thin validation harness against one external library to de-risk Phase 7/8 work.

## Reference Pointers (online)
- Black-Scholes & risk-neutral discounting: Hull 10e, ch.13; formula summary in QuantLib docs (https://www.quantlib.org/reference/class_quant_lib_1_1_european_option.html).
- Digital option (cash-or-nothing) pricing: `price = df * payoff * N(d2)`; see QuantLib/financepy digital option examples (https://www.quantlib.org/reference/class_quant_lib_1_1_cash_or_nothing_payoff.html).
- Monte Carlo discounting: Glasserman ch.3; expected payoff must be discounted by `exp(-rT)` (also see financepy MC examples: https://pypi.org/project/financepy/).
