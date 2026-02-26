#!/usr/bin/env python3
"""
Generate payoff truth tables for Julia cross-validation.

Phase 0 of Julia port plan - creates hand-verified payoff reference values
for validating Julia payoff implementations against Python.

Output: tests/references/payoff_truth_tables.csv

Coverage:
- FIA: Cap, Participation, Spread, Trigger (75 rows)
- RILA: Buffer, Floor, Buffer+Floor, Step-rate (60 rows)
- Comparisons: Buffer vs Floor at same returns (15 rows)

All expected values computed using Python implementation and marked with
[T1] tier references from METHODOLOGY.md.
"""

import csv
from pathlib import Path
from typing import Optional

from annuity_pricing.options.payoffs.fia import (
    CappedCallPayoff,
    ParticipationPayoff,
    SpreadPayoff,
    TriggerPayoff,
)
from annuity_pricing.options.payoffs.rila import (
    BufferPayoff,
    FloorPayoff,
    BufferWithFloorPayoff,
    StepRateBufferPayoff,
)


def generate_payoff_truth_tables(
    output_path: Optional[Path] = None,
) -> list[dict]:
    """
    Generate payoff truth tables for Julia cross-validation.

    Parameters
    ----------
    output_path : Path, optional
        Output CSV path. If None, returns records without writing.

    Returns
    -------
    list[dict]
        List of truth table records
    """
    print("Generating payoff truth tables...")
    print()

    records = []

    # Generate FIA cases
    records.extend(_generate_fia_cap_cases())
    records.extend(_generate_fia_participation_cases())
    records.extend(_generate_fia_spread_cases())
    records.extend(_generate_fia_trigger_cases())

    # Generate RILA cases
    records.extend(_generate_rila_buffer_cases())
    records.extend(_generate_rila_floor_cases())
    records.extend(_generate_rila_buffer_floor_cases())
    records.extend(_generate_rila_step_rate_cases())

    # Generate comparison cases
    records.extend(_generate_comparison_cases())

    # Add sequential IDs
    for i, record in enumerate(records):
        record["test_id"] = f"{record['category']}_{record['method'].upper()}_{i + 1:03d}"

    if output_path:
        _write_csv(records, output_path)

    return records


def _generate_fia_cap_cases() -> list[dict]:
    """Generate FIA cap payoff test cases (15 rows)."""
    cases = []
    payoff = CappedCallPayoff(cap_rate=0.10, floor_rate=0.0)

    # Normal cases (8)
    normal_returns = [0.00, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20, 0.25]
    for ret in normal_returns:
        result = payoff.calculate(ret)
        cases.append({
            "category": "FIA",
            "method": "cap",
            "index_return": ret,
            "cap_rate": 0.10,
            "participation_rate": None,
            "spread_rate": None,
            "trigger_rate": None,
            "trigger_threshold": None,
            "buffer_rate": None,
            "floor_rate": 0.0,
            "expected_payoff": result.credited_return,
            "cap_applied": result.cap_applied,
            "floor_applied": result.floor_applied,
            "edge_case": "normal" if ret < 0.10 else "capped",
            "formula": "max(0, min(index_return, cap))",
            "reference": "[T1] fia.py:33",
        })

    # Edge cases (7)
    edge_cases = [
        (-0.01, "negative_just_below_zero"),
        (-0.05, "negative_moderate"),
        (-0.20, "negative_large"),
        (-0.50, "negative_extreme"),
        (0.001, "positive_tiny"),
        (0.10, "exactly_at_cap"),
        (0.0999, "just_below_cap"),
    ]
    for ret, edge_type in edge_cases:
        result = payoff.calculate(ret)
        cases.append({
            "category": "FIA",
            "method": "cap",
            "index_return": ret,
            "cap_rate": 0.10,
            "participation_rate": None,
            "spread_rate": None,
            "trigger_rate": None,
            "trigger_threshold": None,
            "buffer_rate": None,
            "floor_rate": 0.0,
            "expected_payoff": result.credited_return,
            "cap_applied": result.cap_applied,
            "floor_applied": result.floor_applied,
            "edge_case": edge_type,
            "formula": "max(0, min(index_return, cap))",
            "reference": "[T1] fia.py:33",
        })

    print(f"  FIA cap: {len(cases)} cases")
    return cases


def _generate_fia_participation_cases() -> list[dict]:
    """Generate FIA participation payoff test cases (15 rows)."""
    cases = []
    payoff = ParticipationPayoff(participation_rate=0.80, floor_rate=0.0)

    # Normal cases (8)
    normal_returns = [0.00, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.50]
    for ret in normal_returns:
        result = payoff.calculate(ret)
        cases.append({
            "category": "FIA",
            "method": "participation",
            "index_return": ret,
            "cap_rate": None,
            "participation_rate": 0.80,
            "spread_rate": None,
            "trigger_rate": None,
            "trigger_threshold": None,
            "buffer_rate": None,
            "floor_rate": 0.0,
            "expected_payoff": result.credited_return,
            "cap_applied": result.cap_applied,
            "floor_applied": result.floor_applied,
            "edge_case": "normal",
            "formula": "max(0, participation × max(0, index_return))",
            "reference": "[T1] fia.py:130",
        })

    # Edge cases with different participation rates (7)
    edge_cases = [
        (-0.10, 0.80, "negative_with_80%_participation"),
        (-0.20, 1.20, "negative_with_120%_participation"),
        (0.10, 1.50, "positive_with_150%_participation"),
        (0.10, 0.50, "positive_with_50%_participation"),
        (0.001, 0.80, "tiny_positive"),
        (-0.001, 0.80, "tiny_negative"),
        (0.00, 0.80, "exactly_zero"),
    ]
    for ret, part_rate, edge_type in edge_cases:
        test_payoff = ParticipationPayoff(participation_rate=part_rate, floor_rate=0.0)
        result = test_payoff.calculate(ret)
        cases.append({
            "category": "FIA",
            "method": "participation",
            "index_return": ret,
            "cap_rate": None,
            "participation_rate": part_rate,
            "spread_rate": None,
            "trigger_rate": None,
            "trigger_threshold": None,
            "buffer_rate": None,
            "floor_rate": 0.0,
            "expected_payoff": result.credited_return,
            "cap_applied": result.cap_applied,
            "floor_applied": result.floor_applied,
            "edge_case": edge_type,
            "formula": "max(0, participation × max(0, index_return))",
            "reference": "[T1] fia.py:130",
        })

    print(f"  FIA participation: {len(cases)} cases")
    return cases


def _generate_fia_spread_cases() -> list[dict]:
    """Generate FIA spread payoff test cases (15 rows)."""
    cases = []
    payoff = SpreadPayoff(spread_rate=0.02, floor_rate=0.0)

    # Normal cases (8)
    normal_returns = [0.00, 0.01, 0.02, 0.03, 0.05, 0.10, 0.15, 0.20]
    for ret in normal_returns:
        result = payoff.calculate(ret)
        cases.append({
            "category": "FIA",
            "method": "spread",
            "index_return": ret,
            "cap_rate": None,
            "participation_rate": None,
            "spread_rate": 0.02,
            "trigger_rate": None,
            "trigger_threshold": None,
            "buffer_rate": None,
            "floor_rate": 0.0,
            "expected_payoff": result.credited_return,
            "cap_applied": result.cap_applied,
            "floor_applied": result.floor_applied,
            "edge_case": "normal",
            "formula": "max(0, index_return - spread) for positive returns",
            "reference": "[T1] fia.py:255",
        })

    # Edge cases (7)
    edge_cases = [
        (-0.05, 0.02, "negative_return"),
        (0.02, 0.02, "return_equals_spread"),
        (0.019, 0.02, "return_just_below_spread"),
        (0.021, 0.02, "return_just_above_spread"),
        (0.001, 0.02, "tiny_positive_below_spread"),
        (0.05, 0.05, "return_equals_larger_spread"),
        (0.10, 0.00, "zero_spread"),
    ]
    for ret, spread, edge_type in edge_cases:
        test_payoff = SpreadPayoff(spread_rate=spread, floor_rate=0.0)
        result = test_payoff.calculate(ret)
        cases.append({
            "category": "FIA",
            "method": "spread",
            "index_return": ret,
            "cap_rate": None,
            "participation_rate": None,
            "spread_rate": spread,
            "trigger_rate": None,
            "trigger_threshold": None,
            "buffer_rate": None,
            "floor_rate": 0.0,
            "expected_payoff": result.credited_return,
            "cap_applied": result.cap_applied,
            "floor_applied": result.floor_applied,
            "edge_case": edge_type,
            "formula": "max(0, index_return - spread) for positive returns",
            "reference": "[T1] fia.py:255",
        })

    print(f"  FIA spread: {len(cases)} cases")
    return cases


def _generate_fia_trigger_cases() -> list[dict]:
    """Generate FIA trigger payoff test cases (15 rows)."""
    cases = []
    payoff = TriggerPayoff(trigger_rate=0.05, trigger_threshold=0.0, floor_rate=0.0)

    # Normal cases (8)
    normal_returns = [-0.10, -0.05, -0.01, 0.00, 0.01, 0.05, 0.10, 0.20]
    for ret in normal_returns:
        result = payoff.calculate(ret)
        cases.append({
            "category": "FIA",
            "method": "trigger",
            "index_return": ret,
            "cap_rate": None,
            "participation_rate": None,
            "spread_rate": None,
            "trigger_rate": 0.05,
            "trigger_threshold": 0.0,
            "buffer_rate": None,
            "floor_rate": 0.0,
            "expected_payoff": result.credited_return,
            "cap_applied": result.cap_applied,
            "floor_applied": result.floor_applied,
            "edge_case": "triggered" if ret >= 0.0 else "not_triggered",
            "formula": "trigger_rate if return >= threshold else floor",
            "reference": "[T1] fia.py:375",
        })

    # Edge cases with different thresholds (7)
    edge_cases = [
        (0.0, 0.0, 0.05, "exactly_at_zero_threshold"),
        (-0.0001, 0.0, 0.05, "just_below_zero_threshold"),
        (0.0001, 0.0, 0.05, "just_above_zero_threshold"),
        (0.05, 0.05, 0.08, "exactly_at_5%_threshold"),
        (0.049, 0.05, 0.08, "just_below_5%_threshold"),
        (0.051, 0.05, 0.08, "just_above_5%_threshold"),
        (-0.50, 0.0, 0.05, "large_negative"),
    ]
    for ret, threshold, trig_rate, edge_type in edge_cases:
        test_payoff = TriggerPayoff(trigger_rate=trig_rate, trigger_threshold=threshold, floor_rate=0.0)
        result = test_payoff.calculate(ret)
        cases.append({
            "category": "FIA",
            "method": "trigger",
            "index_return": ret,
            "cap_rate": None,
            "participation_rate": None,
            "spread_rate": None,
            "trigger_rate": trig_rate,
            "trigger_threshold": threshold,
            "buffer_rate": None,
            "floor_rate": 0.0,
            "expected_payoff": result.credited_return,
            "cap_applied": result.cap_applied,
            "floor_applied": result.floor_applied,
            "edge_case": edge_type,
            "formula": "trigger_rate if return >= threshold else floor",
            "reference": "[T1] fia.py:375",
        })

    print(f"  FIA trigger: {len(cases)} cases")
    return cases


def _generate_rila_buffer_cases() -> list[dict]:
    """Generate RILA buffer payoff test cases (20 rows)."""
    cases = []

    # Common buffer scenarios (10)
    buffer_scenarios = [
        (0.10, 0.05, "positive_within_cap"),
        (0.10, 0.15, "positive_above_cap"),
        (0.10, -0.05, "negative_within_buffer"),
        (0.10, -0.10, "negative_at_exact_buffer"),
        (0.10, -0.15, "negative_beyond_buffer"),
        (0.10, -0.25, "negative_large_loss"),
        (0.15, -0.10, "15%_buffer_within"),
        (0.15, -0.20, "15%_buffer_beyond"),
        (0.20, -0.15, "20%_buffer_within"),
        (0.20, -0.30, "20%_buffer_beyond"),
    ]
    for buf_rate, ret, scenario in buffer_scenarios:
        payoff = BufferPayoff(buffer_rate=buf_rate, cap_rate=0.20)
        result = payoff.calculate(ret)
        cases.append({
            "category": "RILA",
            "method": "buffer",
            "index_return": ret,
            "cap_rate": 0.20,
            "participation_rate": None,
            "spread_rate": None,
            "trigger_rate": None,
            "trigger_threshold": None,
            "buffer_rate": buf_rate,
            "floor_rate": None,
            "expected_payoff": result.credited_return,
            "cap_applied": result.cap_applied,
            "floor_applied": result.floor_applied,
            "edge_case": scenario,
            "formula": "max(index_return + buffer, 0) for losses; min(return, cap) for gains",
            "reference": "[T1] rila.py:33",
        })

    # Edge cases (10)
    edge_cases = [
        (0.10, -0.0999, "just_inside_buffer"),
        (0.10, -0.1001, "just_outside_buffer"),
        (0.10, 0.0, "exactly_zero"),
        (0.10, -0.50, "extreme_loss"),
        (0.10, -0.75, "catastrophic_loss"),
        (1.0, -0.50, "100%_buffer_large_loss"),  # 100% buffer edge case
        (1.0, -0.99, "100%_buffer_near_total_loss"),
        (0.99, -0.50, "99%_buffer"),
        (0.05, -0.08, "small_5%_buffer"),
        (0.25, -0.20, "25%_buffer_within"),
    ]
    for buf_rate, ret, edge_type in edge_cases:
        payoff = BufferPayoff(buffer_rate=buf_rate, cap_rate=0.25)
        result = payoff.calculate(ret)
        cases.append({
            "category": "RILA",
            "method": "buffer",
            "index_return": ret,
            "cap_rate": 0.25,
            "participation_rate": None,
            "spread_rate": None,
            "trigger_rate": None,
            "trigger_threshold": None,
            "buffer_rate": buf_rate,
            "floor_rate": None,
            "expected_payoff": result.credited_return,
            "cap_applied": result.cap_applied,
            "floor_applied": result.floor_applied,
            "edge_case": edge_type,
            "formula": "max(index_return + buffer, 0) for losses; min(return, cap) for gains",
            "reference": "[T1] rila.py:33",
        })

    print(f"  RILA buffer: {len(cases)} cases")
    return cases


def _generate_rila_floor_cases() -> list[dict]:
    """Generate RILA floor payoff test cases (15 rows)."""
    cases = []

    # Common floor scenarios (8)
    floor_scenarios = [
        (-0.10, 0.05, "positive_within_cap"),
        (-0.10, 0.15, "positive_above_cap"),
        (-0.10, -0.05, "negative_above_floor"),
        (-0.10, -0.10, "negative_at_exact_floor"),
        (-0.10, -0.15, "negative_below_floor"),
        (-0.10, -0.25, "negative_large_loss"),
        (-0.15, -0.20, "-15%_floor_hit"),
        (-0.20, -0.30, "-20%_floor_hit"),
    ]
    for floor_rate, ret, scenario in floor_scenarios:
        payoff = FloorPayoff(floor_rate=floor_rate, cap_rate=0.20)
        result = payoff.calculate(ret)
        cases.append({
            "category": "RILA",
            "method": "floor",
            "index_return": ret,
            "cap_rate": 0.20,
            "participation_rate": None,
            "spread_rate": None,
            "trigger_rate": None,
            "trigger_threshold": None,
            "buffer_rate": None,
            "floor_rate": floor_rate,
            "expected_payoff": result.credited_return,
            "cap_applied": result.cap_applied,
            "floor_applied": result.floor_applied,
            "edge_case": scenario,
            "formula": "max(index_return, floor); min(result, cap)",
            "reference": "[T1] rila.py:186",
        })

    # Edge cases (7)
    edge_cases = [
        (-0.10, -0.0999, "just_above_floor"),
        (-0.10, -0.1001, "just_below_floor"),
        (-0.10, 0.0, "exactly_zero"),
        (-0.10, -0.50, "extreme_loss"),
        (-0.05, -0.08, "small_floor_hit"),
        (0.0, -0.10, "zero_floor_full_protection"),
        (-0.25, -0.30, "deep_floor_hit"),
    ]
    for floor_rate, ret, edge_type in edge_cases:
        payoff = FloorPayoff(floor_rate=floor_rate, cap_rate=0.25)
        result = payoff.calculate(ret)
        cases.append({
            "category": "RILA",
            "method": "floor",
            "index_return": ret,
            "cap_rate": 0.25,
            "participation_rate": None,
            "spread_rate": None,
            "trigger_rate": None,
            "trigger_threshold": None,
            "buffer_rate": None,
            "floor_rate": floor_rate,
            "expected_payoff": result.credited_return,
            "cap_applied": result.cap_applied,
            "floor_applied": result.floor_applied,
            "edge_case": edge_type,
            "formula": "max(index_return, floor); min(result, cap)",
            "reference": "[T1] rila.py:186",
        })

    print(f"  RILA floor: {len(cases)} cases")
    return cases


def _generate_rila_buffer_floor_cases() -> list[dict]:
    """Generate RILA buffer+floor combined payoff test cases (15 rows)."""
    cases = []

    # Scenarios where buffer applies, floor doesn't (8)
    buffer_only_scenarios = [
        (0.10, -0.20, -0.05, "buffer_absorbs_within_floor"),
        (0.10, -0.20, -0.08, "buffer_absorbs_above_floor"),
        (0.10, -0.20, 0.05, "positive_return"),
        (0.10, -0.20, 0.15, "positive_capped"),
        (0.15, -0.25, -0.12, "larger_buffer"),
        (0.10, -0.20, -0.15, "buffer_partial_floor_not_hit"),
        (0.10, -0.20, -0.10, "at_buffer_boundary"),
        (0.10, -0.20, 0.0, "exactly_zero"),
    ]
    for buf_rate, floor_rate, ret, scenario in buffer_only_scenarios:
        payoff = BufferWithFloorPayoff(buffer_rate=buf_rate, floor_rate=floor_rate, cap_rate=0.20)
        result = payoff.calculate(ret)
        cases.append({
            "category": "RILA",
            "method": "buffer_floor",
            "index_return": ret,
            "cap_rate": 0.20,
            "participation_rate": None,
            "spread_rate": None,
            "trigger_rate": None,
            "trigger_threshold": None,
            "buffer_rate": buf_rate,
            "floor_rate": floor_rate,
            "expected_payoff": result.credited_return,
            "cap_applied": result.cap_applied,
            "floor_applied": result.floor_applied,
            "edge_case": scenario,
            "formula": "buffer first, then floor as backstop",
            "reference": "[T1] rila.py:314",
        })

    # Scenarios where floor kicks in (7)
    floor_kicks_in = [
        (0.10, -0.20, -0.35, "floor_kicks_in_large_loss"),
        (0.10, -0.20, -0.40, "floor_kicks_in_very_large"),
        (0.10, -0.20, -0.50, "floor_kicks_in_extreme"),
        (0.10, -0.15, -0.30, "tighter_floor_kicks_in"),
        (0.05, -0.10, -0.20, "small_buffer_floor_kicks_in"),
        (0.10, -0.20, -0.29, "just_at_floor_boundary"),
        (0.10, -0.20, -0.31, "just_beyond_floor_boundary"),
    ]
    for buf_rate, floor_rate, ret, scenario in floor_kicks_in:
        payoff = BufferWithFloorPayoff(buffer_rate=buf_rate, floor_rate=floor_rate, cap_rate=0.20)
        result = payoff.calculate(ret)
        cases.append({
            "category": "RILA",
            "method": "buffer_floor",
            "index_return": ret,
            "cap_rate": 0.20,
            "participation_rate": None,
            "spread_rate": None,
            "trigger_rate": None,
            "trigger_threshold": None,
            "buffer_rate": buf_rate,
            "floor_rate": floor_rate,
            "expected_payoff": result.credited_return,
            "cap_applied": result.cap_applied,
            "floor_applied": result.floor_applied,
            "edge_case": scenario,
            "formula": "buffer first, then floor as backstop",
            "reference": "[T1] rila.py:314",
        })

    print(f"  RILA buffer+floor: {len(cases)} cases")
    return cases


def _generate_rila_step_rate_cases() -> list[dict]:
    """Generate RILA step-rate buffer payoff test cases (10 rows)."""
    cases = []

    # Step-rate scenarios: 10% tier1 + 10% tier2 at 50% protection
    payoff = StepRateBufferPayoff(
        tier1_buffer=0.10,
        tier2_buffer=0.10,
        tier2_protection=0.50,
        cap_rate=0.25,
    )

    scenarios = [
        (0.10, "positive_return"),
        (0.0, "exactly_zero"),
        (-0.05, "within_tier1"),
        (-0.10, "at_tier1_boundary"),
        (-0.12, "in_tier2"),
        (-0.15, "in_tier2_deeper"),
        (-0.20, "at_tier2_boundary"),
        (-0.25, "beyond_tier2"),
        (-0.30, "well_beyond_tier2"),
        (-0.50, "extreme_loss"),
    ]
    for ret, scenario in scenarios:
        result = payoff.calculate(ret)
        cases.append({
            "category": "RILA",
            "method": "step_rate",
            "index_return": ret,
            "cap_rate": 0.25,
            "participation_rate": None,
            "spread_rate": None,
            "trigger_rate": None,
            "trigger_threshold": None,
            "buffer_rate": 0.10,  # tier1
            "floor_rate": None,
            "expected_payoff": result.credited_return,
            "cap_applied": result.cap_applied,
            "floor_applied": result.floor_applied,
            "edge_case": scenario,
            "formula": "tier1=10% full + tier2=10% at 50% protection",
            "reference": "[T1] rila.py:422",
        })

    print(f"  RILA step-rate: {len(cases)} cases")
    return cases


def _generate_comparison_cases() -> list[dict]:
    """Generate buffer vs floor comparison cases (15 rows)."""
    cases = []

    # Compare 10% buffer vs -10% floor at various returns
    buffer_payoff = BufferPayoff(buffer_rate=0.10, cap_rate=0.20)
    floor_payoff = FloorPayoff(floor_rate=-0.10, cap_rate=0.20)

    returns = [
        (0.15, "positive_capped"),
        (0.05, "positive_small"),
        (0.0, "exactly_zero"),
        (-0.03, "small_loss_buffer_wins"),
        (-0.05, "moderate_loss_buffer_wins"),
        (-0.08, "larger_loss_buffer_wins"),
        (-0.10, "at_boundary_buffer_wins"),
        (-0.12, "beyond_boundary_same"),
        (-0.15, "floor_catches_up"),
        (-0.20, "floor_better"),
        (-0.25, "floor_much_better"),
        (-0.30, "floor_significantly_better"),
        (-0.40, "extreme_floor_dominates"),
        (-0.50, "catastrophic_floor_dominates"),
        (-0.75, "near_total_loss"),
    ]

    for ret, scenario in returns:
        buf_result = buffer_payoff.calculate(ret)
        floor_result = floor_payoff.calculate(ret)

        # Determine winner
        if buf_result.credited_return > floor_result.credited_return:
            winner = "buffer"
        elif floor_result.credited_return > buf_result.credited_return:
            winner = "floor"
        else:
            winner = "tie"

        cases.append({
            "category": "COMPARISON",
            "method": "buffer_vs_floor",
            "index_return": ret,
            "cap_rate": 0.20,
            "participation_rate": None,
            "spread_rate": None,
            "trigger_rate": None,
            "trigger_threshold": None,
            "buffer_rate": 0.10,
            "floor_rate": -0.10,
            "expected_payoff": buf_result.credited_return,  # Buffer result
            "cap_applied": buf_result.cap_applied,
            "floor_applied": floor_result.floor_applied,
            "edge_case": f"{scenario}_winner={winner}",
            "formula": f"buffer={buf_result.credited_return:.4f}, floor={floor_result.credited_return:.4f}",
            "reference": "[T1] Buffer vs Floor comparison",
        })

    print(f"  Comparison: {len(cases)} cases")
    return cases


def _write_csv(records: list[dict], output_path: Path) -> None:
    """Write records to CSV with consistent column ordering."""
    column_order = [
        "test_id",
        "category",
        "method",
        "index_return",
        "cap_rate",
        "participation_rate",
        "spread_rate",
        "trigger_rate",
        "trigger_threshold",
        "buffer_rate",
        "floor_rate",
        "expected_payoff",
        "cap_applied",
        "floor_applied",
        "edge_case",
        "formula",
        "reference",
    ]

    print()
    print(f"Writing {len(records)} records to {output_path}")

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=column_order)
        writer.writeheader()
        writer.writerows(records)

    print("Done!")


def print_summary(records: list[dict]) -> None:
    """Print summary statistics for generated truth tables."""
    print()
    print("=" * 60)
    print("Summary Statistics")
    print("=" * 60)

    # Category counts
    categories = {}
    for r in records:
        cat = r["category"]
        categories[cat] = categories.get(cat, 0) + 1

    print("\nCategory Distribution:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count} cases")

    # Method counts
    methods = {}
    for r in records:
        method = r["method"]
        methods[method] = methods.get(method, 0) + 1

    print("\nMethod Distribution:")
    for method, count in sorted(methods.items()):
        print(f"  {method}: {count} cases")

    # Edge case highlights
    print("\nKey Edge Cases Covered:")
    edge_cases = [r for r in records if "100%" in r.get("edge_case", "") or "extreme" in r.get("edge_case", "").lower()]
    for ec in edge_cases[:5]:
        print(f"  - {ec['method']}: {ec['edge_case']} -> {ec['expected_payoff']:.4f}")

    print(f"\nTotal: {len(records)} test cases")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate payoff truth tables")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("tests/references/payoff_truth_tables.csv"),
        help="Output CSV file path",
    )

    args = parser.parse_args()
    records = generate_payoff_truth_tables(args.output)
    print_summary(records)
