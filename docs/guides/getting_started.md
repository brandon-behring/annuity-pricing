# Getting Started

This guide walks you through the basics of using `annuity-pricing` to price annuity products.

## Installation

### Basic Installation

```bash
pip install annuity-pricing
```

### With Validation Dependencies

For cross-validation against external libraries:

```bash
pip install annuity-pricing[validation]
```

This includes `financepy`, `QuantLib-Python`, and `pyfeng` for verification.

### Development Installation

```bash
git clone https://github.com/brandon-behring/annuity-pricing.git
cd annuity-pricing
pip install -e ".[dev,validation]"
```

---

## Core Concepts

### Product Types

| Product | Description | Key Parameters |
|---------|-------------|----------------|
| **MYGA** | Guaranteed fixed rate | Term, guaranteed rate |
| **FIA** | Index-linked with floor | Cap, participation, floor (0%) |
| **RILA** | Index-linked with buffer/floor | Buffer/floor level, cap |
| **GLWB** | Lifetime withdrawal benefit | Rollup rate, withdrawal rate |

### Pricing Approach

All products use **risk-neutral pricing** [T1]:

1. **MYGA**: Deterministic cash flows discounted at risk-free rate
2. **FIA/RILA**: Option replication using Black-Scholes
3. **GLWB**: Monte Carlo simulation with behavioral assumptions

---

## Your First Pricing

### MYGA: Guaranteed Rate Product

```python
from annuity_pricing.products.myga import MYGAPricer
from annuity_pricing.data.schemas import MYGAProduct

# Define the product
myga = MYGAProduct(
    company_name="Example Life",
    product_name="5-Year MYGA",
    product_group="MYGA",
    status="current",
    fixed_rate=0.045,  # 4.5% guaranteed
    guarantee_duration=5,
)

# Price it
pricer = MYGAPricer()
result = pricer.price(myga, principal=100_000, discount_rate=0.05)

print(f"Present Value: ${result.present_value:,.0f}")
# Spread is the difference between earned rate and discount rate
spread = result.details["fixed_rate"] - result.details["discount_rate"]
print(f"Spread to Insurer: {spread:.2%}")
```

### FIA: Indexed Annuity with Cap

```python
from annuity_pricing.products.fia import FIAPricer, MarketParams
from annuity_pricing.data.schemas import FIAProduct

# Market conditions
market = MarketParams(
    spot=100.0,
    risk_free_rate=0.05,
    dividend_yield=0.02,
    volatility=0.20,
)

# Product with 10% cap
fia = FIAProduct(
    company_name="Example Life",
    product_name="S&P 500 Cap",
    product_group="FIA",
    status="current",
    cap_rate=0.10,
    participation_rate=1.0,  # 100% participation
    index_used="S&P 500",
)

# Price
pricer = FIAPricer(market_params=market, seed=42)
result = pricer.price(fia, term_years=1.0, premium=100_000)

print(f"Expected Credit: {result.expected_credit:.2%}")
print(f"Option Budget: {result.option_budget:.2%}")
print(f"Present Value: ${result.present_value:,.0f}")
```

### RILA: Buffer Protection

```python
from annuity_pricing.products.rila import RILAPricer, MarketParams
from annuity_pricing.data.schemas import RILAProduct

# Market conditions
market = MarketParams(
    spot=100.0,
    risk_free_rate=0.05,
    dividend_yield=0.02,
    volatility=0.20,
)

# 10% buffer, 15% cap
rila = RILAProduct(
    company_name="Example Life",
    product_name="10% Buffer S&P",
    product_group="RILA",
    status="current",
    buffer_rate=0.10,
    buffer_modifier="Losses Covered Up To",
    cap_rate=0.15,
    index_used="S&P 500",
)

pricer = RILAPricer(market_params=market, seed=42)
result = pricer.price(rila, term_years=1.0, premium=100_000)

print(f"Expected Return: {result.expected_return:.2%}")
print(f"Downside Protection Value: ${result.protection_value:,.2f}")
print(f"Present Value: ${result.present_value:,.0f}")
```

---

## Understanding Results

### PricingResult Dataclass

All pricers return frozen dataclasses. The base class has common fields:

```python
@dataclass(frozen=True)
class PricingResult:
    present_value: float           # PV of future cash flows
    duration: Optional[float]      # Macaulay/modified duration
    convexity: Optional[float]     # Convexity measure
    details: Optional[dict]        # Product-specific details
    as_of_date: Optional[date]     # Valuation date
```

**Product-specific result classes** extend this with additional fields:

- **FIAPricingResult**: `expected_credit`, `option_budget`, `fair_cap`, `fair_participation`, `embedded_option_value`
- **RILAPricingResult**: `expected_return`, `protection_value`, `protection_type`, `upside_value`, `max_loss`

### Key Metrics

| Metric | Description | Typical Range |
|--------|-------------|---------------|
| `present_value` | Discounted value of liabilities | Premium ± 20% |
| `expected_credit` | E[credited return] under risk-neutral | 2-8% annually |
| `option_budget` | Option cost as % of premium | 2-5% |
| `fair_cap` | Cap that makes option budget = target | 5-15% |

---

## Market Data

### Setting Up Market Parameters

```python
from annuity_pricing.products.fia import MarketParams

# Manual specification
market = MarketParams(
    spot=4500.0,           # S&P 500 level
    risk_free_rate=0.045,  # Treasury yield
    dividend_yield=0.015,  # S&P dividend yield
    volatility=0.18,       # Implied volatility
)

# Or load from loaders (requires API keys)
from annuity_pricing.loaders.yield_curve import YieldCurveLoader
from annuity_pricing.data.market_data import get_sp500_dividend_yield

loader = YieldCurveLoader()
curve = loader.load_treasury_curve()
rate_5y = curve.rate(5.0)  # 5-year rate
```

---

## Validation

### Cross-Validation with External Libraries

```python
from annuity_pricing.adapters.financepy_adapter import FinancepyAdapter

adapter = FinancepyAdapter()

# Compare Black-Scholes prices
our_price = 4.76  # Our calculation
fp_price = adapter.price_call(spot=42, strike=40, rate=0.10, vol=0.20, time=0.5)

assert abs(our_price - fp_price) < 0.01, "Prices should match"
```

### Running Validation Tests

```bash
# Run all validation tests
pytest tests/validation/ -v

# Run adapter tests (requires validation deps)
pytest tests/unit/test_adapters.py -v
```

---

## Next Steps

- {doc}`pricing_myga` — Deep dive into MYGA calculations
- {doc}`pricing_fia` — FIA option budgeting and fair caps
- {doc}`pricing_rila` — Buffer vs floor protection analysis
- {doc}`glwb_walkthrough` — Monte Carlo GLWB valuation
- {doc}`../api/products` — Full API reference

---

## Knowledge Tiers

Throughout the documentation, claims are tagged with knowledge tiers:

| Tier | Meaning | Example |
|------|---------|---------|
| **[T1]** | Academically validated | "Black-Scholes (1973)" |
| **[T2]** | Empirical from data | "Median cap = 5%" |
| **[T3]** | Assumption | "Option budget = 3%" |

When working with parameters:
- **[T1]**: Apply directly
- **[T2]**: Verify against current data
- **[T3]**: Consider sensitivity analysis
