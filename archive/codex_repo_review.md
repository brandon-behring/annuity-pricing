# Codex Review – annuity-pricing

## Snapshot
- Solid foundations: typed dataclasses, defensive validation, and ~2k test functions (`rg "def test" tests | wc -l → 2020`). Stress testing/behavioral/regulatory code is present and reasonably documented in-line.
- Storytelling is inconsistent: public docs claim different test counts (998 vs 1686 vs 2471) and “all phases complete”, while large parts of the docs/guides/notebooks are still TODO scaffolds.
- Several user-facing examples don’t match the actual API (e.g., `guaranteed_rate` vs `fixed_rate`, `PricingResult` fields).

## Documentation completeness and accuracy
- Incomplete guides with `{todo}` blocks: `docs/guides/pricing_fia.md`, `pricing_rila.md`, `pricing_myga.md`, `market_setup.md`, `behavior_calibration.md`, `regulatory_vm21_vm22.md`, `glwb_walkthrough.md` are all marked “under development”.
- Validation/knowledge gaps: `docs/knowledge/derivations/glwb_pde.md` is still TODO; `docs/knowledge/README.md` flags it.
- Quick-start and getting-started snippets reference fields that don’t exist (`guaranteed_rate` instead of `fixed_rate`), and show a `PricingResult` shape that doesn’t match `src/annuity_pricing/products/base.py` (docs list `expected_credit/option_budget`, actual base result only has `present_value/duration/convexity/details`).
- Cross-validation narrative conflicts: `docs/index.md` claims 998 tests and “Production-Ready”, `ROADMAP.md` claims 1686 tests and all phases complete, `CURRENT_WORK.md` claims 2471 tests & 85% coverage, while code/config show a 75% coverage floor and many TODO docs.

**Options (docs)**
1) Finish the TODO guides and derivations; add short runnable snippets mirrored from tests.  
   - Pros: Converts marketing claims into teachable artifacts; reduces support burden.  
   - Cons: Time-consuming; requires keeping examples in sync with API churn.
2) Hide or demote unfinished sections (remove `{todo}` blocks, add “planned” badges) until content exists.  
   - Pros: Reduces credibility risk and user confusion today.  
   - Cons: Loses visibility into roadmap items; fewer entry points for contributors.

**Options (example accuracy)**
1) Update docs/README examples to match schemas (`fixed_rate`, `term_years`, result objects) and add doctest-style smoke checks in CI.  
   - Pros: Prevents drift; users can copy/paste with confidence.  
   - Cons: Slight CI overhead; requires maintaining stable fixtures.
2) Add compatibility aliases (e.g., accept `guaranteed_rate` in `MYGAProduct.__init__`) to preserve examples.  
   - Pros: Minimizes breaking changes for readers.  
   - Cons: Pollutes API surface; may hide misuse.

## Testing and coverage story
- Test counts are inconsistent across docs (998 vs 1686 vs 2471). Actual definitions are ~2020. Coverage gate in `pyproject.toml` is 75% (not the 85% stated in `CURRENT_WORK.md`), and root `README.md` doesn’t advertise the real numbers.
- No automated source of truth for these numbers; claims appear hand-edited.
- Warning filter ignores `UserWarning: Breakeven calculation not yet implemented`, but no such warning exists in code—likely dead config.

**Options**
1) Add a small script/Make target to emit test counts + coverage (e.g., `pytest --co` + `coverage report --fail-under`). Inject into docs via CI or a badge.  
   - Pros: Single source of truth, removes manual edits; builds trust.  
   - Cons: Requires CI plumbing; adds minutes to pipeline.
2) Trim hard numbers from narrative; replace with ranges and last-measured date.  
   - Pros: No tooling work; avoids stale claims.  
   - Cons: Less compelling marketing; still needs occasional updates.
3) Either implement the breakeven warning (if functionality is missing) or drop the filter.  
   - Pros: Aligns config with behavior; clearer signals in CI.  
   - Cons: Minor maintenance task.

## Release notes and versioning
- Two changelogs diverge: root `CHANGELOG.md` stops at 0.1.0 (Unreleased still “initial project structure”), while `docs/reference/changelog.md` lists 0.2.0 changes. `pyproject.toml`/`CITATION.cff` say 0.2.0.

**Options**
1) Collapse to a single canonical changelog and link everywhere.  
   - Pros: Eliminates confusion; standard Keep-a-Changelog flow.  
   - Cons: One-time merge chore.
2) Keep dual changelogs but script-sync the root file from the docs version on release.  
   - Pros: Preserves docs layout; automatable.  
   - Cons: More moving parts; risk of drift if the script isn’t run.

## Validation notebooks and cross-validation claims
- Several validation notebooks carry “TODO” placeholders (`notebooks/validation/_TEMPLATE.ipynb`, `mortality/tables_vs_julia.ipynb`, `curves/yield_curve_vs_pycurve.ipynb`) and print “TODO” instead of executing checks.
- `ROADMAP_EXTENDED.md` cross-validation matrix still marks FIA/RILA as “GAP” while `ROADMAP.md` claims full completion; `docs/validation/cross_validation.md` marks mortality as “stub”.

**Options**
1) Execute and commit notebook outputs (or convert to lightweight Python scripts with assertions) for each cross-validation claim.  
   - Pros: Evidence-backed claims; enables regression detection.  
   - Cons: Heavier dependencies (QuantLib/financepy); slower CI.
2) Downscope claims (e.g., mark FIA/RILA cross-val as pending, note skipped mortality) until validators run in automation.  
   - Pros: Honest status without extra infra.  
   - Cons: Less persuasive validation story.

## API surface and schema alignment
- `MYGAProduct` in `src/annuity_pricing/data/schemas.py` uses `fixed_rate`, `guarantee_duration`; docs use `guaranteed_rate`. Similar mismatch for `PricingResult` fields in `docs/guides/getting_started.md`.
- Some guides show `premium` positional args while pricers often expect `principal`/`term_years` explicitly; not covered by tests.

**Options**
1) Normalize docs + examples to the exact dataclass fields and pricer signatures; add a tiny doc-example test per product.  
   - Pros: Reduces user error; keeps docs self-testing.  
   - Cons: Requires ongoing maintenance with API changes.
2) Add shim constructors or keyword aliases to accept documented names.  
   - Pros: Backward-compatible for readers; easier onboarding.  
   - Cons: Expands surface area; may hide misuse in production.

## Suggested near-term fixes (low effort, high trust gain)
- Update README/docs to remove stale test counts and fix example field names.
- Pick one changelog as canonical and reflect 0.2.0 there.
- Remove or implement the dangling breakeven warning filter.
- Mark TODO guides/notebooks as “planned” or fill with minimal runnable examples to avoid broken sections.

## ArXiv / Paper (paper/main.tex) Audit
- Claims “production-ready” with 1608 unit tests (5 skipped) and scikit-learn as a core dependency. In reality: pyproject omits scikit-learn; coverage gate is 75%; docs show many TODO guides; ROADMAP/CURRENT_WORK cite 1686/2471 tests; `rg "def test"` finds ~2020 test functions. The repository URL in the paper (`github.com/brandon-behring/…`) differs from the repo metadata (`bbehring/annuity-pricing`).
- Paper says “core dependencies: numpy, scipy, pandas, scikit-learn” and Python 3.10–3.13; pyproject lists numpy/pandas/scipy/pyarrow only and does not mention scikit-learn. If scikit-learn is required for figures, it should be in `pyproject.toml` or the paper should drop it.
- “Production-ready” conflicts with prototype flags: VM-21/VM-22 are explicitly prototypes, GLWB guide is TODO, and several guides/derivations are unfinished. Either soften the claim in the paper or finish the missing docs/tests.
- Test count in paper (1608) matches `paper/artifacts/execution.log` but not the newer counts in ROADMAP/CURRENT_WORK or the raw count of test functions. Pick one source of truth and cite the date/commit hash in the paper.
- Availability section points to PyPI v0.2.0 and claims “1608 unit tests … CI”. PyPI badge in docs/index.md is fine, but the paper should mirror actual CI thresholds (75% coverage) and current test counts.

**Options (paper)**
1) Refresh the paper with current facts: repo URL, dependency list from `pyproject.toml`, test count/coverage from a fresh CI run, and temper “production-ready” to “research-grade with prototypes” unless the TODO guides/tests are completed.  
2) If the paper must stay at v0.2.0, add a “Results as of commit <hash>/date” note and remove scikit-learn/production-ready language to avoid misrepresentation.  
