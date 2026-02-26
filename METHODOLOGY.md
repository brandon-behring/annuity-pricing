# METHODOLOGY.md - Frozen Actuarial Pricing Methodology

**Purpose**: Immutable methodological decisions for actuarial pricing. NO CHANGES without documented justification and full re-evaluation.

**Status**: FROZEN (2025-12-04) | **Version**: 1.0

---

## Knowledge Tier Key

Throughout this document, claims are annotated with knowledge tiers:

| Tag | Meaning | Implication |
|-----|---------|-------------|
| `[T1]` | Academically validated | Trust and apply |
| `[T2]` | Empirical from WINK data | Apply, verify with current data |
| `[T3]` | Assumption, needs justification | Consider sensitivity analysis |

---

## 1. Product Definitions

### 1.1 MYGA (Multi-Year Guaranteed Annuity) [T1]

| Specification | Value | Tier | Source |
|--------------|-------|------|--------|
| **Rate guarantee** | Fixed for entire term | T1 | Contract definition |
| **Principal protection** | 100% | T1 | Contract definition |
| **Key field** | `fixedRate` | T2 | WINK schema |
| **Duration field** | `guaranteeDuration` | T2 | WINK schema |

### 1.2 FIA (Fixed Indexed Annuity) [T1]

| Specification | Value | Tier | Source |
|--------------|-------|------|--------|
| **Downside protection** | 0% floor (cannot go negative) | T1 | Contract definition |
| **Upside limits** | Cap, participation, spread | T1 | Contract definition |
| **Crediting methods** | PTP, monthly avg, monthly sum, TEP | T1 | Industry standard |
| **Index basis** | Price return (not total return) | T2 | Most contracts |

**FIA Crediting Formula [T1]**:
```python
# Point-to-Point with Cap
credited = min(max(index_return, 0), cap)

# Participation Rate
credited = max(index_return * participation, 0)

# Spread
credited = max(index_return - spread, 0)

# Performance Triggered
credited = trigger_rate if index_return > 0 else 0
```

### 1.3 RILA (Registered Index-Linked Annuity) [T1]

| Specification | Value | Tier | Source |
|--------------|-------|------|--------|
| **Downside protection** | Partial (buffer or floor) | T1 | Contract definition |
| **SEC registered** | Yes | T1 | Regulatory requirement |
| **Principal risk** | Yes (beyond buffer/floor) | T1 | Contract definition |

**Buffer Payoff Formula [T1]**:
```python
# Buffer: Insurer absorbs FIRST X% of losses
if index_return >= 0:
    payoff = min(index_return, cap)
elif index_return >= -buffer:
    payoff = 0  # Buffer absorbs loss
else:
    payoff = index_return + buffer  # Client absorbs excess
```

**Floor Payoff Formula [T1]**:
```python
# Floor: Client absorbs UP TO X% of losses
if index_return >= 0:
    payoff = min(index_return, cap)
else:
    payoff = max(index_return, -floor)  # Floor limits loss
```

**Critical Distinction [T1]**:
- **Buffer**: Protects against SMALL losses (absorbs first X%)
- **Floor**: Protects against LARGE losses (limits max loss to X%)

---

## 2. Option Pricing Fundamentals

### 2.1 Black-Scholes Framework [T1]

| Parameter | Symbol | Tier | Source |
|-----------|--------|------|--------|
| **Spot price** | S | T1 | Market data |
| **Strike price** | K | T1 | Contract |
| **Risk-free rate** | r | T1 | Treasury/SOFR |
| **Volatility** | σ | T1 | Implied from market |
| **Time to maturity** | T | T1 | Contract |
| **Dividend yield** | q | T1 | Market data |

**Black-Scholes Call Formula [T1]**:
```
C = S * e^(-qT) * N(d1) - K * e^(-rT) * N(d2)

d1 = [ln(S/K) + (r - q + σ²/2)T] / (σ√T)
d2 = d1 - σ√T
```

**Put-Call Parity [T1]**:
```
C - P = S * e^(-qT) - K * e^(-rT)
```

**Verification**: Any BS implementation MUST satisfy put-call parity to within numerical precision (< 0.01).

### 2.2 No-Arbitrage Bounds [T1]

| Bound | Formula | Violation Action |
|-------|---------|------------------|
| **Call upper** | C ≤ S | HALT |
| **Call lower** | C ≥ max(S*e^(-qT) - K*e^(-rT), 0) | HALT |
| **Put upper** | P ≤ K*e^(-rT) | HALT |
| **Put lower** | P ≥ max(K*e^(-rT) - S*e^(-qT), 0) | HALT |

### 2.3 Greeks [T1]

| Greek | Definition | Use |
|-------|------------|-----|
| **Delta** | ∂V/∂S | Hedge ratio |
| **Gamma** | ∂²V/∂S² | Convexity |
| **Vega** | ∂V/∂σ | Vol sensitivity |
| **Theta** | ∂V/∂t | Time decay |
| **Rho** | ∂V/∂r | Rate sensitivity |

---

## 3. Option Replication for Annuity Products

### 3.1 FIA Cap Replication [T1]

A capped call (0% floor, X% cap) is replicated by:
```
Capped_Call = Long Call(K=100) - Long Call(K=100+cap)
            = Call Spread
```

**Reference**: Hull Ch.11, Boyle & Tian (2008)

### 3.2 RILA Buffer Replication [T1]

A buffer payoff is replicated by:
```
Buffer = Long Put(K=100) - Long Put(K=100-buffer)
       = Put Spread (bearish)
```

**Reference**: Boyle & Tian (2008) "Structured Notes"

### 3.3 RILA Floor Replication [T1]

A floor payoff is replicated by:
```
Floor = Long Put(K=100-floor)
```

**Reference**: Standard put definition

---

## 4. Valuation Methodology

### 4.1 MYGA Valuation [T1]

| Component | Formula | Tier |
|-----------|---------|------|
| **Present Value** | PV = Σ CF_t / (1 + r_t)^t | T1 |
| **Duration** | D = -∂PV/∂r / PV | T1 |
| **Convexity** | C = ∂²PV/∂r² / PV | T1 |

### 4.2 FIA/RILA Valuation [T1/T3]

| Component | Approach | Tier |
|-----------|----------|------|
| **Embedded option** | BS or MC pricing | T1 |
| **Option budget** | Premium per dollar of assets | T3 |
| **Fair cap/participation** | Solve for rate given budget | T1 |

**Option Budget Assumption [T3]**:
```python
OPTION_BUDGET = 0.03  # 3% of assets annually
# [T3] This is an assumption - actual budgets are proprietary
# Sensitivity analysis recommended: test 2%, 3%, 4%
```

---

## 5. Monte Carlo Specifications

### 5.1 GBM Path Generation [T1]

```python
# Geometric Brownian Motion
S[t+dt] = S[t] * exp((r - q - σ²/2)*dt + σ*√dt*Z)

# where Z ~ N(0,1)
```

**Reference**: Glasserman (2003) Ch.3

### 5.2 MC Parameters [T3]

| Parameter | Default | Tier | Rationale |
|-----------|---------|------|-----------|
| **Paths** | 100,000 | T3 | Convergence to ~0.1% |
| **Steps per year** | 252 | T1 | Trading days |
| **Variance reduction** | Antithetic variates | T1 | Standard technique |
| **Random seed** | Fixed for reproducibility | T3 | Best practice |

### 5.3 MC Convergence Criterion [T1]

MC price must converge to BS price for vanilla options:
```
|MC_price - BS_price| / BS_price < 0.01  (1% relative error)
```

---

## 6. Data Specifications

### 6.1 WINK Data Quality [T2]

| Field | Issue | Action | Tier |
|-------|-------|--------|------|
| `capRate` | max=9999.99 | Clip to ≤10.0 | T2 |
| `performanceTriggeredRate` | max=999 | Clip to ≤1.0 | T2 |
| `spreadRate` | max=99.0 | Clip to ≤1.0 | T2 |
| `guaranteeDuration` | Contains -1 | Filter ≥0 | T2 |
| `mva` | "None" strings | Coerce to null | T2 |

**Reference**: `wink-research-archive/gap-reports/gap-report-round2.md`

### 6.2 Rate Scale Convention [T2]

All rates in WINK are **decimals**:
- 0.05 = 5%
- 1.0 = 100% (for participation rates)
- 0.875 = 87.5% (for mgsvBaseRate)

### 6.3 Checksum Verification [T1]

```python
def load_wink_data(path: str) -> pd.DataFrame:
    """Load WINK data with SHA-256 verification."""
    verify_checksum(path, expected_sha256=WINK_CHECKSUM)
    return pd.read_parquet(path)
```

---

## 7. Market Data Sources

### 7.1 Required Data [T1]

| Data | Source | Priority |
|------|--------|----------|
| **Index levels** | Yahoo Finance / Stooq | Required |
| **Treasury curve** | FRED (DTB3, DGS1, DGS10) | Required |
| **VIX** | FRED (VIXCLS) | Required |

### 7.2 Forward Price Formula [T1]

```
F = S * exp((r - q) * T)

# where:
# F = forward price
# S = spot price
# r = risk-free rate
# q = dividend yield
# T = time in years
```

---

## 8. Suspicious Results Protocol

### 8.1 Automatic HALT Triggers [T1/T2]

| Condition | Tier | Action |
|-----------|------|--------|
| Option value > underlying | T1 | HALT, check arbitrage bounds |
| Put-call parity error > 0.01 | T1 | HALT, check BS implementation |
| FIA payoff < 0 | T1 | HALT, check floor enforcement |
| MC diverges from BS > 5% (vanilla) | T1 | HALT, check convergence |
| Implied vol < 0 or > 2.0 | T2 | HALT, check calibration |

### 8.2 Verification Sequence [T1]

1. **Anti-pattern tests**: Run `tests/anti_patterns/` (MUST pass)
2. **Known-answer tests**: Run `tests/validation/test_bs_known_answers.py`
3. **Convergence tests**: Run `tests/validation/test_mc_convergence.py`
4. **Data sanity**: Run `tests/validation/test_wink_sanity.py`

---

## 9. Key Academic References

### 9.1 Option Pricing [T1]

| Reference | Topic |
|-----------|-------|
| Black & Scholes (1973) | Original BS model |
| Hull (2021) Ch.15 | BS implementation, Greeks |
| Glasserman (2003) | Monte Carlo methods |

### 9.2 Annuity Pricing [T1]

| Reference | Topic |
|-----------|-------|
| Hardy (2003) | Investment Guarantees |
| Boyle & Tian (2008) | Buffer/floor payoffs |

### 9.3 Regulatory [T1]

| Reference | Topic |
|-----------|-------|
| FINRA Notice 22-08 | Complex products guidance |
| NAIC Standard Nonforfeiture Law | MGSV requirements |
| VM-21 | VA guarantee valuation |

---

## 10. Amendment Process

### 10.1 How to Propose Changes

1. Document current specification with tier
2. Document proposed change with rationale
3. If changing T1 claim → requires academic reference
4. Run FULL test suite
5. Document decision in CHANGELOG.md

### 10.2 What Cannot Be Changed Without Full Re-evaluation

- No-arbitrage bounds (Section 2.2) - T1
- Put-call parity requirement (Section 2.1) - T1
- Buffer vs Floor definitions (Section 1.3) - T1
- Black-Scholes formula (Section 2.1) - T1

---

## 11. Tier Summary

| Section | T1 Claims | T2 Claims | T3 Claims |
|---------|-----------|-----------|-----------|
| 1. Products | 12 | 4 | 0 |
| 2. Options | 8 | 0 | 0 |
| 3. Replication | 3 | 0 | 0 |
| 4. Valuation | 4 | 0 | 2 (budget) |
| 5. Monte Carlo | 3 | 0 | 3 (params) |
| 6. Data | 1 | 5 | 0 |
| 7. Market Data | 2 | 0 | 0 |
| 8. Suspicious | 5 | 1 | 0 |

**Total**: 38 T1, 10 T2, 5 T3

---

## Document History

| Date | Version | Changes |
|------|---------|---------|
| 2025-12-04 | 1.0 | Initial specification |

---

**This document is FROZEN. Any proposed changes must follow the Amendment Process (Section 10).**
