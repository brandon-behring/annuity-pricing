# annuity-pricing

**Open-source actuarial pricing for MYGA, FIA, RILA, and GLWB annuity products.**

```{image} https://img.shields.io/pypi/v/annuity-pricing.svg
:target: https://pypi.org/project/annuity-pricing/
:alt: PyPI version
```
```{image} https://img.shields.io/pypi/pyversions/annuity-pricing.svg
:target: https://pypi.org/project/annuity-pricing/
:alt: Python versions
```

---

## What is annuity-pricing?

A research-focused Python library for pricing and analyzing annuity products:

- **MYGA** (Multi-Year Guaranteed Annuity) — Present value calculations with guaranteed rates
- **FIA** (Fixed Indexed Annuity) — Option budgeting with caps, participation rates, and spreads
- **RILA** (Registered Index-Linked Annuity) — Buffer/floor protection with market participation
- **GLWB** (Guaranteed Lifetime Withdrawal Benefit) — Monte Carlo valuation of living benefits

### Key Features

| Feature | Description |
|---------|-------------|
| **Risk-Neutral Pricing** | Black-Scholes and Monte Carlo engines with proper drift |
| **Cross-Validated** | Verified against financepy, QuantLib, and Hull textbook examples |
| **Regulatory Prototypes** | VM-21/VM-22 reserve calculations (beta) |
| **Behavioral Models** | Dynamic lapse, withdrawal efficiency, expense loading |
| **Research-Grade** | Type hints, frozen dataclasses, 2470+ tests (6 skipped) |

---

## Quick Start

### Installation

```bash
pip install annuity-pricing
```

For development with validation dependencies:

```bash
pip install annuity-pricing[validation]
```

### Basic Usage

```python
from annuity_pricing.products.fia import FIAPricer, MarketParams
from annuity_pricing.data.schemas import FIAProduct

# Set up market conditions
market = MarketParams(
    spot=100.0,
    risk_free_rate=0.05,
    dividend_yield=0.02,
    volatility=0.20,
)

# Price an FIA with 10% cap
fia = FIAProduct(
    company_name="Example Life",
    product_name="S&P 500 Cap",
    product_group="FIA",
    status="current",
    cap_rate=0.10,
    index_used="S&P 500",
)

pricer = FIAPricer(market_params=market)
result = pricer.price(fia, term_years=1.0, premium=100_000)

print(f"Expected Credit: {result.expected_credit:.2%}")
print(f"Present Value: ${result.present_value:,.0f}")
```

---

## Documentation

```{toctree}
:maxdepth: 2
:caption: Getting Started

guides/getting_started
guides/installation
```

```{toctree}
:maxdepth: 2
:caption: Product Guides

guides/pricing_myga
guides/pricing_fia
guides/pricing_rila
guides/glwb_walkthrough
```

```{toctree}
:maxdepth: 2
:caption: Advanced Topics

guides/market_setup
guides/regulatory_vm21_vm22
guides/behavior_calibration
```

```{toctree}
:maxdepth: 2
:caption: Validation

testing_strategy
validation/validation_evidence
validation/cross_validation
validation/golden_cases
```

```{toctree}
:maxdepth: 2
:caption: API Reference

api/products
api/options
api/loaders
api/behavioral
api/glwb
api/regulatory
```

```{toctree}
:maxdepth: 1
:caption: Model Cards

model_cards/index
```

```{toctree}
:maxdepth: 1
:caption: Reference

glossary
reference/changelog
reference/contributing
```

---

## Validation Status

Cross-validated against external libraries (as of 2025-12-06):

| Module | Validator | Status |
|--------|-----------|--------|
| Black-Scholes | financepy | ✅ Validated |
| Monte Carlo | Internal BS | ✅ Validated |
| Greeks | financepy | ✅ Validated |
| Yield Curves | QuantLib | ✅ Validated |
| Mortality | - | ⚠️ Stub |

See {doc}`validation/cross_validation` for details.

---

## Citation

If you use this software in research, please cite:

```bibtex
@software{annuity_pricing,
  author = {Behring, Brandon},
  title = {annuity-pricing: Actuarial Pricing for Annuity Products},
  year = {2025},
  url = {https://github.com/brandonmbehring-dev/annuity-pricing}
}
```

---

## License

MIT License. See [LICENSE](https://github.com/brandonmbehring-dev/annuity-pricing/blob/main/LICENSE) for details.

## Indices and tables

* {ref}`genindex`
* {ref}`modindex`
* {ref}`search`
