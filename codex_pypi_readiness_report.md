# Codex Report: annuity-pricing PyPI Readiness and Cross-Repo Review

## Scope and method
- Scanned 105 git repos under /home/brandon_behring for packaging, docs, tests, CI, and governance signals.
- Deeper review of annuity-pricing and temporalcv, plus spot checks of high-signal repos:
  - /home/brandon_behring/Claude/temporalcv
  - /home/brandon_behring/Claude/lever_of_archimedes/knowledge/sources/repos/ml/optuna
  - /home/brandon_behring/Claude/lever_of_archimedes/knowledge/sources/repos/forecasting/sktime
  - /home/brandon_behring/Claude/lever_of_archimedes/knowledge/sources/repos/ml/scikit-learn
  - /home/brandon_behring/Claude/lever_of_archimedes/knowledge/sources/repos/governance/presidio
  - /home/brandon_behring/Claude/lever_of_archimedes/knowledge/sources/repos/causal/causalml
  - /home/brandon_behring/Claude/lever_of_archimedes/knowledge/sources/repos/evaluation/guardrails

## Cross-repo signals (counts out of 105 repos)
- README*: 101
- LICENSE*: 74
- .github/workflows: 54
- docs/: 53
- pyproject.toml: 47
- tests/: 34
- .pre-commit-config.yaml: 29
- CONTRIBUTING.md: 28
- CHANGELOG.md: 16
- SECURITY.md: 15
- CODE_OF_CONDUCT.md: 15
- CITATION.cff: 14
- CODEOWNERS: 12
- benchmarks/: 8
- tox.ini: 4
- mkdocs.yml: 4
- asv.conf.json: 1

## Where annuity-pricing already meets professional standards
- Packaging metadata is complete in `pyproject.toml` with extras, classifiers, and URLs.
- Strong repo hygiene: `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CITATION.cff`, `LICENSE`.
- CI, docs, notebooks, and PyPI publish workflows are in place.
- Docs are extensive and structured (assumptions, validation, regulatory, guides).
- Tests are deep and well-organized (unit, validation, anti-patterns, performance).
- Typed API with `py.typed` present and mypy/ruff checks enforced.

## Gaps and upgrades compared to top-tier repos (temporalcv and others)
1) Governance and ownership
   - Missing CODE_OF_CONDUCT and CODEOWNERS (both appear in many high-signal repos).
   - Example to emulate: sktime keeps `CODEOWNERS` and `GOVERNANCE.md`.
2) Packaging polish for PyPI
   - `py.typed` is present but not guaranteed to ship with setuptools without explicit package data.
   - Consider adding `tool.setuptools.package-data` for `py.typed` or `include-package-data = true` with a MANIFEST.
3) Installation ergonomics
   - README only shows repo clone installs. PyPI users expect `pip install annuity-pricing`.
   - Optional extras are strong but not shown in README (for example, `pip install annuity-pricing[dev]`).
4) Benchmarking and performance regression tracking
   - optuna and scikit-learn include `asv` performance benchmarks.
   - annuity-pricing has performance tests but no persistent benchmark history or charts.
5) Consistency and DRY in tooling
   - `black` is in dev deps but formatting is done with `ruff format`.
   - Simplify to one formatter to reduce duplicated tooling and config drift.
6) Release and public API clarity
   - No explicit public API or stability policy doc (some repos have a short policy in docs or CONTRIBUTING).
   - Consider a short "Public API and compatibility" section in docs or README.

## What temporalcv does well that you can reuse directly
- Clear spec + evidence trail: `SPECIFICATION.md`, `docs/testing_strategy.md`, `docs/validation_evidence.md`.
- Benchmarks folder with reproducible loaders and datasets.
- Documentation storytelling: tutorials, examples gallery, and validation evidence referenced from README.
- CI includes security audit and strict docs build (useful signals for PyPI trust).

## Tutorials and evidence to make correctness obvious
1) Reproducible pricing validation notebook
   - Show BS/GBM, Heston, and SABR results vs QuantLib/financepy with golden values.
   - Include exact input parameters and expected outputs in the tutorial narrative.
2) Cross-library comparison table
   - Similar to the README feature table, but for numeric validation: price deltas, greeks, and tolerances.
3) Monte Carlo convergence benchmark
   - Plot error vs paths and runtime. Use a fixed seed and publish a reference plot in docs.
4) End-to-end pipeline demo
   - Load yield curve, price a MYGA, simulate FIA/RILA payouts, and run stress tests in one tutorial.
5) Data provenance and licensing note
   - If WINK data is not redistributable, add a synthetic or anonymized example dataset and document it.

## Naming and consistency checks
- Align GitHub URLs in README badges with `pyproject.toml` URLs (currently different org names).
- Add a short note in README: package name is `annuity-pricing`, import name is `annuity_pricing`.
- Consider renaming `METHODOLOGY.md` to a more standard label (for example `METHODOLOGY.md`) and keep it linked.

## Prioritized action list
1) Add CODE_OF_CONDUCT.md and CODEOWNERS for governance clarity.
2) Ensure `py.typed` is included in the built wheel (setuptools package data).
3) Update README install section to include PyPI and extras examples.
4) Add a benchmark/performance harness (asv or pytest-benchmark history).
5) Publish a validation tutorial notebook with cross-library results and tolerance justification.
