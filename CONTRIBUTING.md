# Contributing to annuity-pricing

Thank you for your interest in contributing! This document outlines the process and guidelines.

## Development Setup

```bash
# Clone and setup
git clone <repo-url>
cd annuity-pricing

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: .\venv\Scripts\activate  # Windows

# Install in development mode
pip install -e ".[dev]"

# Verify setup
python scripts/setup_check.py --verbose
```

## Code Quality Standards

### Required Before PR

1. **Anti-pattern tests MUST pass**:
   ```bash
   pytest tests/anti_patterns/ -v
   ```
   These tests prevent critical actuarial bugs (arbitrage violations, put-call parity failures, etc.)

2. **All tests pass**:
   ```bash
   pytest tests/ -v
   ```

3. **Type checking**:
   ```bash
   mypy src/annuity_pricing
   ```

4. **Linting**:
   ```bash
   ruff check src/ tests/
   ```

### Code Style

- **Type hints required** on all function signatures
- **NumPy-style docstrings** with knowledge tier tags [T1]/[T2]/[T3]
- **Ruff formatting** (100 char line length)
- **Explicit error handling** - never fail silently

### Knowledge Tier Tags

All claims in docstrings must be tagged:

| Tag | Meaning | Example |
|-----|---------|---------|
| `[T1]` | Academically validated | "Black-Scholes (1973)" |
| `[T2]` | Empirically derived | "Median cap rate = 5%" |
| `[T3]` | Assumption | "Option budget = 3%" |

## Pull Request Process

1. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Write tests first** (test-driven development encouraged)

3. **Ensure all checks pass locally**:
   ```bash
   pytest tests/anti_patterns/ -v  # Critical bugs
   pytest tests/ -v                # All tests
   mypy src/annuity_pricing        # Type checking
   ruff check src/ tests/          # Linting
   ```

4. **Commit with descriptive message**:
   ```
   feat: Add buffer payoff calculation for RILA

   - Implements put spread replication [T1]
   - Validated against QuantLib
   - Tests in tests/validation/test_rila_vs_quantlib.py
   ```

5. **Open PR** with:
   - Clear description of changes
   - Link to any related issues
   - Test evidence (coverage, validation)

## Commit Message Format

```
<type>: <short summary>

<optional body with details>

<optional footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `test`: Adding/updating tests
- `refactor`: Code change that neither fixes bug nor adds feature
- `chore`: Build, config, etc.

## Test Categories

| Directory | Purpose | When to Run |
|-----------|---------|-------------|
| `tests/anti_patterns/` | Bug prevention | Before every commit |
| `tests/validation/` | External validation (Hull examples) | After pricing changes |
| `tests/unit/` | Unit tests | Always |
| `tests/integration/` | End-to-end tests | Before PR |

## Adding New Tests

### Anti-Pattern Tests

When you fix a bug, add a test that would have caught it:

```python
# tests/anti_patterns/test_my_bug.py
def test_option_price_not_exceed_underlying():
    """[T1] Option price must be < underlying price."""
    # This test prevents a specific class of bug
    result = price_option(...)
    assert result.price < underlying, "No-arbitrage violation"
```

### Validation Tests

When implementing pricing logic, validate against external sources:

```python
# tests/validation/test_my_implementation.py
def test_vs_hull_example_15_6():
    """[T1] Verify against Hull textbook example."""
    # Hull Ch. 15, Example 15.6
    expected = 4.76  # From textbook
    actual = black_scholes_call(S=42, K=40, r=0.10, q=0, sigma=0.20, T=0.5)
    assert abs(actual - expected) < 0.01
```

## Public API Stability Policy

Starting with v1.0.0, annuity-pricing follows [Semantic Versioning](https://semver.org/):

- **Public API** = all symbols importable from `annuity_pricing.*` top-level modules
- **Patch** (1.0.x): Bug fixes only, no API changes
- **Minor** (1.x.0): New features, backward-compatible
- **Major** (x.0.0): Breaking changes (with deprecation cycle)

Internal modules (prefixed with `_` or under `annuity_pricing.internal`) are not covered by this policy.

## Questions?

- Open an issue for bugs or feature requests
- Check existing issues before creating new ones
- For security issues, see SECURITY.md
