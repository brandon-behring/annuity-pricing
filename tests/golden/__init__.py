"""
Golden file regression testing.

Golden files contain expected outputs from authoritative sources:
- Hull textbook examples (known analytical solutions)
- SEC RILA rule examples (regulatory compliance)
- Portfolio baselines (historical snapshots)

These tests catch regressions where implementation changes
inadvertently alter outputs from known-correct values.

Usage:
    pytest tests/golden/ -v

Regeneration:
    python scripts/regenerate_goldens.py --verify  # Check drift
    python scripts/regenerate_goldens.py           # Regenerate
"""
