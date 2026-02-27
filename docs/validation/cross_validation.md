# Cross-Validation

This library is cross-validated against external implementations to ensure correctness.

## Validation Status

| Module | Validator | Status | Date |
|--------|-----------|--------|------|
| Black-Scholes | financepy | ✅ Validated | 2025-12-06 |
| Monte Carlo | Internal BS | ✅ Validated | 2025-12-06 |
| Greeks | financepy | ✅ Validated | 2025-12-06 |
| Yield Curves | QuantLib | ✅ Validated | 2025-12-06 |
| Mortality | - | ⚠️ Stub | - |

## Achieved Tolerances

| Validation | Target | Achieved |
|------------|--------|----------|
| BS Call Price vs financepy | <0.02 | ✅ <0.01 |
| BS Put Price vs financepy | <0.02 | ✅ <0.01 |
| BS Delta vs financepy | <0.01 | ✅ <0.001 |
| BS Gamma vs financepy | <0.001 | ✅ <0.0001 |
| BS Vega vs financepy | <0.5 | ✅ <0.1 (scaled) |
| BS Theta vs financepy | <0.05 | ✅ <0.01 (scaled) |
| MC→BS (100k paths) | <0.15 | ✅ <0.10 |
| Hull 15.6 golden case | <0.02 | ✅ <0.01 |

## Adapter Tests

```bash
pytest tests/unit/test_adapters.py -v
# 19 passed, 4 skipped
```

| Adapter | Tests | Status |
|---------|-------|--------|
| FinancepyAdapter | 7 | ✅ PASSED |
| QuantLibAdapter | 7 | ✅ PASSED |
| PyfengAdapter | 4 | ⚠️ SKIPPED (scipy compatibility) |

## Running Validation

```bash
# Install validation dependencies
pip install annuity-pricing[validation]

# Run adapter tests
pytest tests/unit/test_adapters.py -v

# Run validation notebooks
jupyter nbconvert --execute notebooks/validation/options/*.ipynb
```

## Known Issues

### pyfeng scipy compatibility

pyfeng uses `scipy.misc.derivative` which was removed in scipy 1.12+.
Tests are skipped until upstream fix is available.

## See Also

- {doc}`golden_cases` — Golden test cases
- [CROSS_VALIDATION_MATRIX.md](https://github.com/brandon-behring/annuity-pricing/blob/main/docs/CROSS_VALIDATION_MATRIX.md)
