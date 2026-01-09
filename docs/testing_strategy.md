# Testing Strategy

This document describes the multi-layer validation architecture used in
annuity-pricing to ensure mathematical correctness and prevent pricing errors.

## 6-Layer Validation Architecture

| Layer | Purpose | Location | Gate |
|-------|---------|----------|------|
| 1 | **Unit tests** | `tests/unit/` | Function correctness |
| 2 | **Integration tests** | `tests/integration/` | End-to-end flows |
| 3 | **Anti-pattern tests** | `tests/anti_patterns/` | Bug prevention |
| 4 | **Validation tests** | `tests/validation/` | Golden cases |
| 5 | **Property tests** | `tests/properties/` | Invariants |
| 6 | **Stress tests** | `tests/chaos/` | Edge cases |

## Layer 3: Anti-Pattern Tests (Critical)

These tests catch known bugs **BEFORE** they happen. They encode lessons
from past pricing errors and domain knowledge.

### Test Matrix

| Test | Prevents | Why Critical |
|------|----------|--------------|
| `test_arbitrage_bounds.py` | Option > underlying | No-arbitrage [T1] |
| `test_put_call_parity.py` | BS implementation errors | Fundamental identity [T1] |
| `test_floor_enforcement.py` | Negative FIA credits | FIA floor = 0% [T1] |
| `test_buffer_mechanics.py` | Buffer payoff errors | Buffer absorbs first X% [T1] |
| `test_spread_rate_halt.py` | Unreasonable spreads | Market sanity check [T2] |
| `test_vectorized_consistency.py` | Scalar/vector mismatch | Implementation correctness |

### Anti-Pattern Test Example

```python
@pytest.mark.anti_pattern
def test_option_cannot_exceed_underlying():
    """[T1] No-arbitrage: C ≤ S, P ≤ K*exp(-rT)."""
    spot = 100.0
    call_price = black_scholes_call(spot, strike=100, ...)

    assert call_price <= spot, (
        f"ARBITRAGE VIOLATION: Call {call_price:.4f} > Spot {spot:.4f}"
    )
```

## Layer 4: Validation Tests (Known Answers)

Golden cases from textbooks and external libraries establish correctness.

### Hull Textbook Examples

| Example | S | K | r | σ | T | Expected | Status |
|---------|---|---|---|---|---|----------|--------|
| 15.6 Call | 42 | 40 | 0.10 | 0.20 | 0.5 | 4.76 | ✓ |
| 15.6 Put | 42 | 40 | 0.10 | 0.20 | 0.5 | 0.81 | ✓ |

### Cross-Library Validation

| Library | Module | Tolerance | Status |
|---------|--------|-----------|--------|
| financepy | BS pricing | 1e-10 | ✓ |
| QuantLib | Yield curves | 1e-8 | ✓ |
| pyfeng | SABR vol | 1e-6 | ✓ |

## Coverage Targets

| Category | Target | Rationale |
|----------|--------|-----------|
| Core pricers | 90% | Critical path, mathematical correctness |
| Options module | 85% | Foundation for all pricing |
| Loaders | 70% | I/O handling, error cases |
| Scripts | 60% | Utility code, lower risk |

**Overall minimum**: 75% (enforced in CI)

## Running Tests

### Full Suite

```bash
pytest tests/ -v --cov=annuity_pricing --cov-fail-under=75
```

### Anti-Pattern Tests Only

```bash
# MUST pass before every commit
pytest tests/anti_patterns/ -v
```

### Validation Tests

```bash
# Golden cases from Hull textbook
pytest tests/validation/test_bs_known_answers.py -v

# Cross-library validation
pytest tests/validation/test_fia_vs_financepy.py -v
```

### By Marker

```bash
# Run only anti-pattern tests
pytest -m anti_pattern

# Run validation tests
pytest -m validation

# Skip slow tests
pytest -m "not slow"
```

## Test Markers

| Marker | Purpose |
|--------|---------|
| `@pytest.mark.anti_pattern` | Bug prevention (MUST pass) |
| `@pytest.mark.validation` | External verification |
| `@pytest.mark.unit` | Standard unit tests |
| `@pytest.mark.integration` | End-to-end flows |
| `@pytest.mark.slow` | Tests > 10 seconds |

## Continuous Integration

The CI workflow enforces:

1. **All tests pass** on Ubuntu and Windows
2. **Coverage ≥ 75%** aggregate
3. **Anti-pattern tests pass** (blocking)
4. **mypy clean** (no type errors)
5. **ruff clean** (no lint errors)

## Adding New Tests

### For New Features

1. Write anti-pattern test first (what bugs could occur?)
2. Write unit tests for individual functions
3. Write integration test for the workflow
4. Verify coverage meets thresholds

### For Bug Fixes

1. Write test that reproduces the bug
2. Verify test fails
3. Fix the bug
4. Verify test passes
5. Add to `docs/episodes/bugs/` postmortem

## See Also

- {doc}`/validation/cross_validation` - Detailed validation results
- {doc}`/validation/golden_cases` - Golden case definitions
- `tests/conftest.py` - Shared fixtures
