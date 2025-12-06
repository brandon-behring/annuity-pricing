# Regulatory Summary: FINRA Notice 22-08

**Tier**: L3 (Regulatory Reference)
**Citation**: FINRA Regulatory Notice 22-08 (March 8, 2022)
**Document**: Complex Products and Options
**Status**: [x] Acquired | [x] Summarized

---

## Key Purpose

Reminds broker-dealer members of sales practice obligations for complex products and options, and solicits comment on:
1. Effective practices for complex products/options
2. Whether current regulatory framework is adequate given self-directed platform growth

---

## Complex Product Definition

**No standard definition exists.** FINRA uses flexible criteria:

### Characteristics That Render a Product "Complex"

| Characteristic | Description |
|----------------|-------------|
| **Difficult to understand** | Features that make essential characteristics/risks hard to grasp |
| **Complex payout structure** | Non-linear, path-dependent, or conditional payouts |
| **Multi-feature combination** | Combines multiple product types or strategies |
| **Unexpected performance** | Performs differently than intuition suggests in various markets |

### Examples of Complex Products

| Category | Products |
|----------|----------|
| **Structured products** | Steepener notes, worst-of notes, reverse convertibles |
| **Geared ETPs** | Leveraged ETFs, inverse ETFs |
| **Volatility-linked** | VIX ETPs, volatility ETNs |
| **Defined outcome ETFs** | Buffer ETFs with caps/floors |
| **Crypto-related** | Bitcoin futures ETFs/mutual funds |
| **Limited liquidity** | Interval funds, tender-offer funds |
| **Insurance-linked** | RILAs, FIAs, structured annuities |

---

## RILA Specific Mention

> "Structured annuities, often referred to as **registered index-linked annuities (RILAs)**, which also offer certain structured note-type exposures in an insurance vehicle, have seen **rapid growth**." (p. 12)

**Regulatory concern**: RILAs combine:
- Structured product characteristics (buffers, caps, floors)
- Insurance wrapper
- Complex crediting mechanisms

---

## Regulatory Framework

### Key FINRA Rules Referenced

| Rule | Subject |
|------|---------|
| 2111 | Suitability (for non-retail recommendations) |
| 2210 | Communications with the Public |
| 2220 | Options Communications |
| 2310 | Direct Participation Programs |
| 2320 | Variable Contracts |
| 2330 | Deferred Variable Annuities |
| 2360 | Options |

### Regulation Best Interest (Reg BI)

For **retail customer recommendations**, Reg BI requires:

1. **Care Obligation**: Reasonable diligence to understand:
   - Nature of recommended security
   - Potential risks, rewards, costs
   - Reasonable basis that recommendation is in customer's best interest

2. **Reasonable Basis Requirement**:
   - Must fully understand the product
   - Violation possible even if product *could* be suitable for some customers

---

## Current Concerns Highlighted

### Account Opening Gaps
- Red flags in customer experience representations not identified
- Minimum experience requirements bypassed

### Disclosure Deficiencies
- Most firms rely only on ODD (Options Disclosure Document)
- Wide variation in additional educational materials

### Options Exercise Procedures
- Varying cut-off times (not always 5:30 PM ET rule maximum)
- Poor communication of firm-specific deadlines

---

## Questions for Comment (Key Items)

### Complex Products

1. How should products be categorized as "complex"?
2. Should **account approval processes** (like options) apply to complex products?
3. Should **knowledge assessments** be required before trading?
4. Should **principal approval** be required for retail accounts?
5. Should **periodic reassessment** of account approval be required?

### Options

1. Should **standardized option levels** be mandated?
2. Should **suitability determination** apply at each level?
3. Should **conversations with customers** be required before approval?
4. Should **total position risk display** be required?
5. Should firms allow investors until **5:30 PM ET** for exercise decisions?

---

## International Comparison

| Jurisdiction | Approach |
|--------------|----------|
| **EU (MiFID II)** | Appropriateness assessment required; warning if insufficient knowledge |
| **Canada** | Enhanced KYP suitability; product may be deemed inappropriate for retail |
| **Hong Kong** | Explicit complex product definition; mandated warnings |
| **UK/EU/Australia** | Product intervention powers (can prohibit sales) |

### Product Intervention Powers (Not in US)

Foreign regulators can:
- Prohibit marketing/distribution of specific products
- Impose leverage limits, margin close-outs
- Require standardized risk warnings
- Ban monetary incentives to clients

---

## Implications for Annuity-Pricing Library

### Products Likely Affected

| Product | Complexity Factors |
|---------|-------------------|
| **RILA** | Buffer/cap mechanics, multi-period crediting |
| **FIA** | Index crediting methods (PTP, ratchet, HWM) |
| **VA w/GLWB** | Interaction of withdrawal benefits with separate account |
| **Structured notes** | Embedded optionality, issuer credit risk |

### Documentation Needs

1. **Product summaries** with key risk factors
2. **Performance scenarios** showing behavior in different markets
3. **Fee disclosure** linking costs to features
4. **Suitability guidance** mapping to investor profiles

### Validation Considerations

- Test that product explanations are accurate
- Verify scenario calculations match prospectus
- Document how products perform in stress scenarios

---

## Key Takeaways for Implementation

### 1. Complexity Assessment Framework

```python
@dataclass
class ComplexityAssessment:
    """Assess product complexity per FINRA 22-08 criteria."""

    product_name: str

    # Complexity factors (1-5 scale)
    payout_complexity: int      # Non-linear, path-dependent
    multi_feature: bool         # Combines multiple strategies
    market_sensitivity: int     # Unexpected behavior in stress
    liquidity_constraints: bool # Limited redemption
    embedded_derivatives: bool  # Options, futures, etc.

    def complexity_score(self) -> int:
        """Calculate overall complexity score."""
        score = self.payout_complexity + self.market_sensitivity
        if self.multi_feature:
            score += 2
        if self.liquidity_constraints:
            score += 2
        if self.embedded_derivatives:
            score += 2
        return score

    def is_complex(self) -> bool:
        """Determine if product should be treated as complex."""
        return self.complexity_score() >= 5
```

### 2. Product Types and Complexity

| Product | Complexity Score | Primary Factors |
|---------|------------------|-----------------|
| MYGA | 2 | Simple fixed rate |
| FIA (basic) | 5 | Index crediting + participation limits |
| FIA (HWM) | 7 | Path-dependent + index crediting |
| RILA | 8 | Buffer mechanics + limited liquidity |
| VA w/GLWB | 9 | Multi-feature + derivatives + mortality |

### 3. Disclosure Elements to Include

For each product:
- Key features (1 page max)
- Risk factors (prioritized)
- Performance under scenarios:
  - Market up 10%
  - Market down 10%
  - Market flat
  - High volatility period
- Fee impact on returns
- Comparison to simpler alternative

---

## Regulatory Status

**Comment period ended**: May 9, 2022

**Current status**: Under SEC/FINRA review. Final rules pending.

**Expected direction**: More stringent requirements for self-directed access to complex products, potentially including:
- Mandatory account approval for complex products
- Knowledge assessments
- Enhanced disclosures

---

## Change Log

| Date | Change |
|------|--------|
| 2025-12-05 | Initial summary from PDF |
