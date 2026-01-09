# RILAPricer Model Card

## Overview

| Field | Value |
|-------|-------|
| **Version** | 0.2.0 |
| **Module** | `annuity_pricing.products.rila` |
| **Type** | Pricer |
| **License** | MIT |
| **Knowledge Tier** | T1 (Put spread replication) |

## Component Details

`RILAPricer` values Registered Index-Linked Annuity products with
partial downside protection. Unlike FIA (0% floor), RILA offers
buffer or floor protection in exchange for higher upside caps.

## Intended Use

**Primary use cases**:
- Fair value calculation for RILA products
- Buffer vs floor protection comparison
- Competitive cap rate analysis
- Product design and pricing

**Out-of-scope**:
- Real-time trading
- Policy administration
- Regulatory capital (see VM-21)

## Parameters

| Parameter | Type | Default | Description | Tier |
|-----------|------|---------|-------------|------|
| `market_params` | MarketParams | required | Spot, rate, vol, dividend | T1 |
| `buffer` | float | 0.10 | Buffer level (e.g., 0.10 = 10%) | T1 |
| `floor` | float | None | Floor level (alternative to buffer) | T1 |
| `cap_rate` | float | 0.15 | Maximum credited return | T2 |
| `participation` | float | 1.0 | Participation above buffer | T2 |

## Protection Mechanics

### Buffer (absorbs FIRST X% of losses)
[T1] Implemented as put spread: Long ATM put - Short OTM put

```
Index Return: -15%
Buffer: 10%
Client Loss: -5% (buffer absorbed first 10%)
```

### Floor (covers losses BEYOND X%)
[T1] Implemented as long OTM put

```
Index Return: -15%
Floor: -10%
Client Loss: -10% (capped at floor)
```

## Assumptions

| Assumption | Validation | Tier |
|------------|------------|------|
| Buffer = put spread | Options theory | T1 |
| Floor = OTM put | Options theory | T1 |
| Log-normal returns | Standard BS | T1 |
| Constant volatility | Use Heston if needed | T1 |
| European exercise | Standard RILA terms | T1 |

## Validation

### Put Spread Replication
[T1] Buffer payoff verified against explicit put spread:
- Long ATM put (K = S)
- Short OTM put (K = S × (1 - buffer))

### Boundary Conditions
[T1] Verified:
- `buffer(0%)` = `floor(0%)` = FIA equivalent
- Maximum loss = index return - buffer (for buffer)
- Maximum loss = floor level (for floor)

### Cross-Library
[T2] QuantLib validation for put spread pricing

## Limitations

1. **Buffer vs Floor exclusive**: Cannot combine both
2. **Single period**: No multi-year compounding
3. **No tiered buffers**: Single buffer level only
4. **SEC registered**: Subject to securities regulation

## References

- [T1] SEC Rule: RILAs as registered securities
- [T1] Hull, J. C. (2018). *Options, Futures, and Other Derivatives*
- [T2] WINK RILA rate surveys

## See Also

- {class}`annuity_pricing.products.fia.FIAPricer` - For 0% floor
- {class}`annuity_pricing.options.payoffs.rila.BufferPayoff` - Buffer calculation
- {doc}`/guides/pricing_rila` - Usage guide
