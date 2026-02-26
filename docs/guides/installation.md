# Installation

## Requirements

- Python 3.10 or higher
- NumPy, Pandas, SciPy (installed automatically)

## Installation Options

### From PyPI (Recommended)

```bash
pip install annuity-pricing
```

### With Optional Dependencies

```bash
# Validation dependencies (financepy, QuantLib, pyfeng)
pip install annuity-pricing[validation]

# Development dependencies
pip install annuity-pricing[dev]

# All optional dependencies
pip install annuity-pricing[all]
```

### From Source

```bash
git clone https://github.com/brandonmbehring-dev/annuity-pricing.git
cd annuity-pricing
pip install -e ".[dev,validation]"
```

## Verification

```python
import annuity_pricing
print(annuity_pricing.__version__)  # Should print "1.0.0"

# Quick test
from annuity_pricing.options.pricing.black_scholes import black_scholes_call
price = black_scholes_call(spot=100, strike=100, rate=0.05, dividend=0, volatility=0.2, time_to_expiry=1)
print(f"ATM call price: {price:.2f}")  # Should be ~10.45
```

## Optional Dependencies

| Extra | Packages | Purpose |
|-------|----------|---------|
| `validation` | financepy, QuantLib-Python, pyfeng | Cross-validation |
| `actuarial` | actuarialmath, lifelib | Mortality tables |
| `viz` | matplotlib, seaborn, plotly | Visualization |
| `dev` | pytest, mypy, ruff | Development |

## Troubleshooting

### QuantLib Installation Issues

On some systems, QuantLib-Python requires compilation:

```bash
# Ubuntu/Debian
sudo apt-get install libquantlib0-dev
pip install QuantLib-Python

# macOS (with Homebrew)
brew install quantlib
pip install QuantLib-Python
```

### Import Errors

If you see `ModuleNotFoundError: No module named 'annuity_pricing'`:

```bash
# Ensure you're in the right environment
which python
pip list | grep annuity

# Reinstall
pip install --force-reinstall annuity-pricing
```
