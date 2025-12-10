# Regulatory: VM-21 and VM-22

```{warning}
VM-21/VM-22 implementations are **prototypes** pending full NAIC scenario compliance.
See the [API Reference](../api/regulatory.md) for current capabilities.
```

## Overview

VM-21 and VM-22 are NAIC Valuation Manual requirements for principle-based reserving (PBR).

## VM-21: Variable Annuities

Reserve calculation for VA products with living benefits:

```python
from annuity_pricing.regulatory.vm21 import VM21Calculator

calculator = VM21Calculator(
    yield_curve=curve,
    mortality_table=table,
    n_scenarios=1000,
)

result = calculator.calculate_reserve(contract)
print(f"CTE70 Reserve: ${result.cte70:,.0f}")
```

## VM-22: Fixed Annuities

Reserve calculation for fixed annuity products:

```python
from annuity_pricing.regulatory.vm22 import VM22Calculator

calculator = VM22Calculator(yield_curve=curve)
result = calculator.calculate_reserve(contract)
```

## Scenario Generation

```python
from annuity_pricing.regulatory.scenarios import ScenarioGenerator

generator = ScenarioGenerator(n_scenarios=1000, seed=42)
scenarios = generator.generate_risk_neutral()
```

## Caveats

```{warning}
VM-21/VM-22 implementations are **beta** and for research purposes only.
Not suitable for production regulatory filings.
```

## See Also

- {doc}`glwb_walkthrough` — GLWB valuation
- {doc}`../api/regulatory` — Regulatory API reference
