#!/usr/bin/env python3
"""
Fair Cap and Participation Rate Calculation Demo.

This example demonstrates how to calculate fair cap and participation rates
given an option budget. These calculations answer the actuarial question:

    "Given a 3% option budget, what cap rate (or participation rate) is fair?"

Key Concepts:
- Option budget: The % of premium allocated to purchasing index options
- Fair cap: Maximum return cap achievable with the given budget
- Fair participation: % participation in index gains achievable with budget

Usage:
    python examples/01_fair_rates.py          # Interactive with plots
    python examples/01_fair_rates.py --ci     # CI mode (no plots)

See Also:
    - docs/guides/pricing_fia.md
    - METHODOLOGY.md Section 3.1 (FIA Cap Replication)
"""

import argparse
import sys
from dataclasses import dataclass

# Add src to path if running as script
sys.path.insert(0, "src")

from annuity_pricing import FIAPricer, FIAProduct, MarketParams


@dataclass
class FairRateResult:
    """Results from fair rate calculation."""

    option_budget_pct: float
    fair_cap: float
    fair_participation: float
    volatility: float


def calculate_fair_rates(
    spot: float = 100.0,
    risk_free_rate: float = 0.045,
    dividend_yield: float = 0.02,
    volatility: float = 0.18,
    option_budget_pct: float = 0.03,
    term_years: float = 1.0,
    premium: float = 100_000.0,
) -> FairRateResult:
    """
    Calculate fair cap and participation rates for given market conditions.

    Parameters
    ----------
    spot : float
        Current index level
    risk_free_rate : float
        Risk-free rate (annualized)
    dividend_yield : float
        Dividend yield (annualized)
    volatility : float
        Implied volatility (annualized)
    option_budget_pct : float
        Option budget as % of premium (e.g., 0.03 = 3%)
    term_years : float
        Option term in years
    premium : float
        Premium amount

    Returns
    -------
    FairRateResult
        Fair cap and participation rates
    """
    market = MarketParams(
        spot=spot,
        risk_free_rate=risk_free_rate,
        dividend_yield=dividend_yield,
        volatility=volatility,
    )
    pricer = FIAPricer(market_params=market)

    # Create a minimal product (we just need the pricer methods)
    product = FIAProduct(
        company_name="Demo",
        product_name="Fair Rate Demo",
        product_group="FIA",
        status="current",
        cap_rate=0.10,  # Will be overridden by calculation
    )

    # Calculate option budget in dollars
    option_budget = option_budget_pct * premium

    # Use internal methods to calculate fair rates
    fair_cap = pricer._solve_fair_cap(term_years, option_budget, premium)
    fair_participation = pricer._solve_fair_participation(term_years, option_budget, premium)

    return FairRateResult(
        option_budget_pct=option_budget_pct,
        fair_cap=fair_cap,
        fair_participation=fair_participation,
        volatility=volatility,
    )


def volatility_sensitivity(
    vol_range: tuple[float, float] = (0.10, 0.35),
    vol_steps: int = 6,
    option_budget_pct: float = 0.03,
) -> list[FairRateResult]:
    """
    Analyze how volatility affects fair rates.

    Higher volatility → options more expensive → lower fair cap/participation.

    Parameters
    ----------
    vol_range : tuple
        (min_vol, max_vol) range to analyze
    vol_steps : int
        Number of volatility levels to calculate
    option_budget_pct : float
        Option budget as % of premium

    Returns
    -------
    list[FairRateResult]
        Fair rates at each volatility level
    """
    import numpy as np

    vols = np.linspace(vol_range[0], vol_range[1], vol_steps)
    results = []

    for vol in vols:
        result = calculate_fair_rates(
            volatility=vol,
            option_budget_pct=option_budget_pct,
        )
        results.append(result)

    return results


def print_results(result: FairRateResult) -> None:
    """Print fair rate calculation results."""
    print("\n" + "=" * 60)
    print("FAIR RATE CALCULATION RESULTS")
    print("=" * 60)
    print(f"\nMarket Conditions:")
    print(f"  Volatility:     {result.volatility:.1%}")
    print(f"  Option Budget:  {result.option_budget_pct:.1%} of premium")
    print(f"\nFair Rates (what the insurer can offer):")
    print(f"  Fair Cap Rate:          {result.fair_cap:.2%}")
    print(f"  Fair Participation:     {result.fair_participation:.2%}")
    print("\nInterpretation:")
    print(f"  - With {result.option_budget_pct:.1%} option budget, insurer can offer:")
    print(f"    • A {result.fair_cap:.1%} cap on a point-to-point strategy, OR")
    print(f"    • {result.fair_participation:.0%} participation rate (no cap)")


def print_sensitivity_table(results: list[FairRateResult]) -> None:
    """Print volatility sensitivity analysis as a table."""
    print("\n" + "=" * 60)
    print("VOLATILITY SENSITIVITY ANALYSIS")
    print("=" * 60)
    print(f"\nOption Budget: {results[0].option_budget_pct:.1%}")
    print("\n  Volatility   Fair Cap   Fair Participation")
    print("  " + "-" * 44)

    for r in results:
        print(f"    {r.volatility:5.1%}      {r.fair_cap:6.2%}        {r.fair_participation:5.0%}")

    print("\n* Insight: Higher volatility -> more expensive options -> lower fair rates")


def plot_sensitivity(results: list[FairRateResult]) -> None:
    """Plot volatility sensitivity (requires matplotlib)."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("\nNote: matplotlib not installed, skipping plot")
        return

    vols = [r.volatility * 100 for r in results]
    caps = [r.fair_cap * 100 for r in results]
    parts = [r.fair_participation * 100 for r in results]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Fair Cap vs Volatility
    ax1.plot(vols, caps, "b-o", linewidth=2, markersize=8)
    ax1.set_xlabel("Volatility (%)", fontsize=12)
    ax1.set_ylabel("Fair Cap Rate (%)", fontsize=12)
    ax1.set_title("Fair Cap Rate vs Volatility", fontsize=14)
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(0, max(caps) * 1.1)

    # Fair Participation vs Volatility
    ax2.plot(vols, parts, "r-o", linewidth=2, markersize=8)
    ax2.set_xlabel("Volatility (%)", fontsize=12)
    ax2.set_ylabel("Fair Participation Rate (%)", fontsize=12)
    ax2.set_title("Fair Participation Rate vs Volatility", fontsize=14)
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(0, max(parts) * 1.1)

    plt.suptitle(
        f"FIA Fair Rates Sensitivity (Option Budget: {results[0].option_budget_pct:.1%})",
        fontsize=14,
        fontweight="bold",
    )
    plt.tight_layout()
    plt.savefig("examples/fair_rates_sensitivity.png", dpi=150)
    print("\nPlot saved to: examples/fair_rates_sensitivity.png")
    plt.show()


def main() -> None:
    """Run fair rate calculation demo."""
    parser = argparse.ArgumentParser(description="Fair Cap/Participation Rate Demo")
    parser.add_argument("--ci", action="store_true", help="CI mode (no interactive plots)")
    parser.add_argument(
        "--budget", type=float, default=0.03, help="Option budget as decimal (default: 0.03)"
    )
    parser.add_argument("--vol", type=float, default=0.18, help="Volatility (default: 0.18)")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("FIA FAIR RATE CALCULATION DEMO")
    print("=" * 60)
    print("\nThis demo shows how to calculate 'fair' cap and participation")
    print("rates given an option budget and market conditions.")

    # Single calculation
    result = calculate_fair_rates(
        option_budget_pct=args.budget,
        volatility=args.vol,
    )
    print_results(result)

    # Sensitivity analysis
    sensitivity_results = volatility_sensitivity(option_budget_pct=args.budget)
    print_sensitivity_table(sensitivity_results)

    # Plot (only if not in CI mode)
    if not args.ci:
        plot_sensitivity(sensitivity_results)

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
