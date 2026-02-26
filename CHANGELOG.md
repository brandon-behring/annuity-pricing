# Changelog

All notable changes to annuity-pricing will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [1.0.0] - 2026-02-26

### Added

- **OSS Professionalization**
  - `CODE_OF_CONDUCT.md` (Contributor Covenant v2.1)
  - `.github/CODEOWNERS` file
  - Public API stability policy in CONTRIBUTING.md
  - Regulatory disclaimer in README (VM-21/VM-22 are prototypes)
  - WINK data licensing note (proprietary data not included)
  - SVG logo and updated README branding
  - Model cards for all 4 pricers (MYGA, FIA, RILA, GLWB)

- **Testing & Quality**
  - E2E Testing Remediation (P0-P3): ~900 new tests
  - Oracle fallback for cross-library validation
  - Coverage gating (75% threshold)
  - Deep Skeptical Audit tests
  - 2,696 passing tests across 9 categories, 85%+ coverage

- **Type Safety**
  - Full mypy strictness: zero `ignore_errors` modules
  - Type annotations for all regulatory, stress testing, GLWB, Heston modules

### Changed

- **Version**: 0.2.0 -> 1.0.0 (Production/Stable)
- **PyPI classifier**: "Development Status :: 5 - Production/Stable"
- Renamed `CONSTITUTION.md` -> `METHODOLOGY.md` (updated 59 file references)
- Consolidated all GitHub URLs to `brandonmbehring-dev/annuity-pricing`
- Updated CONTRIBUTING.md: "Black" -> "Ruff" formatting
- ArXiv paper updated: test counts, version references, URLs
- Zenodo metadata updated: test counts, version, URLs

### Fixed

- Fixed mypy type errors in 11 source files (33 errors resolved)
- Fixed stale test count in paper/zenodo.json (1011 -> 2471+)
- Fixed URL inconsistency (bbehring -> brandonmbehring-dev) across 15 files

---

## [0.2.0] - 2025-12-06

### Added

- **Technical Hardening**
  - Wired mortality tables into GLWB via `MortalityLoader`
  - Integrated behavioral models into `path_sim.py`
  - Risk-neutral drift with `RiskNeutralEquityParams`
  - RILA breakeven solver with `brentq`
  - RILA Greeks (`RILAGreeks` dataclass)

- **Stress Testing Framework** (Phase 12)
  - Historical scenario replay (2008 crisis, COVID-19)
  - Sensitivity analysis (Greeks-based)
  - Reverse stress testing
  - 272 stress testing tests

- **Stochastic Volatility** (Phase 11)
  - Heston model with COS method
  - SABR model for vol smile
  - Cross-validation vs QuantLib/pyfeng

- **PyPI Publishability**
  - `py.typed` marker for PEP 561
  - `CITATION.cff` for academic citations
  - GitHub Actions CI/CD workflows
  - Comprehensive pyproject.toml metadata

- **Validation**
  - Adapter tests for financepy, QuantLib, pyfeng
  - Validation notebooks executed with outputs
  - CROSS_VALIDATION_MATRIX.md with tolerances

- **Documentation**
  - Sphinx documentation with Furo theme
  - MyST-NB for notebook integration
  - API autodoc for all modules
  - ArXiv paper submission

### Changed

- Bumped version from 0.1.0 to 0.2.0
- Test count increased from 911 to 2470+
- Coverage increased to 85%+

### Fixed

- FIA/RILA PV formula now correctly discounts full payoff
- Greeks vega/theta scaling conventions documented
- 100% buffer edge case (maps to ATM put)

---

## [0.1.0] - 2025-12-05

### Added

- Initial release with Phases 0-10 complete
- MYGA, FIA, RILA, GLWB pricers
- Black-Scholes and Monte Carlo engines
- VM-21/VM-22 regulatory prototypes
- Behavioral models (lapse, withdrawal, expenses)
- Yield curve and mortality loaders
- METHODOLOGY.md with frozen methodology
- ROADMAP.md with implementation phases
- 911 passing tests

---

## Version History Summary

| Version | Date | Description |
|---------|------|-------------|
| 1.0.0 | 2026-02-26 | OSS professionalization, full mypy strictness, 1.0 release |
| 0.2.0 | 2025-12-06 | Technical hardening, PyPI release, Sphinx docs |
| 0.1.0 | 2025-12-05 | Initial project setup and context engineering |

---

## Versioning Policy

- **Major** (X.0.0): Breaking API changes, methodology changes
- **Minor** (0.X.0): New features, new products, new pricers
- **Patch** (0.0.X): Bug fixes, documentation updates
