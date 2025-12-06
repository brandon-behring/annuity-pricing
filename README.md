# Annuity Pricing

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
    dividend_yield=0.02,
    volatility=0.18
)

# Price a MYGA product
myga = MYGAProduct(
    company="Example Life",
    product_name="5-Year MYGA",
    guarantee_duration=5,
    guaranteed_rate=0.045
)
result = registry.price(myga, premium=100_000)
print(f"Present Value: ${result.present_value:,.2f}")

# Price an FIA product
fia = FIAProduct(
    company="Example Life",
    product_name="S&P 500 Cap",
    guarantee_duration=6,
    index_name="S&P 500",
    crediting_method="annual_point_to_point",
    cap_rate=0.10
)
result = registry.price(fia, premium=100_000)
print(f"Expected Credit: {result.expected_credit:.2%}")
```

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
