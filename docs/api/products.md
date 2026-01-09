# Products API

Product pricers for MYGA, FIA, RILA, and related annuity products.

## Which Pricer Should I Use?

Use this decision tree to select the appropriate pricer:

```{mermaid}
graph TD
    A[Annuity Product] --> B{Downside Protection?}
    B -->|Full 0% floor| C[FIA]
    B -->|Partial buffer/floor| D[RILA]
    B -->|Fixed rate guarantee| E[MYGA]
    B -->|Lifetime income rider| F[GLWB]

    C --> G{Crediting Method?}
    G -->|Cap| H[CappedCallPayoff]
    G -->|Participation| I[ParticipationPayoff]
    G -->|Spread| J[SpreadPayoff]

    D --> K{Protection Type?}
    K -->|Absorbs first X%| L[BufferPayoff]
    K -->|Covers beyond X%| M[FloorPayoff]

    style A fill:#e1f5fe
    style C fill:#c8e6c9
    style D fill:#fff9c4
    style E fill:#ffccbc
    style F fill:#e1bee7
```

### Product Comparison

| Product | Downside | Upside | Complexity | Typical Use |
|---------|----------|--------|------------|-------------|
| **MYGA** | None (fixed) | Fixed rate | Low | Accumulation |
| **FIA** | 0% floor | Capped/Part. | Medium | Conservative growth |
| **RILA** | Buffer/Floor | Higher caps | High | Growth-oriented |
| **GLWB** | Guarantee | Variable | High | Lifetime income |

## FIA Crediting Methods

```{mermaid}
graph LR
    A[Index Return] --> B{Method}
    B -->|Cap| C["min(return, cap)"]
    B -->|Participation| D["return × part_rate"]
    B -->|Spread| E["max(0, return - spread)"]

    C --> F[Apply 0% Floor]
    D --> F
    E --> F

    F --> G[Credited Return]
```

## RILA Protection Mechanics

```{mermaid}
graph TB
    subgraph Buffer["Buffer Protection"]
        B1["Index: -15%"]
        B2["Buffer: 10%"]
        B3["Client: -5%"]
        B1 --> B2 --> B3
    end

    subgraph Floor["Floor Protection"]
        F1["Index: -15%"]
        F2["Floor: -10%"]
        F3["Client: -10%"]
        F1 --> F2 --> F3
    end
```

**Buffer**: Absorbs FIRST X% of losses (put spread)
**Floor**: Limits losses to X% (OTM put)

---

## Product Schemas

```{eval-rst}
.. automodule:: annuity_pricing.data.schemas
   :members:
   :undoc-members:
   :show-inheritance:
```

## Base Pricer

```{eval-rst}
.. automodule:: annuity_pricing.products.base
   :members:
   :undoc-members:
   :show-inheritance:
```

## MYGA Pricer

```{eval-rst}
.. automodule:: annuity_pricing.products.myga
   :members:
   :undoc-members:
   :show-inheritance:
```

## FIA Pricer

```{eval-rst}
.. automodule:: annuity_pricing.products.fia
   :members:
   :undoc-members:
   :show-inheritance:
```

## RILA Pricer

```{eval-rst}
.. automodule:: annuity_pricing.products.rila
   :members:
   :undoc-members:
   :show-inheritance:
```

## Product Registry

```{eval-rst}
.. automodule:: annuity_pricing.products.registry
   :members:
   :undoc-members:
   :show-inheritance:
```
