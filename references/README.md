# References - Annuity Pricing

Academic references supporting the annuity-pricing codebase.

**Last Updated**: 2025-12-05

---

## Directory Structure

```
references/
├── textbooks/              # Core textbooks for options and actuarial pricing
├── papers/
│   └── options/            # Option pricing theory and annuity design
└── regulatory/             # NAIC and FINRA regulatory documents
```

---

## Textbooks

### Options & Derivatives

| File | Citation | Purpose |
|------|----------|---------|
| `Hull_2021_Options_Futures_Derivatives_11ed.pdf` | Hull, J. C. (2021). *Options, Futures, and Other Derivatives* (11th ed.). Pearson. ISBN: 978-0136939979 | Black-Scholes, Greeks, volatility surfaces |
| `Glasserman_2003_Monte_Carlo_Methods.pdf` | Glasserman, P. (2003). *Monte Carlo Methods in Financial Engineering*. Springer. ISBN: 978-0387004518 | GBM paths, variance reduction, path-dependent options |

### Actuarial

| File | Citation | Purpose |
|------|----------|---------|
| `Hardy_2003_Investment_Guarantees.pdf` | Hardy, M. R. (2003). *Investment Guarantees: Modeling and Risk Management for Equity-Linked Life Insurance*. Wiley. ISBN: 978-0471392903 | Equity-indexed annuity valuation, GMAB/GMDB pricing |

---

## Papers

### Options Pricing

| File | Citation | DOI | Purpose |
|------|----------|-----|---------|
| `Black_Scholes_1973_Option_Pricing.pdf` | Black, F., & Scholes, M. (1973). The Pricing of Options and Corporate Liabilities. *Journal of Political Economy*, 81(3), 637-654. | [10.1086/260062](https://doi.org/10.1086/260062) | Foundation of option pricing theory |
| `Boyle_Tian_2008_Equity_Indexed_Annuities.pdf` | Boyle, P., & Tian, W. (2008). The design of equity-indexed annuities. *Insurance: Mathematics and Economics*, 43(3), 303-315. | [10.1016/j.insmatheco.2008.05.006](https://doi.org/10.1016/j.insmatheco.2008.05.006) | FIA cap/participation design, buffer payoffs |

---

## Regulatory Documents

| File | Citation | Purpose |
|------|----------|---------|
| `NAIC_Model_805_Nonforfeiture_Law.pdf` | NAIC Model #805. Standard Nonforfeiture Law for Individual Deferred Annuities. | MGSV calculation, surrender values |
| `NAIC_Model_806_Regulation.pdf` | NAIC Model #806. Regulation for Recognizing a New Annuity Mortality Table for Use in Determining Reserve Liabilities. | Reserve calculations |
| `FINRA_Notice_22-08_Complex_Products.pdf` | FINRA Regulatory Notice 22-08 (March 2022). Complex Products and Options—Increased Complexity Requires a Stronger Approach. | RILA suitability requirements |

---

## Missing References (Manual Acquisition Needed)

SEC documents are blocked by rate limiting. Fetch manually:

| Document | URL |
|----------|-----|
| SEC RILA Investor Testing Report (2023) | https://www.sec.gov/files/rila-report-092023.pdf |
| SEC RILA Final Rule (2024) | https://www.sec.gov/files/rules/final/2024/33-11294.pdf |

---

## Usage in Codebase

| Reference | Module | How Used |
|-----------|--------|----------|
| Hull (2021) Ch. 15-19 | `options/pricing/black_scholes.py` | BS formula, Greeks implementation |
| Hull (2021) Ch. 21 | `options/simulation/monte_carlo.py` | GBM simulation, variance reduction |
| Glasserman (2003) Ch. 3-4 | `options/simulation/gbm.py` | Antithetic variates, control variates |
| Hardy (2003) Ch. 5-7 | `products/fia.py`, `products/rila.py` | GMAB valuation, embedded options |
| Black & Scholes (1973) | `options/pricing/black_scholes.py` | Core pricing formula |
| Boyle & Tian (2008) | `options/payoffs/fia.py`, `options/payoffs/rila.py` | Cap/participation design, buffer mechanics |
| NAIC 805/806 | `valuation/myga_pv.py` | MGSV factor (87.5%) |
| FINRA 22-08 | `validation/gates.py` | Suitability requirements for RILA |

---

## Citation Format

For academic use, cite as:

```bibtex
@book{hull2021options,
  author = {Hull, John C.},
  title = {Options, Futures, and Other Derivatives},
  edition = {11},
  publisher = {Pearson},
  year = {2021},
  isbn = {978-0136939979}
}

@book{glasserman2003monte,
  author = {Glasserman, Paul},
  title = {Monte Carlo Methods in Financial Engineering},
  publisher = {Springer},
  year = {2003},
  series = {Applications of Mathematics},
  volume = {53},
  isbn = {978-0387004518}
}

@book{hardy2003investment,
  author = {Hardy, Mary R.},
  title = {Investment Guarantees: Modeling and Risk Management for Equity-Linked Life Insurance},
  publisher = {Wiley},
  year = {2003},
  isbn = {978-0471392903}
}

@article{black1973pricing,
  author = {Black, Fischer and Scholes, Myron},
  title = {The Pricing of Options and Corporate Liabilities},
  journal = {Journal of Political Economy},
  volume = {81},
  number = {3},
  pages = {637--654},
  year = {1973},
  doi = {10.1086/260062}
}

@article{boyle2008design,
  author = {Boyle, Phelim and Tian, Weidong},
  title = {The design of equity-indexed annuities},
  journal = {Insurance: Mathematics and Economics},
  volume = {43},
  number = {3},
  pages = {303--315},
  year = {2008},
  doi = {10.1016/j.insmatheco.2008.05.006}
}
```
