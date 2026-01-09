# Annuity Pricing

[![CI](https://github.com/brandonmbehring-dev/annuity-pricing/workflows/CI/badge.svg)](https://github.com/brandonmbehring-dev/annuity-pricing/actions)
[![Python versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://pypi.org/project/annuity-pricing/)
[![Coverage](https://codecov.io/gh/brandonmbehring-dev/annuity-pricing/branch/main/graph/badge.svg)](https://codecov.io/gh/brandonmbehring-dev/annuity-pricing)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Actuarial pricing calculations for MYGA, FIA, and RILA annuity products using WINK competitive rate data.

## Overview

This library provides research and pricing tooling for fixed annuity products:

- **MYGA** (Multi-Year Guaranteed Annuity): Fixed rate products
- **FIA** (Fixed Indexed Annuity): Index-linked with floor protection
- **RILA** (Registered Index-Linked Annuity): Buffer/floor protection products

### Capabilities

- **Competitive positioning**: Rate percentiles, spreads over Treasury
- **Product valuation**: Present value of liabilities, embedded option value
- **Rate setting**: Recommendations given market conditions
- **Option modeling**: Black-Scholes closed-form and Monte Carlo simulation

### Modeling Assumptions

This library uses the following key assumptions for pricing. Users should understand these limitations:

| Assumption | Description | Reference |
|------------|-------------|-----------|
| **Risk-neutral pricing** | Option values derived under Q-measure with μ = r - q | [T1] Black-Scholes (1973) |
| **GBM dynamics** | Single-factor log-normal index model | [T1] Standard option theory |
| **Constant volatility** | σ constant over term (no vol surface) | Simplification |
| **No credit risk** | Insurer solvency assumed | Simplification |
| **No transaction costs** | Continuous hedging assumed | [T1] BS framework |
| **FIA 0% floor** | Principal protected, credited ≥ 0 | [T1] Product design |
| **RILA buffer/floor** | Protection level as stated | [T1] Product design |
| **Single-period crediting** | Point-to-point (monthly averaging supported) | [F.3] |

**For research use.** Production deployment requires:
- Stochastic volatility models (SABR, Heston)
- Credit/counterparty risk adjustments
- Policyholder behavior calibration to company experience
- Regulatory capital calculations (VM-21/VM-22 are prototypes)

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd annuity-pricing

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install in development mode
pip install -e ".[dev]"
```

## Quick Start

```python
from annuity_pricing.products import ProductRegistry, create_default_registry
from annuity_pricing.data.schemas import MYGAProduct, FIAProduct

# Create registry with market environment
registry = create_default_registry(
    risk_free_rate=0.045,
    volatility=0.18,
)

# Price a MYGA product
myga = MYGAProduct(
    company_name="Example Life",
    product_name="5-Year MYGA",
    product_group="MYGA",
    status="current",
    guarantee_duration=5,
    fixed_rate=0.045,  # 4.5% guaranteed
)
result = registry.price(myga, principal=100_000)
print(f"Present Value: ${result.present_value:,.2f}")

# Price an FIA product
fia = FIAProduct(
    company_name="Example Life",
    product_name="S&P 500 Cap",
    product_group="FIA",
    status="current",
    index_used="S&P 500",
    indexing_method="Annual Point to Point",
    cap_rate=0.10,
    term_years=6,
)
result = registry.price(fia, term_years=6, premium=100_000)
print(f"Expected Credit: {result.expected_credit:.2%}")
```

## Common Pricing Mistakes

This library includes anti-pattern tests that catch common implementation errors.
If you're implementing similar logic, watch out for these:

| Mistake | Example | Why Bad | Fix |
|---------|---------|---------|-----|
| **Option > underlying** | `call_price > spot` | No-arbitrage violation [T1] | Check d1/d2 time scaling |
| **Negative FIA credit** | `-0.05` when floor is 0% | FIA floor enforcement broken | Use `max(credit, 0)` |
| **Buffer absorbs gains** | Positive index, negative payoff | Buffer mechanics inverted | Buffer absorbs LOSSES only |
| **Put-call parity fails** | `C - P ≠ S - Ke^(-rT)` | BS implementation error | Verify d1/d2 formulas |
| **Wrong drift** | Using μ instead of r-q | Physical vs risk-neutral measure | Use r - q for Q-measure |

**Automated detection**: Run `pytest tests/anti_patterns/ -v` to verify these constraints.

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run anti-pattern tests (must pass before commit)
pytest tests/anti_patterns/ -v

# Run with coverage
pytest tests/ --cov=src -v
```

## Project Structure

```
src/annuity_pricing/
├── config/          # Settings and market parameters
├── data/            # WINK data loading and cleaning
├── products/        # Product pricers (MYGA, FIA, RILA)
├── competitive/     # Rate positioning analysis
├── valuation/       # Present value calculations
├── options/         # Option pricing (BS, Monte Carlo)
├── rate_setting/    # Rate recommendations
└── validation/      # Validation gates and checks
```

## Documentation

- See `CLAUDE.md` for development conventions
- See `docs/knowledge/` for domain documentation
- See `wink-research-archive/` for WINK data documentation

## License

MIT License - see LICENSE file for details.
