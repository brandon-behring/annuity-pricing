# Contributing

Thank you for your interest in contributing to annuity-pricing!

## Development Setup

```bash
# Clone the repository
git clone https://github.com/brandonmbehring-dev/annuity-pricing.git
cd annuity-pricing

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install in development mode
pip install -e ".[dev,validation]"
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test categories
pytest tests/unit/ -v           # Unit tests
pytest tests/validation/ -v     # Validation tests
pytest tests/anti_patterns/ -v  # Bug prevention tests
```

## Code Style

We use:
- **ruff** for linting
- **mypy** for type checking
- **NumPy-style docstrings** with tier annotations

```bash
# Run linting
ruff check src/

# Run type checking
mypy src/

# Format code
ruff format src/
```

## Documentation

```bash
# Build documentation locally
cd docs
pip install -r requirements.txt
make html

# View at docs/_build/html/index.html
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Write tests for new functionality
4. Ensure all tests pass (`pytest tests/`)
5. Update documentation if needed
6. Submit a pull request

## Knowledge Tier System

When adding documentation, use tier annotations:

| Tier | Meaning | Example |
|------|---------|---------|
| **[T1]** | Academically validated | "Black-Scholes (1973)" |
| **[T2]** | Empirical from data | "Median cap = 5%" |
| **[T3]** | Assumption | "Option budget = 3%" |

## Code of Conduct

Please be respectful and constructive in all interactions.

## Questions?

Open an issue on GitHub or reach out to the maintainers.
