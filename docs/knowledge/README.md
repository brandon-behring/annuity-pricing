# Knowledge Base Structure

This directory contains tiered documentation for the annuity-pricing library.

---

## Tier System

| Tier | Directory | Purpose | When to Use |
|------|-----------|---------|-------------|
| **L1** | `domain/` | Quick reference | Need formula or definition fast |
| **L2** | `derivations/` | Full derivations | Need to understand "why" |
| **L3** | `references/` | Paper summaries | Need academic grounding |

---

## Directory Contents

### L1: Domain (`domain/`)

Quick-reference documents for key concepts:

| Document | Topic |
|----------|-------|
| `dynamic_lapse.md` | Moneyness-based lapse modeling |
| `glwb_mechanics.md` | GLWB product mechanics |
| `vm21_vm22.md` | Regulatory framework (PBR) |
| `rila_mechanics.md` | RILA buffer/cap/floor |

### L2: Derivations (`derivations/`)

Full mathematical derivations:

| Document | Topic |
|----------|-------|
| `bs_greeks.md` | Black-Scholes Greeks derivation |
| `glwb_pde.md` | GLWB PDE approach (TODO) |

### L3: References (`references/`)

Paper summaries with key equations:

| Document | Paper |
|----------|-------|
| `_TEMPLATE.md` | Template for new summaries |
| `bauer_kling_russ_2008.md` | Universal GMxB framework |

---

## Usage Guidelines

### For Developers

1. **Start with L1** for quick answers
2. **Go to L2** if you need the derivation
3. **Check L3** for academic justification

### For Claude/AI

The CLAUDE.md reference index maps topics to knowledge tiers:

```markdown
## Reference Index
| Topic | L1 | L2 | L3 |
|-------|----|----|-----|
| GLWB | glwb_mechanics.md | glwb_pde.md | milevsky_2006.md |
```

### Adding New Documents

1. Determine appropriate tier
2. Use existing documents as templates
3. Include validation test cases where applicable
4. Update this README

---

## Document Standards

### L1 Documents (Quick Reference)

- **Header**: Tier, domain, related code
- **Content**: Definitions, formulas, examples
- **Length**: 1-2 pages max
- **Focus**: "What" and "How"

### L2 Documents (Derivations)

- **Header**: Tier, prerequisites
- **Content**: Full derivation with steps
- **Length**: As needed
- **Focus**: "Why" and mathematical rigor

### L3 Documents (Paper Summaries)

- **Use template**: `_TEMPLATE.md`
- **Content**: Key contribution, methodology, equations
- **Include**: Validation test cases from paper
- **Focus**: Extracting implementable knowledge

---

## Cross-References

| Knowledge Doc | Validation Notebook | Code Module |
|---------------|---------------------|-------------|
| `bs_greeks.md` | `options/black_scholes_vs_financepy.ipynb` | `options/pricing/` |
| `rila_mechanics.md` | - | `products/rila.py` |
| `dynamic_lapse.md` | - | `behavior/lapse.py` |
