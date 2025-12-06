# Changelog

All notable changes to annuity-pricing will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Initial project structure with context engineering setup
- WINK data dictionary (62 columns) in `wink-research-archive/`
- 10 L3 reference summaries in `docs/knowledge/references/`:
  - Black-Scholes 1973 (original formula)
  - Boyle & Tian 2008 (EIA investor perspective)
  - Bauer, Kling & Russ 2008 (universal GMxB)
  - Hardy 2003 (investment guarantees, EIA crediting, RSLN model)
  - Hull 2021 (BS-Merton, Greeks)
  - NAIC Model 805 (nonforfeiture law)
  - NAIC Model 806 (regulation, EIA option cost test)
  - FINRA 22-08 (complex products guidance)
  - SEC RILA 2023 (investor testing report)
- Helper scripts:
  - `scripts/validate.sh` - Tests + type check + lint
  - `scripts/setup_check.py` - Environment verification
  - `scripts/fetch_market_data.py` - FRED/Yahoo data fetch
  - `scripts/run_notebooks.sh` - Notebook execution
- Validation notebook scaffolds in `notebooks/validation/`
- Domain knowledge documents in `docs/knowledge/domain/`
- CLAUDE.md with troubleshooting section

### Changed
- N/A (initial release)

### Fixed
- N/A (initial release)

---

## [0.1.0] - 2025-12-05

### Added
- Initial project setup
- CONSTITUTION.md with frozen methodology
- ROADMAP.md with implementation phases
- pyproject.toml with dependencies
- Source structure under `src/annuity_pricing/`
- Test structure under `tests/`

---

## Version History Summary

| Version | Date | Description |
|---------|------|-------------|
| 0.1.0 | 2025-12-05 | Initial project setup and context engineering |

---

## Versioning Policy

- **Major** (X.0.0): Breaking API changes, methodology changes
- **Minor** (0.X.0): New features, new products, new pricers
- **Patch** (0.0.X): Bug fixes, documentation updates

---

## Notes for Maintainers

When making changes:

1. **Add entry to [Unreleased]** section immediately
2. **Group by type**: Added, Changed, Deprecated, Removed, Fixed, Security
3. **Include references** to issues/PRs where applicable
4. **On release**: Move [Unreleased] items to versioned section, update dates
